"""Measure the round trip delay from playback, through the mixer and pedal, back to the recording.

A log sine sweep is used rather than a steady sine, as a steady sine correlates equally well
one period either side of the true delay. The sweep gives a single sharp peak, even after it
has been clipped by an analogue drive pedal.
"""

import math

import numpy as np


LEAD_SECONDS = 0.05
SWEEP_SECONDS = 0.25
FADE_SECONDS = 0.01
MAX_DELAY_SECONDS = 1.0
SWEEP_LEVEL = 0.5
START_FREQUENCY = 100.0
REPEATS = 3
# Normalised correlation below this means the sweep did not come back (cable, channel or gain).
MIN_CORRELATION = 0.3
# Repeated measurements must agree to within this, otherwise the loop is not stable.
TOLERANCE_SECONDS = 0.0005


class CalibrationError(RuntimeError):
    pass


def make_sweep(rate: int) -> np.ndarray:
    """
    Build a mono log sine sweep with short fades so it starts and stops without a click.

    Parameters
    ----------
        rate : int
            sample rate in Hz

    Returns
    -------
        np.ndarray
            float32 samples of shape (frames,)
    """
    frames = int(SWEEP_SECONDS * rate)
    end_frequency = min(8000.0, 0.4 * rate)
    t = np.arange(frames) / rate
    k = math.log(end_frequency / START_FREQUENCY)
    phase = 2 * math.pi * START_FREQUENCY * SWEEP_SECONDS / k * (np.exp(t * k / SWEEP_SECONDS) - 1)
    sweep = SWEEP_LEVEL * np.sin(phase)
    fade = int(FADE_SECONDS * rate)
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, fade))
    sweep[:fade] *= ramp
    sweep[-fade:] *= ramp[::-1]
    return sweep.astype(np.float32)


def make_calibration_signal(rate: int) -> np.ndarray:
    """
    Pad the sweep with a little silence before it, and enough after it to catch the longest delay we search for.

    Parameters
    ----------
        rate : int
            sample rate in Hz

    Returns
    -------
        np.ndarray
            float32 samples of shape (frames,)
    """
    lead = int(LEAD_SECONDS * rate)
    tail = int(MAX_DELAY_SECONDS * rate)
    return np.concatenate([np.zeros(lead, np.float32), make_sweep(rate), np.zeros(tail, np.float32)])


def measure_delay(played: np.ndarray, recorded: np.ndarray, max_delay: int) -> int:
    """
    Find how many frames the recording lags the playback using FFT cross correlation.

    Parameters
    ----------
        played : np.ndarray
            the mono signal sent to the output
        recorded : np.ndarray
            the mono signal captured on the return channel, index aligned with played
        max_delay : int
            the largest delay in frames to search

    Returns
    -------
        int
            the delay in frames

    Raises
    ------
        CalibrationError
            if the recording does not contain a clear copy of the played signal
    """
    played = np.asarray(played, dtype=np.float64).ravel()
    recorded = np.asarray(recorded, dtype=np.float64).ravel()
    size = 1 << (len(played) + len(recorded)).bit_length()
    correlation = np.fft.irfft(np.fft.rfft(recorded, size) * np.conj(np.fft.rfft(played, size)), size)
    # Use the magnitude as some mixers and pedals invert the polarity.
    search = np.abs(correlation[:max_delay + 1])
    delay = int(np.argmax(search))
    window = recorded[delay:delay + len(played)]
    energy = np.linalg.norm(played) * np.linalg.norm(window)
    score = search[delay] / energy if energy > 0 else 0.0
    if score < MIN_CORRELATION:
        raise CalibrationError(
            "Calibration sweep was not found in the recording. Check the cable, return channel and gain "
            f"(correlation {score:.2f})")
    return delay


def combine_measurements(delays: list[int], rate: int) -> int:
    """
    Check repeated measurements agree and return their median.

    Parameters
    ----------
        delays : list[int]
            each measured delay in frames
        rate : int
            sample rate in Hz, used to convert the tolerance to frames

    Returns
    -------
        int
            the median delay in frames
    """
    tolerance = max(1, round(TOLERANCE_SECONDS * rate))
    if max(delays) - min(delays) > tolerance:
        raise CalibrationError(f"Latency measurements disagree: {delays} frames at {rate} Hz")
    return int(np.median(delays))
