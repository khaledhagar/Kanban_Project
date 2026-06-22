# Backend

FastAPI service for the Project Management MVP. It serves the static site at `/`
and the JSON API under `/api`, all from a single process inside the Docker
container. Managed with `uv` (Python 3.13).

## Stack

- FastAPI, served by Uvicorn.
- `uv` for dependency management; deps declared in `pyproject.toml` and pinned in
  `uv.lock` (committed for reproducible Docker builds).
- Tests: `pytest` + `pytest-cov` with FastAPI's `TestClient`.

## Structure

- `app/main.py` - `create_app(static_dir=DEFAULT_STATIC_DIR, db_path=...)` builds
  the FastAPI app: initializes the DB, defines `GET /api/health`, includes the
  auth and board routers, and mounts the static site. The static mount is
  registered last so `/api` routes take precedence over the catch-all at `/`. The
  factory lets tests serve a fixture directory and a temp DB; `app = create_app()`
  is the production instance. `DEFAULT_STATIC_DIR` is the `PM_STATIC_DIR` env var
  if set, else `backend/static` (the e2e harness sets it to the built
  `frontend/out`).
- `app/auth.py` - login/session auth. Credentials are hardcoded (`user` /
  `password`). Sessions live in an in-memory `token -> username` dict (not
  persisted). `current_user` is a dependency that reads the `pm_session` cookie
  and 401s when absent/invalid; reuse it to protect future routes.
- `app/db.py` - SQLite data access (stdlib `sqlite3`, no ORM) per the design in
  `docs/DATABASE.md`. `init_db` creates the `users`/`boards` tables idempotently
  and ensures the hardcoded user row; `create_app` calls it on startup.
  `connect` opens a short-lived connection (creates the file and parent dir if
  missing, `Row` factory, foreign keys on). The board is one JSON blob per user:
  `get_or_create_board` returns the stored board or lazily seeds `SEED_BOARD`
  (the demo five columns / eight cards) on first read; `save_board` upserts the
  whole blob and bumps `updated_at`. DB path is `PM_DB_PATH` (default
  `backend/data/pm.db`), passed through `create_app(db_path=...)` and held on
  `app.state.db_path` so tests can use a temp file.
- `app/board.py` - board API router. `get_db` is a request-scoped dependency
  yielding a connection from `app.state.db_path`. Routes depend on
  `current_user`, so they 401 without a session. Pydantic `Board`/`Column`/`Card`
  models validate the top-level shape on `PUT`; the JSON is stored verbatim.
- `app/ai.py` - OpenRouter client, structured chat, and routes. `_post` POSTs to
  the OpenAI-compatible Chat Completions API (`MODEL = openai/gpt-oss-120b`)
  using `OPENROUTER_API_KEY`; a missing key raises `AIError`. `ask(prompt)` is
  the plain one-shot used by the diagnostic. `chat(board, history, message)`
  builds the request (`build_messages`: system context + board JSON + history +
  question) and requests strict Structured Outputs (`_RESPONSE_SCHEMA`:
  `{reply, board_update}`). Because the stored board keeps cards as a map but
  strict schemas cannot express dynamic keys, the AI exchanges cards as an array;
  `_board_to_ai`/`_board_from_ai` convert, and `_validated_update` runs the result
  through the `Board` model, returning `None` (ignored) on malformed updates so a
  bad update never corrupts the stored board. Loads the root `.env` on import; in
  Docker the key is passed via `--env-file`. See `docs/AI.md`.
  - `GET /api/ai/health` (auth-gated) asks "2+2"; 503 if the key is missing.
  - `POST /api/ai/chat` (auth-gated) `{message, history}` -> `{reply, board}`;
    persists a `board_update` to SQLite when present and returns the current
    board; 503 if the key is missing.
- `static/` - files served at `/` (`html=True`, so `/` returns `index.html`,
  and `/_next/...` assets resolve to files). In the Docker image this directory
  is replaced by the exported Next.js bundle (`frontend/out`); the committed
  `index.html` is only a dev fallback for running the backend standalone.
- `tests/` - `test_health.py` (health), `test_static.py` (serving),
  `test_auth.py` (login/logout/me), and `test_board.py` (board read/write,
  auth gating, persistence across an app restart over a temp DB).
- `pyproject.toml` - project metadata, deps, and tool config. `package = false`
  (this is an application, not a library); `pythonpath = ["."]` makes `app`
  importable in tests.

## Routes

- `GET /api/health` -> `{ "status": "ok" }`.
- `POST /api/login` `{username, password}` -> sets the `pm_session` cookie and
  returns `{username}`; 401 on bad credentials.
- `POST /api/logout` -> clears the session and cookie.
- `GET /api/me` -> `{username}` when authenticated, else 401.
- `GET /api/board` -> the signed-in user's board JSON (seeds the demo board on
  first read); 401 without a session.
- `PUT /api/board` `{columns, cards}` -> replaces the whole board blob and
  returns it; 401 without a session.
- `GET /api/ai/health` -> `{answer}` from a live "2+2" model call; 401 without a
  session, 503 if `OPENROUTER_API_KEY` is missing.
- `POST /api/ai/chat` `{message, history}` -> `{reply, board}`; the AI may update
  and persist the board; 401 without a session, 503 if the key is missing.
- `GET /` (and other non-`/api` paths) -> static files from `static/`.

## Commands

Run from `backend/`:

- `uv sync` - create the virtualenv and install deps from the lockfile.
- `uv run uvicorn app.main:app --reload` - run the dev server locally.
- `uv run pytest` - run tests with coverage (fails under 80%).

## Tests

- Unit: `GET /api/health` returns 200 and `{"status": "ok"}`.
- Integration (`test_serves_app_shell_and_next_asset`): builds the app over a
  temp fixture dir mirroring the export shape (an `index.html` shell plus a
  `/_next/static` asset) and asserts the shell serves, the asset returns 200,
  `/api/health` still wins over the catch-all, and unknown paths 404.
- Auth (`test_auth.py`): correct credentials set a session and `/api/me`
  reflects it; wrong credentials 401; logout clears the session.
- Board (`test_board.py`): a signed-in user reads the seeded board, an update
  round-trips, the routes 401 without a session, and a board edit survives a
  fresh `create_app` over the same temp DB file (auto-created on demand).
- AI (`test_ai.py`): mocked unit tests for request building, reply parsing,
  missing-key error, and the diagnostic route (auth gate, answer, 503). Part 9
  adds chat coverage: `build_messages` embeds board + history + question;
  `chat` parses reply + update, leaves the board unchanged on a reply-only turn,
  and drops malformed updates; the `POST /api/ai/chat` route gates on auth,
  applies and persists a board update (verified across an app restart), leaves
  the board unchanged on reply-only, and 503s without a key. Two opt-in live
  tests (2+2 and Structured Outputs) are skipped unless `OPENROUTER_API_KEY` and
  `RUN_LIVE_AI` are both set.
- Coverage floor is 90% (`--cov-fail-under=90` in `pyproject.toml`); the current
  suite covers 100% of `app`.
