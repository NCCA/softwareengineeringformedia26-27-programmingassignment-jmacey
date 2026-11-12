from training_tool.session import TrainingSession
import numpy as np
import soundfile as sf


def test_choose_input_by_device_id_and_preserve_it_after_refresh():
    devices = [
        {"name": "Output", "max_input_channels": 0, "default_samplerate": 48000},
        {"name": "FLOW 8", "max_input_channels": 10, "default_samplerate": 48000},
        {"name": "Microphone", "max_input_channels": 1, "default_samplerate": 44100},
    ]
    session = TrainingSession(query_devices=lambda: devices)
    session.refresh_devices()
    assert [device["id"] for device in session.devices] == [1, 2]
    session.select_device(2)
    session.refresh_devices()
    assert session.selected_device_id == 2
    assert session.selected_device["name"] == "Microphone"


def test_resize_controls_preserves_existing_labels_and_positions():
    session = TrainingSession()
    session.set_control_count(3)
    session.set_control_label(0, "Drive")
    session.set_control_value(0, 0.75)
    session.set_control_count(5)
    assert session.controls[0] == {"label": "Drive", "value": 0.75}
    assert session.controls[4] == {"label": "Control 5", "value": 0.5}
    session.set_control_count(1)
    assert session.controls == [{"label": "Drive", "value": 0.75}]


def test_add_folder_select_samples_and_do_not_duplicate_on_reload(tmp_path):
    for name in ("B.wav", "a.FLAC"):
        sf.write(tmp_path / name, np.zeros(800), 8000)
    (tmp_path / "notes.txt").write_text("ignore me")
    (tmp_path / "broken.wav").write_text("not audio")
    session = TrainingSession()
    skipped = session.add_sample_folder(tmp_path)
    assert [s["name"] for s in session.samples] == ["a.FLAC", "B.wav"]
    assert session.samples[0]["duration"] == 0.1
    assert len(skipped) == 1
    session.select_sample(0, True)
    session.add_sample_folder(tmp_path)
    assert len(session.samples) == 2
    assert session.selected_sample_paths == [str((tmp_path / "a.FLAC").resolve())]
