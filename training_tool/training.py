"""Plan dial combinations and keep a record of each captured sample."""

from collections.abc import Callable
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import shutil
from threading import Event

import numpy as np
import sounddevice as sd
import soundfile as sf


type Capture = Callable[[str, int, int, int, Event], tuple[np.ndarray, int]]


class RecordingCancelled(Exception):
    pass


def capture_sample(source: str, device: int, output: int, channel: int,
                   cancelled: Event) -> tuple[np.ndarray, int]:
    audio, rate = sf.read(source, dtype="float32", always_2d=True)
    output_channels = int(sd.query_devices(output, "output")["max_output_channels"])
    if output_channels == 1 and audio.shape[1] > 1:
        audio = audio.mean(axis=1, keepdims=True)
    elif audio.shape[1] > output_channels:
        raise ValueError("Playback output has too few channels for this sample")
    # Keep a short tail for the pedal's decay. Timing is stored raw for later alignment.
    audio = np.pad(audio, ((0, round(rate * 0.25)), (0, 0)))
    recorded = sd.playrec(audio, samplerate=rate, channels=1, dtype="float32",
                          device=(device, output), input_mapping=[channel],
                          output_mapping=list(range(1, audio.shape[1] + 1)))
    try:
        stream = sd.get_stream()
        while stream.active:
            if cancelled.wait(0.02):
                raise RecordingCancelled()
        status = sd.wait()
        if status:
            raise RuntimeError(f"Audio dropped samples: {status}")
        if cancelled.is_set():
            raise RecordingCancelled()
    finally:
        sd.stop()
    return recorded, rate


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
            "return_channel": self.channel, "tail_seconds": 0.25,
            "alignment": "raw device timing; align input and output before training",
            "total_batches": self.total_batches, "completed_batches": self.batch,
            "recordings": self.completed,
        }
        temporary = self.folder / "manifest.tmp"
        temporary.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        temporary.replace(self.folder / "manifest.json")

    def record_batch(self, cancelled: Event, progress: Callable[[str], None],
                     capture: Capture = capture_sample) -> None:
        if self.finished:
            raise ValueError("Training is already complete")
        for index, source in enumerate(self.sources):
            if cancelled.is_set():
                raise RecordingCancelled()
            if any(r["batch"] == self.batch and r["sample"] == index for r in self.completed):
                continue
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
