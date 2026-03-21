# Product Context: zush_jobqueue

## Why this project exists

zush needs a durable local queue runner that can accept work from CLI commands, keep running after the caller exits, and persist queue state in the same user-owned config area as the rest of the zush ecosystem.

## Problems it solves

- Avoid tying long-running jobs to a foreground CLI process.
- Provide a stable local API for queue operations.
- Let the CLI reuse the same queue server instead of spawning ad hoc workers.
- Persist queue, restore, and log data in a predictable location.

## User experience goals

- Queue commands should feel immediate.
- Starting the server should be automatic when needed.
- Failure to connect after spawn should be explicit and graceful.
- Queue behavior should be predictable: FIFO, one running job per named queue.
- Logs and restore state should be inspectable on disk.

## Primary workflows

- Add a payload under a queue name.
- Enqueue that payload.
- Inspect queue contents.
- Start a named job sequence.
- Configure queuekill behavior for a named queue.
- Force-complete a running job.
- Quit the server and optionally persist restorable state.