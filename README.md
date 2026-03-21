# zush_jobqueue

Detached job queue extension for zush.

## Features

- FastAPI server on port `16666`
- Detached background startup when the CLI needs the server
- Named FIFO queues with one running job per queue
- Job types: `zushcmd`, `cmd`, `python`, `sleep`
- Queuekill configuration with fallback action
- `add` supports inline JSON or `--payload-file`
- Queue restore and daily completion logs under `~/.zush/jobqueue/`

## Storage

- State: `~/.zush/jobqueue/state.json`
- Restore snapshot: `~/.zush/jobqueue/restore.json`
- Logs: `~/.zush/jobqueue/logs/YYYY-MM-DD.json`

## Runtime Overrides

For testing and isolated runs, the runtime can be redirected without touching the default user config tree.

- `ZUSH_JOBQUEUE_HOST`
- `ZUSH_JOBQUEUE_PORT`
- `ZUSH_JOBQUEUE_STORAGE_DIR`
- `ZUSH_JOBQUEUE_PYTHON`

The standalone server also accepts `--storage-dir`:

```bash
uv run zush-jobqueue serve --port 17777 --storage-dir ./.tmp-jobqueue
```

This is intended for integration tests and disposable local verification.

## Standalone CLI

```bash
uv run zush-jobqueue serve
uv run zush-jobqueue add build '[{"type":"sleep","int":1}]'
uv run zush-jobqueue add build --payload-file ./payload.json
uv run zush-jobqueue queue build
uv run zush-jobqueue start build
uv run zush-jobqueue check build
uv run zush-jobqueue check build --wait --timeout 30
uv run zush-jobqueue complete build
uv run zush-jobqueue quit --restore
```

If a restore snapshot exists at startup, the server loads it into active state and consumes the snapshot file.

When `complete` is called for an actively running long-lived job, the running work is cancelled and the queue status is recorded as `cancelled`.

`check <name>` returns the current per-queue completion view, including `completed`, `status`, `running`, and `pending`.

`check --wait` polls until the named queue reaches a terminal completed state or the timeout expires.

## zush extension

The package exposes `src/zush_jobqueue/__zush__.py`, so zush can discover it as a plugin package and mount the `jobqueue` command group.

## Development

```bash
uv sync
uv run pytest
```

The test suite includes a real-process integration test that starts the server on an isolated port and storage directory, then verifies queuekill preemption through actual HTTP calls.
It also covers real `cmd` and `zushcmd` subprocess execution, forced cancellation of long-running jobs, and restore-on-start behavior.
