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

- `app/main.py` - the FastAPI app. Defines `GET /api/health` and mounts the
  static site. The static mount is registered last so `/api` routes take
  precedence over the catch-all at `/`.
- `static/` - files served at `/` (`html=True`, so `/` returns `index.html`).
  Currently a placeholder hello-world page; Part 3 replaces it with the exported
  Next.js bundle.
- `tests/` - `test_health.py` (health route) and `test_static.py` (root page).
- `pyproject.toml` - project metadata, deps, and tool config. `package = false`
  (this is an application, not a library); `pythonpath = ["."]` makes `app`
  importable in tests.

## Routes

- `GET /api/health` -> `{ "status": "ok" }`.
- `GET /` (and other non-`/api` paths) -> static files from `static/`.

## Commands

Run from `backend/`:

- `uv sync` - create the virtualenv and install deps from the lockfile.
- `uv run uvicorn app.main:app --reload` - run the dev server locally.
- `uv run pytest` - run tests with coverage (fails under 80%).

## Tests

- Unit: `GET /api/health` returns 200 and `{"status": "ok"}`.
- Integration: `GET /` returns 200 HTML containing the hello-world marker.
- Coverage floor is 80% (`--cov-fail-under=80` in `pyproject.toml`); the current
  suite covers 100% of `app`.
