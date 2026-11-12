"""Small Qt interface for the training session."""

import math
from threading import Event

import soundfile as sf

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QThread

if __package__:
    from .session import TrainingSession
    from .training import TrainingRun, RecordingCancelled, capture_sample, Capture
else:
    from session import TrainingSession
    from training import TrainingRun, RecordingCancelled, capture_sample, Capture


class BatchWorker(QThread):
    progress = Signal(str)

    def __init__(self, run: TrainingRun, capture: Capture, parent: QObject) -> None:
        super().__init__(parent)
        self.training_run = run
        self.capture = capture
        self.cancelled = Event()
        self.result = ""

    def run(self) -> None:
        try:
            self.training_run.record_batch(self.cancelled, self.progress.emit, self.capture)
        except RecordingCancelled:
            self.result = "Paused. Confirm the pedal settings to retry the unfinished samples."
        except Exception as error:
            self.result = f"Recording failed: {error}. Confirm the settings to retry unfinished samples."


class TrainingBackend(QObject):
    devicesChanged = Signal()
    controlsChanged = Signal()
    samplesChanged = Signal()
    messageChanged = Signal()
    trainingChanged = Signal()

    def __init__(self, session: TrainingSession | None = None, capture: Capture | None = None) -> None:
        super().__init__()
        self.session = session or TrainingSession()
        self._message = ""
        self._run: TrainingRun | None = None
        self._worker: BatchWorker | None = None
        self._capture = capture or capture_sample
        self.session.set_control_count(3)
        self.refreshDevices()

    @Property("QVariantList", notify=devicesChanged)
    def devices(self) -> list[dict]:
        return self.session.devices

    @Property(int, notify=devicesChanged)
    def selectedDeviceIndex(self) -> int:
        return next((i for i, d in enumerate(self.session.devices)
                     if d["id"] == self.session.selected_device_id), -1)

    @Property("QVariantList", notify=controlsChanged)
    def controls(self) -> list[dict]:
        return self.session.controls

    @Property("QVariantList", notify=samplesChanged)
    def samples(self) -> list[dict]:
        return self.session.samples

    @Property(int, notify=samplesChanged)
    def selectedSampleCount(self) -> int:
        return len(self.session.selected_sample_paths)

    @Property(str, notify=messageChanged)
    def message(self) -> str:
        return self._message

    @Slot(str)
    def _set_message(self, message: str) -> None:
        self._message = message
        self.messageChanged.emit()

    @Slot()
    def refreshDevices(self) -> None:
        if self.runActive or self.recording:
            return
        try:
            self.session.refresh_devices()
            self._set_message("Inputs refreshed" if self.devices else "No audio inputs found. Connect your mixer and refresh.")
        except Exception as error:
            # PortAudio may be unavailable, denied permission, or lose a USB device.
            self.session.outputs = []
            self.session.selected_output_id = -1
            self.session.devices = []
            self.session.selected_device_id = -1
            self._set_message(f"Cannot read audio inputs: {error}")
        self.devicesChanged.emit()

    @Slot(int)
    def selectDevice(self, index: int) -> None:
        if self.runActive or self.recording:
            return
        if 0 <= index < len(self.devices):
            self.session.select_device(self.devices[index]["id"])
            self.devicesChanged.emit()

    @Slot(int)
    def setControlCount(self, count: int) -> None:
        if self.runActive or self.recording:
            return
        try:
            self.session.set_control_count(count)
        except ValueError as error:
            self._set_message(str(error))
            return
        self.controlsChanged.emit()

    @Slot(int, str)
    def setControlLabel(self, index: int, label: str) -> None:
        if self.runActive or self.recording:
            return
        self.session.set_control_label(index, label)
        self.controlsChanged.emit()

    @Slot(int, float)
    def setControlValue(self, index: int, value: float) -> None:
        if self.runActive or self.recording:
            return
        self.session.set_control_value(index, value)
        self.controlsChanged.emit()

    @Slot(QUrl)
    def addSampleFolder(self, url: QUrl) -> None:
        if self.runActive or self.recording:
            return
        try:
            skipped = self.session.add_sample_folder(url.toLocalFile())
        except (OSError, ValueError) as error:
            self._set_message(str(error))
            return
        self.samplesChanged.emit()
        detail = f" Skipped unreadable audio: {', '.join(skipped)}" if skipped else ""
        self._set_message(f"{len(self.samples)} samples available.{detail}")

    @Slot(int, bool)
    def selectSample(self, index: int, selected: bool) -> None:
        if self.runActive or self.recording:
            return
        self.session.select_sample(index, selected)
        self.samplesChanged.emit()

    @Slot(bool)
    def selectAllSamples(self, selected: bool) -> None:
        if self.runActive or self.recording:
            return
        for index in range(len(self.samples)):
            self.session.select_sample(index, selected)
        self.samplesChanged.emit()

    @Slot()
    def clearSamples(self) -> None:
        if self.runActive or self.recording:
            return
        self.session.samples.clear()
        self.samplesChanged.emit()

    @Property("QVariantList", notify=devicesChanged)
    def outputs(self) -> list[dict]:
        return self.session.outputs

    @Property(int, notify=devicesChanged)
    def selectedOutputIndex(self) -> int:
        return next((i for i, d in enumerate(self.outputs)
                     if d["id"] == self.session.selected_output_id), -1)

    @Property(int, notify=devicesChanged)
    def returnChannel(self) -> int:
        return self.session.return_channel

    @Property(bool, notify=trainingChanged)
    def runActive(self) -> bool:
        return self._run is not None and not self._run.finished

    @Property(bool, notify=trainingChanged)
    def recording(self) -> bool:
        return self._worker is not None

    @Property(str, notify=trainingChanged)
    def trainingSummary(self) -> str:
        if self._run is None:
            return "Prepare a run, then set the physical pedal to match the displayed dials."
        if self._run.finished:
            return f"Training complete. {len(self._run.completed)} recordings saved in {self._run.folder}"
        return (f"Set the pedal for batch {self._run.batch + 1}/{self._run.total_batches}. "
                f"Each batch records {len(self._run.sources)} input samples.")

    @Property(str, notify=controlsChanged)
    def planSize(self) -> str:
        batches = math.prod(c["steps"] for c in self.controls)
        return f"{batches:,} dial combinations"

    @Slot(int)
    def selectOutput(self, index: int) -> None:
        if not self.runActive and not self.recording and 0 <= index < len(self.outputs):
            self.session.selected_output_id = self.outputs[index]["id"]
            self.devicesChanged.emit()

    @Slot(int)
    def setReturnChannel(self, channel: int) -> None:
        device = self.session.selected_device
        if not self.runActive and not self.recording and device and 1 <= channel <= device["channels"]:
            self.session.return_channel = channel
            self.devicesChanged.emit()

    @Slot(int, int)
    def setControlSteps(self, index: int, steps: int) -> None:
        if self.runActive or self.recording:
            return
        try:
            self.session.set_control_steps(index, steps)
        except ValueError as error:
            self._set_message(str(error))
            return
        self.controlsChanged.emit()

    @Slot(QUrl)
    def prepareRun(self, folder: QUrl) -> None:
        if self.runActive or self.recording:
            return
        try:
            if self.session.selected_device is None or self.session.selected_output is None:
                raise ValueError("Choose a mixer input and a playback output")
            sources = self.session.selected_sample_paths
            if not sources:
                raise ValueError("Select at least one input sample")
            for source in sources:
                info = sf.info(source)
                if info.frames == 0:
                    raise ValueError(f"Input sample is empty: {source}")
                if (self.session.selected_output["channels"] != 1
                        and info.channels > self.session.selected_output["channels"]):
                    raise ValueError(f"Playback output has too few channels for {source}")
            self._run = TrainingRun(self.controls, sources, folder.toLocalFile(),
                                    self.session.selected_device_id, self.session.selected_output_id,
                                    self.session.return_channel)
        except Exception as error:
            self._set_message(str(error))
            return
        self._show_positions()
        self._set_message(f"Run saved in {self._run.folder}. Set the pedal, then record the batch.")
        self.trainingChanged.emit()

    def _show_positions(self) -> None:
        for control, target in zip(self.controls, self._run.positions):
            control["value"] = target["value"]
        self.controlsChanged.emit()

    @Slot()
    def recordBatch(self) -> None:
        if not self.runActive or self.recording:
            return
        self._worker = BatchWorker(self._run, self._capture, self)
        self._worker.progress.connect(self._set_message)
        self._worker.finished.connect(self._batch_finished)
        self._worker.start()
        self.trainingChanged.emit()

    @Slot()
    def _batch_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker.result:
            self._set_message(worker.result)
        elif self._run.finished:
            self._set_message("All batches recorded.")
        else:
            self._show_positions()
            self._set_message("Batch saved. Set the pedal to the new positions, then record the next batch.")
        worker.deleteLater()
        self.trainingChanged.emit()

    @Slot()
    def pauseRecording(self) -> None:
        if self._worker:
            self._worker.cancelled.set()

    @Slot()
    def endRun(self) -> None:
        if self.recording:
            return
        self._run = None
        self._set_message("Run ended. Saved recordings and their manifest have been kept.")
        self.trainingChanged.emit()

    @Slot()
    def shutdown(self) -> None:
        if self._worker:
            self._worker.cancelled.set()
            self._worker.wait()
