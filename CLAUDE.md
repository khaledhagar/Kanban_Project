# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Source-of-truth docs

This repo keeps detailed, per-area docs. Read the relevant one before changing code, and update it when you change behavior:

- `AGENTS.md` (root) — business requirements, technical decisions, color scheme, coding standards (keep it simple, no emojis, root-cause fixes only).
- `backend/AGENTS.md`, `frontend/AGENTS.md`, `scripts/AGENTS.md` — module-level structure, routes, and test layout for each area.
- `docs/PLAN.md` — the 10-part build plan and global testing standards (90% coverage floor).
- `docs/DATABASE.md` — schema and the "board as one JSON blob" rationale.
- `docs/AI.md` — OpenRouter usage and the Structured Outputs design.

## Commands

Backend (run from `backend/`, Python 3.13 via `uv`):

```sh
uv sync                                   # install deps from uv.lock
uv run uvicorn app.main:app --reload      # dev server (serves /api; static from backend/static)
uv run pytest                             # all tests + coverage (fails under 90%)
uv run pytest tests/test_ai.py::test_ask_without_key_raises -o addopts=""  # single test
RUN_LIVE_AI=1 uv run pytest -k live -o addopts=""   # opt-in live OpenRouter tests
```

Note: `--cov-fail-under=90` is in `pyproject.toml` `addopts`, so running a *subset* of tests will fail the coverage gate. Pass `-o addopts=""` to disable coverage when running a single/filtered test.

Frontend (run from `frontend/`):

```sh
npm run dev          # Next dev server
npm run build        # static export to out/
npm run lint
npm run test:unit    # vitest run (jsdom)
npx vitest run --coverage                          # unit + coverage gate (90%, all 4 metrics)
npx vitest run src/components/ChatSidebar.test.tsx # single file
npx vitest run -t "renders the reply"              # single test by name
npm run test:e2e     # Playwright (builds the app and starts uvicorn itself)
```

Whole app in Docker (from repo root):

```sh
scripts/start.ps1   # or scripts/start.sh — build image + run container on :8000
scripts/stop.ps1    # or scripts/stop.sh  — stops AND removes the container (data survives in the pm-data volume)
```

Login is hardcoded: `user` / `password`.

## Architecture

Single Docker container, no Node server in production. The multi-stage `Dockerfile` builds the Next.js static export, then a FastAPI/uvicorn image serves that export at `/` and the JSON API under `/api` from one process.

**App wiring (`backend/app/main.py`):** `create_app(static_dir, db_path)` is a factory (tests pass a temp dir/DB). It calls `db.init_db`, includes the `auth`, `board`, and `ai` routers, then mounts `StaticFiles` at `/` **last** so `/api/*` routes take precedence over the catch-all.

**Auth (`app/auth.py`):** credentials are hardcoded; sessions are an in-memory `token -> username` dict (not persisted). The `current_user` dependency reads the `pm_session` cookie and 401s otherwise — reuse it to gate any new route.

**Persistence (`app/db.py`, `docs/DATABASE.md`):** SQLite via stdlib `sqlite3` (no ORM). The whole board is stored as **one JSON document** per user (`boards.data`), mirroring the frontend `BoardData`. There are no per-card/column rows or routes — every change is a full-board replace (`GET /api/board`, `PUT /api/board`). `get_or_create_board` lazily seeds the demo board on first read. DB path comes from `PM_DB_PATH` (default `backend/data/pm.db`).

**AI (`app/ai.py`, `docs/AI.md`):** OpenRouter's OpenAI-compatible API, model `openai/gpt-oss-120b`, keyed by `OPENROUTER_API_KEY`. `POST /api/ai/chat` sends system context + board JSON + history + message and requests strict Structured Outputs `{reply, board_update}`. **Key subtlety:** the stored board keeps cards as a dynamic-keyed map, which strict JSON schemas cannot express, so the AI exchanges cards as an *array*; `_board_to_ai`/`_board_from_ai` convert, and `_validated_update` runs any update through the `Board` model and drops malformed ones (never trust the model). A missing key fails clearly (`AIError` → 503), no silent fallback.

**Frontend (`frontend/src/`):** Next 16 App Router, `output: "export"`. `AuthGate` shows `LoginForm` or `KanbanBoard`. `KanbanBoard` loads the board from the API and persists every mutation back; a `useEffect` watching `board` calls `saveBoard`, but skips when `board === persisted.current` — so the initial load and AI-applied updates don't trigger a redundant PUT. `ChatSidebar` calls `applyServerBoard` (which sets `persisted.current` first) so an AI board change refreshes the UI without re-saving. Pure board logic (`moveCard`, ids) lives in `src/lib/kanban.ts`; the API client is `src/lib/api.ts`.

## Cross-cutting conventions

- **Env / secrets:** `OPENROUTER_API_KEY` lives in the project-root `.env` (git-ignored, excluded from the image via `.dockerignore`). `app/ai.py` loads it with `load_dotenv` for local/dev/tests; the start scripts pass it to the container with `docker run --env-file`.
- **The board is shared server state** (one row for the single MVP user). Because of this, the Playwright suite runs serially (`workers: 1`), resets the board to the seed in `beforeEach`, and points `PM_DB_PATH` at a temp file so it never touches the dev DB. Keep these in mind when adding e2e tests.
- **Drag-and-drop** is verified by e2e, not unit tests — driving real pointer drag (`@dnd-kit`) in jsdom is contrived. Don't add jsdom drag tests to chase coverage.
- **Coverage floor is 90%** (lines/statements, plus functions/branches on the frontend), enforced in config. It is a floor, not a target: add tests for real behavior, not to pad the number.
- Theme colors are CSS variables in `frontend/src/app/globals.css` (`--navy-dark`, `--primary-blue`, `--secondary-purple`, `--accent-yellow`, `--gray-text`). Stable `data-testid` hooks (`column-<id>`, `card-<id>`) back the e2e tests — keep them stable.
