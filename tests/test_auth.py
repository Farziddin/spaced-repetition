"""Tests for the Telegram WebApp authentication service."""

import hmac
import hashlib
import json
import urllib.parse

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def _make_init_data(user: dict, bot_token: str) -> str:
    """Helper to construct a valid Telegram initData string."""
    user_str = json.dumps(user, separators=(',', ':'))
    params = {"user": user_str, "auth_date": "1700000000"}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    params["hash"] = hash_value
    return urllib.parse.urlencode(params)


class TestVerifyTelegramWebappData:
    def test_valid_data_returns_user(self, monkeypatch):
        bot_token = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        user = {"id": 123456789, "first_name": "Test", "username": "testuser"}

        from app.config import settings as app_settings
        monkeypatch.setattr(app_settings, "TELEGRAM_BOT_TOKEN", bot_token)

        init_data = _make_init_data(user, bot_token)

        from app.services.auth import verify_telegram_webapp_data
        result = verify_telegram_webapp_data(init_data)

        assert result is not None
        assert result["id"] == user["id"]
        assert result["username"] == user["username"]

    def test_invalid_hash_returns_none(self, monkeypatch):
        bot_token = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        user = {"id": 123456789, "first_name": "Test"}

        from app.config import settings as app_settings
        monkeypatch.setattr(app_settings, "TELEGRAM_BOT_TOKEN", bot_token)

        # Create init data with wrong bot token
        init_data = _make_init_data(user, "wrong_token")

        from app.services.auth import verify_telegram_webapp_data
        result = verify_telegram_webapp_data(init_data)

        assert result is None

    def test_missing_hash_returns_none(self, monkeypatch):
        from app.config import settings as app_settings
        monkeypatch.setattr(app_settings, "TELEGRAM_BOT_TOKEN", "some_token")

        from app.services.auth import verify_telegram_webapp_data
        result = verify_telegram_webapp_data("user=%7B%22id%22%3A1%7D&auth_date=1700000000")

        assert result is None

    def test_empty_string_returns_none(self, monkeypatch):
        from app.config import settings as app_settings
        monkeypatch.setattr(app_settings, "TELEGRAM_BOT_TOKEN", "some_token")

        from app.services.auth import verify_telegram_webapp_data
        result = verify_telegram_webapp_data("")

        assert result is None
