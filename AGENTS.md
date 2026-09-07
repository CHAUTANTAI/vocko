# VocKO — Agent Entry Point

Vocabulary learning web app: **FastAPI + MongoDB** backend, **Nuxt 3** frontend, optional **OpenRouter** AI, optional Chrome extension for TOEIC page scanning.

Cursor loads this file plus `.cursor/rules/*.mdc` (scoped by path). Prefer those rules when editing matching files.

## Architecture

```
Browser (Nuxt :3000)
  └─ useApi() + Pinia auth (JWT cookies) → FastAPI (:8000)
       ├─ api_auth / api_decks / api_learning / api_tags / api_import
       ├─ services.py (SRS SM-2 + queues)
       ├─ MongoDB `vocko`
       └─ OpenRouter (optional: hint, grade, explain, tag suggest, TOEIC import)
localExtension/ — MV3 “VocKO TOEIC Scanner” (DOM scan; not wired into Nuxt)
```

## Where to change what

| Concern | Start here |
|---|---|
| HTTP routes | `server/src/api_*.py`, wired in `main.py` |
| Request/response shapes | Prefer models next to routes; `models.py` is reference |
| SRS / queue / progress | `server/src/services.py`, `learning_config.py` |
| Answer matching | `server/src/answer_match.py` |
| AI hint/grade/explain | `server/src/learning_ai.py`, `openrouter_client.py` |
| Card serialize / tags / POS | `server/src/card_helpers.py` |
| TOEIC paste import | `server/src/api_import.py`, `toeic_*.py`, `data/toeic_*.txt` |
| Indexes / migrations | `server/src/init_indexes.py` |
| Frontend API + 401 refresh | `web/nuxt/composables/useApi.ts` |
| Auth state | `web/nuxt/stores/auth.ts`, `utils/authCookies.ts` |
| Pages / routes | `web/nuxt/pages/` |
| Flashcard UI | `web/nuxt/components/Flashcard.vue` |

**Not mounted:** `server/src/api_sources.py` exists but is **not** included in `main.py` — do not assume `/sources` works until wired.

## MongoDB collections

`users`, `decks`, `flashcards`, `user_progress`, `learning_sessions`, `study_records`, `tags`, `card_tags`

- Deck owns cards; tags link via `card_tags` (not only embedded lists).
- Soft-delete style: cards may have `deleted`.
- Progress is per `(user_id, card_id)` with SM-2 fields + `recent_grades`.

## Learning product surface

- Modes: `learn` (new + due), `review` (due only).
- Interaction: `typed` (string match ± 1 typo ± optional AI grade) or `self_grade` (`known` / `unsure` / `forgot`).
- Session flow: start → next → answer|self-grade|hint → continue-round → finish; history/stats/weak-tags/explain endpoints exist.
- Smart queue weights (weak/new/easy): see `learning_config.py`.

## Frontend routes

| Path | Role |
|---|---|
| `/` | Landing |
| `/login`, `/register` | Auth (`middleware/guest.ts`) |
| `/deck`, `/deck/[id]` | Decks + cards (`middleware/auth.ts`) |
| `/learning/session`, `/learning/history` | Study + history |
| `/import/toeic-text` | Paste text → AI vocab extract |

Stack: Nuxt 3 (`type: module`), Pinia, VeeValidate+Yup, VueUse, Tailwind, TipTap, Lucide, Fuse.

## Run / test

Backend (`server/`):

```bash
python -m pip install -r requirements.txt
python src/init_indexes.py
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
python -m pytest
```

On Windows use `py -3` / `python -m pip` if `python`/`pip` are missing from PATH.

Frontend (`web/nuxt/`):

```bash
npm install
npm run dev
```

Env: `server/.env` from `.env.example`; `web/nuxt/.env` needs `NUXT_PUBLIC_API_BASE` (default `http://localhost:8000`). OpenRouter key optional.

## Agent do / don't

- Change API payloads and callers together (backend + `useApi` / pages).
- Prefer `useApi()` for authenticated calls; use Pinia auth, not ad-hoc tokens.
- Prefer extending `Flashcard.vue` / existing pages over new parallel UI.
- Keep Mongo indexes compatible with existing `.env` / Atlas setups.
- Do not invent GitNexus or other removed tooling.
- Do not commit secrets (`.env`).

## Cursor rules map

| Rule file | When |
|---|---|
| `vocko-overview.mdc` | Always |
| `backend-fastapi.mdc` | `server/**` |
| `frontend-nuxt.mdc` | `web/nuxt/**` |
| `learning-srs.mdc` | Learning / SRS files |
| `import-toeic.mdc` | TOEIC import / lemma pipeline |

## Docs

- [README.md](README.md) — quickstart + env
- [server/README.md](server/README.md) — backend
- [web/nuxt/README.md](web/nuxt/README.md) — frontend (some “Next Steps” may be outdated; prefer this file)
