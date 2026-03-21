# Tech Context: zush_jobqueue

## Technologies

- Python project managed with uv.
- HTTP server target: FastAPI.
- ASGI server target: uvicorn.
- CLI integration target: zush plugin commands.
- Tests: pytest.

## Expected dependencies

- `fastapi`
- `uvicorn`
- `httpx` for client communication and tests
- `pytest`

## Runtime constraints

- Default port is fixed at `16666` unless future config introduces overrides.
- Detached startup must work on Windows.
- The server must not depend on the parent CLI process staying alive.
- Job execution should use dedicated handlers per job type.
- Tests may overload host, port, storage dir, and Python executable through runtime environment variables.
- `zushcmd` subprocesses should force UTF-8 output on Windows to avoid `UnicodeEncodeError` when zush prints tree glyphs.
- Restore snapshots are consumed on startup and persisted back to `state.json`.
- CLI `add` now accepts either a raw payload argument or a JSON file path via `--payload-file`.
- CLI and HTTP both expose a per-name completion check surface.

## Integration points

- Reuse zush path conventions for locating `~/.zush`.
- Keep jobqueue persistence independent from zush plugin persistedCtx.
- For `zushcmd` jobs, execute zush commands through a controlled integration path.

## Open implementation details

- Define the exact server health endpoint used by CLI bootstrap.
- Decide the internal persistence file schema for queue state and restore data.
- Decide whether background execution uses threads, subprocesses, or both per job type.