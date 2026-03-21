from __future__ import annotations

from threading import Event

from zush_jobqueue.executors import cmd, python, sleep, zushcmd


EXECUTORS = {
    "cmd": cmd.execute,
    "python": python.execute,
    "sleep": sleep.execute,
    "zushcmd": zushcmd.execute,
}


def run_payload(payload: list[dict], cancel_event: Event) -> list[dict]:
    results: list[dict] = []
    for item in payload:
        job_type = item.get("type")
        executor = EXECUTORS.get(job_type)
        if executor is None:
            results.append({"status": "failed", "error": f"Unknown job type: {job_type}"})
            break
        result = executor(item, cancel_event)
        results.append(result)
        if result.get("status") in {"failed", "cancelled"}:
            break
    return results