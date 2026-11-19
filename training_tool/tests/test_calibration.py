import numpy as np
import pytest

from .. import calibration
from ..calibration import CalibrationError, combine_measurements, make_calibration_signal, measure_delay


def loop(signal: np.ndarray, delay: int, gain: float = 1.0) -> np.ndarray:
    """Simulate the mixer and pedal by delaying the signal within a buffer of the same length."""
    recorded = np.zeros_like(signal)
    recorded[delay:] = gain * signal[:len(signal) - delay]
    return recorded


@pytest.mark.parametrize("rate", [8000, 44100, 48000, 96000])
def test_signal_has_room_for_the_largest_delay_and_stays_in_range(rate: int) -> None:
    signal = make_calibration_signal(rate)
    assert signal.dtype == np.float32
    assert signal.ndim == 1
    assert np.max(np.abs(signal)) <= calibration.SWEEP_LEVEL
    assert signal[0] == 0 and signal[-1] == 0
    silent_tail = len(signal) - np.flatnonzero(signal)[-1] - 1
    assert silent_tail >= int(calibration.MAX_DELAY_SECONDS * rate)


@pytest.mark.parametrize("delay", [0, 1, 127, 2205, 20000])
def test_measure_delay_finds_exact_delay(delay: int) -> None:
    signal = make_calibration_signal(44100)
    assert measure_delay(signal, loop(signal, delay, 0.7), 44100) == delay


def test_measure_delay_handles_inverted_and_clipped_return() -> None:
    signal = make_calibration_signal(48000)
    # A heavily driven analogue pedal clips the sweep and may invert it.
    driven = -np.tanh(8 * loop(signal, 913))
    rng = np.random.default_rng(1)
    driven += 0.02 * rng.standard_normal(len(signal))
    assert measure_delay(signal, driven, 48000) == 913


@pytest.mark.parametrize("returned", ["silence", "noise"])
def test_measure_delay_rejects_missing_sweep(returned: str) -> None:
    signal = make_calibration_signal(8000)
    rng = np.random.default_rng(2)
    recorded = np.zeros_like(signal) if returned == "silence" else 0.3 * rng.standard_normal(len(signal))
    with pytest.raises(CalibrationError, match="not found"):
        measure_delay(signal, recorded, 8000)


def test_combine_measurements_returns_median_of_agreeing_values() -> None:
    assert combine_measurements([500, 501, 500], 48000) == 500


def test_combine_measurements_rejects_unstable_loop() -> None:
    with pytest.raises(CalibrationError, match="disagree"):
        combine_measurements([500, 900, 500], 48000)
