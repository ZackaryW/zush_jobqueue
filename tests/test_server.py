from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from zush.paths import DirectoryStorage

from zush_jobqueue.server import create_app


def test_add_get_and_queue_roundtrip(tmp_path: Path) -> None:
    storage = DirectoryStorage(tmp_path)
    client = TestClient(create_app(storage=storage))
    payload = [{"type": "sleep", "int": 1}]

    response = client.post("/add/build", json=payload)
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = client.get("/get/build")
    assert response.status_code == 200
    assert response.json() == payload

    response = client.put("/queue/build")
    assert response.status_code == 200
    body = response.json()
    assert body["queued"] == 1

    response = client.get("/queue")
    assert response.status_code == 200
    queue_body = response.json()
    assert queue_body["queues"]["build"]["pending"] == 1
    assert queue_body["queues"]["build"]["running"] is False


def test_start_begins_execution_and_complete_logs_result(tmp_path: Path) -> None:
    storage = DirectoryStorage(tmp_path)
    client = TestClient(create_app(storage=storage))
    payload = [{"type": "sleep", "int": 0}]

    client.post("/add/nightly", json=payload)
    client.put("/queue/nightly")

    response = client.get("/start/nightly")
    assert response.status_code == 200
    assert response.json() == payload

    response = client.post("/complete/nightly")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    logs = sorted((tmp_path / "jobqueue" / "logs").glob("*.json"))
    assert logs
    entries = json.loads(logs[0].read_text(encoding="utf-8"))
    assert entries[-1]["name"] == "nightly"
    assert entries[-1]["status"] == "completed"


def test_queuekill_configuration_is_reported_and_quit_can_restore(tmp_path: Path) -> None:
    storage = DirectoryStorage(tmp_path)
    client = TestClient(create_app(storage=storage))
    payload = [{"type": "sleep", "int": 0}]

    client.post("/add/main", json=payload)
    client.put("/queue/main")

    response = client.post(
        "/queuekill/main",
        json={"max_lifetime": 5, "action": "fallback"},
    )
    assert response.status_code == 200
    assert response.json() == {"name": "main", "max_lifetime": 5.0, "action": "fallback"}

    response = client.post("/quit", json={"restore": True})
    assert response.status_code == 200
    assert response.json()["restore"] is True

    restore = tmp_path / "jobqueue" / "restore.json"
    assert restore.exists()


def test_restore_snapshot_is_loaded_on_start_and_consumed(tmp_path: Path) -> None:
    storage = DirectoryStorage(tmp_path)
    restore = tmp_path / "jobqueue" / "restore.json"
    restore.parent.mkdir(parents=True, exist_ok=True)
    restore.write_text(
        json.dumps(
            {
                "payloads": {"restored": [{"type": "sleep", "int": 0}]},
                "queues": {"restored": {"pending": [{"id": 1, "name": "restored", "payload": [{"type": "sleep", "int": 0}], "status": "queued", "started_at": None}], "running": None}},
                "queuekill": {},
                "last_status": {},
            }
        ),
        encoding="utf-8",
    )

    client = TestClient(create_app(storage=storage))

    response = client.get("/get/restored")
    assert response.status_code == 200
    assert response.json() == [{"type": "sleep", "int": 0}]

    response = client.get("/queue")
    assert response.status_code == 200
    assert response.json()["queues"]["restored"]["pending"] == 1
    assert not restore.exists()


def test_check_endpoint_reports_completion_state(tmp_path: Path) -> None:
    storage = DirectoryStorage(tmp_path)
    client = TestClient(create_app(storage=storage))
    payload = [{"type": "sleep", "int": 0}]

    client.post("/add/donejob", json=payload)
    client.put("/queue/donejob")
    client.get("/start/donejob")

    response = client.get("/check/donejob")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "donejob"
    assert body["completed"] is True
    assert body["status"] == "completed"
    assert body["running"] is False
    assert body["pending"] == 0
