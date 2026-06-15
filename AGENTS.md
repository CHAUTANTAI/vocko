# VocKO AI Agent Instructions

## Purpose
This repository contains a vocabulary learning web app with a Python FastAPI backend and a Nuxt 3 frontend.

Use this file to quickly understand project boundaries, where to make changes, and how to run the app locally.

## Repository layout
- `server/` — backend service
  - `src/main.py` — FastAPI app entrypoint
  - `src/api_*.py` — HTTP endpoints grouped by feature
  - `src/models.py` — Pydantic request/response models
  - `src/services.py` — spaced repetition/SRS logic
  - `src/db.py` — MongoDB connection
  - `src/utils.py` — auth and helper utilities
  - `src/init_indexes.py` — MongoDB index initialization script
  - `tests/` — Pytest tests for backend logic and API
- `web/nuxt/` — Nuxt 3 frontend
  - `composables/useApi.ts` — API client and auth handling
  - `stores/auth.ts` — Pinia auth store
  - `pages/` — page routes and views
  - `components/` — reusable Vue components
  - `middleware/` — auth/guest route guards
  - `utils/` — client utilities

## How to run
### Backend
```bash
cd server
python -m pip install -r requirements.txt
python src/init_indexes.py
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```
- Use `python -m pip` on Windows when `pip` is unavailable.
- API base URL default: `http://127.0.0.1:8000`

### Frontend
```bash
cd web/nuxt
npm install
npm run dev
```
- Frontend base URL default: `http://127.0.0.1:3000`
- Frontend reads `NUXT_PUBLIC_API_BASE` from `web/nuxt/.env`

### Backend tests
```bash
cd server
python -m pytest
```

## Important conventions
- Backend auth is JWT-based. `server/src/api_auth.py` handles sign-up, sign-in, refresh.
- Learning sessions and grading are implemented in `server/src/api_learning.py` and `server/src/services.py`.
- Frontend API calls are centralized in `web/nuxt/composables/useApi.ts`; use that composable for authenticated calls and refresh handling.
- UI routing and page structure are in `web/nuxt/pages/`.
- The frontend is Nuxt 3 with `type: module` and uses Pinia, VeeValidate, VueUse, and Tailwind.

## Agent guidance
- If modifying backend behavior, update Pydantic models and API payload shapes together.
- If changing frontend API usage, update `useApi.ts` and verify the corresponding page or component in `pages/` or `components/`.
- For UI work, prefer existing components like `Flashcard.vue` and use Pinia auth state rather than ad hoc local state.
- For database/index changes, preserve compatibility with existing MongoDB settings in `server/.env`.

## Links
- Main README: [README.md](README.md)
- Backend docs: [server/README.md](server/README.md)
- Frontend docs: [web/nuxt/README.md](web/nuxt/README.md)
- Project overview in root README
