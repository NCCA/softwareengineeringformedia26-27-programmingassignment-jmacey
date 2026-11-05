from enum import IntEnum

import numpy as np


class Note(IntEnum):
    C = 0
    C_SHARP = 1
    D_FLAT = 1
    D = 2
    D_SHARP = 3
    E_FLAT = 3
    E = 4
    F = 5
    F_SHARP = 6
    G_FLAT = 6
    G = 7
    G_SHARP = 8
    A_FLAT = 8
    A = 9
    A_SHARP = 10
    B_FLAT = 10
    B = 11


class AudioSample:
    def __init__(self, sample_rate: int = 44100) -> None:
        """
        Build our audio sample with default sample rate of 44100 Hz
        """
        self._sample_rate = sample_rate
        self._audio = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value: int) -> None:
        if not isinstance(value, int):
            raise TypeError("need int only")
        if value <= 0:
            raise ValueError("Need positive non zero value")
        self._sample_rate = value

    @property
    def audio(self) -> np.ndarray:
        return self._audio

    @audio.setter
    def audio(self, _):
        raise NotImplementedError("audio is set by methods of class")

    def _sine(self, frequency: float, duration: float, amplitude: float) -> np.ndarray:
        samples = int(self._sample_rate * duration)
        t = np.arange(samples) / self._sample_rate
        return amplitude * np.sin(2.0 * np.pi * frequency * t)

    def _note_to_frequency(self, note: Note, octave: int) -> float:
        semitones_from_a4 = 12 * (octave - 4) + note - Note.A
        return 440.0 * 2 ** (semitones_from_a4 / 12)

    def sine_tone(self, note: str | None, octave: int, duration: float, amplitude: float):
        if isinstance(note, str):
            note = Note[note.strip().upper()]
        self._audio = self._sine(self._note_to_frequency(note, octave), duration, amplitude)
