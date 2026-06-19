# Scripts

Start and stop scripts for the Project Management MVP Docker container. Use the
`.sh` scripts on Mac and Linux and the `.ps1` scripts on Windows; both pairs do
the same thing.

## Scripts

- `start.sh` / `start.ps1` - build the image from the repo-root `Dockerfile`,
  remove any existing `pm-mvp` container, then run a new one. Prints the URL.
  The `Dockerfile` is multi-stage: it builds the Next.js static export, then
  copies it into the FastAPI runtime image, so no separate frontend build step
  is needed.
- `stop.sh` / `stop.ps1` - stop and remove the `pm-mvp` container (no-op if it is
  not running).

## Conventions

- Image and container are both named `pm-mvp`.
- The app listens on container port 8000. Host port defaults to 8000 and can be
  overridden with the `PORT` environment variable (e.g. `PORT=9000 ./start.sh`).
- After `start`, the app is at `http://localhost:<PORT>/` and health is at
  `http://localhost:<PORT>/api/health`.
- Build and run failures are fatal (`set -euo pipefail`;
  `$PSNativeCommandUseErrorActionPreference` in PowerShell). The pre-run
  container cleanup is best-effort so a missing container does not abort start.

## Requirements

- Docker must be running. On Windows that means Docker Desktop is started.
