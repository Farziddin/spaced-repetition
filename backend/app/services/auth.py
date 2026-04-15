"""Telegram WebApp authentication helpers."""

import hashlib
import hmac
import json
import urllib.parse
from typing import Optional

from app.config import settings


def verify_telegram_webapp_data(init_data: str) -> Optional[dict]:
    """
    Validate the Telegram WebApp initData string.

    Returns the parsed user dict if valid, None otherwise.
    See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        hash_value = parsed.pop("hash", None)
        if not hash_value:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            settings.TELEGRAM_BOT_TOKEN.encode(),
            hashlib.sha256,
        ).digest()

        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, hash_value):
            return None

        user_str = parsed.get("user")
        if not user_str:
            return None

        return json.loads(user_str)
    except Exception:
        return None
