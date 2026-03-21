from __future__ import annotations

import subprocess
import time
from threading import Event
from typing import Mapping


def run_subprocess(
    command: list[str] | str,
    cancel_event: Event,
    shell: bool = False,
    env: Mapping[str, str] | None = None,
) -> dict:
    process = subprocess.Popen(
        command,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(env) if env is not None else None,
    )
    while True:
        if cancel_event.is_set():
            process.kill()
            stdout, stderr = process.communicate()
            return {
                "status": "cancelled",
                "returncode": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            return {
                "status": "completed" if process.returncode == 0 else "failed",
                "returncode": process.returncode,
                "stdout": stdout,
                "stderr": stderr,
            }
        time.sleep(0.05)