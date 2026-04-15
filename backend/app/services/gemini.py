"""Google Gemini API integration for translation and verification."""

import json
import logging
from typing import Optional

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _model = genai.GenerativeModel(settings.GEMINI_MODEL)
    return _model


async def get_word_variants(word: str, target_language: str, native_language: str) -> list[dict]:
    """
    Fetch the most common translations and contexts for a word using Gemini.

    Returns a list of dicts: [{context, translation, example}, ...]
    """
    model = _get_model()
    prompt = (
        f"Provide the top 5 most common meanings/translations of the {target_language} word '{word}' "
        f"into {native_language}. For each meaning include: a short context label (e.g. 'direction', "
        f"'correct/right'), the translation, and one example sentence in {target_language}. "
        f"Respond ONLY with a valid JSON array like: "
        f'[{{"context": "...", "translation": "...", "example": "..."}}]'
    )
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        variants = json.loads(text)
        return variants if isinstance(variants, list) else []
    except Exception as exc:
        logger.error("Gemini get_word_variants error: %s", exc)
        return []


async def verify_translation(
    word: str,
    context: str,
    target_language: str,
    native_language: str,
    user_translation: str,
) -> Optional[bool]:
    """
    Ask Gemini whether `user_translation` is a correct translation of `word`
    in the given context.

    Returns True/False, or None if the API call fails.
    """
    model = _get_model()
    prompt = (
        f"Is '{user_translation}' a correct {native_language} translation of the {target_language} word "
        f"'{word}' when used in the context of '{context}'? "
        f"Answer ONLY with a single word: yes or no."
    )
    try:
        response = model.generate_content(prompt)
        answer = response.text.strip().lower()
        return answer.startswith("yes")
    except Exception as exc:
        logger.error("Gemini verify_translation error: %s", exc)
        return None


async def translate_word(word: str, from_language: str, to_language: str, context: str) -> Optional[str]:
    """
    Translate a single word from one language to another given a context.

    Used when the user switches target languages (background re-translation).
    """
    model = _get_model()
    prompt = (
        f"Translate the {from_language} word '{word}' (context: {context}) into {to_language}. "
        f"Respond ONLY with the translated word or short phrase, nothing else."
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        logger.error("Gemini translate_word error: %s", exc)
        return None
