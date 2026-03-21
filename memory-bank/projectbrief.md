# Project Brief: zush_jobqueue

## Project

zush_jobqueue is a zush extension that provides a detached local job queue server and CLI commands that communicate with it.

## Goal

- Start and manage a lightweight HTTP server on port 16666.
- Keep the server detached from the invoking CLI process so queued work survives the caller exiting.
- Store queue state, logs, and restore data under the zush config tree in a dedicated `jobqueue` area.
- Expose both HTTP endpoints and zush CLI commands for queue operations.

## Server contract

- Framework target: FastAPI.
- Default port: `16666`.
- Named queues execute FIFO with one running job per queue.
- Before each CLI command that depends on the server, check whether the server is reachable.
- If the server is not reachable, spawn it in detached mode and wait up to a timeout.
- If the server still cannot be reached after spawn, exit gracefully.

## Endpoints

- `POST /add/{name}` accepts `list[dict]` job definitions and stores them as the named payload.
- `GET /get/{name}` returns the stored payload for the name.
- `PUT /queue/{name}` enqueues the named payload.
- `GET /queue` returns queue state.
- `GET /start/{name}` returns the named payload and starts queuekill timing when configured.
- `POST /queuekill/{name}` configures max lifetime and a target action.
- `POST /complete/{name}` forces the running job to be marked complete.
- `POST /quit` shuts the server down; request body may enable restore persistence.

## Job types

Each job item is a dict with a type-specific shape.

- `type = "zushcmd"`: run a zush command path with args and kwargs.
- `type = "cmd"`: run an OS command.
- `type = "python"`: run Python code.
- `type = "sleep"`: sleep for a number of seconds.

## Persistence

- Use a dedicated structure under `~/.zush/jobqueue/`.
- Keep server state independent from plugin persistedCtx storage.
- Write completion logs to `~/.zush/jobqueue/logs/{date}.json`.
- On quit with restore enabled, save queue state to the jobqueue storage area.