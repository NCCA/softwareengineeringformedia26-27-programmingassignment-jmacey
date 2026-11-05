import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    from audiosample import AudioSample

    return AudioSample, mo


@app.cell
def _(AudioSample, mo):
    sample = AudioSample()
    sample.sine_tone("F",5,1,1.0)

    mo.audio(sample.audio,sample.sample_rate,normalize=False)
    return


if __name__ == "__main__":
    app.run()
