#!/usr/bin/env -S uv run --script
"""Launch the QML training sample preparation window."""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from training_tool.backend import TrainingBackend


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
