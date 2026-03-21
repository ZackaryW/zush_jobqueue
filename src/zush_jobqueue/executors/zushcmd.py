from __future__ import annotations

import os
import sys
from threading import Event

from zush_jobqueue.executors.common import run_subprocess


def execute(item: dict, cancel_event: Event) -> dict:
    command_path = str(item.get("cmd", ""))
    args = [str(value) for value in item.get("args", [])]
    kwargs = item.get("kwargs", {})
    command = [sys.executable, "-m", "zush", *command_path.split("."), *args]
    if isinstance(kwargs, dict):
        for key, value in kwargs.items():
            option = f"--{str(key).replace('_', '-')}"
            if isinstance(value, bool):
                if value:
                    command.append(option)
                continue
            if isinstance(value, list):
                for item_value in value:
                    command.extend([option, str(item_value)])
                continue
            command.extend([option, str(value)])
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return run_subprocess(command, cancel_event, env=env)