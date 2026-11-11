from enum import IntEnum, StrEnum

import numpy as np
import soundfile as sf


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


class ArpeggioMode(StrEnum):
    ASCEND = "ascend"
    DESCEND = "descend"
    ASCEND_DESCEND = "ascend_descend"


CHORD_TEMPLATES = {
    "major": frozenset((0, 4, 7)),
    "minor": frozenset((0, 3, 7)),
    "diminished": frozenset((0, 3, 6)),
    "augmented": frozenset((0, 4, 8)),
    "dominant7": frozenset((0, 4, 7, 10)),
    "major7": frozenset((0, 4, 7, 11)),
    "minor7": frozenset((0, 3, 7, 10)),
}


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
        return amplitude * np.sin(2.0 * np.pi * frequency * t, dtype=np.float32)

    def _note_to_frequency(self, note: Note, octave: int) -> float:
        semitones_from_a4 = 12 * (octave - 4) + note - Note.A
        return 440.0 * 2 ** (semitones_from_a4 / 12)

    def sine_tone(self, note: str | None, octave: int, duration: float, amplitude: float):
        if isinstance(note, str):
            note = Note[note.strip().upper()]
        self._audio = self._sine(self._note_to_frequency(note, octave), duration, amplitude)

    def _adsr_envelope(
        self, samples: int, attack: float, decay: float, sustain: float, release: float
    ) -> np.ndarray:
        """
        Build a linear ADSR envelope the same length as the note, the sustain section
        fills whatever time is left after the attack, decay and release.

        Parameters
        ----------
            samples : int
                total number of samples in the note
            attack : float
                time in seconds to ramp from silence to full amplitude
            decay : float
                time in seconds to fall from full amplitude to the sustain level
            sustain : float
                sustain level in the range 0.0 - 1.0
            release : float
                time in seconds to fade from the sustain level to silence
        """
        if min(attack, decay, release) < 0.0:
            raise ValueError("attack, decay and release must be positive")
        if not 0.0 <= sustain <= 1.0:
            raise ValueError("sustain must be in the range 0.0 - 1.0")
        attack_samples = int(attack * self._sample_rate)
        decay_samples = int(decay * self._sample_rate)
        release_samples = int(release * self._sample_rate)
        sustain_samples = samples - attack_samples - decay_samples - release_samples
        if sustain_samples < 0:
            raise ValueError("attack + decay + release must fit inside the duration")
        # endpoint=False so each section starts where the last one left off without
        # repeating a sample, the release does include the end point so we finish on 0
        return np.concatenate(
            [
                np.linspace(0.0, 1.0, attack_samples, endpoint=False),
                np.linspace(1.0, sustain, decay_samples, endpoint=False),
                np.full(sustain_samples, sustain),
                np.linspace(sustain, 0.0, release_samples),
            ]
        ).astype(np.float32)

    def adsr_tone(
        self,
        note: Note | str,
        octave: int,
        duration: float,
        amplitude: float,
        attack: float,
        decay: float,
        sustain: float,
        release: float,
    ) -> None:
        """
        Generate a sine tone shaped by an ADSR (attack, decay, sustain, release) envelope.
        See https://en.wikipedia.org/wiki/Envelope_(music) for more details.

        Parameters
        ----------
            note : Note | str
                the note to play, either a Note or its name e.g. "C_SHARP"
            octave : int
                the octave of the note, A4 is 440 Hz
            duration : float
                total length of the note in seconds, including the release
            amplitude : float
                peak amplitude reached at the end of the attack
            attack : float
                time in seconds to ramp from silence to full amplitude
            decay : float
                time in seconds to fall from full amplitude to the sustain level
            sustain : float
                sustain level as a fraction of amplitude (0.0 - 1.0)
            release : float
                time in seconds to fade from the sustain level to silence
        """
        if isinstance(note, str):
            note = Note[note.strip().upper()]
        tone = self._sine(self._note_to_frequency(note, octave), duration, amplitude)
        self._audio = tone * self._adsr_envelope(len(tone), attack, decay, sustain, release)

    def _chord(self, root: Note | str, chord_type: str, octave: int, duration: float, amplitude: float) -> np.ndarray:
        if chord_type not in CHORD_TEMPLATES:
            raise ValueError(f"{chord_type} is not a valid chord")
        if isinstance(root, str):
            root = Note[root.strip().upper()]
        offsets = CHORD_TEMPLATES[chord_type]
        samples = int(self._sample_rate * duration)
        audio = np.zeros(samples, dtype=np.float32)
        for offset in offsets:
            frequency = self._note_to_frequency(root + offset, octave)
            audio += self._sine(frequency, duration, amplitude)
        return audio / len(offsets)

    def chord(self, root: Note | str, chord_type: str, octave: int, duration: float, amplitude: float) -> None:
        self._audio = self._chord(root, chord_type, octave, duration, amplitude)

    def adsr_chord(
        self,
        root: Note | str,
        chord_type: str,
        octave: int,
        duration: float,
        amplitude: float,
        attack: float,
        decay: float,
        sustain: float,
        release: float,
    ) -> None:
        """
        Generate a chord shaped by an ADSR envelope, the envelope is applied to the
        mixed chord so all the notes start and stop together.

        Parameters
        ----------
            root : Note | str
                the root note of the chord, either a Note or its name e.g. "C_SHARP"
            chord_type : str
                one of the keys in CHORD_TEMPLATES e.g. "major"
            octave : int
                the octave of the root note, A4 is 440 Hz
            duration : float
                total length of the chord in seconds, including the release
            amplitude : float
                amplitude of each note before the chord is mixed
            attack : float
                time in seconds to ramp from silence to full amplitude
            decay : float
                time in seconds to fall from full amplitude to the sustain level
            sustain : float
                sustain level as a fraction of amplitude (0.0 - 1.0)
            release : float
                time in seconds to fade from the sustain level to silence
        """
        audio = self._chord(root, chord_type, octave, duration, amplitude)
        self._audio = audio * self._adsr_envelope(len(audio), attack, decay, sustain, release)

    def _arpeggio(
        self,
        root: Note | str,
        chord_type: str,
        octave: int,
        note_duration: float,
        amplitude: float,
        mode: ArpeggioMode | str,
        envelope: np.ndarray | None = None,
    ) -> np.ndarray:
        if chord_type not in CHORD_TEMPLATES:
            raise ValueError(f"{chord_type} is not a valid chord")
        # passing an unknown string to the enum raises a ValueError for us
        mode = ArpeggioMode(mode)
        if isinstance(root, str):
            root = Note[root.strip().upper()]
        # the templates are sets so sort them to get the notes in pitch order
        offsets = sorted(CHORD_TEMPLATES[chord_type])
        if mode == ArpeggioMode.DESCEND:
            offsets.reverse()
        elif mode == ArpeggioMode.ASCEND_DESCEND:
            # go back down without repeating the top note e.g. C E G E C
            offsets += offsets[-2::-1]
        notes = []
        for offset in offsets:
            tone = self._sine(self._note_to_frequency(root + offset, octave), note_duration, amplitude)
            notes.append(tone if envelope is None else tone * envelope)
        return np.concatenate(notes)

    def arpeggio(
        self,
        root: Note | str,
        chord_type: str,
        octave: int,
        note_duration: float,
        amplitude: float,
        mode: ArpeggioMode | str = ArpeggioMode.ASCEND,
    ) -> None:
        """
        Generate an arpeggio, playing the notes of a chord one after another. The
        total length is the number of notes played multiplied by note_duration.

        Parameters
        ----------
            root : Note | str
                the root note of the chord, either a Note or its name e.g. "C_SHARP"
            chord_type : str
                one of the keys in CHORD_TEMPLATES e.g. "major"
            octave : int
                the octave of the root note, A4 is 440 Hz
            note_duration : float
                length of each individual note in seconds
            amplitude : float
                amplitude of each note
            mode : ArpeggioMode | str
                ascend, descend or ascend_descend (up then back down without
                repeating the top note)
        """
        self._audio = self._arpeggio(root, chord_type, octave, note_duration, amplitude, mode)

    def adsr_arpeggio(
        self,
        root: Note | str,
        chord_type: str,
        octave: int,
        note_duration: float,
        amplitude: float,
        mode: ArpeggioMode | str,
        attack: float,
        decay: float,
        sustain: float,
        release: float,
    ) -> None:
        """
        Generate an arpeggio where each note has its own ADSR envelope, the envelope is
        re-triggered for every note in the same way as a synth arpeggiator.

        Parameters
        ----------
            root : Note | str
                the root note of the chord, either a Note or its name e.g. "C_SHARP"
            chord_type : str
                one of the keys in CHORD_TEMPLATES e.g. "major"
            octave : int
                the octave of the root note, A4 is 440 Hz
            note_duration : float
                length of each individual note in seconds, the envelope must fit inside this
            amplitude : float
                peak amplitude of each note
            mode : ArpeggioMode | str
                ascend, descend or ascend_descend
            attack : float
                time in seconds to ramp from silence to full amplitude
            decay : float
                time in seconds to fall from full amplitude to the sustain level
            sustain : float
                sustain level as a fraction of amplitude (0.0 - 1.0)
            release : float
                time in seconds to fade from the sustain level to silence
        """
        # every note is the same length so we only need to build the envelope once
        envelope = self._adsr_envelope(int(self._sample_rate * note_duration), attack, decay, sustain, release)
        self._audio = self._arpeggio(root, chord_type, octave, note_duration, amplitude, mode, envelope)

    def write(self, filename: str):
        sf.write(filename, self._audio, self._sample_rate)
