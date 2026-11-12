import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QObject, QMetaObject, qInstallMessageHandler
from PySide6.QtCore import Qt, QUrl
from PySide6.QtTest import QTest
from PySide6.QtQuick import QQuickItem
from shiboken6 import delete
import numpy as np
import soundfile as sf

from training_tool.app import create_engine
from training_tool.backend import TrainingBackend
from training_tool.session import TrainingSession


def test_qml_loads_and_controls_follow_the_session():
    app = QGuiApplication.instance() or QGuiApplication([])
    backend = TrainingBackend(TrainingSession(query_devices=lambda: []))
    messages = []
    previous_handler = qInstallMessageHandler(lambda kind, context, message: messages.append(message))
    engine = create_engine(backend)
    app.processEvents()
    assert len(engine.rootObjects()) == 1
    root = engine.rootObjects()[0]
    count = root.findChild(QObject, "controlCount")
    assert count is not None
    count.setProperty("value", 4)
    QMetaObject.invokeMethod(count, "valueModified")
    app.processEvents()
    assert len(backend.controls) == 4
    backend.setControlLabel(0, "Drive")
    backend.setControlValue(0, 0.8)
    assert backend.controls[0] == {"label": "Drive", "value": 0.8}
    backend.setControlCount(0)
    app.processEvents()
    assert count.property("value") == 0
    root.close()
    delete(engine)
    app.processEvents()
    qInstallMessageHandler(previous_handler)
    assert not [m for m in messages if "Binding loop" in m or "TypeError" in m]


def test_missing_audio_hardware_is_reported_without_preventing_setup():
    def unavailable():
        raise OSError("USB mixer disconnected")

    backend = TrainingBackend(TrainingSession(query_devices=unavailable))
    assert backend.devices == []
    assert backend.selectedDeviceIndex == -1
    assert "USB mixer disconnected" in backend.message
    backend.setControlCount(2)
    assert len(backend.controls) == 2


def test_user_can_select_a_sample_in_the_qml_list(tmp_path):
    sf.write(tmp_path / "tone.wav", np.zeros(800), 8000)
    app = QGuiApplication.instance() or QGuiApplication([])
    backend = TrainingBackend(TrainingSession(query_devices=lambda: []))
    backend.addSampleFolder(QUrl.fromLocalFile(str(tmp_path)))
    engine = create_engine(backend)
    root = engine.rootObjects()[0]
    QTest.qWait(50)
    view = root.findChild(QQuickItem, "sampleList")
    rows = [item for item in view.property("contentItem").childItems()
            if item.property("text")]
    assert len(rows) == 1
    row = rows[0]
    position = row.mapToScene(row.boundingRect().center()).toPoint()
    QTest.mouseClick(root, Qt.MouseButton.LeftButton, pos=position)
    app.processEvents()
    assert backend.selectedSampleCount == 1
    assert row.property("checked") is True
    QTest.mouseClick(root, Qt.MouseButton.LeftButton, pos=position)
    app.processEvents()
    assert backend.selectedSampleCount == 0
    root.close()
    delete(engine)
