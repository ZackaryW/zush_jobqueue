from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING, Any

from zush.paths import default_storage

from zush_jobqueue.paths import jobqueue_dir, log_dir, restore_file, state_file

if TYPE_CHECKING:
    from zush.paths import ZushStorage


def _normalize_state(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {
            "payloads": {},
            "queues": {},
            "queuekill": {},
            "last_status": {},
        }
    payloads = data.get("payloads") if isinstance(data.get("payloads"), dict) else {}
    queues = data.get("queues") if isinstance(data.get("queues"), dict) else {}
    queuekill = data.get("queuekill") if isinstance(data.get("queuekill"), dict) else {}
    last_status = data.get("last_status") if isinstance(data.get("last_status"), dict) else {}
    return {
        "payloads": payloads,
        "queues": queues,
        "queuekill": queuekill,
        "last_status": last_status,
    }


class JobQueueStore:
    def __init__(self, storage: ZushStorage | None = None) -> None:
        self.storage = storage or default_storage()
        self._lock = RLock()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        jobqueue_dir(self.storage).mkdir(parents=True, exist_ok=True)
        log_dir(self.storage).mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict[str, Any]:
        with self._lock:
            restored = self._read_json(restore_file(self.storage))
            if restored is not None:
                normalized = _normalize_state(restored)
                self._delete_file(restore_file(self.storage))
                self._write_json(state_file(self.storage), normalized)
                return normalized
            state = self._read_json(state_file(self.storage))
            if state is not None:
                return _normalize_state(state)
            return _normalize_state({})

    def save_state(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._write_json(state_file(self.storage), _normalize_state(data))

    def save_restore(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._write_json(restore_file(self.storage), _normalize_state(data))

    def append_log(self, entry: dict[str, Any]) -> None:
        with self._lock:
            log_path = log_dir(self.storage) / f"{date.today().isoformat()}.json"
            existing = self._read_json(log_path)
            payload = existing if isinstance(existing, list) else []
            payload.append(entry)
            self._write_json(log_path, payload)

    def _read_json(self, path: Path) -> Any | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _delete_file(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            return