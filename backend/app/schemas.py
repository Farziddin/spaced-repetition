from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    target_language: str = "English"
    native_language: str = "Uzbek"
    daily_limit: int = Field(default=10, ge=1, le=100)
    review_time: Optional[time] = None


class UserUpdate(BaseModel):
    target_language: Optional[str] = None
    native_language: Optional[str] = None
    daily_limit: Optional[int] = Field(default=None, ge=1, le=100)
    review_time: Optional[time] = None


class UserOut(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    target_language: str
    native_language: str
    daily_limit: int
    review_time: Optional[time]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Word / dictionary schemas
# ---------------------------------------------------------------------------

class WordVariant(BaseModel):
    context: str
    translation: str
    example: Optional[str] = None


class WordLookupRequest(BaseModel):
    word: str
    target_language: str
    native_language: str


class WordLookupResponse(BaseModel):
    word: str
    language: str
    variants: list[WordVariant]
    cached: bool


class UserWordCreate(BaseModel):
    word: str
    target_language: str
    context: str
    native_translation: str


class UserWordOut(BaseModel):
    id: int
    word: str
    language: str
    context: str
    native_translation: str
    srs_interval: int
    repetition_count: int
    next_review: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Review schemas
# ---------------------------------------------------------------------------

class ReviewItemOut(BaseModel):
    id: int
    session_id: int
    user_word_id: int
    word: str
    language: str
    context: str
    direction: str          # "target_to_native" or "native_to_target"
    prompt: str             # The word to display as prompt
    hint: str               # Context hint shown in parentheses

    model_config = {"from_attributes": True}


class AnswerSubmit(BaseModel):
    item_id: int
    user_answer: str


class AnswerResult(BaseModel):
    is_correct: bool
    correct_answer: str
    cached: bool


class GradeSubmit(BaseModel):
    item_id: int
    grade: int = Field(ge=1, le=5)


class SessionReport(BaseModel):
    session_id: int
    remembered: list[dict]
    forgotten: list[dict]


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------

class TranslationVerifyRequest(BaseModel):
    user_word_id: int
    user_input: str
