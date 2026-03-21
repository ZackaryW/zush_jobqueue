from __future__ import annotations

import threading
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from zush_jobqueue.executors import run_payload
from zush_jobqueue.store import JobQueueStore

if TYPE_CHECKING:
    from zush.paths import ZushStorage


class JobQueueManager:
    def __init__(
        self,
        storage: ZushStorage | None = None,
        shutdown_callback=None,
    ) -> None:
        self.store = JobQueueStore(storage=storage)
        self._lock = threading.RLock()
        self._shutdown_callback = shutdown_callback
        self._state = self.store.load_state()
        self._sequence = self._initial_sequence()

    def _initial_sequence(self) -> int:
        highest = 0
        queues = self._state.get("queues", {})
        if not isinstance(queues, dict):
            return 0
        for entry in queues.values():
            if not isinstance(entry, dict):
                continue
            running = entry.get("running")
            pending = entry.get("pending", [])
            if isinstance(running, dict) and isinstance(running.get("id"), int):
                highest = max(highest, running["id"])
            if isinstance(pending, list):
                for item in pending:
                    if isinstance(item, dict) and isinstance(item.get("id"), int):
                        highest = max(highest, item["id"])
        return highest

    def set_shutdown_callback(self, callback) -> None:
        self._shutdown_callback = callback

    def add_payload(self, name: str, payload: list[dict]) -> dict[str, Any]:
        with self._lock:
            self._state.setdefault("payloads", {})[name] = deepcopy(payload)
            self._persist()
            return {"name": name, "count": len(payload)}

    def get_payload(self, name: str) -> list[dict]:
        with self._lock:
            payload = self._state.setdefault("payloads", {}).get(name)
            if payload is None:
                raise KeyError(name)
            return deepcopy(payload)

    def queue_payload(self, name: str) -> dict[str, Any]:
        payload = self.get_payload(name)
        with self._lock:
            queue = self._queue_record(name)
            queue["pending"].append(self._new_entry(name, payload))
            self._persist()
            return {"name": name, "queued": len(queue["pending"])}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            queues = {}
            for name, record in self._state.setdefault("queues", {}).items():
                if not isinstance(record, dict):
                    continue
                queues[name] = {
                    "pending": len(record.get("pending", [])),
                    "running": isinstance(record.get("running"), dict),
                    "queuekill": deepcopy(self._state.setdefault("queuekill", {}).get(name)),
                    "last_status": self._state.setdefault("last_status", {}).get(name),
                }
            return {"queues": queues}

    def check(self, name: str) -> dict[str, Any]:
        with self._lock:
            queue = self._queue_record(name)
            pending = len(queue.get("pending", []))
            running = isinstance(queue.get("running"), dict)
            status = self._state.setdefault("last_status", {}).get(name)
            completed = bool(status in {"completed", "failed", "cancelled", "queuekilled"} and not running and pending == 0)
            return {
                "name": name,
                "completed": completed,
                "status": status,
                "running": running,
                "pending": pending,
            }

    def configure_queuekill(self, name: str, max_lifetime: float, action: str) -> dict[str, Any]:
        with self._lock:
            self._state.setdefault("queuekill", {})[name] = {
                "max_lifetime": float(max_lifetime),
                "action": action,
            }
            self._persist()
            return {
                "name": name,
                "max_lifetime": float(max_lifetime),
                "action": action,
            }

    def start(self, name: str) -> list[dict]:
        with self._lock:
            queue = self._queue_record(name)
            if isinstance(queue.get("running"), dict):
                return deepcopy(queue["running"]["payload"])
            if queue["pending"]:
                entry = queue["pending"].pop(0)
            else:
                entry = self._new_entry(name, self.get_payload(name))
            queue["running"] = entry
            self._persist()
            self._start_background_run(name, entry)
            return deepcopy(entry["payload"])

    def complete(self, name: str, status: str = "completed") -> dict[str, Any]:
        with self._lock:
            queue = self._queue_record(name)
            running = queue.get("running")
            if not isinstance(running, dict):
                last_status = self._state.setdefault("last_status", {}).get(name, status)
                return {"name": name, "status": last_status}
            cancel_event = running.get("cancel_event")
            if isinstance(cancel_event, threading.Event):
                cancel_event.set()
            cancelled_status = "cancelled"
            self._finalize_locked(name, running, cancelled_status, [])
            return {"name": name, "status": cancelled_status}

    def quit(self, restore: bool = False) -> dict[str, Any]:
        with self._lock:
            snapshot = self._serializable_state()
            if restore:
                self.store.save_restore(snapshot)
            self._persist()
        if callable(self._shutdown_callback):
            self._shutdown_callback()
        return {"ok": True, "restore": restore}

    def _queue_record(self, name: str) -> dict[str, Any]:
        queues = self._state.setdefault("queues", {})
        record = queues.get(name)
        if not isinstance(record, dict):
            record = {"pending": [], "running": None}
            queues[name] = record
        pending = record.get("pending")
        if not isinstance(pending, list):
            record["pending"] = []
        if "running" not in record:
            record["running"] = None
        return record

    def _new_entry(self, name: str, payload: list[dict]) -> dict[str, Any]:
        self._sequence += 1
        return {
            "id": self._sequence,
            "name": name,
            "payload": deepcopy(payload),
            "status": "queued",
            "started_at": None,
            "cancel_event": None,
        }

    def _start_background_run(self, name: str, entry: dict[str, Any]) -> None:
        cancel_event = threading.Event()
        entry["cancel_event"] = cancel_event
        entry["started_at"] = time.time()
        entry["status"] = "running"
        self._schedule_queuekill(name, entry)
        thread = threading.Thread(
            target=self._run_entry,
            args=(name, entry["id"], deepcopy(entry["payload"]), cancel_event),
            daemon=True,
        )
        thread.start()

    def _schedule_queuekill(self, name: str, entry: dict[str, Any]) -> None:
        queuekill = self._state.setdefault("queuekill", {}).get(name)
        if not isinstance(queuekill, dict):
            return
        timeout = queuekill.get("max_lifetime")
        if not isinstance(timeout, int | float):
            return
        timer = threading.Timer(float(timeout), self._on_queuekill_timeout, args=(name, entry["id"]))
        entry["queuekill_timer"] = timer
        timer.daemon = True
        timer.start()

    def _on_queuekill_timeout(self, name: str, entry_id: int) -> None:
        with self._lock:
            queue = self._queue_record(name)
            running = queue.get("running")
            if not isinstance(running, dict) or running.get("id") != entry_id:
                return
            queuekill = self._state.setdefault("queuekill", {}).get(name, {})
            action = queuekill.get("action")
            cancel_event = running.get("cancel_event")
            if isinstance(cancel_event, threading.Event):
                cancel_event.set()
            self._finalize_locked(name, running, "queuekilled", [])
        if isinstance(action, str) and action:
            try:
                self.start(action)
            except KeyError:
                return

    def _run_entry(self, name: str, entry_id: int, payload: list[dict], cancel_event: threading.Event) -> None:
        results = run_payload(payload, cancel_event)
        status = "completed"
        if results:
            final_status = results[-1].get("status")
            if final_status == "failed":
                status = "failed"
            elif final_status == "cancelled":
                status = "cancelled"
        with self._lock:
            queue = self._queue_record(name)
            running = queue.get("running")
            if not isinstance(running, dict) or running.get("id") != entry_id:
                return
            self._finalize_locked(name, running, status, results)

    def _finalize_locked(self, name: str, entry: dict[str, Any], status: str, results: list[dict]) -> None:
        timer = entry.get("queuekill_timer")
        if hasattr(timer, "cancel"):
            timer.cancel()
        self._state.setdefault("last_status", {})[name] = status
        queue = self._queue_record(name)
        queue["running"] = None
        self.store.append_log(
            {
                "name": name,
                "status": status,
                "id": entry.get("id"),
                "results": deepcopy(results),
            }
        )
        self._persist()
        if queue["pending"]:
            next_entry = queue["pending"].pop(0)
            queue["running"] = next_entry
            self._persist()
            self._start_background_run(name, next_entry)

    def _serializable_state(self) -> dict[str, Any]:
        payloads = deepcopy(self._state.setdefault("payloads", {}))
        queuekill = deepcopy(self._state.setdefault("queuekill", {}))
        last_status = deepcopy(self._state.setdefault("last_status", {}))
        queues = {}
        for name, record in self._state.setdefault("queues", {}).items():
            if not isinstance(record, dict):
                continue
            queues[name] = {
                "pending": [self._clean_entry(item) for item in record.get("pending", []) if isinstance(item, dict)],
                "running": self._clean_entry(record.get("running")) if isinstance(record.get("running"), dict) else None,
            }
        return {
            "payloads": payloads,
            "queues": queues,
            "queuekill": queuekill,
            "last_status": last_status,
        }

    def _clean_entry(self, entry: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(entry, dict):
            return None
        return {
            "id": entry.get("id"),
            "name": entry.get("name"),
            "payload": deepcopy(entry.get("payload", [])),
            "status": entry.get("status"),
            "started_at": entry.get("started_at"),
        }

    def _persist(self) -> None:
        self.store.save_state(self._serializable_state())