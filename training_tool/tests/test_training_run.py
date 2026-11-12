from pathlib import Path
import json
from threading import Event

import numpy as np
import pytest
import soundfile as sf

from ..session import TrainingSession
from ..training import TrainingRun, RecordingCancelled, capture_sample


def make_run(tmp_path: Path, controls: list[dict] | None = None, samples: int = 2) -> TrainingRun:
    sources = []
    for index in range(samples):
        source = tmp_path / f"source{index}.wav"
        sf.write(source, np.full(80, 0.25), 8000, subtype="FLOAT")
        sources.append(str(source))
    return TrainingRun(controls if controls is not None else [
        {"label": "Drive", "value": 0.5, "steps": 2},
        {"label": "Tone", "value": 0.5, "steps": 3},
    ], sources, str(tmp_path), 2, 3, 4)


def fake_capture(source: str, device: int, output: int, channel: int,
                 cancelled: Event) -> tuple[np.ndarray, int]:
    assert (device, output, channel) == (2, 3, 4)
    data, rate = sf.read(source, always_2d=True, dtype="float32")
    return data * 2, rate


def test_every_sample_is_recorded_at_every_combination_with_paired_metadata(tmp_path):
    run = make_run(tmp_path)
    targets = []
    while not run.finished:
        targets.append([c["value"] for c in run.positions])
        run.record_batch(Event(), lambda message: None, fake_capture)
    assert targets == [[0, 0], [0, 0.5], [0, 1], [1, 0], [1, 0.5], [1, 1]]
    manifest = json.loads((run.folder / "manifest.json").read_text())
    assert manifest["completed_batches"] == 6
    assert len(manifest["recordings"]) == 12
    for recording in manifest["recordings"]:
        assert [c["value"] for c in recording["controls"]] == targets[recording["batch"]]
        data, rate = sf.read(run.folder / recording["output"], always_2d=True)
        assert data.shape == (80, 1)
        assert rate == 8000
        assert np.allclose(data, 0.5)
        assert (run.folder / recording["input"]).is_file()
    with pytest.raises(ValueError, match="complete"):
        run.record_batch(Event(), lambda message: None, fake_capture)


def test_failure_retries_only_unfinished_samples_and_does_not_advance_dials(tmp_path):
    run = make_run(tmp_path)
    calls = []

    def fail_second(*args):
        calls.append(args[0])
        if len(calls) == 2:
            raise OSError("Mixer disconnected")
        return fake_capture(*args)

    with pytest.raises(OSError, match="disconnected"):
        run.record_batch(Event(), lambda message: None, fail_second)
    assert run.batch == 0
    assert len(run.completed) == 1
    first = (run.folder / run.completed[0]["output"]).read_bytes()
    run.record_batch(Event(), lambda message: None, fail_second)
    assert len(calls) == 3
    assert run.batch == 1
    assert first == (run.folder / run.completed[0]["output"]).read_bytes()


def test_cancelling_current_sample_discards_it_and_keeps_dial_positions(tmp_path):
    run = make_run(tmp_path)
    cancelled = Event()

    def cancel(*args):
        cancelled.set()
        return fake_capture(*args)

    with pytest.raises(RecordingCancelled):
        run.record_batch(cancelled, lambda message: None, cancel)
    assert run.batch == 0
    assert run.completed == []
    assert list(run.folder.glob("*.wav")) == []


def test_no_controls_records_one_batch_and_copies_inputs(tmp_path):
    run = make_run(tmp_path, controls=[])
    Path(run.sources[0]).unlink()
    run.record_batch(Event(), lambda message: None, fake_capture)
    assert run.finished
    assert run.total_batches == 1
    assert len(run.completed) == 2


@pytest.mark.parametrize("steps", [0, 1, 102])
def test_invalid_steps_are_rejected(steps):
    session = TrainingSession()
    session.set_control_count(1)
    with pytest.raises(ValueError, match="positions"):
        session.set_control_steps(0, steps)


def test_empty_selection_does_not_create_a_run(tmp_path):
    with pytest.raises(ValueError, match="Select"):
        TrainingRun([], [], str(tmp_path), 0, 1, 1)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("source_channels, output_channels", [(1, 1), (1, 2), (2, 1), (2, 2)])
def test_capture_uses_selected_routes_and_keeps_tail(monkeypatch, tmp_path, source_channels, output_channels):
    from .. import training

    source = tmp_path / "tone.wav"
    original = np.full((80, source_channels), 0.25, dtype=np.float32)
    if source_channels == 2:
        original[:, 1] = 0.75
    sf.write(source, original, 8000, subtype="FLOAT")
    captured = {}

    def playrec(audio, **kwargs):
        captured.update(kwargs)
        captured["audio"] = audio.copy()
        return np.zeros((len(audio), 1), dtype=np.float32)

    class Stream:
        active = False

    monkeypatch.setattr(training.sd, "query_devices", lambda device, kind: {"max_output_channels": output_channels})
    monkeypatch.setattr(training.sd, "playrec", playrec)
    monkeypatch.setattr(training.sd, "get_stream", Stream)
    monkeypatch.setattr(training.sd, "wait", lambda: None)
    monkeypatch.setattr(training.sd, "stop", lambda: None)
    data, rate = capture_sample(str(source), 2, 3, 4, Event())
    assert captured["device"] == (2, 3)
    assert captured["input_mapping"] == [4]
    playback_channels = min(source_channels, output_channels)
    assert captured["output_mapping"] == list(range(1, playback_channels + 1))
    assert captured["audio"].shape == (2080, playback_channels)
    expected = original.mean(axis=1, keepdims=True) if output_channels == 1 else original
    assert np.allclose(captured["audio"][:80], expected)
    assert np.all(captured["audio"][80:] == 0)
    assert data.shape == (2080, 1)
    assert rate == 8000
