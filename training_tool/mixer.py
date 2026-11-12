#!/usr/bin/env -S uv run --script
"""
Record audio from a USB mixing desk (or any Core Audio input) to a WAV file.

Requirements:
    pip install sounddevice soundfile numpy

Usage:
    python mixer.py --list                       # show audio devices
    python mixer.py -d "Xenyx" out.wav           # record until Ctrl-C
    python mixer.py -d 3 -t 30 out.wav           # record 30 seconds from device 3
    python mixer.py -d "QU" -c 1 2 7 8 out.wav   # pick specific channels (1-based)
    python mixer.py -d "Flow" --scan             # which channel has signal?

Behringer FLOW 8 in Recording mode sends 10 USB channels:
    1-8 = input channels (pre-fader), 9/10 = main L/R mix.
In Streaming mode it sends only the stereo main mix.
"""

from collections.abc import Callable, Iterable, Mapping
from typing import Any

import argparse
import queue
import sys
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

def input_devices(query_devices: Callable[[], Iterable[Mapping[str, Any]]] | None = None) -> list[dict]:
    if query_devices is None:
        import sounddevice

        query_devices = sounddevice.query_devices
    return [
        {"id": index, "name": device["name"],
         "channels": int(device["max_input_channels"]),
         "sample_rate": int(device["default_samplerate"])}
        for index, device in enumerate(query_devices())
        if device["max_input_channels"] > 0
    ]


def output_devices(query_devices: Callable[[], Iterable[Mapping[str, Any]]] | None = None) -> list[dict]:
    query_devices = query_devices or sd.query_devices
    return [
        {"id": index, "name": device["name"], "channels": int(device.get("max_output_channels", 0))}
        for index, device in enumerate(query_devices())
        if device.get("max_output_channels", 0) > 0
    ]


def list_devices() -> None:
    """Print every device with input channels and its default sample rate."""
    print(f"{'idx':>3}  {'in':>3}  {'rate':>7}  name")
    for dev in input_devices():
        print(f"{dev['id']:>3}  {dev['channels']:>3}  {dev['sample_rate']:>7}  {dev['name']}")


def scan_channels(device: int, seconds: float = 2.0) -> None:
    """Record a short burst on every input channel and print its level,
    so you can see which USB channel your signal actually arrives on."""
    info = sd.query_devices(device, "input")
    ch = info["max_input_channels"]
    sr = int(info["default_samplerate"])
    print(f"Scanning {ch} channels on '{info['name']}' for {seconds}s – make some noise...")
    data = sd.rec(int(sr * seconds), samplerate=sr, channels=ch, device=device, dtype="float32")
    sd.wait()
    peak = np.abs(data).max(axis=0)
    rms = np.sqrt((data**2).mean(axis=0))
    for i in range(ch):
        pk_db = 20 * np.log10(max(peak[i], 1e-9))
        rms_db = 20 * np.log10(max(rms[i], 1e-9))
        bar = "#" * max(0, int((pk_db + 60) / 2))
        print(f"  ch {i + 1:>2}: peak {pk_db:6.1f} dBFS  rms {rms_db:6.1f} dBFS  {bar}")


def resolve_device(spec: str) -> int:
    """Accept either a device index or a case-insensitive substring of its name."""
    if spec.isdigit():
        return int(spec)
    matches = [
        i for i, d in enumerate(sd.query_devices()) if spec.lower() in d["name"].lower() and d["max_input_channels"] > 0
    ]
    if not matches:
        sys.exit(f"No input device matching '{spec}'. Run with --list.")
    if len(matches) > 1:
        print(f"Several devices match '{spec}', using index {matches[0]}.")
    return matches[0]


def record(
    filename: str,
    device: int,
    channels: list[int] | None,
    samplerate: int | None,
    duration: float | None,
    subtype: str,
) -> None:
    info = sd.query_devices(device, "input")
    max_ch = info["max_input_channels"]
    samplerate = samplerate or int(info["default_samplerate"])

    # Channel selection: PortAudio's Core Audio backend can open the device
    # with all channels and we slice afterwards. Simple, and works the same
    # for a 2-in desk or a 32-in digital mixer.
    if channels:
        bad = [c for c in channels if c < 1 or c > max_ch]
        if bad:
            sys.exit(f"Channels {bad} out of range (device has {max_ch}).")
        open_ch = max(channels)
        select = np.array(channels) - 1
    else:
        open_ch = max_ch
        select = None
    out_ch = len(select) if select is not None else open_ch

    # The audio callback runs on a real-time thread. It must not block,
    # so it only copies the buffer into a queue; disk I/O happens here
    # on the main thread.
    q: queue.Queue[np.ndarray] = queue.Queue()
    xruns = 0
    peak = np.zeros(out_ch, dtype=np.float32)

    def callback(indata, frames, time_info, status):
        nonlocal xruns
        if status.input_overflow:
            xruns += 1
        q.put(indata.copy())

    print(f"Recording '{info['name']}' | {out_ch} ch @ {samplerate} Hz -> {filename} ({subtype})")
    print("Press Ctrl-C to stop." if duration is None else f"Duration: {duration}s")

    def write_block(f: sf.SoundFile, block: np.ndarray) -> None:
        if select is not None:
            block = block[:, select]
        f.write(block)
        np.maximum(peak, np.abs(block).max(axis=0), out=peak)

    with sf.SoundFile(filename, mode="w", samplerate=samplerate, channels=out_ch, subtype=subtype) as f:
        start = time.monotonic()
        try:
            with sd.InputStream(
                device=device,
                channels=open_ch,
                samplerate=samplerate,
                dtype="float32",
                callback=callback,
                latency="high",  # bigger buffers = fewer dropouts; latency doesn't matter here
            ):
                last_meter = 0.0
                while True:
                    write_block(f, q.get())
                    now = time.monotonic() - start
                    if now - last_meter > 0.25:
                        db = 20 * np.log10(np.maximum(peak, 1e-9))
                        meter = " ".join(f"{d:6.1f}" for d in db)
                        print(f"\r{now:7.1f}s  peak dBFS: {meter}", end="", flush=True)
                        peak[:] = 0
                        last_meter = now
                    if duration is not None and now >= duration:
                        break
        except KeyboardInterrupt:
            pass
        # Stream is closed now; flush anything still queued so the tail isn't lost.
        while not q.empty():
            write_block(f, q.get_nowait())
        print()
    if xruns:
        print(f"Warning: {xruns} input overflow(s) – try a larger blocksize or fewer apps.")
    print(f"Saved {filename}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("filename", nargs="?", default="desk.wav")
    p.add_argument("-l", "--list", action="store_true", help="list input devices")
    p.add_argument("-s", "--scan", action="store_true", help="show per-channel levels for 2s")
    p.add_argument("-d", "--device", help="device index or name substring")
    p.add_argument("-c", "--channels", type=int, nargs="+", help="1-based channels to record")
    p.add_argument("-r", "--samplerate", type=int, help="defaults to device rate")
    p.add_argument("-t", "--duration", type=float, help="seconds (default: until Ctrl-C)")
    p.add_argument(
        "--subtype",
        default="PCM_24",
        choices=["PCM_16", "PCM_24", "FLOAT"],
        help="WAV sample format (default PCM_24)",
    )
    args = p.parse_args()

    if args.list:
        list_devices()
        return
    if args.device is None:
        sys.exit("Specify --device (see --list).")
    if args.scan:
        scan_channels(resolve_device(args.device))
        return

    record(
        args.filename,
        resolve_device(args.device),
        args.channels,
        args.samplerate,
        args.duration,
        args.subtype,
    )


if __name__ == "__main__":
    main()
