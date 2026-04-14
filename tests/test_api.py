"""Integration tests for the FastAPI backend."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Override settings before importing app
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/spaced_repetition_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test_token")
os.environ.setdefault("GEMINI_API_KEY", "test_key")
os.environ.setdefault("SECRET_KEY", "test-secret")

from app.database import Base, get_db
from app.main import app

# Create a test engine
TEST_DATABASE_URL = os.environ["DATABASE_URL"]
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_user(client):
    payload = {
        "telegram_id": 111111111,
        "username": "testuser",
        "target_language": "English",
        "native_language": "Uzbek",
        "daily_limit": 10,
    }
    resp = await client.post("/users/", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["telegram_id"] == 111111111
    assert data["target_language"] == "English"


@pytest.mark.asyncio
async def test_create_duplicate_user(client):
    payload = {
        "telegram_id": 111111111,
        "username": "testuser",
    }
    resp = await client.post("/users/", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_user(client):
    resp = await client.get("/users/111111111")
    assert resp.status_code == 200
    assert resp.json()["telegram_id"] == 111111111


@pytest.mark.asyncio
async def test_get_nonexistent_user(client):
    resp = await client.get("/users/999999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_user_settings(client):
    payload = {"daily_limit": 20, "target_language": "Spanish"}
    resp = await client.patch("/users/111111111", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_limit"] == 20
    assert data["target_language"] == "Spanish"


@pytest.mark.asyncio
async def test_init_webapp_user(client):
    resp = await client.get("/users/me/init", params={"telegram_id": 222222222, "username": "newuser"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["telegram_id"] == 222222222

    # Second call should return same user (not create a new one)
    resp2 = await client.get("/users/me/init", params={"telegram_id": 222222222})
    assert resp2.status_code == 200
    assert resp2.json()["id"] == data["id"]


@pytest.mark.asyncio
async def test_no_words_due(client):
    """User with no words should get 404 on review start."""
    resp = await client.post("/reviews/start", params={"telegram_id": 111111111})
    assert resp.status_code == 404
