# Pedal training samples

I use this tool to play source audio through a physical pedal and record its output at different dial settings.

From the repository root:

```bash
uv run training_tool/app.py
```

Choose the pedal return device and channel, then the playback output. Playback uses output channels starting at 1, with one channel for mono files and two for stereo files. Stereo inputs are averaged to mono when the playback device has one channel. We need to route this output through the pedal and back into the selected return channel.

Label the dials and choose the number of positions for each. Three steps means 0%, 50% and 100%. The tool visits every combination, so three dials with three steps gives 27 batches. Select the source samples and press **Prepare run...** to choose a destination folder.

Set the physical pedal to match the displayed dials, then press **Pedal set: record batch**. The tool plays and records every selected sample before showing the next dial settings. We confirm each batch ourselves. **Pause** discards the current sample; pressing the record button again retries only unfinished samples. **End run** keeps saved files and unlocks setup. Closing the app also stops recording. Reopening a saved run is not currently supported.

Each run gets its own folder containing copies of the inputs, WAV recordings and `manifest.json`. The manifest pairs each input and output with the dial values, sample rate and recording length. Recordings include a 0.25 second tail. They keep the device's raw timing, so we still need to align the input and output before using them for training.
