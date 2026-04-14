from datetime import datetime, time
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_language: Mapped[str] = mapped_column(String(64), default="English")
    native_language: Mapped[str] = mapped_column(String(64), default="Uzbek")
    daily_limit: Mapped[int] = mapped_column(Integer, default=10)
    review_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    words: Mapped[list["UserWord"]] = relationship("UserWord", back_populates="user")


class GlobalDictionary(Base):
    """Global cache for word translations and contexts."""

    __tablename__ = "global_dictionary"
    __table_args__ = (UniqueConstraint("word", "language", name="uq_word_language"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    variants_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: list of {context, translation}
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user_words: Mapped[list["UserWord"]] = relationship("UserWord", back_populates="global_entry")


class UserWord(Base):
    __tablename__ = "user_words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    global_word_id: Mapped[int] = mapped_column(Integer, ForeignKey("global_dictionary.id"), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    native_translation: Mapped[str] = mapped_column(String(256), nullable=False)
    srs_interval: Mapped[int] = mapped_column(Integer, default=1)  # days until next review
    repetition_count: Mapped[int] = mapped_column(Integer, default=0)
    easiness_factor: Mapped[float] = mapped_column(default=2.5)
    next_review: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="words")
    global_entry: Mapped["GlobalDictionary"] = relationship("GlobalDictionary", back_populates="user_words")
    translation_variants: Mapped[list["TranslationVariant"]] = relationship(
        "TranslationVariant", back_populates="user_word"
    )


class TranslationVariant(Base):
    """Cache for AI-checked user translation attempts."""

    __tablename__ = "translation_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_word_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_words.id"), nullable=False)
    user_input: Mapped[str] = mapped_column(String(512), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user_word: Mapped["UserWord"] = relationship("UserWord", back_populates="translation_variants")


class ReviewSession(Base):
    """Tracks an active review session for a user."""

    __tablename__ = "review_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["ReviewItem"]] = relationship("ReviewItem", back_populates="session")


class ReviewItem(Base):
    """A single word within a review session."""

    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("review_sessions.id"), nullable=False)
    user_word_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_words.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False)  # "target_to_native" or "native_to_target"
    user_answer: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    grade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    session: Mapped["ReviewSession"] = relationship("ReviewSession", back_populates="items")
