"""Plan dial combinations and keep a record of each captured sample."""

from collections.abc import Callable
from contextlib import ExitStack
from dataclasses import dataclass, field
from typing import Any, Self
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import shutil
from threading import Event
from time import monotonic

import numpy as np
import sounddevice as sd
import soundfile as sf

if __package__:
    from . import calibration
else:
    import calibration


type Capture = Callable[[str, int, int, int, Event], tuple[np.ndarray, int]]


class RecordingCancelled(Exception):
    pass


REQUESTED_LATENCY = 0.2
SETTLING_SECONDS = 0.5
TAIL_SECONDS = 0.25


@dataclass
class _CaptureJob:
    playback: np.ndarray
    recorded: np.ndarray
    position: int = 0
    status: sd.CallbackFlags = field(default_factory=sd.CallbackFlags)
    done: Event = field(default_factory=Event)
    error: Exception | None = None


class BatchRecorder:
    """Keep a duplex stream running between samples of the same sample rate."""

    def __init__(self, device: int, output: int, channel: int,
                 cancelled: Event, source_channels: int,
                 calibration: dict[int, int] | None = None,
                 progress: Callable[[str], None] | None = None) -> None:
        self.device = device
        self.output = output
        self.channel = channel
        self.cancelled = cancelled
        capacity = int(sd.query_devices(output, "output")["max_output_channels"])
        if capacity < 1 or (capacity != 1 and source_channels > capacity):
            raise ValueError("Playback output has too few channels for this sample")
        self.output_channels = min(source_channels, capacity)
        self._stream: sd.Stream | None = None
        self._rate: int | None = None
        self._job: _CaptureJob | None = None
        self.latency: tuple[float, float] = (0.0, 0.0)
        self.tail_seconds = TAIL_SECONDS
        # Measured loop delay in frames for each sample rate. The run owns this dict so
        # calibration happens once per run rather than every time a stream is opened.
        self.calibration = calibration if calibration is not None else {}
        self.progress = progress or (lambda message: None)
        self.latency_frames = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        if self._stream is not None:
            try:
                self._stream.abort()
            finally:
                self._stream.close()
                self._stream = None
                self._job = None

    def _callback(self, indata: np.ndarray, outdata: np.ndarray, frames: int,
                  time_info: Any, status: sd.CallbackFlags) -> None:
        outdata.fill(0)
        job = self._job
        if job is None:
            return
        try:
            job.status |= status
            end = min(job.position + frames, len(job.playback))
            count = end - job.position
            outdata[:count, :job.playback.shape[1]] = job.playback[job.position:end]
            job.recorded[job.position:end, 0] = indata[:count, self.channel - 1]
            job.position = end
            if end == len(job.playback):
                self._job = None
                job.done.set()
        except Exception as error:
            job.error = error
            self._job = None
            job.done.set()
            raise sd.CallbackAbort from error

    def _open(self, rate: int) -> None:
        if self._stream is not None and self._rate == rate:
            return
        self.close()
        self._stream = sd.Stream(
            samplerate=rate, device=(self.device, self.output),
            channels=(self.channel, self.output_channels), dtype="float32",
            latency=(REQUESTED_LATENCY, REQUESTED_LATENCY), blocksize=0,
            callback=self._callback,
        )
        self._rate = rate
        self.latency = tuple(float(value) for value in self._stream.latency)
        self._stream.start()
        # Only silence is played whilst the device settles; no training audio is discarded.
        if self.cancelled.wait(max(SETTLING_SECONDS, sum(self.latency))):
            raise RecordingCancelled()
        if not self._stream.active:
            raise RuntimeError("Audio stream stopped whilst settling")

    def _play(self, audio: np.ndarray, rate: int, cancelled: Event) -> np.ndarray:
        """Play audio on the open stream and return the return channel, index aligned with the playback."""
        job = _CaptureJob(audio, np.empty((len(audio), 1), dtype=np.float32))
        deadline = monotonic() + len(audio) / rate + max(5.0, sum(self.latency))
        self._job = job
        try:
            while not job.done.wait(0.02):
                if cancelled.is_set():
                    raise RecordingCancelled()
                if not self._stream.active:
                    raise RuntimeError("Audio stream stopped during recording")
                if monotonic() > deadline:
                    raise RuntimeError("Audio device stopped delivering recording buffers")
            if cancelled.is_set():
                raise RecordingCancelled()
            if job.error is not None:
                raise RuntimeError(f"Audio callback failed: {job.error}") from job.error
            if job.status:
                raise RuntimeError(f"Audio discontinuity during recording: {job.status}")
            return job.recorded
        finally:
            self._job = None

    def calibrate(self, rate: int, cancelled: Event) -> int:
        """
        Measure the loop delay at this rate by playing a sweep through the pedal several times.

        Parameters
        ----------
            rate : int
                sample rate of the open stream
            cancelled : Event
                set to stop the measurement

        Returns
        -------
            int
                the delay in frames
        """
        self._open(rate)
        signal = calibration.make_calibration_signal(rate)
        # Send the sweep to every output channel so it reaches the pedal whichever side is wired.
        playback = np.repeat(signal[:, None], self.output_channels, axis=1)
        max_delay = int(calibration.MAX_DELAY_SECONDS * rate)
        delays = []
        for repeat in range(calibration.REPEATS):
            self.progress(f"Measuring loop latency at {rate} Hz ({repeat + 1}/{calibration.REPEATS})...")
            recorded = self._play(playback, rate, cancelled)
            delays.append(calibration.measure_delay(signal, recorded[:, 0], max_delay))
        return calibration.combine_measurements(delays, rate)

    def capture(self, source: str, device: int, output: int, channel: int,
                cancelled: Event) -> tuple[np.ndarray, int]:
        if cancelled.is_set():
            raise RecordingCancelled()
        audio, rate = sf.read(source, dtype="float32", always_2d=True)
        if not len(audio):
            raise ValueError(f"Input sample is empty: {source}")
        if self.output_channels == 1 and audio.shape[1] > 1:
            audio = audio.mean(axis=1, keepdims=True)
        self._open(rate)
        if rate not in self.calibration:
            self.calibration[rate] = self.calibrate(rate, cancelled)
        self.latency_frames = self.calibration[rate]
        # Record for the loop delay as well as the decay tail, then drop the delay from the
        # start so the recording lines up sample for sample with the input.
        tail = math.ceil(rate * self.tail_seconds)
        audio = np.pad(audio, ((0, tail + self.latency_frames), (0, 0)))
        recorded = self._play(audio, rate, cancelled)
        return recorded[self.latency_frames:], rate


def capture_sample(source: str, device: int, output: int, channel: int,
                   cancelled: Event) -> tuple[np.ndarray, int]:
    with BatchRecorder(device, output, channel, cancelled, sf.info(source).channels) as recorder:
        return recorder.capture(source, device, output, channel, cancelled)


class TrainingRun:
    def __init__(self, controls: list[dict], sources: list[str], folder: str,
                 device: int, output: int, channel: int) -> None:
        if not sources:
            raise ValueError("Select at least one input sample")
        if any(not 2 <= c["steps"] <= 101 for c in controls):
            raise ValueError("Choose between 2 and 101 positions per dial")
        self.controls = deepcopy(controls)
        self.sources = list(sources)
        self.total_batches = math.prod(c["steps"] for c in controls)
        self.batch = 0
        self.completed: list[dict] = []
        # Loop delay in frames keyed by sample rate, measured on the first batch.
        self.calibration: dict[int, int] = {}
        self.device, self.output, self.channel = device, output, channel
        self.folder = Path(tempfile.mkdtemp(prefix="training-", dir=folder))
        inputs = self.folder / "inputs"
        inputs.mkdir()
        self.inputs = []
        for index, source in enumerate(self.sources):
            target = inputs / f"{index + 1:04d}{Path(source).suffix}"
            shutil.copyfile(source, target)
            self.inputs.append(target)
        self._save_manifest()

    @property
    def finished(self) -> bool:
        return self.batch == self.total_batches

    @property
    def positions(self) -> list[dict]:
        index = min(self.batch, self.total_batches - 1)
        values = []
        for control in reversed(self.controls):
            index, step = divmod(index, control["steps"])
            values.append({**control, "value": step / (control["steps"] - 1)})
        return list(reversed(values))

    def _save_manifest(self) -> None:
        manifest = {
            "controls": self.controls, "sources": self.sources,
            "input_device": self.device, "output_device": self.output,
            "return_channel": self.channel, "tail_seconds": TAIL_SECONDS,
            "capture_settings": {"requested_latency_seconds": REQUESTED_LATENCY,
                                 "minimum_settling_seconds": SETTLING_SECONDS,
                                 "latency_compensated": True},
            "calibration": {str(rate): {"latency_frames": frames, "latency_seconds": frames / rate}
                            for rate, frames in self.calibration.items()},
            "alignment": "measured loop latency removed; outputs line up sample for sample with inputs",
            "total_batches": self.total_batches, "completed_batches": self.batch,
            "recordings": self.completed,
        }
        temporary = self.folder / "manifest.tmp"
        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.replace(self.folder / "manifest.json")

    def record_batch(self, cancelled: Event, progress: Callable[[str], None],
                     capture: Capture | None = None) -> None:
        if self.finished:
            raise ValueError("Training is already complete")
        pending = [i for i in range(len(self.sources))
                   if not any(r["batch"] == self.batch and r["sample"] == i for r in self.completed)]
        with ExitStack() as stack:
            recorder = None
            if capture is None and pending:
                if cancelled.is_set():
                    raise RecordingCancelled()
                progress("Opening audio stream and allowing the device to settle...")
                recorder = stack.enter_context(BatchRecorder(
                    self.device, self.output, self.channel, cancelled,
                    max(sf.info(self.inputs[i]).channels for i in pending),
                    self.calibration, progress,
                ))
                capture = recorder.capture
            for index in pending:
                source = self.sources[index]
                if cancelled.is_set():
                    raise RecordingCancelled()
                progress(f"Batch {self.batch + 1}/{self.total_batches}: "
                         f"sample {index + 1}/{len(self.sources)} ({Path(source).name})")
                audio, rate = capture(str(self.inputs[index]), self.device, self.output, self.channel, cancelled)
                if cancelled.is_set():
                    raise RecordingCancelled()
                filename = f"batch-{self.batch + 1:06d}-sample-{index + 1:04d}.wav"
                sf.write(self.folder / filename, audio, rate, subtype="FLOAT")
                self.completed.append({"batch": self.batch, "sample": index,
                                       "source": source, "input": str(self.inputs[index].relative_to(self.folder)),
                                       "output": filename,
                                       "sample_rate": rate, "frames": len(audio),
                                       "controls": self.positions})
                if recorder is not None:
                    self.completed[-1]["device_latency_seconds"] = list(recorder.latency)
                    self.completed[-1]["tail_seconds"] = recorder.tail_seconds
                    self.completed[-1]["latency_frames"] = recorder.latency_frames
                try:
                    self._save_manifest()
                except Exception:
                    self.completed.pop()
                    raise
        self.batch += 1
        try:
            self._save_manifest()
        except Exception:
            self.batch -= 1
            raise
