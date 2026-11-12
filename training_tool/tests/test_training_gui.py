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

from ..app import create_engine
from ..backend import TrainingBackend
from ..session import TrainingSession


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
    assert backend.controls[0] == {"label": "Drive", "value": 0.8, "steps": 3}
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


def test_batches_wait_for_confirmation_and_show_next_dial_positions(tmp_path):
    devices = [{"name": "Test mixer", "max_input_channels": 4,
                "max_output_channels": 2, "default_samplerate": 8000}]
    for name in ("one.wav", "two.wav"):
        sf.write(tmp_path / name, np.full(80, 0.25), 8000)
    captures = []

    def capture(source, device, output, channel, cancelled):
        captures.append(source)
        return np.zeros((80, 1), dtype=np.float32), 8000

    app = QGuiApplication.instance() or QGuiApplication([])
    backend = TrainingBackend(TrainingSession(query_devices=lambda: devices), capture=capture)
    backend.setControlCount(1)
    backend.setControlSteps(0, 2)
    backend.addSampleFolder(QUrl.fromLocalFile(str(tmp_path)))
    backend.selectAllSamples(True)
    engine = create_engine(backend)
    root = engine.rootObjects()[0]
    backend.prepareRun(QUrl.fromLocalFile(str(tmp_path)))
    app.processEvents()
    button = root.findChild(QQuickItem, "recordBatch")
    assert button.property("enabled") is True
    assert backend.controls[0]["value"] == 0
    assert captures == []
    backend.setControlValue(0, 0.8)
    backend.clearSamples()
    assert backend.controls[0]["value"] == 0
    assert backend.selectedSampleCount == 2
    QMetaObject.invokeMethod(button, "clicked")
    for _ in range(200):
        QTest.qWait(5)
        if not backend.recording:
            break
    assert not backend.recording
    assert len(captures) == 2
    assert backend.controls[0]["value"] == 1
    assert "batch 2/2" in backend.trainingSummary
    QTest.qWait(50)
    assert len(captures) == 2
    QMetaObject.invokeMethod(button, "clicked")
    for _ in range(200):
        QTest.qWait(5)
        if not backend.recording:
            break
    assert not backend.recording
    assert not backend.runActive
    assert len(captures) == 4
    assert "Training complete" in backend.trainingSummary
    app.processEvents()
    assert button.property("enabled") is False
    root.close()
    delete(engine)


def test_pause_stops_worker_and_keeps_run_ready_to_retry(tmp_path):
    from threading import Event
    from ..training import RecordingCancelled

    app = QGuiApplication.instance() or QGuiApplication([])
    started = Event()

    def capture(source, device, output, channel, cancelled):
        started.set()
        cancelled.wait(2)
        raise RecordingCancelled()

    devices = [{"name": "Mixer", "max_input_channels": 1,
                "max_output_channels": 1, "default_samplerate": 8000}]
    backend = TrainingBackend(TrainingSession(query_devices=lambda: devices), capture=capture)
    sf.write(tmp_path / "tone.wav", np.zeros(80), 8000)
    backend.addSampleFolder(QUrl.fromLocalFile(str(tmp_path)))
    backend.selectAllSamples(True)
    backend.prepareRun(QUrl.fromLocalFile(str(tmp_path)))
    backend.recordBatch()
    assert started.wait(1)
    backend.pauseRecording()
    for _ in range(200):
        QTest.qWait(5)
        if not backend.recording:
            break
    assert not backend.recording
    assert backend.runActive
    assert "Paused" in backend.message
    assert "batch 1/27" in backend.trainingSummary
    backend.endRun()
    assert not backend.runActive
    app.processEvents()


def test_stereo_source_can_prepare_a_run_with_mono_output(tmp_path):
    QGuiApplication.instance() or QGuiApplication([])
    devices = [{"name": "Mono output", "max_input_channels": 1,
                "max_output_channels": 1, "default_samplerate": 8000}]
    sf.write(tmp_path / "stereo.wav", np.zeros((80, 2)), 8000)
    backend = TrainingBackend(TrainingSession(query_devices=lambda: devices))
    backend.addSampleFolder(QUrl.fromLocalFile(str(tmp_path)))
    backend.selectAllSamples(True)
    backend.prepareRun(QUrl.fromLocalFile(str(tmp_path)))
    assert backend.runActive
    assert "too few channels" not in backend.message
    backend.endRun()
