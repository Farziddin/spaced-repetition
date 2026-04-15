# Spaced Repetition — Telegram Bot & WebApp

A Telegram bot and React WebApp for memorizing vocabulary using the **Spaced Repetition System (SM-2 algorithm)**, powered by Google Gemini AI.

---

## Architecture

| Component | Technology |
|-----------|-----------|
| Frontend (Telegram WebApp) | React 18, TailwindCSS, Vite |
| Backend API | Python, FastAPI, SQLAlchemy |
| Telegram Bot | Python, Aiogram 3.x |
| Database | PostgreSQL 16 |
| Cache & Tasks | Redis 7, Celery |
| AI | Google Gemini 1.5 Flash |
| Infrastructure | Docker, Docker Compose |
| CI/CD | GitHub Actions |

---

## Features

### WebApp (Settings & Word Entry)
- Configure **Target Language**, **daily word limit**, and **review time**
- Add new words with AI-powered polysemy resolution:
  - Fetches multiple contexts/translations from Gemini API
  - Results are cached globally to reduce API costs
  - User selects the specific meaning to learn

### Telegram Bot (Review & SRS)
- Daily notifications at the configured review time
- Review flow:
  - **First 3 repetitions**: always prompt Target Language → translate to Native Language
  - **After 3 repetitions**: 50/50 random direction
  - Context hint shown in parentheses: e.g. `right (direction)`
- User rates recall quality on a **1–5 scale**
- **Auto-grading**: if no grade submitted within 10 minutes, Celery assigns grade 4
- **Session report**: lists forgotten and remembered words at the end

### AI Translation Verification
1. Exact match check against known correct answers
2. Check `TranslationVariants` cache (previously AI-verified answers)
3. Gemini API call as fallback — result is cached for future use

### Language Switching
- Changing the target language triggers a background Celery task
- All existing words are re-translated asynchronously
- SRS progress (intervals, repetition counts) is preserved

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- A Google Gemini API Key

### Setup

```bash
# Clone the repository
git clone https://github.com/Farziddin/spaced-repetition.git
cd spaced-repetition

# Create environment file
cp .env.example .env
# Edit .env and fill in TELEGRAM_BOT_TOKEN and GEMINI_API_KEY

# Start all services
docker compose up --build
```

Services:
- **Frontend WebApp**: http://localhost:80
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## Database Schema

| Table | Key Columns |
|-------|------------|
| `users` | `telegram_id`, `target_language`, `daily_limit`, `review_time` |
| `global_dictionary` | `word`, `language`, `variants_json` (global cache) |
| `user_words` | `user_id`, `global_word_id`, `context`, `srs_interval`, `repetition_count`, `next_review` |
| `translation_variants` | `user_word_id`, `user_input`, `is_correct` (AI check cache) |
| `review_sessions` | `user_id`, `is_active`, `started_at`, `finished_at` |
| `review_items` | `session_id`, `user_word_id`, `direction`, `user_answer`, `grade` |

---

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r backend/requirements.txt pytest pytest-asyncio httpx

# Run unit tests (no database required)
pytest tests/test_srs.py tests/test_auth.py -v

# Run all tests (requires PostgreSQL and Redis)
pytest tests/ -v
```

### Project Structure

```
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   ├── database.py      # Async SQLAlchemy engine
│   │   ├── tasks.py         # Celery tasks
│   │   ├── routers/         # API route handlers
│   │   └── services/        # SRS algorithm, Gemini AI, auth
│   └── requirements.txt
├── bot/               # Aiogram 3.x Telegram bot
│   ├── main.py
│   ├── bot.py
│   ├── handlers/      # /start, /review handlers
│   ├── keyboards/     # Inline keyboards
│   └── services.py    # HTTP client for backend API
├── frontend/          # React + TailwindCSS WebApp
│   └── src/
│       ├── App.jsx
│       └── components/  # Settings, AddWord, WordList
├── tests/             # Pytest test suite
├── docker-compose.yml
└── .github/workflows/ci.yml
```
