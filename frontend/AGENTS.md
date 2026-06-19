# Frontend

A single-board Kanban demo built with Next.js (App Router) and React. The app is
gated behind a login (see `AuthGate`); board state still lives in memory and
resets on reload (no backend persistence yet). The app is built as a static
export (`output: "export"` -> `out/`) and served by FastAPI at `/`; there is no
Node server in production. Later parts of the plan add backend persistence and an
AI chat sidebar (see ../docs/PLAN.md).

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
- `src/lib/api.ts` - thin client for the backend (`getMe`, `login`, `logout`);
  uses relative `/api` URLs with cookie credentials (same-origin in production).
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
  prop; when present, renders a Log out button in the header. Holds
  `BoardData` in `useState(initialData)` and the active drag id. Owns all
  handlers: drag start/end (delegates to `moveCard`), rename column, add card
  (`createId`), edit card, delete card. Sets up `DndContext` with a `PointerSensor`
  (6px activation) and `closestCorners` collision detection, and renders a
  `DragOverlay` preview.
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
  `src/components/KanbanBoard.test.tsx` (rename, add, edit, delete),
  `src/components/KanbanCardPreview.test.tsx`, and the auth flow in
  `LoginForm.test.tsx` / `AuthGate.test.tsx` (which stub `fetch`, so `api.ts`
  runs against a fake backend). Config in `vitest.config.ts`; `@` aliases to
  `src`. Coverage uses the v8 provider with an 80% lines/statements threshold
  over `src/components` and `src/lib` (the test command fails below it).
- E2E (Playwright): runs against the production-like server (FastAPI serving the
  built export) at `127.0.0.1:8000`, started by the `webServer` command in
  `playwright.config.ts` (`npm run build` then uvicorn with `PM_STATIC_DIR`
  pointed at `out/`). `auth.spec.ts` covers the login gate and logout;
  `kanban.spec.ts` covers load, add, rename, edit, delete, and drag (logging in
  via the API in `beforeEach`). Specs live in `tests/` and are excluded from
  Vitest.

## Conventions

- Theme colors are referenced as CSS variables (for example
  `var(--navy-dark)`, `var(--primary-blue)`, `var(--accent-yellow)`), defined in
  `globals.css` to match the project color scheme.
- Board mutations go through pure helpers in `kanban.ts` where possible, keeping
  components thin.
- Stable `data-testid` hooks (`column-<id>`, `card-<id>`) back the e2e tests; keep
  them stable when refactoring.
