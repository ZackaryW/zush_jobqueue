from __future__ import annotations

from threading import Event

from zush_jobqueue.executors.common import run_subprocess


def execute(item: dict, cancel_event: Event) -> dict:
    command = item.get("cmd", "")
    return run_subprocess(str(command), cancel_event, shell=True)