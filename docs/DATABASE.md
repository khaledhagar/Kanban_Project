# Database design

How the Kanban data is persisted. This document is the Part 5 deliverable and
must be approved before Part 6 (backend persistence) begins.

## Goals

- Persist each user's single Kanban board across restarts.
- Support multiple users in the schema, even though the MVP signs in only the
  hardcoded `user`.
- Stay simple: the board is read and written as a whole, so model it that way.

## Storage choice: JSON blob per board

The board is stored as one JSON document in a `TEXT` column, not as relational
`columns`/`cards` tables.

Why:

- The frontend already owns the board as a single `BoardData` value, and the API
  (per the plan) reads it with `GET /api/board` and replaces it with
  `PUT /api/board`. There is no query that needs individual cards or columns.
- A JSON blob mirrors the frontend shape exactly, so there is no mapping layer
  and no schema churn when the board shape evolves (e.g. adding a card field).
- Relational tables for columns/cards would add joins, ordering columns, and
  write fan-out for zero benefit at this scale (one board per user).

Trade-off accepted: the database cannot query inside a board (e.g. "find all
cards titled X"). That is not a requirement now; if it ever becomes one, the
JSON can be migrated into relational tables later.

## Schema

Two tables. SQLite types are dynamic; the declared types document intent.

### `users`

| Column       | Type    | Constraints                                  | Notes                          |
| ------------ | ------- | -------------------------------------------- | ------------------------------ |
| `id`         | INTEGER | PRIMARY KEY AUTOINCREMENT                    | Surrogate key.                 |
| `username`   | TEXT    | NOT NULL UNIQUE                              | `user` for the MVP.            |
| `created_at` | TEXT    | NOT NULL DEFAULT (datetime('now'))           | ISO-8601 UTC.                  |

No password column for the MVP: credentials are hardcoded in the backend. When
real auth arrives, add a nullable `password_hash` column (a backward-compatible
change).

### `boards`

| Column       | Type    | Constraints                                       | Notes                                   |
| ------------ | ------- | ------------------------------------------------- | --------------------------------------- |
| `id`         | INTEGER | PRIMARY KEY AUTOINCREMENT                          | Surrogate key.                          |
| `user_id`    | INTEGER | NOT NULL UNIQUE REFERENCES `users(id)`            | UNIQUE enforces one board per user.     |
| `data`       | TEXT    | NOT NULL                                          | JSON `BoardData` (see below).           |
| `created_at` | TEXT    | NOT NULL DEFAULT (datetime('now'))                | ISO-8601 UTC.                           |
| `updated_at` | TEXT    | NOT NULL DEFAULT (datetime('now'))                | Set to now on every write.              |

The `UNIQUE` constraint on `user_id` is what guarantees the MVP rule of exactly
one board per user, while still allowing the table to hold many users' boards.

```sql
CREATE TABLE IF NOT EXISTS users (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  username   TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS boards (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    INTEGER NOT NULL UNIQUE REFERENCES users(id),
  data       TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## JSON payload (`boards.data`)

Exactly the frontend `BoardData` shape (`src/lib/kanban.ts`): an ordered list of
columns, each holding ordered card ids, plus a flat map of cards.

```json
{
  "columns": [
    { "id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"] },
    { "id": "col-done", "title": "Done", "cardIds": [] }
  ],
  "cards": {
    "card-1": { "id": "card-1", "title": "Align roadmap", "details": "..." },
    "card-2": { "id": "card-2", "title": "Gather signals", "details": "..." }
  }
}
```

The backend stores and returns this verbatim; it validates the top-level shape
(Part 9 needs this for AI updates) but does not otherwise reshape it.

## Database file creation

- One SQLite file. Path comes from `PM_DB_PATH`, defaulting to
  `backend/data/pm.db` (which is `/app/data/pm.db` inside the container).
- On startup the backend runs the `CREATE TABLE IF NOT EXISTS` statements above.
  SQLite creates the file itself if it is missing, so first run just works.
- The hardcoded `user` row is ensured on startup with `INSERT OR IGNORE`.

## Seeding a board

A user's board row is created lazily: the first time `GET /api/board` runs and
the user has no row, the backend inserts one seeded with the demo board (the
same five columns and eight cards as the current frontend `initialData`). This
keeps the first sign-in identical to today's demo, then persists from there.

## Persistence across container restarts

The DB file must outlive the container, because `scripts/start` removes and
recreates the container on each run. Part 6 will mount a named Docker volume at
the data directory (`-v pm-data:/app/data`) so `/app/data/pm.db` survives
restarts and rebuilds. Local (non-Docker) runs persist to `backend/data/pm.db`.
The `data/` directory and `*.db` files are git-ignored.

## Access approach

- Standard-library `sqlite3` (no ORM). The access pattern is "read one row,
  write one row," so an ORM would add weight without value.
- A short-lived connection per request, with `row_factory` set for dict-like
  rows and foreign keys enabled (`PRAGMA foreign_keys = ON`).
- Writes use a single `UPSERT` (`INSERT ... ON CONFLICT(user_id) DO UPDATE`) so
  saving the board is one statement that also bumps `updated_at`.

## Migrations

For the MVP, schema setup is idempotent `CREATE TABLE IF NOT EXISTS` at startup;
there is no migration framework. Future schema changes (e.g. adding
`password_hash`) would be applied as additional idempotent `ALTER`/`CREATE`
statements at startup. This is sufficient for a single-file local database.
