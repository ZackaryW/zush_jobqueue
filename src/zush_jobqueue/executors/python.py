from __future__ import annotations

import sys
from threading import Event

from zush_jobqueue.executors.common import run_subprocess


def execute(item: dict, cancel_event: Event) -> dict:
    code = str(item.get("cmd", ""))
    return run_subprocess([sys.executable, "-c", code], cancel_event)