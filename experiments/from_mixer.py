#!/usr/bin/env -S uv run --script
"""Run the mixer recorder now maintained in the training app."""

import sys
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training_tool.mixer import list_devices, main, record, resolve_device, scan_channels

__all__ = ["list_devices", "main", "record", "resolve_device", "scan_channels"]

if __name__ == "__main__":
    main()
