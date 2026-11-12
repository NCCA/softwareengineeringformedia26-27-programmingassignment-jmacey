import math
from pathlib import Path
from threading import Event, Thread
from typing import Any

import numpy as np
import pytest
import soundfile as sf

from .. import training
from ..training import TrainingRun, RecordingCancelled, capture_sample


@pytest.fixture
def audio_driver(monkeypatch: pytest.MonkeyPatch) -> Any:
    class Driver:
        capacity = 2
        fail_on_job = 0
        stop_on_job = 0
        corrupt_input = False
        cancel_on_job = 0
        cancel_on_start = False
        cancelled = Event()

        def __init__(self) -> None:
            self.streams = []
            self.jobs = []

    driver = Driver()

    class Stream:
        latency = (0.001, 0.002)

        def __init__(self, **kwargs: Any) -> None:
            self.settings = kwargs
            self.callback = kwargs["callback"]
            self.active = False
            self.closed = False
            self.stopped = Event()
            self.thread = None
            self.idle_output = None
            driver.streams.append(self)

        def pump(self, status: Any) -> np.ndarray:
            channels_in, channels_out = self.settings["channels"]
            incoming = np.tile(np.arange(1, channels_in + 1, dtype=np.float32) / 10, (127, 1))
            outgoing = np.full((127, channels_out), np.nan, dtype=np.float32)
            if driver.corrupt_input and self.callback.__self__._job is not None:
                incoming = incoming[:, :1]
            self.callback(incoming, outgoing, 127, None, status)
            return outgoing

        def start(self) -> None:
            self.active = True
            startup_status = training.sd.CallbackFlags()
            startup_status.input_underflow = True
            self.idle_output = self.pump(startup_status)
            if driver.cancel_on_start:
                driver.cancelled.set()

            def process() -> None:
                while not self.stopped.wait(0.0005):
                    status = training.sd.CallbackFlags()
                    job = self.callback.__self__._job
                    if job is not None and all(job is not entry[0] for entry in driver.jobs):
                        driver.jobs.append((job, []))
                        number = len(driver.jobs)
                        if number == driver.fail_on_job:
                            status.input_underflow = True
                        if number == driver.cancel_on_job:
                            driver.cancelled.set()
                        if number == driver.stop_on_job:
                            self.active = False
                            return
                    try:
                        outgoing = self.pump(status)
                    except training.sd.CallbackAbort:
                        self.active = False
                        return
                    if job is not None:
                        next(entry[1] for entry in driver.jobs if entry[0] is job).append(outgoing)

            self.thread = Thread(target=process, daemon=True)
            self.thread.start()

        def abort(self) -> None:
            self.stopped.set()
            if self.thread is not None:
                self.thread.join(timeout=1)
                assert not self.thread.is_alive()
            self.active = False

        def close(self) -> None:
            self.closed = True

    monkeypatch.setattr(training.sd, "query_devices", lambda device, kind: {"max_output_channels": driver.capacity})
    monkeypatch.setattr(training.sd, "Stream", Stream)
    monkeypatch.setattr(training, "SETTLING_SECONDS", 0.005)
    return driver


def write_source(path: Path, channels: int = 1, rate: int = 8000) -> np.ndarray:
    audio = np.full((80, channels), 0.25, dtype=np.float32)
    if channels == 2:
        audio[:, 1] = 0.75
    sf.write(path, audio, rate, subtype="FLOAT")
    return audio


@pytest.mark.parametrize("source_channels, output_channels", [(1, 1), (1, 2), (2, 1), (2, 2)])
def test_capture_routes_mono_and_stereo_and_retains_latency_tail(
    audio_driver: Any, tmp_path: Path, source_channels: int, output_channels: int,
) -> None:
    audio_driver.capacity = output_channels
    source = tmp_path / "tone.wav"
    original = write_source(source, source_channels)
    data, rate = capture_sample(str(source), 2, 3, 4, Event())
    stream = audio_driver.streams[0]
    assert stream.settings["device"] == (2, 3)
    assert stream.settings["channels"] == (4, min(source_channels, output_channels))
    assert stream.settings["latency"] == (0.2, 0.2)
    assert stream.settings["blocksize"] == 0
    assert np.all(stream.idle_output == 0)
    frames = 80 + math.ceil(8000 * (0.25 + sum(stream.latency)))
    assert data.shape == (frames, 1)
    assert np.allclose(data, 0.4)
    assert rate == 8000
    played = np.concatenate(audio_driver.jobs[0][1])[:frames]
    expected = original.mean(axis=1, keepdims=True) if output_channels == 1 else original
    assert np.allclose(played[:80], expected)
    assert np.all(played[80:] == 0)
    assert stream.closed


def make_run(tmp_path: Path, mixed_rates: bool = False) -> TrainingRun:
    sources = [tmp_path / "mono.wav", tmp_path / "stereo.wav"]
    write_source(sources[0])
    write_source(sources[1], channels=2, rate=16000 if mixed_rates else 8000)
    return TrainingRun([], [str(p) for p in sources], str(tmp_path), 2, 3, 4)


def test_batch_reuses_stream_between_mono_and_stereo_files(audio_driver: Any, tmp_path: Path) -> None:
    run = make_run(tmp_path)
    run.record_batch(Event(), lambda message: None)
    assert run.finished
    assert len(audio_driver.streams) == 1
    assert audio_driver.streams[0].settings["channels"] == (4, 2)
    assert len(run.completed) == 2
    assert all(r["device_latency_seconds"] == [0.001, 0.002] for r in run.completed)
    assert all(r["tail_seconds"] == pytest.approx(0.253) for r in run.completed)
    first_playback = np.concatenate(audio_driver.jobs[0][1])
    assert np.all(first_playback[:, 1] == 0)
    assert all(stream.closed for stream in audio_driver.streams)


def test_changed_sample_rate_reopens_stream_without_reinterpreting_audio(audio_driver: Any, tmp_path: Path) -> None:
    run = make_run(tmp_path, mixed_rates=True)
    run.record_batch(Event(), lambda message: None)
    assert [s.settings["samplerate"] for s in audio_driver.streams] == [8000, 16000]
    assert [r["sample_rate"] for r in run.completed] == [8000, 16000]
    assert all(stream.closed for stream in audio_driver.streams)


def test_underflow_during_sample_fails_and_retry_preserves_saved_sample(audio_driver: Any, tmp_path: Path) -> None:
    run = make_run(tmp_path)
    audio_driver.fail_on_job = 2
    with pytest.raises(RuntimeError, match="during recording: input underflow"):
        run.record_batch(Event(), lambda message: None)
    assert run.batch == 0
    assert len(run.completed) == 1
    assert all(stream.closed for stream in audio_driver.streams)
    saved = run.folder / run.completed[0]["output"]
    saved_contents = saved.read_bytes()
    run.record_batch(Event(), lambda message: None)
    assert run.finished
    assert len(audio_driver.jobs) == 3
    assert saved.read_bytes() == saved_contents


@pytest.mark.parametrize("phase", ["settling", "recording"])
def test_cancellation_closes_stream_and_discards_unfinished_recording(
    audio_driver: Any, tmp_path: Path, phase: str,
) -> None:
    run = make_run(tmp_path)
    audio_driver.cancel_on_start = phase == "settling"
    audio_driver.cancel_on_job = 1 if phase == "recording" else 0
    with pytest.raises(RecordingCancelled):
        run.record_batch(audio_driver.cancelled, lambda message: None)
    assert run.batch == 0
    assert run.completed == []
    assert list(run.folder.glob("*.wav")) == []
    assert all(stream.closed for stream in audio_driver.streams)


def test_stream_failure_does_not_hang_or_save_partial_recording(audio_driver: Any, tmp_path: Path) -> None:
    run = make_run(tmp_path)
    audio_driver.stop_on_job = 1
    with pytest.raises(RuntimeError, match="stopped during recording"):
        run.record_batch(Event(), lambda message: None)
    assert not run.completed
    assert all(stream.closed for stream in audio_driver.streams)


def test_callback_exception_reaches_worker_and_closes_stream(audio_driver: Any, tmp_path: Path) -> None:
    run = make_run(tmp_path)
    audio_driver.corrupt_input = True
    with pytest.raises(RuntimeError, match="Audio callback failed"):
        run.record_batch(Event(), lambda message: None)
    assert run.completed == []
    assert all(stream.closed for stream in audio_driver.streams)
