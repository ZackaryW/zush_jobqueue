from __future__ import annotations

import time
from threading import Event


def execute(item: dict, cancel_event: Event) -> dict:
    duration = float(item.get("int", 0))
    deadline = time.monotonic() + max(duration, 0.0)
    while time.monotonic() < deadline:
        if cancel_event.is_set():
            return {"status": "cancelled", "slept": max(duration, 0.0)}
        time.sleep(min(0.05, max(deadline - time.monotonic(), 0.0)))
    return {"status": "completed", "slept": max(duration, 0.0)}