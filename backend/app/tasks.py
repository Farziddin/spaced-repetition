"""Celery application and task definitions."""

import asyncio
import logging
from datetime import datetime, timezone

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "spaced_repetition",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "send-daily-notifications": {
            "task": "app.tasks.send_daily_notifications",
            "schedule": crontab(minute=0),  # runs every hour; task filters by user review_time
        },
    },
)


def _run_async(coro):
    """Helper to run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.auto_grade_task")
def auto_grade_task(review_item_id: int):
    """
    Automatically assign grade 4 to a review item if the user has not graded
    it within 10 minutes of answering.
    """

    async def _inner():
        from sqlalchemy import select

        from app.database import AsyncSessionLocal
        from app.models import ReviewItem, UserWord
        from app.services.srs import calculate_next_review

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(ReviewItem).where(ReviewItem.id == review_item_id))
            item = result.scalar_one_or_none()
            if not item or item.grade is not None:
                return  # Already graded

            # Automatically assign grade 4 ("correct with minor hesitation") as the
            # neutral default when the user does not submit a manual grade within the
            # 10-minute timeout. Grade 4 advances the SRS interval without penalising
            # the user for the timeout.
            item.grade = 4

            result = await db.execute(select(UserWord).where(UserWord.id == item.user_word_id))
            user_word = result.scalar_one_or_none()
            if user_word:
                srs = calculate_next_review(
                    grade=4,
                    repetition_count=user_word.repetition_count,
                    easiness_factor=user_word.easiness_factor,
                    interval=user_word.srs_interval,
                )
                user_word.srs_interval = srs.interval
                user_word.repetition_count = srs.repetition_count
                user_word.easiness_factor = srs.easiness_factor
                user_word.next_review = srs.next_review

            await db.commit()
            logger.info("Auto-graded review item %s with grade 4", review_item_id)

    _run_async(_inner())


@celery_app.task(name="app.tasks.send_daily_notifications")
def send_daily_notifications():
    """
    Check which users have their review_time set to the current hour and
    send them a Telegram notification to start their review.
    """

    async def _inner():
        import aiogram
        from sqlalchemy import select

        from app.database import AsyncSessionLocal
        from app.models import User, UserWord

        bot = aiogram.Bot(token=settings.TELEGRAM_BOT_TOKEN)
        now_hour = datetime.now(timezone.utc).hour
        now_minute = datetime.now(timezone.utc).minute

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            for user in users:
                if user.review_time is None:
                    continue
                if user.review_time.hour != now_hour or user.review_time.minute != now_minute:
                    continue

                # Check if there are words due
                due = await db.execute(
                    select(UserWord).where(
                        UserWord.user_id == user.id,
                        UserWord.next_review <= datetime.now(timezone.utc),
                    )
                )
                if not due.scalars().first():
                    continue

                try:
                    await bot.send_message(
                        user.telegram_id,
                        "🧠 Time for your spaced repetition review! Shall we start?\n"
                        "Use /review to begin your session.",
                    )
                except Exception as exc:
                    logger.warning("Could not notify user %s: %s", user.telegram_id, exc)

        await bot.session.close()

    _run_async(_inner())


@celery_app.task(name="app.tasks.retranslate_words_task")
def retranslate_words_task(user_id: int, old_language: str, new_language: str):
    """
    Asynchronously re-translate all of a user's words when they switch target languages.
    SRS progress is preserved.
    """

    async def _inner():
        from sqlalchemy import select

        from app.database import AsyncSessionLocal
        from app.models import GlobalDictionary, User, UserWord
        from app.services.gemini import translate_word

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return

            result = await db.execute(
                select(UserWord, GlobalDictionary)
                .join(GlobalDictionary, UserWord.global_word_id == GlobalDictionary.id)
                .where(UserWord.user_id == user_id, GlobalDictionary.language == old_language)
            )
            rows = result.all()

            for uw, gd in rows:
                translated = await translate_word(
                    word=gd.word,
                    from_language=old_language,
                    to_language=new_language,
                    context=uw.context,
                )
                if translated:
                    uw.native_translation = translated

            await db.commit()
            logger.info(
                "Retranslated %d words for user %d from %s to %s",
                len(rows),
                user_id,
                old_language,
                new_language,
            )

    _run_async(_inner())
