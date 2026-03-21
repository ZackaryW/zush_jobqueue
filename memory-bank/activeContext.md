# Active Context: zush_jobqueue

## Current focus

Detached queue server, CLI wrapper, zush plugin surface, restore-on-start behavior, and real-process integration coverage are implemented.

## Confirmed decisions

- Use uv for project workflow.
- Use FastAPI for the server.
- Listen on port `16666`.
- Spawn the server as a separate background Python process.
- One running job per named queue, FIFO order.
- Add `POST /complete/{name}`.
- Store data under `~/.zush/jobqueue/` rather than persisted plugin config.
- Write completion logs under `~/.zush/jobqueue/logs/{date}.json`.
- Force UTF-8 for `zushcmd` subprocess execution so Windows can handle zush tree output reliably.
- Allow `add` payload input from either inline JSON or `--payload-file`.
- Consume `restore.json` on startup by loading it into active state and rewriting `state.json`.
- Treat forced completion of an actively running job as cancellation in queue status and logs.
- Provide a dedicated `check` command and `/check/{name}` endpoint for per-queue completion state.
- `check` also supports `--wait` with timeout and poll interval controls for blocking completion checks.

## Confirmed job item types

- `zushcmd`
- `cmd`
- `python`
- `sleep`

## Confirmed queuekill behavior

- On max lifetime, stop tracking the running job, shift to the next action, and run the configured target job.

## Next steps

- Expand tests around richer subprocess payload behavior and cancellation edge cases.
- Decide whether startup should auto-restore and clear restore snapshots after successful load.
- Add richer queue inspection and result query endpoints.