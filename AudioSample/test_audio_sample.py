# /// script
# dependencies = [
#     "marimo",
#     "audiosample @ git+https://github.com/NCCA/softwareengineeringformedia26-27-programmingassignment-jmacey.git@v0.1.0#subdirectory=AudioSample",
#     "av",
# ]
# ///

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
    import matplotlib.pyplot as plt
    import numpy as np
    from audiosample import CHORD_TEMPLATES, ArpeggioMode, AudioSample, Note

    return ArpeggioMode, AudioSample, CHORD_TEMPLATES, Note, mo, np, plt


@app.cell
def _(AudioSample, mo, plt):
    sample = AudioSample()
    sample.sine_tone("A", 4, 0.2, 1.0)

    mo.audio(sample.audio, sample.sample_rate, normalize=False)

    _fig, _ax = plt.subplots(figsize=(8, 4))
    _ax.plot(sample.audio[:100])  # only show a few samples
    _ax.set_xlabel("Time (ms)")
    _ax.set_ylabel("Amplitude")
    _ax.set_title("A4 Hz sine wave")
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
    play_duration = mo.ui.slider(0.1, 5.0, step=0.1, value=0.5, label="Duration", show_value=True)

    amplitude = mo.ui.slider(0.0, 1.0, step=0.01, value=0.5, label="Amplitude", show_value=True)
    octave = mo.ui.slider(1, 8, step=1, value=4, label="octave", show_value=True)
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
    ax.set_title(f"{note_picker.value.name.replace('_SHARP', '♯')} {octave.value} (first {len(_samples)} samples)")
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
    mo.vstack([
        mo.hstack([note_picker, octave], justify="start"),
        mo.hstack([play_duration, amplitude], justify="start"),
        num_samples,
        mo.audio(sample.audio, rate=sample.sample_rate, normalize=False),
        fig,
    ])
    return


@app.cell
def _(mo, plt, sample):
    sample.chord("C", "minor", 4, 1.5, 1.0)

    _fig, _ax = plt.subplots(figsize=(8, 4))
    _ax.plot(sample.audio)  # only show a few samples
    _ax.set_xlabel("Time (ms)")
    _ax.set_ylabel("Amplitude")
    _ax.set_title("A4 Hz sine wave")
    # _ax.set_ylim(-1.1, 1.1)
    _ax.grid(True)
    _fig

    mo.audio(sample.audio, sample.sample_rate, normalize=False)
    return


@app.cell
def _(CHORD_TEMPLATES, Note, mo):
    # pre define some of our controls so we can use them later
    cplay_duration = mo.ui.slider(0.1, 5.0, step=0.1, value=0.5, label="Duration", show_value=True)

    camplitude = mo.ui.slider(0.0, 1.0, step=0.01, value=0.5, label="Amplitude", show_value=True)
    coctave = mo.ui.slider(1, 8, step=1, value=4, label="octave", show_value=True)
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
    mo.vstack([
        mo.hstack([cnote_picker, cchord_picker, coctave], justify="start"),
        mo.hstack([cplay_duration, camplitude], justify="start"),
        cnum_samples,
        mo.audio(sample.audio, sample.sample_rate, normalize=True),
        fig_chord,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## ADSR envelope

    A plain sine wave starts and stops instantly, which sounds harsh (you can often hear a click at each end). Real instruments have a shape to their volume over time and the classic way to model this is an [ADSR envelope](https://en.wikipedia.org/wiki/Envelope_(music)).

    - **Attack** time to ramp from silence up to the full amplitude
    - **Decay** time to fall from the full amplitude to the sustain level
    - **Sustain** the level (as a fraction of the amplitude) held whilst the note is playing
    - **Release** time to fade from the sustain level back to silence

    The `adsr_tone` method generates a sine wave and multiplies it by this envelope. The duration is the total length of the note, so attack + decay + release must fit inside it, whatever time is left over is spent at the sustain level.
    """)
    return


@app.cell
def _(Note, mo):
    # controls for the ADSR demo, prefixed with a so they don't clash with the ones above
    anote_picker = mo.ui.dropdown(
        options={note.name.replace("_SHARP", "♯"): note for note in Note},
        value="A",
        label="Note",
    )
    aoctave = mo.ui.slider(1, 8, step=1, value=4, label="octave", show_value=True)
    aplay_duration = mo.ui.slider(0.5, 5.0, step=0.1, value=2.0, label="Duration", show_value=True)
    aamplitude = mo.ui.slider(0.0, 1.0, step=0.01, value=0.8, label="Amplitude", show_value=True)
    attack = mo.ui.slider(0.0, 2.0, step=0.01, value=0.1, label="Attack (s)", show_value=True)
    decay = mo.ui.slider(0.0, 2.0, step=0.01, value=0.2, label="Decay (s)", show_value=True)
    sustain = mo.ui.slider(0.0, 1.0, step=0.01, value=0.6, label="Sustain level", show_value=True)
    release = mo.ui.slider(0.0, 2.0, step=0.01, value=0.5, label="Release (s)", show_value=True)
    return (
        aamplitude,
        anote_picker,
        aoctave,
        aplay_duration,
        attack,
        decay,
        release,
        sustain,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Next we generate the tone and plot the whole note so we can see the envelope shape. The dashed lines show where each stage of the envelope starts. If the envelope times are longer than the note `adsr_tone` raises a `ValueError`, so we catch it and show a message instead.
    """)
    return


@app.cell
def _(np, plt):
    def plot_adsr(audio, sample_rate, attack, decay, release, title):
        """plot the whole sound against time with a dashed line at the start of each ADSR stage"""
        time = np.arange(len(audio)) / sample_rate
        duration = len(audio) / sample_rate
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(time, audio, linewidth=0.5)
        stages = {
            "decay": attack,
            "sustain": attack + decay,
            "release": duration - release,
        }
        for name, start in stages.items():
            ax.axvline(start, color="red", linestyle="--", linewidth=1)
            ax.text(start, 1.05, name, color="red", ha="left")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Amplitude")
        ax.set_title(title)
        ax.set_ylim(-1.1, 1.2)
        ax.grid(True)
        return fig

    return (plot_adsr,)


@app.cell
def _(
    AudioSample,
    aamplitude,
    anote_picker,
    aoctave,
    aplay_duration,
    attack,
    decay,
    mo,
    plot_adsr,
    release,
    sustain,
):
    adsr_sample = AudioSample()
    try:
        adsr_sample.adsr_tone(
            note=anote_picker.value,
            octave=aoctave.value,
            duration=aplay_duration.value,
            amplitude=aamplitude.value,
            attack=attack.value,
            decay=decay.value,
            sustain=sustain.value,
            release=release.value,
        )
    except ValueError as _error:
        adsr_output = mo.callout(
            mo.md(f"**{_error}**, try a longer duration or shorter envelope times."),
            kind="warn",
        )
    else:
        adsr_output = mo.vstack([
            mo.audio(
                adsr_sample.audio,
                rate=adsr_sample.sample_rate,
                normalize=False,
            ),
            plot_adsr(
                adsr_sample.audio,
                adsr_sample.sample_rate,
                attack.value,
                decay.value,
                release.value,
                f"{anote_picker.selected_key} {aoctave.value} with ADSR envelope",
            ),
        ])
    return (adsr_output,)


@app.cell
def _(
    aamplitude,
    adsr_output,
    anote_picker,
    aoctave,
    aplay_duration,
    attack,
    decay,
    mo,
    release,
    sustain,
):
    mo.vstack([
        mo.hstack([anote_picker, aoctave], justify="start"),
        mo.hstack([aplay_duration, aamplitude], justify="start"),
        mo.hstack([attack, decay], justify="start"),
        mo.hstack([sustain, release], justify="start"),
        adsr_output,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### ADSR chords

    The same envelope can be applied to a chord using `adsr_chord`. The notes of the chord are mixed together first and then the envelope is applied to the result, so all the notes start and stop together (a bit like pressing all the keys of a piano at the same time).
    """)
    return


@app.cell
def _(CHORD_TEMPLATES, Note, mo):
    # controls for the ADSR chord demo, prefixed with ac
    acnote_picker = mo.ui.dropdown(
        options={note.name.replace("_SHARP", "♯"): note for note in Note},
        value="C",
        label="Root",
    )
    acchord_picker = mo.ui.dropdown(options=CHORD_TEMPLATES, value="major", label="Chord")
    acoctave = mo.ui.slider(1, 8, step=1, value=4, label="octave", show_value=True)
    acplay_duration = mo.ui.slider(0.5, 5.0, step=0.1, value=2.0, label="Duration", show_value=True)
    acamplitude = mo.ui.slider(0.0, 1.0, step=0.01, value=0.8, label="Amplitude", show_value=True)
    acattack = mo.ui.slider(0.0, 2.0, step=0.01, value=0.05, label="Attack (s)", show_value=True)
    acdecay = mo.ui.slider(0.0, 2.0, step=0.01, value=0.3, label="Decay (s)", show_value=True)
    acsustain = mo.ui.slider(0.0, 1.0, step=0.01, value=0.5, label="Sustain level", show_value=True)
    acrelease = mo.ui.slider(0.0, 2.0, step=0.01, value=0.8, label="Release (s)", show_value=True)
    return (
        acamplitude,
        acattack,
        acchord_picker,
        acdecay,
        acnote_picker,
        acoctave,
        acplay_duration,
        acrelease,
        acsustain,
    )


@app.cell
def _(
    AudioSample,
    acamplitude,
    acattack,
    acchord_picker,
    acdecay,
    acnote_picker,
    acoctave,
    acplay_duration,
    acrelease,
    acsustain,
    mo,
    plot_adsr,
):
    adsr_chord_sample = AudioSample()
    try:
        adsr_chord_sample.adsr_chord(
            root=acnote_picker.value,
            chord_type=acchord_picker.selected_key,
            octave=acoctave.value,
            duration=acplay_duration.value,
            amplitude=acamplitude.value,
            attack=acattack.value,
            decay=acdecay.value,
            sustain=acsustain.value,
            release=acrelease.value,
        )
    except ValueError as _error:
        adsr_chord_output = mo.callout(
            mo.md(f"**{_error}**, try a longer duration or shorter envelope times."),
            kind="warn",
        )
    else:
        adsr_chord_output = mo.vstack([
            mo.audio(
                adsr_chord_sample.audio,
                rate=adsr_chord_sample.sample_rate,
                normalize=False,
            ),
            plot_adsr(
                adsr_chord_sample.audio,
                adsr_chord_sample.sample_rate,
                acattack.value,
                acdecay.value,
                acrelease.value,
                f"{acnote_picker.selected_key} {acchord_picker.selected_key} {acoctave.value} with ADSR envelope",
            ),
        ])
    return (adsr_chord_output,)


@app.cell
def _(
    acamplitude,
    acattack,
    acchord_picker,
    acdecay,
    acnote_picker,
    acoctave,
    acplay_duration,
    acrelease,
    acsustain,
    adsr_chord_output,
    mo,
):
    mo.vstack([
        mo.hstack([acnote_picker, acchord_picker, acoctave], justify="start"),
        mo.hstack([acplay_duration, acamplitude], justify="start"),
        mo.hstack([acattack, acdecay], justify="start"),
        mo.hstack([acsustain, acrelease], justify="start"),
        adsr_chord_output,
    ])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Arpeggios

    An [arpeggio](https://en.wikipedia.org/wiki/Arpeggio) plays the notes of a chord one after another rather than all at once. The `arpeggio` method takes the length of each individual note, so the total length is the number of notes played multiplied by the note duration. There are three modes in the `ArpeggioMode` enum.

    - **ascend** play the notes from lowest to highest (C E G for C major)
    - **descend** play the notes from highest to lowest (G E C)
    - **ascend_descend** go up and back down again without repeating the top note (C E G E C)

    `adsr_arpeggio` does the same but applies an ADSR envelope to each note, the envelope is re-triggered for every note (in the same way as a synth arpeggiator), so attack + decay + release has to fit inside a single note. Use the switch below to turn the envelope on and off and hear the difference.
    """)
    return


@app.cell
def _(ArpeggioMode, CHORD_TEMPLATES, Note, mo):
    # controls for the arpeggio demo, prefixed with ar
    arnote_picker = mo.ui.dropdown(
        options={note.name.replace("_SHARP", "♯"): note for note in Note},
        value="C",
        label="Root",
    )
    archord_picker = mo.ui.dropdown(options=CHORD_TEMPLATES, value="major", label="Chord")
    armode = mo.ui.dropdown(
        options={mode.value: mode for mode in ArpeggioMode},
        value="ascend_descend",
        label="Mode",
    )
    aroctave = mo.ui.slider(1, 8, step=1, value=4, label="octave", show_value=True)
    arnote_duration = mo.ui.slider(
        0.05,
        1.0,
        step=0.05,
        value=0.25,
        label="Note duration",
        show_value=True,
    )
    aramplitude = mo.ui.slider(0.0, 1.0, step=0.01, value=0.8, label="Amplitude", show_value=True)
    aruse_adsr = mo.ui.switch(value=True, label="ADSR envelope")
    arattack = mo.ui.slider(0.0, 0.5, step=0.005, value=0.01, label="Attack (s)", show_value=True)
    ardecay = mo.ui.slider(0.0, 0.5, step=0.005, value=0.05, label="Decay (s)", show_value=True)
    arsustain = mo.ui.slider(0.0, 1.0, step=0.01, value=0.6, label="Sustain level", show_value=True)
    arrelease = mo.ui.slider(0.0, 0.5, step=0.005, value=0.1, label="Release (s)", show_value=True)
    return (
        aramplitude,
        arattack,
        archord_picker,
        ardecay,
        armode,
        arnote_duration,
        arnote_picker,
        aroctave,
        arrelease,
        arsustain,
        aruse_adsr,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Next we generate the arpeggio, calling `adsr_arpeggio` or `arpeggio` depending on the switch. The plot marks the start of each note rather than the envelope stages as the envelope repeats for every note.
    """)
    return


@app.cell
def _(
    AudioSample,
    aramplitude,
    arattack,
    archord_picker,
    ardecay,
    armode,
    arnote_duration,
    arnote_picker,
    aroctave,
    arrelease,
    arsustain,
    aruse_adsr,
    mo,
    np,
    plt,
):
    arpeggio_sample = AudioSample()
    try:
        if aruse_adsr.value:
            arpeggio_sample.adsr_arpeggio(
                root=arnote_picker.value,
                chord_type=archord_picker.selected_key,
                octave=aroctave.value,
                note_duration=arnote_duration.value,
                amplitude=aramplitude.value,
                mode=armode.value,
                attack=arattack.value,
                decay=ardecay.value,
                sustain=arsustain.value,
                release=arrelease.value,
            )
        else:
            arpeggio_sample.arpeggio(
                root=arnote_picker.value,
                chord_type=archord_picker.selected_key,
                octave=aroctave.value,
                note_duration=arnote_duration.value,
                amplitude=aramplitude.value,
                mode=armode.value,
            )
    except ValueError as _error:
        arpeggio_output = mo.callout(
            mo.md(f"**{_error}**, try a longer note duration or shorter envelope times."),
            kind="warn",
        )
    else:
        _time = np.arange(len(arpeggio_sample.audio)) / arpeggio_sample.sample_rate
        _fig, _ax = plt.subplots(figsize=(10, 4))
        _ax.plot(_time, arpeggio_sample.audio, linewidth=0.5)
        # each note is the same length so we can work out how many were played from the total
        _notes = round(len(_time) / (arpeggio_sample.sample_rate * arnote_duration.value))
        for _note in range(1, _notes):
            _ax.axvline(
                _note * arnote_duration.value,
                color="red",
                linestyle="--",
                linewidth=1,
            )
        _ax.set_xlabel("Time (s)")
        _ax.set_ylabel("Amplitude")
        _ax.set_title(
            f"{arnote_picker.selected_key} {archord_picker.selected_key} {aroctave.value} "
            f"{armode.selected_key} arpeggio, {_notes} notes {_time[-1]:0.2f}s"
        )
        _ax.set_ylim(-1.1, 1.1)
        _ax.grid(True)
        arpeggio_output = mo.vstack([
            mo.audio(
                arpeggio_sample.audio,
                rate=arpeggio_sample.sample_rate,
                normalize=False,
            ),
            _fig,
        ])
    return (arpeggio_output,)


@app.cell
def _(
    aramplitude,
    arattack,
    archord_picker,
    ardecay,
    armode,
    arnote_duration,
    arnote_picker,
    aroctave,
    arpeggio_output,
    arrelease,
    arsustain,
    aruse_adsr,
    mo,
):
    mo.vstack([
        mo.hstack(
            [arnote_picker, archord_picker, armode, aroctave],
            justify="start",
        ),
        mo.hstack([arnote_duration, aramplitude], justify="start"),
        aruse_adsr,
        mo.hstack([arattack, ardecay], justify="start"),
        mo.hstack([arsustain, arrelease], justify="start"),
        arpeggio_output,
    ])
    return


@app.cell
def _(sample):
    sample.write("c_major_4_0.5_0.5.wav")
    return


@app.cell
def _(Note, np, sample):
    _duration = 0.2
    # adsr_tone(
    #         note=anote_picker.value,
    #         octave=aoctave.value,
    #         duration=aplay_duration.value,
    #         amplitude=aamplitude.value,
    #         attack=attack.value,
    #         decay=decay.value,
    #         sustain=sustain.value,
    #         release=release.value,
    #     )

    for _octave in range(1, 8):
        for _amplitude in np.arange(0.1, 1.0, 0.1):
            for _n in Note:
                # sample.sine_tone(_n.name, _octave, _duration, _amplitude)
                sample.adsr_tone(
                    _n.name,
                    _octave,
                    _duration,
                    _amplitude,
                    attack=0.01,
                    decay=0.01,
                    sustain=0.18,
                    release=0.01,
                )
                sample.write(
                    f"/Users/jmacey/teaching/SEM/SEMAssignment26-27Jon/input_data/{_n.name}_{_octave}_{_amplitude:0.2f}.wav"
                )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
