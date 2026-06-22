# Frontend

A single-board Kanban built with Next.js (App Router) and React. The app is
gated behind a login (see `AuthGate`); once signed in, the board is loaded from
and persisted to the backend (`GET`/`PUT /api/board`), so edits survive reloads
and restarts. An AI chat sidebar (`ChatSidebar`) can read and change the board;
when the assistant returns an update the board UI refreshes automatically. The
app is built as a static export (`output: "export"` -> `out/`) and served by
FastAPI at `/`; there is no Node server in production.

## Stack

- Next.js 16 (App Router) and React 19, TypeScript.
- Tailwind CSS v4 (via `@tailwindcss/postcss`); theme tokens are CSS variables
  in `src/app/globals.css`.
- Drag and drop with `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`.
- `clsx` for conditional class names.
- Fonts: Space Grotesk (display) and Manrope (body), self-hosted via
  `next/font/local` from `src/app/fonts/*.woff2`. They are not fetched from
  Google at build/dev time, so the build and tests do not depend on the network.

## Structure

- `src/app/layout.tsx` - root layout, loads fonts and global CSS, sets metadata.
- `src/app/page.tsx` - home route; renders `AuthGate`.
- `src/app/globals.css` - Tailwind import and CSS variable theme tokens.
- `src/lib/kanban.ts` - data model and pure board logic (no React).
- `src/lib/api.ts` - thin client for the backend (`getMe`, `login`, `logout`,
  `getBoard`, `saveBoard`, `sendChat`); uses relative `/api` URLs with cookie
  credentials (same-origin in production). `getBoard` returns the user's
  `BoardData`; `saveBoard` PUTs the whole board as JSON; `sendChat(message,
  history)` POSTs to `/api/ai/chat` and returns `{ reply, board }`.
- `src/components/` - the board and auth UI (see below).
- `src/test/setup.ts`, `src/test/vitest.d.ts` - Vitest + Testing Library setup.

## Data model (`src/lib/kanban.ts`)

- `Card`: `{ id, title, details }`.
- `Column`: `{ id, title, cardIds: string[] }`.
- `BoardData`: `{ columns: Column[], cards: Record<string, Card> }` - cards are
  stored in a flat map; columns hold ordered card ids.
- `initialData` - the seeded demo board (5 columns, 8 cards).
- `moveCard(columns, activeId, overId)` - pure function returning new columns
  after a drag; handles reorder within a column and move across columns, with
  drops onto either a card or an empty column. Returns the input unchanged on
  no-op or invalid moves.
- `createId(prefix)` - generates a unique-ish id from random + timestamp.

## Components (`src/components/`)

- `AuthGate.tsx` - top-level gate (`"use client"`). On mount calls `getMe`;
  shows nothing while loading, `LoginForm` when unauthenticated, and
  `KanbanBoard` (with an `onLogout` handler) when authenticated.
- `LoginForm.tsx` - sign-in form; validates non-empty fields, calls `login`,
  shows an error on failure, and calls `onAuthed` on success.
- `KanbanBoard.tsx` - the board (`"use client"`). Takes an optional `onLogout`
  prop; when present, renders a Log out button in the header. On mount it loads
  the board via `getBoard` (showing a "Loading board..." placeholder until it
  arrives) into `useState<BoardData | null>`. All mutations go through a small
  `mutate(updater)` helper that sets state; a `useEffect` watching `board`
  persists each change via `saveBoard`, skipping the just-loaded board by
  comparing against a `persisted` ref (which also avoids resaving an unchanged
  board). Owns all handlers: drag start/end (delegates to `moveCard`), rename
  column, add card (`createId`), edit card, delete card. Sets up `DndContext`
  with a `PointerSensor` (6px activation) and `closestCorners` collision
  detection, and renders a `DragOverlay` preview. Also renders `ChatSidebar` and
  passes `applyServerBoard`, which adopts a board the backend already persisted
  (sets the `persisted` ref first so the save effect skips the redundant PUT).
- `ChatSidebar.tsx` - the AI chat (`"use client"`). A fixed bottom-right panel
  toggled open/closed. Holds the message list, input, and a sending flag. On
  submit it sends the message plus the prior turns as `history` to `sendChat`,
  appends the reply, and calls `onBoardUpdate(board)` so the board refreshes from
  the persisted state; a failed call shows an inline error and does not touch the
  board. Styled to the color scheme (purple submit, blue user bubbles).
- `KanbanColumn.tsx` - one column; a droppable region wrapping a `SortableContext`
  of cards, an editable title input (rename on change), an empty-state, and the
  `NewCardForm`. Exposes `data-testid="column-<id>"`.
- `KanbanCard.tsx` - a sortable card; whole card is the drag handle. Shows title,
  details, and Edit and Remove buttons. Edit swaps the card into an inline form
  (title input + details textarea, Save/Cancel); while editing, the drag
  listeners are omitted so the inputs are usable. Exposes
  `data-testid="card-<id>"`.
- `KanbanCardPreview.tsx` - presentational card used inside the drag overlay.
- `NewCardForm.tsx` - local open/closed + form state; validates a non-empty
  title, calls `onAdd(title, details)`, then resets and closes.

State flows top-down from `KanbanBoard`; child components are controlled via
callbacks and do not own board state (except `NewCardForm`'s local input state).

## Scripts

- `npm run dev` - Next dev server.
- `npm run build` / `npm run start` - production build / serve.
- `npm run lint` - ESLint (`eslint-config-next`).
- `npm run test` / `test:unit` - Vitest run (jsdom).
- `npm run test:unit:watch` - Vitest watch.
- `npm run test:e2e` - Playwright.
- `npm run test:all` - unit then e2e.

## Tests

- Unit (Vitest, jsdom): `src/**/*.{test,spec}.{ts,tsx}`. Coverage:
  `src/lib/kanban.test.ts` (`moveCard`, `createId`),
  `src/lib/api.test.ts` (`getBoard`/`saveBoard` request shape and error paths),
  `src/components/KanbanBoard.test.tsx` (stubs `fetch` so the board loads from a
  fake backend, then rename/add/edit/delete and asserts mutations PUT the full
  board), `src/components/KanbanCardPreview.test.tsx`,
  `src/components/ChatSidebar.test.tsx` (stubs `fetch`: sends message + history,
  renders the reply, refreshes the board via `onBoardUpdate`, shows an error on
  failure), and the auth flow in `LoginForm.test.tsx` / `AuthGate.test.tsx`
  (which stub `fetch`, so `api.ts` runs against a fake backend). Config in
  `vitest.config.ts`; `@` aliases to
  `src`. Coverage uses the v8 provider with an 80% lines/statements threshold
  over `src/components` and `src/lib` (the test command fails below it).
- E2E (Playwright): runs against the production-like server (FastAPI serving the
  built export) at `127.0.0.1:8000`, started by the `webServer` command in
  `playwright.config.ts` (`npm run build` then uvicorn with `PM_STATIC_DIR`
  pointed at `out/` and `PM_DB_PATH` pointed at a temp file so persistence does
  not touch the dev DB). `auth.spec.ts` covers the login gate and logout;
  `kanban.spec.ts` covers load, add, rename, edit, delete, drag, persistence
  across a reload and a fresh session, and an AI chat turn (mocking
  `/api/ai/chat` so the assistant returns a board update and the board refreshes
  without reload). Because the board is now shared server
  state (one row for the single MVP user), `kanban.spec.ts` resets it to the seed
  via the API in `beforeEach`, and the suite runs serially (`workers: 1`) so
  parallel tests do not race on that row. Specs live in `tests/` and are excluded
  from Vitest.

## Conventions

- Theme colors are referenced as CSS variables (for example
  `var(--navy-dark)`, `var(--primary-blue)`, `var(--accent-yellow)`), defined in
  `globals.css` to match the project color scheme.
- Board mutations go through pure helpers in `kanban.ts` where possible, keeping
  components thin.
- Stable `data-testid` hooks (`column-<id>`, `card-<id>`) back the e2e tests; keep
  them stable when refactoring.
