import { defineConfig, devices } from "@playwright/test";
import os from "node:os";
import path from "node:path";

// E2E runs against the production-like setup: FastAPI serving the built static
// export. This exercises the real API (auth, etc.) and matches how the app is
// shipped, instead of the bare Next dev server.
export default defineConfig({
  testDir: "./tests",
  // The board is now shared server state (one row for the single MVP user), so
  // tests reset and mutate the same board. Run serially to keep them isolated;
  // parallel workers would race on that shared row.
  workers: 1,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      "npm run build && uv run --directory ../backend uvicorn app.main:app --host 127.0.0.1 --port 8000",
    url: "http://127.0.0.1:8000/api/health",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    cwd: __dirname,
    env: {
      PM_STATIC_DIR: path.resolve(__dirname, "out"),
      // Isolate persistence from the dev database; the suite seeds per test.
      PM_DB_PATH: path.join(os.tmpdir(), "pm-e2e.db"),
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
