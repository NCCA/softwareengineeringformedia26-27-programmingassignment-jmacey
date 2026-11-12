"""Session state independent of the GUI and physical audio hardware."""

from pathlib import Path

import soundfile as sf

if __package__:
    from .mixer import input_devices, output_devices
else:
    from mixer import input_devices, output_devices


class TrainingSession:
    def __init__(self, query_devices=None) -> None:
        self._query_devices = query_devices
        self.devices: list[dict] = []
        self.selected_device_id: int = -1
        self.outputs: list[dict] = []
        self.selected_output_id: int = -1
        self.return_channel: int = 1
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
            {"label": f"Control {i + 1}", "value": 0.5, "steps": 3}
            for i in range(len(self.controls), count)
        ]

    def set_control_label(self, index: int, label: str) -> None:
        self.controls[index]["label"] = label.strip() or f"Control {index + 1}"

    def set_control_value(self, index: int, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValueError("Control values must be between 0 and 1")
        self.controls[index]["value"] = value

    def set_control_steps(self, index: int, steps: int) -> None:
        if not 2 <= steps <= 101:
            raise ValueError("Choose between 2 and 101 positions per dial")
        self.controls[index]["steps"] = steps

    @property
    def selected_output(self) -> dict | None:
        return next((d for d in self.outputs if d["id"] == self.selected_output_id), None)

    @property
    def selected_device(self) -> dict | None:
        return next((d for d in self.devices if d["id"] == self.selected_device_id), None)

    def refresh_devices(self) -> None:
        self.devices = input_devices(self._query_devices)
        self.outputs = output_devices(self._query_devices)
        if self.selected_output is None:
            self.selected_output_id = self.outputs[0]["id"] if self.outputs else -1
        if self.selected_device is None:
            self.selected_device_id = self.devices[0]["id"] if self.devices else -1
            self.return_channel = 1
        elif self.return_channel > self.selected_device["channels"]:
            self.return_channel = 1

    def select_device(self, device_id: int) -> None:
        if not any(d["id"] == device_id for d in self.devices):
            raise ValueError("Choose an available audio input")
        self.selected_device_id = device_id
        self.return_channel = 1

    def settings_data(self) -> dict:
        return {
            "version": 1,
            "input": self.selected_device["name"] if self.selected_device else None,
            "output": self.selected_output["name"] if self.selected_output else None,
            "return_channel": self.return_channel,
            "controls": [dict(control) for control in self.controls],
            "samples": [{"path": sample["path"], "selected": sample["selected"]}
                        for sample in self.samples],
        }

    def restore_settings(self, data: dict) -> list[str]:
        """Check the whole setup before replacing the current session."""
        if not isinstance(data, dict) or data.get("version") != 1:
            raise ValueError("Unsupported settings format")
        controls = data.get("controls")
        samples = data.get("samples")
        channel = data.get("return_channel", 1)
        if not isinstance(controls, list) or len(controls) > 16:
            raise ValueError("Settings must contain between 0 and 16 controls")
        if not isinstance(samples, list) or type(channel) is not int or channel < 1:
            raise ValueError("Invalid samples or return channel")
        for key in ("input", "output"):
            if data.get(key) is not None and not isinstance(data[key], str):
                raise ValueError("Invalid audio device name")
        restored_controls = []
        for control in controls:
            if (not isinstance(control, dict)
                    or not isinstance(control.get("label"), str)
                    or not control["label"].strip() or len(control["label"]) > 64
                    or type(control.get("value")) not in (float, int)
                    or not 0 <= control["value"] <= 1
                    or type(control.get("steps")) is not int
                    or not 2 <= control["steps"] <= 101):
                raise ValueError("Invalid control settings")
            restored_controls.append({key: control[key] for key in ("label", "value", "steps")})
        restored_samples = []
        skipped = []
        known = set()
        for sample in samples:
            if (not isinstance(sample, dict) or not isinstance(sample.get("path"), str)
                    or type(sample.get("selected")) is not bool):
                raise ValueError("Invalid sample settings")
            path = Path(sample["path"]).expanduser().resolve()
            if str(path) in known:
                continue
            known.add(str(path))
            try:
                info = sf.info(path)
            except (OSError, sf.LibsndfileError):
                skipped.append(str(path))
                continue
            restored_samples.append({"name": path.name, "path": str(path),
                                     "duration": info.duration, "channels": info.channels,
                                     "sample_rate": info.samplerate, "selected": sample["selected"]})
        warnings = []
        for key, available, attribute in (
                ("input", self.devices, "selected_device_id"),
                ("output", self.outputs, "selected_output_id")):
            match = next((d for d in available if d["name"] == data.get(key)), None)
            setattr(self, attribute, match["id"] if match else (available[0]["id"] if available else -1))
            if data.get(key) and match is None:
                warnings.append(f"Audio device unavailable: {data[key]}")
        self.return_channel = channel if self.selected_device and channel <= self.selected_device["channels"] else 1
        self.controls = restored_controls
        self.samples = restored_samples
        if skipped:
            warnings.append(f"Skipped missing or unreadable samples: {', '.join(skipped)}")
        return warnings
