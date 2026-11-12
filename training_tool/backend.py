"""Small Qt interface for the training session."""

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl

if __package__:
    from .session import TrainingSession
else:
    from session import TrainingSession


class TrainingBackend(QObject):
    devicesChanged = Signal()
    controlsChanged = Signal()
    samplesChanged = Signal()
    messageChanged = Signal()

    def __init__(self, session: TrainingSession | None = None) -> None:
        super().__init__()
        self.session = session or TrainingSession()
        self._message = ""
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

    def _set_message(self, message: str) -> None:
        self._message = message
        self.messageChanged.emit()

    @Slot()
    def refreshDevices(self) -> None:
        try:
            self.session.refresh_devices()
            self._set_message("Inputs refreshed" if self.devices else "No audio inputs found. Connect your mixer and refresh.")
        except Exception as error:
            # PortAudio may be unavailable, denied permission, or lose a USB device.
            self.session.devices = []
            self.session.selected_device_id = -1
            self._set_message(f"Cannot read audio inputs: {error}")
        self.devicesChanged.emit()

    @Slot(int)
    def selectDevice(self, index: int) -> None:
        if 0 <= index < len(self.devices):
            self.session.select_device(self.devices[index]["id"])
            self.devicesChanged.emit()

    @Slot(int)
    def setControlCount(self, count: int) -> None:
        try:
            self.session.set_control_count(count)
        except ValueError as error:
            self._set_message(str(error))
            return
        self.controlsChanged.emit()

    @Slot(int, str)
    def setControlLabel(self, index: int, label: str) -> None:
        self.session.set_control_label(index, label)
        self.controlsChanged.emit()

    @Slot(int, float)
    def setControlValue(self, index: int, value: float) -> None:
        self.session.set_control_value(index, value)
        self.controlsChanged.emit()

    @Slot(QUrl)
    def addSampleFolder(self, url: QUrl) -> None:
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
        self.session.select_sample(index, selected)
        self.samplesChanged.emit()

    @Slot(bool)
    def selectAllSamples(self, selected: bool) -> None:
        for index in range(len(self.samples)):
            self.session.select_sample(index, selected)
        self.samplesChanged.emit()

    @Slot()
    def clearSamples(self) -> None:
        self.session.samples.clear()
        self.samplesChanged.emit()
