import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import soundfile as sf
from PySide6.QtCore import QSettings, QUrl

from ..backend import TrainingBackend
from ..session import TrainingSession


def make_backend(settings=None):
    devices = [{"name": "Mixer", "max_input_channels": 4,
                "max_output_channels": 2, "default_samplerate": 8000}]
    return TrainingBackend(TrainingSession(query_devices=lambda: devices), settings=settings)


def test_settings_file_round_trip(tmp_path):
    backend = make_backend()
    sf.write(tmp_path / "tone.wav", np.zeros(80), 8000)
    backend.addSampleFolder(QUrl.fromLocalFile(str(tmp_path)))
    backend.selectAllSamples(True)
    backend.setControlCount(1)
    backend.setControlLabel(0, "Drive")
    backend.setControlValue(0, 0.75)
    backend.setControlSteps(0, 7)
    backend.setReturnChannel(3)
    url = QUrl.fromLocalFile(str(tmp_path / "setup.json"))
    backend.saveSettings(url)

    restored = make_backend()
    restored.loadSettings(url)

    assert restored.controls == [{"label": "Drive", "value": 0.75, "steps": 7}]
    assert restored.returnChannel == 3
    assert restored.samples == backend.samples


def test_last_setup_restored_from_qsettings(tmp_path):
    path = str(tmp_path / "preferences.ini")
    backend = make_backend(QSettings(path, QSettings.Format.IniFormat))
    backend.setControlCount(0)
    backend.setReturnChannel(2)
    backend.shutdown()

    restored = make_backend(QSettings(path, QSettings.Format.IniFormat))

    assert restored.controls == []
    assert restored.returnChannel == 2


@pytest.mark.parametrize("contents", ['{', '[]', '{"version": 99}',
    '{"version": 1, "controls": [{"label": "Drive", "value": 2, "steps": 3}], "samples": []}'])
def test_invalid_file_keeps_current_setup(tmp_path, contents):
    backend = make_backend()
    backend.setControlCount(1)
    before = [dict(c) for c in backend.controls]
    path = tmp_path / "invalid.json"
    path.write_text(contents)

    backend.loadSettings(QUrl.fromLocalFile(str(path)))

    assert backend.controls == before
    assert "Cannot load settings" in backend.message


def test_missing_samples_are_reported(tmp_path):
    backend = make_backend()
    path = tmp_path / "setup.json"
    backend.saveSettings(QUrl.fromLocalFile(str(path)))
    data = json.loads(path.read_text())
    data["samples"] = [{"path": str(tmp_path / "gone.wav"), "selected": True}]
    path.write_text(json.dumps(data))

    backend.loadSettings(QUrl.fromLocalFile(str(path)))

    assert backend.samples == []
    assert "gone.wav" in backend.message
