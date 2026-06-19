# Frontend

A single-board Kanban demo built with Next.js (App Router) and React. This is
currently a pure client-side demo: all board state lives in memory and resets on
reload. There is no auth, persistence, or backend wiring yet. Later parts of the
plan add static export, a login gate, backend persistence, and an AI chat
sidebar (see ../docs/PLAN.md).

## Stack

- Next.js 16 (App Router) and React 19, TypeScript.
- Tailwind CSS v4 (via `@tailwindcss/postcss`); theme tokens are CSS variables
  in `src/app/globals.css`.
- Drag and drop with `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/utilities`.
- `clsx` for conditional class names.
- Fonts: Space Grotesk (display) and Manrope (body) via `next/font/google`.

## Structure

- `src/app/layout.tsx` - root layout, loads fonts and global CSS, sets metadata.
- `src/app/page.tsx` - home route; renders `KanbanBoard`.
- `src/app/globals.css` - Tailwind import and CSS variable theme tokens.
- `src/lib/kanban.ts` - data model and pure board logic (no React).
- `src/components/` - the board UI (see below).
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

- `KanbanBoard.tsx` - the only stateful component (`"use client"`). Holds
  `BoardData` in `useState(initialData)` and the active drag id. Owns all
  handlers: drag start/end (delegates to `moveCard`), rename column, add card
  (`createId`), delete card. Sets up `DndContext` with a `PointerSensor`
  (6px activation) and `closestCorners` collision detection, and renders a
  `DragOverlay` preview.
- `KanbanColumn.tsx` - one column; a droppable region wrapping a `SortableContext`
  of cards, an editable title input (rename on change), an empty-state, and the
  `NewCardForm`. Exposes `data-testid="column-<id>"`.
- `KanbanCard.tsx` - a sortable card; whole card is the drag handle. Shows title,
  details, and a Remove button. Exposes `data-testid="card-<id>"`.
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

- Unit (Vitest, jsdom): `src/**/*.{test,spec}.{ts,tsx}`. Existing coverage:
  `src/lib/kanban.test.ts` (board logic), `src/components/KanbanBoard.test.tsx`
  (board interactions). Config in `vitest.config.ts`; `@` aliases to `src`.
  Coverage uses the v8 provider; no minimum threshold is set yet (the plan
  requires adding an 80% floor).
- E2E (Playwright): `tests/kanban.spec.ts` covers load, add card, and drag
  between columns. Config in `playwright.config.ts` runs against the dev server
  on `127.0.0.1:3000`. Playwright specs live in `tests/` and are excluded from
  Vitest.

## Conventions

- Theme colors are referenced as CSS variables (for example
  `var(--navy-dark)`, `var(--primary-blue)`, `var(--accent-yellow)`), defined in
  `globals.css` to match the project color scheme.
- Board mutations go through pure helpers in `kanban.ts` where possible, keeping
  components thin.
- Stable `data-testid` hooks (`column-<id>`, `card-<id>`) back the e2e tests; keep
  them stable when refactoring.
