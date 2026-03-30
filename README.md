# VocKO Vocabulary Learning Platform

## Project structure

- `server/` — FastAPI backend (MongoDB via PyMongo)
  - `src/main.py` — API entrypoint, CORS (`ALLOWED_ORIGINS`), rate-limit wiring
  - `src/rate_limit.py` — SlowAPI limiter (auth routes)
  - `src/db.py` — MongoDB client (`MONGO_URI`, `MONGO_DB` from `.env`)
  - `src/services.py` — SRS queue + `user_progress` updates (SM-2 style)
  - `src/models.py` — Pydantic models (reference shapes)
  - `src/utils.py` — Password hashing and JWT helpers (`SECRET_KEY` from `.env`)
  - `src/api_auth.py` — Sign up, sign in, refresh token
  - `src/api_decks.py` — List/create decks, cards (JWT)
  - `src/api_learning.py` — Learning sessions (uses `services`)
  - `src/init_indexes.py` — Run once from `server/`: `python src/init_indexes.py`
  - `tests/` — Pytest smoke/unit tests (`pytest` from `server/`)
- `web/nuxt/` — Nuxt 3 (Tailwind, Pinia, VeeValidate, VueUse, Motion, Fuse, Lucide)

## Environment (backend)

Create `server/.env` as needed:

- `MONGO_URI` — default `mongodb://localhost:27017`
- `MONGO_DB` — default `vocko`
- `SECRET_KEY` — JWT signing secret (set in production)
- `ALLOWED_ORIGINS` — comma-separated origins, or `*` for development (avoid `*` with credentials in production)

## Environment (frontend)

Copy `web/nuxt/.env.example` to `web/nuxt/.env`:

- `NUXT_PUBLIC_API_BASE` — API origin (default `http://localhost:8000`)

## Quickstart (backend)

```bash
cd server
pip install -r requirements.txt
python src/init_indexes.py
uvicorn src.main:app --reload
```

API: http://localhost:8000

## Quickstart (frontend)

```bash
cd web/nuxt
npm install
npm run dev
```

## Tests (backend)

```bash
cd server
pytest
```

## Stack notes

- Frontend calls the API through `useApi()` (`composables/useApi.ts`) with `NUXT_PUBLIC_API_BASE`, JWT from Pinia, and one retry on 401 after refresh.
- Learning modes: `learn` (new + due cards first) and `review` (due cards only).
