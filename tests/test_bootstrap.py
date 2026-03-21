from __future__ import annotations

from pathlib import Path
import sys

import httpx

from zush_jobqueue.bootstrap import ensure_server, runtime_settings


class _FakeResponse:
    def raise_for_status(self) -> None:
        return None


def test_ensure_server_returns_when_already_healthy(monkeypatch) -> None:
    calls: list[str] = []

    def fake_get(url: str, timeout: float) -> _FakeResponse:
        calls.append(url)
        return _FakeResponse()

    monkeypatch.setattr("zush_jobqueue.bootstrap.httpx.get", fake_get)

    result = ensure_server()

    assert result is True
    assert calls == ["http://127.0.0.1:16666/health"]


def test_ensure_server_spawns_when_server_is_missing(monkeypatch, tmp_path: Path) -> None:
    checks = {"count": 0}
    spawned: list[list[str]] = []

    def fake_get(url: str, timeout: float) -> _FakeResponse:
        checks["count"] += 1
        if checks["count"] < 3:
            raise httpx.ConnectError("down")
        return _FakeResponse()

    def fake_spawn(host: str, port: int) -> None:
        spawned.append([host, str(port)])

    monkeypatch.setattr("zush_jobqueue.bootstrap.httpx.get", fake_get)
    monkeypatch.setattr("zush_jobqueue.bootstrap.spawn_server_process", fake_spawn)

    result = ensure_server(timeout=1.0, poll_interval=0.01)

    assert result is True
    assert spawned == [["127.0.0.1", "16666"]]


def test_ensure_server_fails_gracefully_after_timeout(monkeypatch) -> None:
    spawned: list[tuple[str, int]] = []

    def fake_get(url: str, timeout: float) -> _FakeResponse:
        raise httpx.ConnectError("still down")

    def fake_spawn(host: str, port: int) -> None:
        spawned.append((host, port))

    monkeypatch.setattr("zush_jobqueue.bootstrap.httpx.get", fake_get)
    monkeypatch.setattr("zush_jobqueue.bootstrap.httpx_post_spawn_delay", 0.0)
    monkeypatch.setattr("zush_jobqueue.bootstrap.spawn_server_process", fake_spawn)

    result = ensure_server(timeout=0.05, poll_interval=0.01)

    assert result is False
    assert spawned == [("127.0.0.1", 16666)]


def test_runtime_settings_allow_test_overrides(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ZUSH_JOBQUEUE_HOST", "127.0.0.2")
    monkeypatch.setenv("ZUSH_JOBQUEUE_PORT", "17777")
    monkeypatch.setenv("ZUSH_JOBQUEUE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setenv("ZUSH_JOBQUEUE_PYTHON", sys.executable)

    settings = runtime_settings()

    assert settings.host == "127.0.0.2"
    assert settings.port == 17777
    assert settings.storage_dir == tmp_path
    assert settings.python_executable == Path(sys.executable)
