# VocKO Nuxt Frontend

## Structure
- `pages/` — Main app pages (decks, learning session)
- `components/Flashcard.vue` — Flashcard UI

## Quickstart

```bash
cd web/nuxt
npm install
npm run dev
```

## Build and start

```bash
cd web/nuxt
npm run build
npm run start
```

## Environment

Create `web/nuxt/.env` with at least:

- `NUXT_PUBLIC_API_BASE` — API origin, for example `http://localhost:8000`

## Next Steps
- Implement API calls to backend
- Add authentication and session management
- Build deck/flashcard CRUD UI
- Build learning session UI
