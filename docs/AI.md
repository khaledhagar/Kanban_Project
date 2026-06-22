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
