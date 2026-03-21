from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 16666
httpx_post_spawn_delay = 0.2


@dataclass(frozen=True)
class RuntimeSettings:
    host: str
    port: int
    storage_dir: Path | None
    python_executable: Path


def runtime_settings() -> RuntimeSettings:
    raw_port = os.environ.get("ZUSH_JOBQUEUE_PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except ValueError:
        port = DEFAULT_PORT
    storage_dir_raw = os.environ.get("ZUSH_JOBQUEUE_STORAGE_DIR")
    python_raw = os.environ.get("ZUSH_JOBQUEUE_PYTHON", sys.executable)
    return RuntimeSettings(
        host=os.environ.get("ZUSH_JOBQUEUE_HOST", DEFAULT_HOST),
        port=port,
        storage_dir=Path(storage_dir_raw) if storage_dir_raw else None,
        python_executable=Path(python_raw),
    )


def health_url(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> str:
    return f"http://{host}:{port}/health"


def is_server_healthy(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
    try:
        response = httpx.get(health_url(host, port), timeout=1.0)
        response.raise_for_status()
    except httpx.HTTPError:
        return False
    return True


def spawn_server_process(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    settings = runtime_settings()
    command = [
        str(settings.python_executable),
        "-m",
        "zush_jobqueue",
        "serve",
        "--host",
        host,
        "--port",
        str(port),
    ]
    if settings.storage_dir is not None:
        command.extend(["--storage-dir", str(settings.storage_dir)])
    kwargs = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(command, **kwargs)


def ensure_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = 5.0,
    poll_interval: float = 0.1,
) -> bool:
    settings = runtime_settings()
    if host == DEFAULT_HOST:
        host = settings.host
    if port == DEFAULT_PORT:
        port = settings.port
    if is_server_healthy(host, port):
        return True
    spawn_server_process(host, port)
    if httpx_post_spawn_delay > 0:
        time.sleep(httpx_post_spawn_delay)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_server_healthy(host, port):
            return True
        time.sleep(poll_interval)
    return False