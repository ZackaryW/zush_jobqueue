# Progress: zush_jobqueue

## What exists

- uv-managed package with runtime dependencies for FastAPI, uvicorn, httpx, click, and local zush integration.
- FastAPI server with add, get, queue, queue listing, start, queuekill, complete, quit, and health endpoints.
- Detached bootstrap flow that checks health, spawns the server when absent, and times out gracefully.
- Runtime overrides for host, port, storage directory, and Python executable to support isolated tests and disposable servers.
- Separate executor modules for `zushcmd`, `cmd`, `python`, and `sleep` jobs.
- Standalone CLI plus zush plugin entrypoint.
- Dedicated storage and daily completion logging under `~/.zush/jobqueue/`.
- Passing pytest suite covering paths, bootstrap, HTTP API, CLI behavior, real-process queuekill behavior, and real `cmd`/`zushcmd` subprocess execution.
- Windows-specific `zushcmd` UTF-8 subprocess handling to prevent encoding failures from zush tree output.
- `add` supports payload files.
- Restore snapshots are loaded on startup, consumed, and written into active state.
- Forced completion of active long-running jobs is tracked as cancellation.
- Dedicated per-name completion checks are available via `check` CLI and `/check/{name}`.
- `check --wait` can block until the queue reaches a terminal state or times out.

## What was decided

- FastAPI server on port `16666`.
- Detached background process startup.
- HTTP endpoints for add, get, queue, queue listing, start, queuekill, complete, and quit.
- Dedicated storage under `~/.zush/jobqueue/`.
- Completion logging under `logs/{date}.json`.
- TDD-first implementation.

## What is next

- Add deeper runtime tests for subprocess cancellation details and multi-step payload results.
- Refine queue inspection and result retrieval ergonomics.
- Decide whether restore behavior needs an explicit opt-out for certain launches.