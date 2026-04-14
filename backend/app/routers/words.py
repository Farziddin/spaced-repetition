import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import GlobalDictionary, User, UserWord
from app.schemas import (
    UserWordCreate,
    UserWordOut,
    WordLookupRequest,
    WordLookupResponse,
    WordVariant,
)
from app.services.gemini import get_word_variants

router = APIRouter(prefix="/words", tags=["words"])


@router.post("/lookup", response_model=WordLookupResponse)
async def lookup_word(payload: WordLookupRequest, db: AsyncSession = Depends(get_db)):
    """
    Retrieve contexts/translations for a word.
    First checks the global cache; if not found, fetches from Gemini API.
    """
    word_lower = payload.word.strip().lower()

    # Check global cache
    result = await db.execute(
        select(GlobalDictionary).where(
            GlobalDictionary.word == word_lower,
            GlobalDictionary.language == payload.target_language,
        )
    )
    cached_entry = result.scalar_one_or_none()

    if cached_entry:
        variants_data = json.loads(cached_entry.variants_json)
        variants = [WordVariant(**v) for v in variants_data]
        return WordLookupResponse(
            word=word_lower,
            language=payload.target_language,
            variants=variants,
            cached=True,
        )

    # Fetch from Gemini
    raw_variants = await get_word_variants(
        word_lower, payload.target_language, payload.native_language
    )
    if not raw_variants:
        raise HTTPException(status_code=502, detail="Could not retrieve translations from AI")

    # Save to global cache
    entry = GlobalDictionary(
        word=word_lower,
        language=payload.target_language,
        variants_json=json.dumps(raw_variants, ensure_ascii=False),
    )
    db.add(entry)
    await db.commit()

    variants = [WordVariant(**v) for v in raw_variants]
    return WordLookupResponse(
        word=word_lower,
        language=payload.target_language,
        variants=variants,
        cached=False,
    )


@router.post("/add", response_model=UserWordOut, status_code=201)
async def add_user_word(payload: UserWordCreate, telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Add a word with the selected context to the user's personal word list."""
    # Get user
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    word_lower = payload.word.strip().lower()

    # Ensure global dictionary entry exists
    result = await db.execute(
        select(GlobalDictionary).where(
            GlobalDictionary.word == word_lower,
            GlobalDictionary.language == payload.target_language,
        )
    )
    global_entry = result.scalar_one_or_none()

    if not global_entry:
        # Create a minimal entry
        global_entry = GlobalDictionary(
            word=word_lower,
            language=payload.target_language,
            variants_json=json.dumps(
                [{"context": payload.context, "translation": payload.native_translation}],
                ensure_ascii=False,
            ),
        )
        db.add(global_entry)
        await db.flush()

    # Check for duplicate
    result = await db.execute(
        select(UserWord).where(
            UserWord.user_id == user.id,
            UserWord.global_word_id == global_entry.id,
            UserWord.context == payload.context,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Word with this context already added")

    user_word = UserWord(
        user_id=user.id,
        global_word_id=global_entry.id,
        context=payload.context,
        native_translation=payload.native_translation,
    )
    db.add(user_word)
    await db.commit()
    await db.refresh(user_word)
    await db.refresh(global_entry)

    return UserWordOut(
        id=user_word.id,
        word=global_entry.word,
        language=global_entry.language,
        context=user_word.context,
        native_translation=user_word.native_translation,
        srs_interval=user_word.srs_interval,
        repetition_count=user_word.repetition_count,
        next_review=user_word.next_review,
        created_at=user_word.created_at,
    )


@router.get("/", response_model=list[UserWordOut])
async def list_user_words(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """List all words for a user."""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.execute(
        select(UserWord, GlobalDictionary)
        .join(GlobalDictionary, UserWord.global_word_id == GlobalDictionary.id)
        .where(UserWord.user_id == user.id)
    )
    rows = result.all()

    return [
        UserWordOut(
            id=uw.id,
            word=gd.word,
            language=gd.language,
            context=uw.context,
            native_translation=uw.native_translation,
            srs_interval=uw.srs_interval,
            repetition_count=uw.repetition_count,
            next_review=uw.next_review,
            created_at=uw.created_at,
        )
        for uw, gd in rows
    ]
