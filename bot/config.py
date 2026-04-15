from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str = ""
    REDIS_URL: str = "redis://redis:6379/0"
    BACKEND_URL: str = "http://backend:8000"
    FRONTEND_URL: str = "http://frontend:80"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
