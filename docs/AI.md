# AI connectivity

How the backend talks to the model. This is the Part 8 deliverable: prove the
backend can reach OpenRouter and record whether the model honors strict
Structured Outputs (which de-risks Part 9).

## Provider and model

- Provider: OpenRouter, OpenAI-compatible Chat Completions API at
  `https://openrouter.ai/api/v1/chat/completions`.
- Model: `openai/gpt-oss-120b`.
- Auth: bearer token from `OPENROUTER_API_KEY`.

## Key handling

- The key lives in the project-root `.env` (git-ignored, and excluded from the
  Docker image via `.dockerignore`).
- `app/ai.py` calls `load_dotenv` on the root `.env` so local dev, tests, and the
  diagnostic route find the key. In Docker there is no `.env` file; the start
  scripts pass it in with `docker run --env-file .env`, and `load_dotenv` does
  not override an already-set variable.
- Missing key fails clearly: `ask` raises `AIError` and `GET /api/ai/health`
  returns 503 with the reason. There is no silent fallback.

## Client

`app/ai.py`:

- `ask(prompt)` POSTs a single user message and returns
  `choices[0].message.content`.
- `GET /api/ai/health` (auth-gated) asks "What is 2+2?" and returns
  `{ "answer": ... }`. This is the diagnostic that proves connectivity.
- `chat(board, history, message)` runs one structured turn (see below).
- `POST /api/ai/chat` (auth-gated) `{ message, history }` -> `{ reply, board }`.

## Structured chat over the board (Part 9)

Each chat turn sends a system message (instructions + the current board JSON),
the prior conversation history, and the user's message, and requests strict
Structured Outputs with this schema:

```
{ reply: string, board_update: AiBoard | null }
```

`reply` is the user-facing text. `board_update` is null when the turn changes
nothing; otherwise it is the COMPLETE updated board, which is persisted via the
same whole-board replace as `PUT /api/board`.

### cards: array on the wire, map in storage

The stored board keeps cards as a map keyed by id (`Record<string, Card>`), but
strict Structured Outputs cannot express an object with dynamic keys (it requires
`additionalProperties: false` and a fixed property set). So the AI schema carries
cards as an **array** (`AiBoard`), and the server converts:

- `_board_to_ai` (map -> array) for the board JSON sent to the model.
- `_board_from_ai` (array -> map) for an incoming `board_update`.

### Validation and safety

`_validated_update` converts an incoming `board_update` to storage shape and runs
it through the Pydantic `Board` model. A malformed update is dropped (returns
`None`) so it never corrupts the stored board; the `reply` still reaches the user.
This holds even though strict outputs should already conform - the server does not
trust the model.

### Live check (2026-06-22)

CONFIRMED. Beyond the mocked tests, a live smoke run of `chat`
(`test_live_chat_updates_board`, opt-in) asked the real model to add a card and
verified it accepted the strict chat schema (nested arrays plus a nullable
`board_update` via `anyOf`) and returned a valid update that passed server-side
validation. So the richer chat schema works live, not just the simple Part 8
probe.

## Tests

- Mocked unit tests (no network): `ask` builds the correct request and parses the
  reply; missing key raises; the route gates on auth, returns the answer, and
  reports a missing key as 503. These run in CI without a key.
- Opt-in live tests (`test_live_*` in `tests/test_ai.py`) are skipped unless both
  `OPENROUTER_API_KEY` and `RUN_LIVE_AI` are set, so a normal `pytest` never
  makes a paid call. Run them with:

  ```sh
  RUN_LIVE_AI=1 uv run pytest tests/test_ai.py -k live
  ```

## Structured Outputs verification (for Part 9)

Part 9 wants the model to return a strict JSON object (`{ reply, board_update? }`).
The live test `test_live_structured_outputs` sends a request with
`response_format: { type: "json_schema", json_schema: { strict: true, schema } }`
and asserts the reply parses as JSON matching the schema.

Result (live run, 2026-06-22): CONFIRMED. `openai/gpt-oss-120b` on OpenRouter
honored a strict `json_schema` request and returned valid JSON conforming to the
schema (both live tests passed). So Part 9 will request strict Structured Outputs
directly (`response_format: { type: "json_schema", json_schema: { strict: true,
schema } }`) rather than falling back to plain JSON mode.

Regardless, Part 9 still validates the parsed response against the schema
server-side rather than trusting the model.
