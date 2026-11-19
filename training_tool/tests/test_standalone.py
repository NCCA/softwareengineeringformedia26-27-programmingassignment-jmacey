import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


@pytest.mark.parametrize("copy_app", [False, True], ids=["checkout", "copied-folder"])
def test_app_launches_directly_from_another_folder(tmp_path: Path, copy_app: bool) -> None:
    folder = Path(__file__).resolve().parents[1]
    if copy_app:
        folder = Path(shutil.copytree(folder, tmp_path / "pedal_capture"))
    script = folder / "app.py"
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["QT_QPA_PLATFORM"] = "offscreen"
    environment["QT_QUICK_BACKEND"] = "software"
    process = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=tmp_path,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    else:
        stdout, stderr = process.communicate()
        raise AssertionError(f"App exited before the window could be used:\n{stdout}\n{stderr}")
    finally:
        if process.poll() is None:
            process.terminate()
        stdout, stderr = process.communicate(timeout=5)
    assert "failed to load component" not in stderr.lower(), stderr
    assert "TypeError" not in stderr, stderr
