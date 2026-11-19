# sample_rate
# input channels
# control_labels (i.e. the controls from the pedal like drive, level gain.)
# private attribs _offsets for output
# _recordings (our main data) list

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from random import Random

import soundfile as sf
import torch
from torch import Tensor
from torch.utils.data import Dataset, Subset


# [] len(dataset)
@dataclass(frozen=True)
class _Recording:
    input_path: Path
    output_path: Path
    controls: tuple[float, ...]


class PedalDataset(Dataset[tuple[Tensor, Tensor, Tensor]]):
    def __init__(
        self,
        manifest_path: str | Path,
        *,
        window_frames: int | None = None,
        hop_frames: int | None = None,
        output_offset_frames: int | None = None,
    ):
        path = Path(manifest_path).resolve()
        manifest = json.loads(path.read_text())

        if window_frames is not None and window_frames <= 0:
            raise ValueError("window frames must be positive")

        if hop_frames is not None and hop_frames <= 0:
            raise ValueError("hop frames must be non negative")

        if output_offset_frames is None:
            output_offset_frames = 0
        if output_offset_frames < 0:
            raise ValueError("output offset frame must be non negative")

        rows = manifest["recordings"]
        self._sample_rate = rows[0]["sample_rate"]
        self.control_labels = tuple(control["label"] for control in manifest["controls"])
        self._output_offset = output_offset_frames

        self._recordings: list[_Recording] = []
        self._examples: list[tuple[int, int, int]] = []
        self._by_input: dict[Path, list[int]] = defaultdict(list)

        input_frames: dict[Path, int] = {}

        for row in rows:
            dry_path = (path.parent / row["input"]).resolve()
            wet_path = (path.parent / row["output"]).resolve()

            if dry_path not in input_frames:
                info = sf.info(dry_path)
                if not input_frames:
                    self.input_channels = info.channels
                input_frames[dry_path] = info.frames
            frames = input_frames[dry_path]
            if frames == 0 or (window_frames is not None and window_frames > frames):
                raise ValueError(f"Dry Clip is too short {dry_path}")

            controls = tuple(float(control["value"]) for control in row["controls"])
            recording_index = len(self._recordings)
            self._recordings.append(_Recording(dry_path, wet_path, controls))
            length = frames if window_frames is None else window_frames
            hop = hop_frames if hop_frames is not None else window_frames
            for start in range(0, frames - length + 1, hop or length):
                self._by_input[dry_path].append(len(self._examples))
                self._examples.append((recording_index, start, length))

    def __len__(self) -> int:
        return len(self._examples)

    def __getitem__(self, index: int) -> tuple[Tensor, Tensor, Tensor]:
        recording_index, start, length = self._examples[index]
        recording = self._recordings[recording_index]
        inputs, _ = sf.read(recording.input_path, start=start, frames=length, dtype="float32", always_2d=True)
        targets, _ = sf.read(
            recording.output_path, start=start + self._output_offset, frames=length, dtype="float32", always_2d=True
        )
        return (
            torch.from_numpy(inputs.T),
            torch.from_numpy(targets.T),
            torch.tensor(recording.controls, dtype=torch.float32),
        )


def split_by_input(
    dataset: PedalDataset,
    *,
    validation_fraction: float = 0.1,
    test_fraction: float = 0.1,
    seed: int = 0,
) -> tuple[Subset, Subset, Subset]:
    """Return train, validation and test subsets grouped by dry input file."""
    if not (0 <= validation_fraction and 0 <= test_fraction and validation_fraction + test_fraction < 1):
        raise ValueError("Validation and test fractions must be non-negative and sum to less than one")

    inputs = sorted(dataset._by_input)
    Random(seed).shuffle(inputs)
    n_valid = max(1, round(len(inputs) * validation_fraction)) if validation_fraction else 0
    n_test = max(1, round(len(inputs) * test_fraction)) if test_fraction else 0
    n_train = len(inputs) - n_valid - n_test
    if n_train <= 0:
        raise ValueError("Too few dry inputs for the requested split")

    def subset(paths: list[Path]) -> Subset:
        return Subset(dataset, [index for path in paths for index in dataset._by_input[path]])

    return (
        subset(inputs[:n_train]),
        subset(inputs[n_train : n_train + n_valid]),
        subset(inputs[n_train + n_valid :]),
    )
