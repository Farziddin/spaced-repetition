from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    GlobalDictionary,
    ReviewItem,
    ReviewSession,
    TranslationVariant,
    User,
    UserWord,
)
from app.schemas import (
    AnswerResult,
    AnswerSubmit,
    GradeSubmit,
    ReviewItemOut,
    SessionReport,
)
from app.services.gemini import verify_translation
from app.services.srs import calculate_next_review, get_review_direction
from app.tasks import auto_grade_task

router = APIRouter(prefix="/reviews", tags=["reviews"])


async def _get_user(telegram_id: int, db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/start", response_model=list[ReviewItemOut])
async def start_review(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """
    Start a new review session for a user.
    Returns the list of review items (words due today).
    """
    user = await _get_user(telegram_id, db)

    # Close any stale active sessions
    result = await db.execute(
        select(ReviewSession).where(
            ReviewSession.user_id == user.id,
            ReviewSession.is_active == True,  # noqa: E712
        )
    )
    for stale in result.scalars().all():
        stale.is_active = False
        stale.finished_at = datetime.now(timezone.utc)

    # Get words due for review (up to daily_limit)
    result = await db.execute(
        select(UserWord, GlobalDictionary)
        .join(GlobalDictionary, UserWord.global_word_id == GlobalDictionary.id)
        .where(
            UserWord.user_id == user.id,
            UserWord.next_review <= datetime.now(timezone.utc),
        )
        .limit(user.daily_limit)
    )
    due_words = result.all()

    if not due_words:
        raise HTTPException(status_code=404, detail="No words due for review")

    # Create session
    session = ReviewSession(user_id=user.id)
    db.add(session)
    await db.flush()

    items_out = []
    for uw, gd in due_words:
        direction = get_review_direction(uw.repetition_count)
        item = ReviewItem(
            session_id=session.id,
            user_word_id=uw.id,
            direction=direction,
        )
        db.add(item)
        await db.flush()

        prompt = gd.word if direction == "target_to_native" else uw.native_translation
        items_out.append(
            ReviewItemOut(
                id=item.id,
                session_id=session.id,
                user_word_id=uw.id,
                word=gd.word,
                language=gd.language,
                context=uw.context,
                direction=direction,
                prompt=prompt,
                hint=f"({uw.context})",
            )
        )

    await db.commit()
    return items_out


@router.post("/answer", response_model=AnswerResult)
async def submit_answer(payload: AnswerSubmit, db: AsyncSession = Depends(get_db)):
    """
    Submit a user's answer for a review item.
    Checks against cached variants first, then Gemini API.
    """
    result = await db.execute(
        select(ReviewItem)
        .join(ReviewSession, ReviewItem.session_id == ReviewSession.id)
        .where(ReviewItem.id == payload.item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    result = await db.execute(select(UserWord).where(UserWord.id == item.user_word_id))
    user_word = result.scalar_one_or_none()

    result = await db.execute(
        select(GlobalDictionary).where(GlobalDictionary.id == user_word.global_word_id)
    )
    global_entry = result.scalar_one_or_none()

    # Determine correct answer
    if item.direction == "target_to_native":
        correct_answer = user_word.native_translation
    else:
        correct_answer = global_entry.word

    user_input_lower = payload.user_answer.strip().lower()
    correct_lower = correct_answer.strip().lower()

    # 1. Check exact match
    if user_input_lower == correct_lower:
        is_correct = True
        cached = True
    else:
        # 2. Check TranslationVariants cache
        result = await db.execute(
            select(TranslationVariant).where(
                TranslationVariant.user_word_id == user_word.id,
                TranslationVariant.user_input == user_input_lower,
            )
        )
        cached_variant = result.scalar_one_or_none()

        if cached_variant is not None:
            is_correct = cached_variant.is_correct
            cached = True
        else:
            # 3. Ask Gemini
            result = await db.execute(
                select(User).where(User.id == user_word.user_id)
            )
            user = result.scalar_one_or_none()

            gemini_result = await verify_translation(
                word=global_entry.word,
                context=user_word.context,
                target_language=global_entry.language,
                native_language=user.native_language if user else "Uzbek",
                user_translation=payload.user_answer,
            )
            is_correct = bool(gemini_result) if gemini_result is not None else False
            cached = False

            # Save to cache
            variant = TranslationVariant(
                user_word_id=user_word.id,
                user_input=user_input_lower,
                is_correct=is_correct,
            )
            db.add(variant)

    # Update item
    item.user_answer = payload.user_answer
    item.is_correct = is_correct
    item.answered_at = datetime.now(timezone.utc)

    await db.commit()

    # Schedule auto-grade task (10-minute timeout)
    auto_grade_task.apply_async(
        args=[item.id],
        countdown=600,
    )

    return AnswerResult(
        is_correct=is_correct,
        correct_answer=correct_answer,
        cached=cached,
    )


@router.post("/grade")
async def submit_grade(payload: GradeSubmit, db: AsyncSession = Depends(get_db)):
    """
    Submit a grade (1-5) for a review item and update SRS parameters.
    """
    result = await db.execute(select(ReviewItem).where(ReviewItem.id == payload.item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    if item.grade is not None:
        return {"detail": "Already graded"}

    item.grade = payload.grade

    result = await db.execute(select(UserWord).where(UserWord.id == item.user_word_id))
    user_word = result.scalar_one_or_none()

    srs = calculate_next_review(
        grade=payload.grade,
        repetition_count=user_word.repetition_count,
        easiness_factor=user_word.easiness_factor,
        interval=user_word.srs_interval,
    )
    user_word.srs_interval = srs.interval
    user_word.repetition_count = srs.repetition_count
    user_word.easiness_factor = srs.easiness_factor
    user_word.next_review = srs.next_review

    await db.commit()
    return {"detail": "Graded successfully", "next_review": srs.next_review.isoformat()}


@router.post("/finish/{session_id}", response_model=SessionReport)
async def finish_session(session_id: int, db: AsyncSession = Depends(get_db)):
    """
    Finish a review session and return the session report.
    """
    result = await db.execute(
        select(ReviewSession).where(ReviewSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.is_active = False
    session.finished_at = datetime.now(timezone.utc)

    # Build report
    result = await db.execute(
        select(ReviewItem, UserWord, GlobalDictionary)
        .join(UserWord, ReviewItem.user_word_id == UserWord.id)
        .join(GlobalDictionary, UserWord.global_word_id == GlobalDictionary.id)
        .where(ReviewItem.session_id == session_id)
    )
    rows = result.all()

    remembered = []
    forgotten = []
    for item, uw, gd in rows:
        entry = {
            "word": gd.word,
            "context": uw.context,
            "correct_answer": uw.native_translation,
            "user_answer": item.user_answer,
        }
        if item.is_correct:
            remembered.append(entry)
        else:
            forgotten.append(entry)

    await db.commit()
    return SessionReport(session_id=session_id, remembered=remembered, forgotten=forgotten)
