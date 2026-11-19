#!/usr/bin/env -S uv run --script

import numpy as np
import soundfile as sf

sample_rate = 44100
rng = np.random.default_rng(42)

audio = np.zeros(sample_rate, dtype=np.float32)  # One second
burst_length = int(0.1 * sample_rate)

burst = rng.standard_normal(burst_length)
burst *= np.hanning(burst_length)
burst *= 0.5 / np.max(np.abs(burst))

start = int(0.2 * sample_rate)
audio[start : start + burst_length] = burst

sf.write("calibration.wav", audio, sample_rate, subtype="FLOAT")
