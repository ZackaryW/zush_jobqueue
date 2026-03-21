from __future__ import annotations

import json
import time
from pathlib import Path

import click
import uvicorn
from zush.paths import DirectoryStorage

from zush_jobqueue.bootstrap import DEFAULT_HOST, DEFAULT_PORT, ensure_server, runtime_settings
from zush_jobqueue.client import JobQueueClient
from zush_jobqueue.server import create_app


def _json_echo(payload) -> None:
    click.echo(json.dumps(payload))


def _load_payload(payload: str | None, payload_file: Path | None):
    if payload_file is not None:
        return json.loads(payload_file.read_text(encoding="utf-8"))
    if payload is None:
        raise click.UsageError("Provide PAYLOAD or --payload-file")
    return json.loads(payload)


def _require_server() -> JobQueueClient:
    if not ensure_server():
        raise click.ClickException("Unable to reach jobqueue server")
    return JobQueueClient()


def _check_until_complete(
    client: JobQueueClient,
    name: str,
    wait: bool,
    timeout: float,
    poll_interval: float,
):
    result = client.check(name)
    if not wait or result.get("completed"):
        return result

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(poll_interval)
        result = client.check(name)
        if result.get("completed"):
            return result
    raise click.ClickException(f"Timed out waiting for queue completion: {name}")


def build_cli(include_serve: bool = True) -> click.Group:
    @click.group()
    def cli() -> None:
        return None

    @cli.command("add")
    @click.argument("name")
    @click.argument("payload", required=False)
    @click.option("--payload-file", type=click.Path(path_type=Path, exists=True, dir_okay=False))
    def add_command(name: str, payload: str | None, payload_file: Path | None) -> None:
        client = _require_server()
        parsed = _load_payload(payload, payload_file)
        _json_echo(client.add(name, parsed))

    @cli.command("get")
    @click.argument("name")
    def get_command(name: str) -> None:
        client = _require_server()
        _json_echo(client.get(name))

    @cli.command("queue")
    @click.argument("name")
    def queue_command(name: str) -> None:
        client = _require_server()
        _json_echo(client.queue(name))

    @cli.command("list")
    def list_command() -> None:
        client = _require_server()
        _json_echo(client.list_queue())

    @cli.command("check")
    @click.argument("name")
    @click.option("--wait", is_flag=True, default=False)
    @click.option("--timeout", type=float, default=30.0, show_default=True)
    @click.option("--poll-interval", type=float, default=0.25, show_default=True)
    def check_command(name: str, wait: bool, timeout: float, poll_interval: float) -> None:
        client = _require_server()
        _json_echo(_check_until_complete(client, name, wait, timeout, poll_interval))

    @cli.command("start")
    @click.argument("name")
    def start_command(name: str) -> None:
        client = _require_server()
        _json_echo(client.start(name))

    @cli.command("queuekill")
    @click.argument("name")
    @click.argument("max_lifetime", type=float)
    @click.argument("action")
    def queuekill_command(name: str, max_lifetime: float, action: str) -> None:
        client = _require_server()
        _json_echo(client.queuekill(name, max_lifetime, action))

    @cli.command("complete")
    @click.argument("name")
    def complete_command(name: str) -> None:
        client = _require_server()
        _json_echo(client.complete(name))

    @cli.command("quit")
    @click.option("--restore/--no-restore", default=False)
    def quit_command(restore: bool) -> None:
        client = _require_server()
        _json_echo(client.quit(restore=restore))

    if include_serve:
        @cli.command("serve")
        @click.option("--host", default=None)
        @click.option("--port", default=None, type=int)
        @click.option("--storage-dir", type=click.Path(path_type=Path, file_okay=False, dir_okay=True))
        def serve_command(host: str | None, port: int | None, storage_dir: Path | None) -> None:
            settings = runtime_settings()
            resolved_host = host or settings.host or DEFAULT_HOST
            resolved_port = port or settings.port or DEFAULT_PORT
            resolved_storage = storage_dir or settings.storage_dir
            server = None

            def request_shutdown() -> None:
                if server is not None:
                    server.should_exit = True

            storage = DirectoryStorage(resolved_storage) if resolved_storage is not None else None
            app = create_app(storage=storage, shutdown_callback=request_shutdown)
            config = uvicorn.Config(app, host=resolved_host, port=resolved_port, log_level="warning")
            nonlocal_server = uvicorn.Server(config)
            server = nonlocal_server
            app.state.manager.set_shutdown_callback(request_shutdown)
            nonlocal_server.run()

    return cli