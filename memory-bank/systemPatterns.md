# System Patterns: zush_jobqueue

## Architecture

- A zush extension exposes CLI commands.
- CLI commands communicate with a local FastAPI server over HTTP.
- The server owns queue state, execution state, restore data, and logging.
- The server is spawned as a detached background process when absent.

## High-level flow

1. User runs a zush jobqueue CLI command.
2. CLI checks whether the server on port `16666` is healthy.
3. If unavailable, CLI spawns the server in detached mode and waits for readiness.
4. If readiness fails before timeout, CLI exits gracefully.
5. CLI sends the requested HTTP command to the server.
6. Server mutates queue state and optionally starts or advances execution.

## Queue model

- Queue namespace is keyed by `name`.
- Each named queue has:
  - stored payload definition
  - pending queue entries
  - at most one running entry
  - optional queuekill configuration
- Execution is FIFO within each named queue.
- Force-complete advances the queue to the next item.

## Queuekill model

- Queuekill is configured per named queue.
- Starting a queue with queuekill configured begins a max-lifetime timer.
- If the running job exceeds max lifetime, the server preempts that job and runs the configured target action.

## Storage layout

- Base directory: `~/.zush/jobqueue/`
- Expected children:
  - server state
  - restore payloads
  - logs
- Completion logs append to per-day JSON files.

## TDD requirement

- Write failing tests first.
- Implement the minimum code to satisfy the tests.
- Keep the extension isolated from unrelated zush core behavior.