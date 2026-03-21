from __future__ import annotations

import socket
import subprocess
import sys
import time
import json
from pathlib import Path

import httpx


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=0.5)
            response.raise_for_status()
            return
        except httpx.HTTPError:
            time.sleep(0.1)
    raise AssertionError("Server did not become healthy in time")


def _wait_for_status(base_url: str, name: str, expected: str, timeout: float = 10.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = httpx.get(f"{base_url}/queue", timeout=0.5)
        response.raise_for_status()
        body = response.json()
        status = body["queues"].get(name, {}).get("last_status")
        if status == expected:
            return body
        time.sleep(0.1)
    raise AssertionError(f"Queue {name} did not reach status {expected}")


def _read_log_entries(storage_dir: Path) -> list[dict]:
    log_files = sorted((storage_dir / "jobqueue" / "logs").glob("*.json"))
    assert log_files
    return json.loads(log_files[-1].read_text(encoding="utf-8"))


def test_real_server_honors_test_overrides_and_queuekill(tmp_path: Path) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    command = [
        sys.executable,
        "-m",
        "zush_jobqueue",
        "serve",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--storage-dir",
        str(tmp_path),
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait_for_health(base_url)

        fallback_payload = [{"type": "python", "cmd": 'print("fallback")'}]
        main_payload = [{"type": "sleep", "int": 2}]

        response = httpx.post(f"{base_url}/add/fallback", json=fallback_payload, timeout=2.0)
        response.raise_for_status()
        response = httpx.post(f"{base_url}/add/main", json=main_payload, timeout=2.0)
        response.raise_for_status()
        response = httpx.put(f"{base_url}/queue/main", timeout=2.0)
        response.raise_for_status()
        response = httpx.post(
            f"{base_url}/queuekill/main",
            json={"max_lifetime": 0.2, "action": "fallback"},
            timeout=2.0,
        )
        response.raise_for_status()
        response = httpx.get(f"{base_url}/start/main", timeout=2.0)
        response.raise_for_status()

        _wait_for_status(base_url, "main", "queuekilled")
        _wait_for_status(base_url, "fallback", "completed")

        log_files = sorted((tmp_path / "jobqueue" / "logs").glob("*.json"))
        assert log_files

        response = httpx.post(f"{base_url}/quit", json={"restore": False}, timeout=2.0)
        response.raise_for_status()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def test_real_server_captures_cmd_and_zushcmd_results(tmp_path: Path) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    command = [
        sys.executable,
        "-m",
        "zush_jobqueue",
        "serve",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--storage-dir",
        str(tmp_path),
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait_for_health(base_url)

        cmd_payload = [{
            "type": "cmd",
            "cmd": f'"{sys.executable}" -c "import sys; print(\'cmd-out\'); print(\'cmd-err\', file=sys.stderr)"',
        }]
        zushcmd_payload = [{"type": "zushcmd", "cmd": "self.map"}]

        response = httpx.post(f"{base_url}/add/cmdjob", json=cmd_payload, timeout=2.0)
        response.raise_for_status()
        response = httpx.get(f"{base_url}/start/cmdjob", timeout=2.0)
        response.raise_for_status()
        _wait_for_status(base_url, "cmdjob", "completed")

        response = httpx.post(f"{base_url}/add/zushjob", json=zushcmd_payload, timeout=2.0)
        response.raise_for_status()
        response = httpx.get(f"{base_url}/start/zushjob", timeout=2.0)
        response.raise_for_status()
        _wait_for_status(base_url, "zushjob", "completed")

        entries = _read_log_entries(tmp_path)
        cmd_entry = next(entry for entry in entries if entry["name"] == "cmdjob")
        zush_entry = next(entry for entry in entries if entry["name"] == "zushjob")

        assert cmd_entry["status"] == "completed"
        assert "cmd-out" in cmd_entry["results"][-1]["stdout"]
        assert "cmd-err" in cmd_entry["results"][-1]["stderr"]

        assert zush_entry["status"] == "completed"
        assert "self" in zush_entry["results"][-1]["stdout"]

        response = httpx.post(f"{base_url}/quit", json={"restore": False}, timeout=2.0)
        response.raise_for_status()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def test_real_server_marks_long_running_cmd_as_cancelled_on_complete(tmp_path: Path) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    command = [
        sys.executable,
        "-m",
        "zush_jobqueue",
        "serve",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--storage-dir",
        str(tmp_path),
    ]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait_for_health(base_url)

        payload = [{
            "type": "cmd",
            "cmd": f'"{sys.executable}" -c "import time; print(\'begin\'); time.sleep(5)"',
        }]

        response = httpx.post(f"{base_url}/add/canceljob", json=payload, timeout=2.0)
        response.raise_for_status()
        response = httpx.get(f"{base_url}/start/canceljob", timeout=2.0)
        response.raise_for_status()
        time.sleep(0.3)

        response = httpx.post(f"{base_url}/complete/canceljob", timeout=2.0)
        response.raise_for_status()
        _wait_for_status(base_url, "canceljob", "cancelled")

        entries = _read_log_entries(tmp_path)
        cancel_entry = next(entry for entry in entries if entry["name"] == "canceljob")
        assert cancel_entry["status"] == "cancelled"

        response = httpx.post(f"{base_url}/quit", json={"restore": False}, timeout=2.0)
        response.raise_for_status()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)