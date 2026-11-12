"""Session state independent of the GUI and physical audio hardware."""

from experiments.mixer_devices import input_devices
from pathlib import Path

import soundfile as sf


class TrainingSession:
    def __init__(self, query_devices=None) -> None:
        self._query_devices = query_devices
        self.devices: list[dict] = []
        self.selected_device_id: int = -1
        self.controls: list[dict] = []
        self.samples: list[dict] = []

    @property
    def selected_sample_paths(self) -> list[str]:
        return [s["path"] for s in self.samples if s["selected"]]

    def add_sample_folder(self, folder: str | Path) -> list[str]:
        """Append readable audio files from one folder, returning skipped filenames."""
        folder = Path(folder).expanduser().resolve()
        if not folder.is_dir():
            raise ValueError("Choose an existing sample folder")
        known = {s["path"] for s in self.samples}
        skipped = []
        for path in sorted(folder.iterdir(), key=lambda p: p.name.casefold()):
            if not path.is_file() or path.suffix.lower() not in {".wav", ".flac", ".aif", ".aiff", ".ogg"}:
                continue
            resolved = str(path.resolve())
            if resolved in known:
                continue
            try:
                info = sf.info(path)
            except (OSError, sf.LibsndfileError):
                skipped.append(path.name)
                continue
            self.samples.append({"name": path.name, "path": resolved,
                                 "duration": info.duration, "channels": info.channels,
                                 "sample_rate": info.samplerate, "selected": False})
            known.add(resolved)
        return skipped

    def select_sample(self, index: int, selected: bool) -> None:
        self.samples[index]["selected"] = selected

    def set_control_count(self, count: int) -> None:
        if not 0 <= count <= 16:
            raise ValueError("Choose between 0 and 16 controls")
        self.controls = self.controls[:count] + [
            {"label": f"Control {i + 1}", "value": 0.5}
            for i in range(len(self.controls), count)
        ]

    def set_control_label(self, index: int, label: str) -> None:
        self.controls[index]["label"] = label.strip() or f"Control {index + 1}"

    def set_control_value(self, index: int, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Control values must be between 0 and 1")
        self.controls[index]["value"] = value

    @property
    def selected_device(self) -> dict | None:
        return next((d for d in self.devices if d["id"] == self.selected_device_id), None)

    def refresh_devices(self) -> None:
        self.devices = input_devices(self._query_devices)
        if self.selected_device is None:
            self.selected_device_id = self.devices[0]["id"] if self.devices else -1

    def select_device(self, device_id: int) -> None:
        if not any(d["id"] == device_id for d in self.devices):
            raise ValueError("Choose an available audio input")
        self.selected_device_id = device_id
