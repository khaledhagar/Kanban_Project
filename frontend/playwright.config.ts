import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

// E2E runs against the production-like setup: FastAPI serving the built static
// export. This exercises the real API (auth, etc.) and matches how the app is
// shipped, instead of the bare Next dev server.
export default defineConfig({
  testDir: "./tests",
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
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
