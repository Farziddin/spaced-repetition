from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/spaced_repetition"
    REDIS_URL: str = "redis://redis:6379/0"
    TELEGRAM_BOT_TOKEN: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    SECRET_KEY: str = "change-me-in-production"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
