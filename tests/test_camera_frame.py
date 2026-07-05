"""Tests for camera_frame signal wiring (VisionWorker → CameraPetWindow)."""
from PyQt6.QtCore import QThread
from PyQt6.QtGui import QImage
from src.vision.worker import VisionWorker
from src.config.settings import VisionSettings


def test_vision_worker_has_camera_frame_signal():
    """VisionWorker declares the camera_frame pyqtSignal."""
    assert hasattr(VisionWorker, "camera_frame")


def test_camera_frame_signal_emits_qimage(qtbot):
    """camera_frame signal carries a QImage object."""
    vision = VisionSettings()
    worker = VisionWorker(vision=vision)
    worker.moveToThread(QThread.currentThread())

    emitted = []
    worker.camera_frame.connect(emitted.append)

    # Emit a test QImage directly via the signal
    test_img = QImage(640, 360, QImage.Format.Format_RGB888)
    worker.camera_frame.emit(test_img)

    assert len(emitted) == 1
    assert isinstance(emitted[0], QImage)
    assert emitted[0].width() == 640
    assert emitted[0].height() == 360
