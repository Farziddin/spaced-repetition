import logging
from typing import Optional

import httpx

from bot.config import settings

logger = logging.getLogger(__name__)

BASE_URL = settings.BACKEND_URL


async def start_review(telegram_id: int) -> Optional[list[dict]]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post(f"/reviews/start?telegram_id={telegram_id}")
        if resp.status_code == 200:
            return resp.json()
        logger.warning("start_review failed: %s %s", resp.status_code, resp.text)
        return None


async def submit_answer(item_id: int, user_answer: str) -> Optional[dict]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post(
            "/reviews/answer",
            json={"item_id": item_id, "user_answer": user_answer},
        )
        if resp.status_code == 200:
            return resp.json()
        logger.warning("submit_answer failed: %s %s", resp.status_code, resp.text)
        return None


async def submit_grade(item_id: int, grade: int) -> Optional[dict]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post(
            "/reviews/grade",
            json={"item_id": item_id, "grade": grade},
        )
        if resp.status_code == 200:
            return resp.json()
        logger.warning("submit_grade failed: %s %s", resp.status_code, resp.text)
        return None


async def finish_session(session_id: int) -> Optional[dict]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        resp = await client.post(f"/reviews/finish/{session_id}")
        if resp.status_code == 200:
            return resp.json()
        logger.warning("finish_session failed: %s %s", resp.status_code, resp.text)
        return None


async def get_or_create_user(telegram_id: int, username: Optional[str] = None) -> Optional[dict]:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        params = {"telegram_id": telegram_id}
        if username:
            params["username"] = username
        resp = await client.get("/users/me/init", params=params)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("get_or_create_user failed: %s %s", resp.status_code, resp.text)
        return None
