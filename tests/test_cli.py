from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from zush_jobqueue.cli import build_cli


def test_cli_add_command_uses_http_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("zush_jobqueue.cli.ensure_server", lambda: True)

    class _FakeClient:
        def add(self, name: str, payload: list[dict]) -> dict:
            captured["name"] = name
            captured["payload"] = payload
            return {"ok": True}

    monkeypatch.setattr("zush_jobqueue.cli.JobQueueClient", lambda: _FakeClient())

    result = CliRunner().invoke(build_cli(), ["add", "deploy", '[{"type":"sleep","int":1}]'])

    assert result.exit_code == 0
    assert captured == {"name": "deploy", "payload": [{"type": "sleep", "int": 1}]}
    assert json.loads(result.output) == {"ok": True}


def test_cli_exits_when_server_cannot_be_started(monkeypatch) -> None:
    monkeypatch.setattr("zush_jobqueue.cli.ensure_server", lambda: False)

    result = CliRunner().invoke(build_cli(), ["queue", "deploy"])

    assert result.exit_code != 0
    assert "Unable to reach jobqueue server" in result.output


def test_cli_add_command_accepts_payload_file(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    payload_file = tmp_path / "payload.json"
    payload_file.write_text('[{"type":"sleep","int":2}]', encoding="utf-8")

    monkeypatch.setattr("zush_jobqueue.cli.ensure_server", lambda: True)

    class _FakeClient:
        def add(self, name: str, payload: list[dict]) -> dict:
            captured["name"] = name
            captured["payload"] = payload
            return {"ok": True}

    monkeypatch.setattr("zush_jobqueue.cli.JobQueueClient", lambda: _FakeClient())

    result = CliRunner().invoke(build_cli(), ["add", "deploy", "--payload-file", str(payload_file)])

    assert result.exit_code == 0
    assert captured == {"name": "deploy", "payload": [{"type": "sleep", "int": 2}]}
    assert json.loads(result.output) == {"ok": True}


def test_cli_check_command_uses_http_client(monkeypatch) -> None:
    monkeypatch.setattr("zush_jobqueue.cli.ensure_server", lambda: True)

    class _FakeClient:
        def check(self, name: str) -> dict:
            return {"name": name, "completed": True, "status": "completed"}

    monkeypatch.setattr("zush_jobqueue.cli.JobQueueClient", lambda: _FakeClient())

    result = CliRunner().invoke(build_cli(), ["check", "deploy"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "name": "deploy",
        "completed": True,
        "status": "completed",
    }


def test_cli_check_waits_until_completion(monkeypatch) -> None:
    monkeypatch.setattr("zush_jobqueue.cli.ensure_server", lambda: True)
    monkeypatch.setattr("zush_jobqueue.cli.time.sleep", lambda _: None)

    responses = iter([
        {"name": "deploy", "completed": False, "status": None, "running": True, "pending": 0},
        {"name": "deploy", "completed": True, "status": "completed", "running": False, "pending": 0},
    ])

    class _FakeClient:
        def check(self, name: str) -> dict:
            return next(responses)

    monkeypatch.setattr("zush_jobqueue.cli.JobQueueClient", lambda: _FakeClient())

    result = CliRunner().invoke(build_cli(), ["check", "deploy", "--wait", "--timeout", "1", "--poll-interval", "0.01"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "name": "deploy",
        "completed": True,
        "status": "completed",
        "running": False,
        "pending": 0,
    }


def test_cli_check_wait_times_out(monkeypatch) -> None:
    monkeypatch.setattr("zush_jobqueue.cli.ensure_server", lambda: True)
    monkeypatch.setattr("zush_jobqueue.cli.time.sleep", lambda _: None)

    class _FakeClient:
        def check(self, name: str) -> dict:
            return {"name": name, "completed": False, "status": None, "running": True, "pending": 1}

    monkeypatch.setattr("zush_jobqueue.cli.JobQueueClient", lambda: _FakeClient())

    result = CliRunner().invoke(build_cli(), ["check", "deploy", "--wait", "--timeout", "0.05", "--poll-interval", "0.01"])

    assert result.exit_code != 0
    assert "Timed out waiting for queue completion" in result.output


def test_cli_next_command_uses_http_client(monkeypatch) -> None:
    monkeypatch.setattr("zush_jobqueue.cli.ensure_server", lambda: True)

    class _FakeClient:
        def next(self, name: str) -> list[dict]:
            return [{"type": "sleep", "int": 0}]

    monkeypatch.setattr("zush_jobqueue.cli.JobQueueClient", lambda: _FakeClient())

    result = CliRunner().invoke(build_cli(), ["next", "deploy"])

    assert result.exit_code == 0
    assert json.loads(result.output) == [{"type": "sleep", "int": 0}]