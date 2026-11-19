"""
PyTorch dataset for paired dry / wet pedal recordings.

The dataset is driven by a JSON manifest which lists each recording, the dry
input file, the wet (pedal) output file and the control values used for the
take. Audio is read lazily from disk in ``__getitem__`` so only the file
metadata is touched when the dataset is built.
"""

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from random import Random

import soundfile as sf
import torch
from torch import Tensor
from torch.utils.data import Dataset, Subset

type Example = tuple[Tensor, Tensor, Tensor]
"""A single (input, target, controls) example returned by the dataset."""


# [] len(dataset)
@dataclass(frozen=True)
class _Recording:
    """
    A single row from the manifest with the paths resolved.

    Attributes
    ----------
        input_path : Path
            absolute path to the dry input file
        output_path : Path
            absolute path to the wet (pedal) output file
        controls : tuple[float, ...]
            control values used for this recording, in manifest order
    """

    input_path: Path
    output_path: Path
    controls: tuple[float, ...]


class PedalDataset(Dataset[Example]):
    """
    Dataset of dry / wet audio pairs plus the pedal control values.

    Each recording can be cut into fixed size windows, so one recording may
    give many examples. If no window size is given each recording is a single
    example covering the whole file.

    Attributes
    ----------
        control_labels : tuple[str, ...]
            names of the pedal controls (e.g. drive, level, gain) in manifest order
        input_channels : int
            number of channels in the dry input files (taken from the first file)
    """

    control_labels: tuple[str, ...]
    input_channels: int

    def __init__(
        self,
        manifest_path: str | Path,
        *,
        window_frames: int | None = None,
        hop_frames: int | None = None,
        output_offset_frames: int | None = None,
    ) -> None:
        """
        Build the example index from a manifest file.

        Parameters
        ----------
            manifest_path : str | Path
                path to the JSON manifest, input and output paths in it are
                relative to the manifest's folder
            window_frames : int | None
                length of each example in frames, None uses the whole file
            hop_frames : int | None
                step between window starts, None defaults to window_frames
                (i.e. no overlap)
            output_offset_frames : int | None
                number of frames to skip in the wet file so it lines up with the
                dry file (for example to remove loop latency), None means 0

        Raises
        ------
            ValueError
                if any of the frame values are invalid or a dry clip is shorter
                than the window
        """
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
        self._sample_rate: int = rows[0]["sample_rate"]
        self.control_labels = tuple(control["label"] for control in manifest["controls"])
        self._output_offset: int = output_offset_frames

        self._recordings: list[_Recording] = []
        # each example is (recording index, start frame, length in frames)
        self._examples: list[tuple[int, int, int]] = []
        # example indices grouped by dry file, used by split_by_input
        self._by_input: dict[Path, list[int]] = defaultdict(list)

        # cache the frame count so a dry file shared by many recordings is only probed once
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

    def __getitem__(self, index: int) -> Example:
        """
        Read one window of audio from disk.

        Parameters
        ----------
            index : int
                the example to load

        Returns
        -------
            tuple[Tensor, Tensor, Tensor]
                the dry input as (channels, frames), the wet target as
                (channels, frames) and the control values as a 1D float tensor
        """
        recording_index, start, length = self._examples[index]
        recording = self._recordings[recording_index]
        inputs, _ = sf.read(recording.input_path, start=start, frames=length, dtype="float32", always_2d=True)
        targets, _ = sf.read(
            recording.output_path, start=start + self._output_offset, frames=length, dtype="float32", always_2d=True
        )
        # soundfile gives (frames, channels) but torch audio code expects (channels, frames)
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
) -> tuple[Subset[Example], Subset[Example], Subset[Example]]:
    """
    Return train, validation and test subsets grouped by dry input file.

    All the examples that share a dry input end up in the same subset, this
    stops the model seeing the same input audio in training and testing.

    Parameters
    ----------
        dataset : PedalDataset
            the dataset to split
        validation_fraction : float
            fraction of the dry inputs to use for validation
        test_fraction : float
            fraction of the dry inputs to use for testing
        seed : int
            seed for the shuffle so the split is repeatable

    Returns
    -------
        tuple[Subset, Subset, Subset]
            the train, validation and test subsets

    Raises
    ------
        ValueError
            if the fractions are invalid or there are not enough dry inputs to
            leave anything for training
    """
    if not (0 <= validation_fraction and 0 <= test_fraction and validation_fraction + test_fraction < 1):
        raise ValueError("Validation and test fractions must be non-negative and sum to less than one")

    inputs = sorted(dataset._by_input)
    Random(seed).shuffle(inputs)
    # any non zero fraction gets at least one input so small datasets still have a split
    n_valid = max(1, round(len(inputs) * validation_fraction)) if validation_fraction else 0
    n_test = max(1, round(len(inputs) * test_fraction)) if test_fraction else 0
    n_train = len(inputs) - n_valid - n_test
    if n_train <= 0:
        raise ValueError("Too few dry inputs for the requested split")

    def subset(paths: list[Path]) -> Subset[Example]:
        return Subset(dataset, [index for path in paths for index in dataset._by_input[path]])

    return (
        subset(inputs[:n_train]),
        subset(inputs[n_train : n_train + n_valid]),
        subset(inputs[n_train + n_valid :]),
    )
