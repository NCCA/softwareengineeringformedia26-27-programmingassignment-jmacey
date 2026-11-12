#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "numpy>=2.5.4",
#     "pyside6>=6.12.0",
#     "sounddevice>=0.5.6",
#     "soundfile>=0.14.0",
# ]
# ///
"""Launch the QML training sample preparation window."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

if __package__:
    from .backend import TrainingBackend
else:
    from backend import TrainingBackend


def create_engine(backend: TrainingBackend) -> QQmlApplicationEngine:
    if QQuickStyle.name() != "Fusion":
        QQuickStyle.setStyle("Fusion")
    engine = QQmlApplicationEngine()
    backend.setParent(engine)
    engine.setInitialProperties({"backend": backend})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parent / "qml" / "Main.qml")))
    return engine


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Pedal training samples")
    app.setOrganizationName("NCCA")
    backend = TrainingBackend()
    engine = create_engine(backend)
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
