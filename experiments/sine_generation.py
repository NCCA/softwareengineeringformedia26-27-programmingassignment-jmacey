import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Basic Tone Generation

    In this notebook I will investigate how I can make some basic tones to generate a proof of concept of my distortion effect.

    I will use the western 12 tone equal temperament system (12 TET) which is standard for most musical instruments such as piano.


    Frequency and octave relationships
    A musical note is associated with a fundamental frequency, measured in hertz (Hz).

    An octave corresponds to a doubling of frequency:
    \[
    f_{\text{octave}}=2f
    \]

    For example:


    |Note	|Frequency|
    |--------|--------|
    |A2	|110.00 Hz |
    |A3	|220.00 Hz |
    |A4	|440.00 Hz |
    |A5	|880.00 Hz |
    |A6	|1760.00 Hz |

    The ratio between adjacent notes in 12 TET is:
    \[
    r=2^{1/12}\approx1.059463094
    \]

    Moving up \(n\) semitones gives:
    \[
    \boxed{f_n=f_0\,2^{n/12}}
    \]

    Here \(f_0\) is the root frequency and \(n\) is the interval in semitones.

    For a root of C4 (approximately 261.626 Hz), we can generate any other pitch using this equation.

    For the following example we will use the standard A 440Hz
    """)
    return


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import matplotlib.pyplot as plt
    import soundfile as sf

    return mo, np, plt, sf


@app.cell
def _():
    # basic sample rate for good quality audio.
    sample_rate = 44100
    frequency = 440  # A 440 hz
    return frequency, sample_rate


@app.cell
def _(mo):
    amplitude = mo.ui.slider(
        0.0, 1.0, step=0.01, value=0.5, label="Amplitude", show_value=True
    )
    amplitude
    return (amplitude,)


@app.cell
def _(amplitude, frequency, np, sample_rate):
    duration = 0.01  # 10ms of sound (could add a slider for this later)
    t = np.arange(0, duration, 1 / sample_rate)
    signal = amplitude.value * np.sin(2 * np.pi * frequency * t)
    return signal, t


@app.cell
def _(frequency, plt, signal, t):
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(t * 1000, signal)
    ax.set_xlabel("Time (ms)")
    ax.set_ylabel("Amplitude")
    ax.set_title(f"{frequency:.0f} Hz sine wave")
    ax.set_ylim(-1.1, 1.1)
    ax.grid(True)
    fig
    return


@app.cell
def _(mo):
    # we need to declare this first so we can use the value in the generation, if we don't display it is not visible.
    play_duration = mo.ui.slider(
        1, 5, step=1, value=2, label="Sound Duration", show_value=True
    )
    return (play_duration,)


@app.cell
def _(amplitude, frequency, mo, np, play_duration, sample_rate):
    _t = np.arange(0, play_duration.value, 1 / sample_rate)
    _signal = amplitude.value * np.sin(2 * np.pi * frequency * _t)

    _stack = mo.vstack(
        [
            play_duration,
            mo.audio(_signal, rate=sample_rate, normalize=False),
        ]
    )

    _stack
    return


@app.cell
def _(sample_rate, sf, signal):
    # now write this to disk as a proof of concept.
    sf.write("A440Sine.wav", signal, sample_rate, subtype="FLOAT")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
