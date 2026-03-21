from pathlib import Path

from zush.paths import DirectoryStorage

from zush_jobqueue.paths import (
    jobqueue_dir,
    log_dir,
    restore_file,
    state_file,
)


def test_jobqueue_paths_live_under_zush_config_dir(tmp_path: Path) -> None:
    storage = DirectoryStorage(tmp_path)

    assert jobqueue_dir(storage) == tmp_path / "jobqueue"
    assert log_dir(storage) == tmp_path / "jobqueue" / "logs"
    assert state_file(storage) == tmp_path / "jobqueue" / "state.json"
    assert restore_file(storage) == tmp_path / "jobqueue" / "restore.json"
