# Canonical Runtime Audit (Phase 0 Freeze)

## Baseline snapshot

- Freeze marker branch: `before-refactor`
- Freeze marker tag: `before-refactor-baseline`

## Backend entrypoint candidates

- `web_app/backend/main_simple.py` — active implementation with `/health`, `/ready`, `/metrics`, `/api/search`, `/api/product/{asin}`, `/api/keywords`
- `web_app/backend/main.py` — compatibility entrypoint re-exporting canonical app
- `web_app/backend/main_v2.py` — legacy compatibility entrypoint re-exporting canonical app (previously empty)

Canonical backend selected: `web_app/backend/main_simple.py`

## Frontend runtime

- Canonical frontend: `web_app/frontend` (Vite React app)
- Canonical dev command: `npm run dev` from `/home/runner/work/amazon-product-hunter-pro/amazon-product-hunter-pro/web_app/frontend`

## Runtime entrypoint alignment

- `Makefile` `dev` target now uses `web_app.backend.main_simple:app`
- `Dockerfile` default command now uses `web_app.backend.main_simple:app`
- `run_dev.py` already uses `web_app.backend.main_simple:app`
- API tests now import canonical backend module

## Migration workflow status

- **No active/usable Alembic migration workflow identified.**
- Current references exist in helper commands, but no active migration configuration/workflow was found in repository runtime paths.
