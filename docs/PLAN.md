# Project Plan

This document plans each part of the build in detail. Every part has a goal, a
checklist of substeps for the agent to tick off, the tests to write, and the
success criteria that prove the part is done. Do not start a part until the
previous part's success criteria are met. Part 1 must be approved by the user
before any code part begins.

See [../AGENTS.md](../AGENTS.md) for business requirements, technical decisions,
the color scheme, and coding standards (keep it simple, no emojis, root-cause
fixes only).

## Architecture summary

- Single Docker container runs FastAPI (Python, managed with `uv`).
- FastAPI serves the statically exported Next.js site at `/` and exposes the
  JSON API under `/api`.
- Next.js is built with `output: "export"` to a static bundle; there is no
  Node server in production.
- Data is a single SQLite database file, created on first run if missing.
- AI calls go to OpenRouter using model `openai/gpt-oss-120b`, keyed by
  `OPENROUTER_API_KEY` from the project-root `.env`.

## Testing standards (apply to every part)

These are global requirements, not a single part. Each part is only "done" when
they hold for the code that part touches.

- Unit coverage floor: minimum 80% (lines/statements) per package, enforced in
  config so the test command fails below the threshold.
  - Frontend: Vitest v8 coverage thresholds in `vitest.config.ts`.
  - Backend: `pytest-cov` with `--cov-fail-under=80` in pytest config.
  - 80% is a floor, not a target. Write tests for behavior worth protecting
    (real logic, boundaries, regressions), not to pad the number. Do not add
    low-value tests just to lift coverage; if meaningful tests already clear
    80%, that is enough. If hitting 80% would require contrived tests, prefer
    simplifying or removing untested-but-trivial code over testing it.
- Robust integration testing: every feature that crosses a boundary (HTTP API,
  database, AI provider, static serving) has at least one integration test that
  exercises the real boundary or a faithful test double.
  - Backend API + DB: pytest against a FastAPI `TestClient` using a temporary
    SQLite file.
  - External AI: integration tests mock the OpenRouter HTTP call; exactly one
    opt-in live connectivity test may hit the real API when a key is present.
  - Full UI flow: Playwright end-to-end against the built/served app.
- Determinism: no test depends on wall-clock time, network flakiness, or random
  ordering. Seed or inject randomness and time where needed.
- Every part's "Tests" must be green and the coverage floor met before moving on.

## Definition of done (per part)

1. All checklist items ticked.
2. All listed tests written and passing.
3. Coverage floor (80%) met for touched packages.
4. Relevant `AGENTS.md` files updated to describe new/changed code.
5. App still starts cleanly via the start script (from Part 2 onward).

---

## Part 1: Plan

Goal: produce this detailed, approved plan and document the existing frontend.

Checklist:

- [x] Enrich `docs/PLAN.md` with per-part goals, checklists, tests, and success
      criteria.
- [x] Bake the 80% coverage floor and integration-testing requirement into the
      testing standards above.
- [x] Create `frontend/AGENTS.md` describing the existing frontend code
      (structure, components, state model, scripts, test setup).
- [x] User reviews and approves the plan before any code part starts.

Tests: none (documentation only).

Success criteria:

- This document covers all 10 parts with actionable checklists and explicit
  success criteria.
- `frontend/AGENTS.md` exists and accurately describes the current code.
- User has explicitly approved the plan.

## Part 2: Scaffolding

Goal: stand up the Docker + FastAPI skeleton that serves a static "hello world"
page and answers one API call locally.

Checklist:

- [x] Create `backend/` FastAPI app managed with `uv` (`pyproject.toml`,
      pinned deps).
- [x] Add a `GET /api/health` route returning JSON `{ "status": "ok" }`.
- [x] Serve a static `index.html` ("hello world") at `/` from FastAPI.
- [x] Write a `Dockerfile` (and `compose` if helpful) using `uv` to install and
      run the app.
- [x] Write `scripts/start` and `scripts/stop` for Mac, PC, and Linux that
      build/run and stop the container.
- [x] Update `backend/AGENTS.md` and `scripts/AGENTS.md`.

Tests:

- Backend unit: `GET /api/health` returns 200 and the expected body
  (FastAPI `TestClient`).
- Backend integration: static `/` returns 200 and contains the hello-world
  marker text.
- Manual/script check: `scripts/start` brings the container up and the page +
  health endpoint are reachable on the documented port.

Success criteria:

- Running the start script serves the hello-world page at `/` and the health
  endpoint responds, all from inside the container.
- Stop script cleanly tears it down.
- Backend coverage >= 80%.

## Part 3: Add in Frontend

Goal: replace the placeholder page with the real Kanban demo, statically built
and served by FastAPI at `/`.

Checklist:

- [x] Set Next.js `output: "export"` and confirm the demo board builds to a
      static bundle.
- [x] Wire the build so FastAPI serves the exported assets at `/` (and static
      file routing for `_next` assets).
- [x] Update start script to build the frontend before/within the image.
- [x] Add inline card editing (edit an existing card's title/details) to the
      demo; this satisfies the "cards can be edited" business requirement, which
      the current demo does not yet cover.
- [x] Keep board state client-side for now (no backend persistence yet).
- [x] Add Vitest coverage thresholds (>= 80%) to `vitest.config.ts`.

Tests:

- Frontend unit: existing `kanban.ts` logic (`moveCard`, `createId`) plus
  component tests for column rename, add card, edit card, delete card.
- Frontend e2e (Playwright): load `/`, see five columns and demo cards,
  drag a card between columns, rename a column, add, edit, and delete a card.
- Backend integration: `/` serves the built app shell (HTML contains the app
  root), and a `_next` asset returns 200.

Success criteria:

- Visiting `/` in the running container shows the working Kanban demo.
- Frontend unit coverage >= 80%; e2e flow passes.

## Part 4: Add in a fake user sign in experience

Goal: gate the board behind a dummy login (`user` / `password`) with logout.

Checklist:

- [x] Add backend auth endpoints: `POST /api/login`, `POST /api/logout`,
      `GET /api/me` using a server-set session cookie. Sessions are kept in an
      in-memory store (a token map) for the MVP; not persisted to SQLite.
- [x] Validate credentials against hardcoded `user` / `password`.
- [x] Frontend: show a login screen at `/` when unauthenticated; show the board
      when authenticated; provide a logout control.
- [x] Redirect/guard so the board is not shown without a valid session.

Tests:

- Backend unit: login with correct creds sets a session and returns success;
  wrong creds return 401; logout clears the session; `/api/me` reflects state.
- Frontend unit: login form validation and submit behavior; logout clears UI.
- E2E: visit `/` -> see login -> bad creds rejected -> good creds show board ->
  logout returns to login.

Success criteria:

- The board is unreachable until login with `user` / `password`.
- Logout works and returns to the login screen.
- Coverage >= 80% on both packages for touched code.

## Part 5: Database modeling

Goal: design and document the Kanban schema persisted as JSON in SQLite, sized
for multiple users though the MVP uses one.

Checklist:

- [x] Propose schema: users, boards (one per user for MVP), and the board
      payload stored as JSON (columns, cards) mirroring the frontend
      `BoardData` shape.
- [x] Document the approach in `docs/DATABASE.md` (tables, columns, JSON shape,
      why JSON, migration/creation strategy).
- [x] Define how a new DB file is created on first run if missing.
- [x] Get explicit user sign-off on the schema before Part 6.

Tests: none (design + docs). Schema is validated by Part 6 tests.

Success criteria:

- `docs/DATABASE.md` exists, is clear, and the user has approved it.
- Schema supports multiple users and a single board per user.

## Part 6: Backend

Goal: implement API routes to read and update a user's Kanban, backed by SQLite,
created on demand.

Checklist:

- [x] Implement the schema from Part 5; auto-create the DB and seed the demo
      board for the user if absent.
- [x] `GET /api/board` returns the current user's board JSON.
- [x] `PUT /api/board` persists changes by replacing the whole board JSON
      blob. Granular per-card/column routes are intentionally avoided for the
      MVP to keep persistence simple, since the board is stored as one JSON
      document.
- [x] Enforce auth: board routes require a valid session.
- [x] Update `backend/AGENTS.md` with data-access description.

Tests:

- Backend unit: read returns seeded board; update persists and round-trips;
  unauthenticated access is rejected; DB auto-creation works against a temp
  file.
- Backend integration: full request -> DB -> response cycle via `TestClient`
  with a temporary SQLite database.

Success criteria:

- A signed-in user can read and modify their board via the API and changes
  survive a process restart (persisted to SQLite).
- Backend coverage >= 80%.

## Part 7: Frontend + Backend

Goal: make the frontend use the backend API so the board is genuinely
persistent.

Checklist:

- [x] Replace in-memory `initialData` usage with data loaded from
      `GET /api/board` after login.
- [x] Persist every mutation (move, rename, add, edit, delete) to the backend
      via `PUT /api/board` (full-board replace).
- [x] Handle load/save states simply (no over-engineering).
- [x] Ensure static-export build still serves correctly with live API calls.

Tests:

- Frontend unit: data layer maps API responses to `BoardData` and sends correct
  update payloads (mock fetch).
- E2E: log in, make changes, reload the page, confirm changes persisted; log in
  as the same user in a fresh session and see the saved board.
- Backend integration: unchanged routes still pass with the real frontend
  payloads.

Success criteria:

- Board edits persist across reloads and restarts through the real API.
- Coverage >= 80% on both packages for touched code.

## Part 8: AI connectivity

Goal: prove the backend can call OpenRouter.

Checklist:

- [x] Add a backend AI client using `OPENROUTER_API_KEY` and model
      `openai/gpt-oss-120b`.
- [x] Add an internal/diagnostic path that asks the model "2+2" and returns the
      answer.
- [x] Fail clearly if the key is missing (no silent fallback).
- [x] While connected, verify whether `openai/gpt-oss-120b` on OpenRouter
      honors strict Structured Outputs (JSON schema). Record the result; this
      de-risks Part 9 before it is built. (Live run 2026-06-22: CONFIRMED it
      honors strict Structured Outputs; recorded in `docs/AI.md`.)

Tests:

- Backend unit: AI client builds the correct request; response parsing works
  (mocked HTTP).
- Opt-in live integration: one test that, only when a real key is present,
  sends "2+2" and asserts the reply contains "4".

Success criteria:

- The "2+2" check returns a correct answer against the real API when run with a
  key; mocked tests pass in CI without a key.

## Part 9: AI over the Kanban with Structured Outputs

Goal: every AI call includes the board JSON plus the user's question and
conversation history, and returns Structured Outputs containing a user-facing
reply and an optional board update.

Checklist:

- [x] Define the Structured Output schema: `{ reply: string, board_update?:
      BoardData | patch }`. (Full board replace; cards exchanged as an array
      because strict schemas cannot express the storage map's dynamic keys.)
- [x] Build the request: system context + board JSON + conversation history +
      user message.
- [x] Request strict Structured Outputs when Part 8 confirmed the model
      supports it; otherwise fall back to JSON mode with the same schema. Either
      way, validate the parsed response against the schema server-side and
      repair/reject malformed output rather than trusting the model. (Strict
      requested; server validates via the `Board` model.)
- [x] Parse and validate the structured response; apply `board_update` to the
      stored board when present.
- [x] Reject/ignore malformed updates safely (root-cause any schema mismatch).

Tests:

- Backend unit: prompt assembly includes board + history + question; structured
  response parsing; applying an update mutates the stored board correctly;
  reply-only responses leave the board unchanged.
- Backend integration: end-to-end with a mocked structured AI response that both
  replies and updates the board, persisted to SQLite.

Success criteria:

- AI responses reliably parse into the schema; board updates persist; a
  reply-only turn changes nothing.
- Backend coverage >= 80%.

## Part 10: AI chat sidebar UI

Goal: a polished sidebar chat where the LLM can update the board, with automatic
UI refresh when it does.

Checklist:

- [x] Build a sidebar chat widget styled to the color scheme in `AGENTS.md`.
- [x] Send user messages (with history) to the Part 9 endpoint; render replies.
- [x] When the response includes a board update, refresh the board UI
      automatically from the persisted state.
- [x] Keep the layout responsive and uncluttered.

Tests:

- Frontend unit: chat sends message + history; renders reply; triggers a board
  refresh when an update is signaled (mock API).
- E2E: open chat, ask the AI to add/move a card (mocked structured response),
  confirm the chat reply appears and the board updates without manual reload.

Success criteria:

- Users can chat with the AI in the sidebar; AI-driven board changes appear
  automatically and persist.
- Frontend coverage >= 80%; e2e flow passes.
