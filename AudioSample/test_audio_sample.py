import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # AudioSample Class

    This note book show the working of the audio sample class and allows the user to experiment with it and hear the resultant audio
    """)
    return


@app.cell
def _():
    import marimo as mo
    import numpy as np
    from audiosample import AudioSample, Note, CHORD_TEMPLATES
    import matplotlib.pyplot as plt

    return AudioSample, CHORD_TEMPLATES, Note, mo, np, plt


@app.cell
def _(AudioSample, mo, plt):
    sample = AudioSample()
    sample.sine_tone("A", 4, 0.2, 1.0)

    mo.audio(sample.audio, sample.sample_rate, normalize=False)

    _fig, _ax = plt.subplots(figsize=(8, 4))
    _ax.plot(sample.audio[:100])  # only show a few samples
    _ax.set_xlabel("Time (ms)")
    _ax.set_ylabel("Amplitude")
    _ax.set_title(f"A4 Hz sine wave")
    _ax.set_ylim(-1.1, 1.1)
    _ax.grid(True)
    _fig
    return (sample,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    This is the simplest approach we can just generate a simple sine and plot it or play it back with mo.audio. In the next example we will create a full user interface to allow us to control all the parameters.

    ## User interface

    One of the limitiations of the marimo user interface setup is we need to define things before we use them (this is due to the way the graph is evaluated). We must first define our components, then generate the audio from it then display the controls to use the values.
    """)
    return


@app.cell
def _(Note, mo):
    # pre define some of our controls so we can use them later
    play_duration = mo.ui.slider(
        0.1, 5.0, step=0.1, value=0.5, label="Duration", show_value=True
    )

    amplitude = mo.ui.slider(
        0.0, 1.0, step=0.01, value=0.5, label="Amplitude", show_value=True
    )
    octave = mo.ui.slider(
        1, 8, step=1, value=4, label="octave", show_value=True
    )
    note_picker = mo.ui.dropdown(
        options={note.name.replace("_SHARP", "♯"): note for note in Note},
        value="C",
        label="Note",
    )
    # how many samples to draw, a full tone is far too many to see the wave
    num_samples = mo.ui.slider(
        10,
        2000,
        step=10,
        value=100,
        label="Graph samples shown",
        show_value=True,
    )
    return amplitude, note_picker, num_samples, octave, play_duration


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Next we will generate our sine tone and generate a graph that can be embedded into our UI
    """)
    return


@app.cell
def _(amplitude, note_picker, num_samples, octave, play_duration, plt, sample):
    sample.sine_tone(
        note=note_picker.value,
        octave=octave.value,
        duration=play_duration.value,
        amplitude=amplitude.value,
    )

    # only plot the first few samples so the individual points are visible
    _samples = sample.audio[: num_samples.value]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(_samples, marker=".", markersize=4)
    ax.set_xlabel("Sample")
    ax.set_ylabel("Amplitude")
    ax.set_title(
        f"{note_picker.value.name.replace('_SHARP', '♯')} {octave.value} (first {len(_samples)} samples)"
    )
    ax.set_ylim(-1.1, 1.1)
    ax.grid(True)
    return (fig,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Finally we can create our ui with the pre-generated data above.
    """)
    return


@app.cell
def _(
    amplitude,
    fig,
    mo,
    note_picker,
    num_samples,
    octave,
    play_duration,
    sample,
):
    mo.vstack(
        [
            mo.hstack([note_picker, octave], justify="start"),
            mo.hstack([play_duration, amplitude], justify="start"),
            num_samples,
            mo.audio(sample.audio, rate=sample.sample_rate, normalize=False),
            fig,
        ]
    )
    return


@app.cell
def _(mo, plt, sample):
    sample.chord("C", "minor", 4, 1.5, 1.0)

    _fig, _ax = plt.subplots(figsize=(8, 4))
    _ax.plot(sample.audio)  # only show a few samples
    _ax.set_xlabel("Time (ms)")
    _ax.set_ylabel("Amplitude")
    _ax.set_title(f"A4 Hz sine wave")
    # _ax.set_ylim(-1.1, 1.1)
    _ax.grid(True)
    _fig

    mo.audio(sample.audio, sample.sample_rate, normalize=False)
    return


@app.cell
def _(CHORD_TEMPLATES, Note, mo):
    # pre define some of our controls so we can use them later
    cplay_duration = mo.ui.slider(
        0.1, 5.0, step=0.1, value=0.5, label="Duration", show_value=True
    )

    camplitude = mo.ui.slider(
        0.0, 1.0, step=0.01, value=0.5, label="Amplitude", show_value=True
    )
    coctave = mo.ui.slider(
        1, 8, step=1, value=4, label="octave", show_value=True
    )
    cnote_picker = mo.ui.dropdown(
        options={note.name.replace("_SHARP", "♯"): note for note in Note},
        value="C",
        label="Note",
    )
    # how many samples to draw, a full tone is far too many to see the wave
    cnum_samples = mo.ui.slider(
        10,
        2000,
        step=10,
        value=100,
        label="Graph samples shown",
        show_value=True,
    )

    cchord_picker = mo.ui.dropdown(
        options=CHORD_TEMPLATES,
        value="major",
        label="Note",
    )
    return (
        camplitude,
        cchord_picker,
        cnote_picker,
        cnum_samples,
        coctave,
        cplay_duration,
    )


@app.cell
def _(
    camplitude,
    cchord_picker,
    cnote_picker,
    cnum_samples,
    coctave,
    cplay_duration,
    plt,
    sample,
):
    sample.chord(
        root=cnote_picker.value,
        chord_type=cchord_picker.selected_key,
        octave=coctave.value,
        duration=cplay_duration.value,
        amplitude=camplitude.value,
    )

    _samples = sample.audio[: cnum_samples.value]
    fig_chord, ax_chord = plt.subplots(figsize=(8, 4))
    ax_chord.plot(_samples, marker=".", markersize=2)
    ax_chord.grid(True)
    return (fig_chord,)


@app.cell
def _(
    camplitude,
    cchord_picker,
    cnote_picker,
    cnum_samples,
    coctave,
    cplay_duration,
    fig_chord,
    mo,
    sample,
):
    mo.vstack(
        [
            mo.hstack([cnote_picker, cchord_picker, coctave], justify="start"),
            mo.hstack([cplay_duration, camplitude], justify="start"),
            cnum_samples,
            mo.audio(sample.audio, sample.sample_rate, normalize=True),
            fig_chord,
        ]
    )
    return


@app.cell
def _(sample):
    sample.write("c_major_4_0.5_0.5.wav")
    return


@app.cell
def _(Note, np, sample):
    _duration = 0.1
    for _octave in range(1, 8):
        for _amplitude in np.arange(0.1, 1.0, 0.1):
            for _n in Note:
                sample.sine_tone(_n.name, _octave, _duration, _amplitude)
                sample.write(f"{_n.name}_{_octave}_{_amplitude:0.2f}.wav")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
