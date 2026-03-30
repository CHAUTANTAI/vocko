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
- `OPENROUTER_API_KEY` — optional; enables AI hints and approximate (LLM) grading during study. Without it, answers are graded by exact string match only and the hint endpoint returns an error.
- `OPENROUTER_MODEL_HINT` — OpenRouter model id for **vocabulary hints** (default Mistral Small 3: `mistralai/mistral-small-24b-instruct-2501`). Avoid stale `:free` slugs that return “No endpoints”.
- `OPENROUTER_MODEL_GRADE` — OpenRouter model id for **answer checking** (default Llama family, e.g. `meta-llama/llama-3.1-8b-instruct`). Hints and grading do not share one model.
- `OPENROUTER_BASE_URL` — optional override (default `https://openrouter.ai/api/v1`)

## Environment (frontend)

Copy `web/nuxt/.env.example` to `web/nuxt/.env`:

- `NUXT_PUBLIC_API_BASE` — API origin (default `http://localhost:8000`)

## Quickstart (backend)

```bash
cd server
python -m pip install -r requirements.txt
python src/init_indexes.py
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

On Windows, if `pip` is not found in PowerShell, `python -m pip` (or `py -m pip`) is the supported way to run pip.

API: http://127.0.0.1:8000

## Quickstart (frontend)

```bash
cd web/nuxt
npm install
npm run dev
```

## Tests (backend)

```bash
cd server
python -m pytest
```

## Stack notes

- Frontend calls the API through `useApi()` (`composables/useApi.ts`) with `NUXT_PUBLIC_API_BASE`, JWT from Pinia, and one retry on 401 after refresh.
- Learning modes: `learn` (new + due cards first) and `review` (due cards only).

## GitNexus (optional — MCP / code graph)

Index repo này cho GitNexus MCP (Cursor, v.v.). Chi tiết, phân biệt **`Already up to date`** vs output có **`nodes | edges`**, và lệnh **`analyze --force`**: xem **[docs/gitnexus.md](docs/gitnexus.md)**.

Tóm tắt — **ép index lại và xác nhận thành công** (có thống kê nodes/edges):

```powershell
cd <repo-root>
node <path-to>\GitNexus\gitnexus\dist\cli\index.js analyze --force --skip-agents-md .
```
