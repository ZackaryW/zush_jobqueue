from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from zush.paths import default_storage

if TYPE_CHECKING:
    from zush.paths import ZushStorage


def _storage_path(storage: ZushStorage | None = None) -> Path:
    active_storage = storage or default_storage()
    return active_storage.config_dir()


def jobqueue_dir(storage: ZushStorage | None = None) -> Path:
    return _storage_path(storage) / "jobqueue"


def log_dir(storage: ZushStorage | None = None) -> Path:
    return jobqueue_dir(storage) / "logs"


def state_file(storage: ZushStorage | None = None) -> Path:
    return jobqueue_dir(storage) / "state.json"


def restore_file(storage: ZushStorage | None = None) -> Path:
    return jobqueue_dir(storage) / "restore.json"