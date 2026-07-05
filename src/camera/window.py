"""CameraPetWindow — single frameless transparent window hosting camera preview + pet overlay.

spec §3.1 / §3.2 / §11 Q4
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint, QSize, QRect
from PyQt6.QtGui import QMouseEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow,
    QLabel,
    QWidget,
    QVBoxLayout,
)

# 确保 resources 路径可解析
_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "ameath"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CameraLabel(QLabel):
    """背景：显示摄像头 QImage（letterbox）。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: black;")


class PetOverlay(QLabel):
    """桌宠 GIF 透明叠加层。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(128, 128)  # 默认尺寸
        from PyQt6.QtGui import QMovie
        self._movie = None
        self._current_gif_path: str | None = None
        self._dragging = False
        self._drag_offset = QPoint()

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_offset = ev.position().toPoint()
            # 通知 controller
            if hasattr(self.parent(), "_controller"):
                self.parent()._controller.start_mouse_drag()
            ev.accept()

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        if self._dragging:
            new_pos = self.parent().mapFromGlobal(ev.globalPosition().toPoint()) - self._drag_offset
            if hasattr(self.parent(), "_controller"):
                self.parent()._controller.update_mouse_drag(new_pos)
            else:
                self.move(new_pos)
            ev.accept()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._dragging = False
            if hasattr(self.parent(), "_controller"):
                self.parent()._controller.end_mouse_drag()
            ev.accept()


class HUDLabel(QLabel):
    """右上角手势标签（占位）。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(
            "color: white; background-color: rgba(0,0,0,128); padding: 4px; border-radius: 4px;"
        )
        self.setFixedSize(140, 24)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()


class CameraPetWindow(QMainWindow):
    """主窗口：frameless + 透明 + Tool + StaysOnTop，固定宽高比。"""

    def __init__(self, win_w: int = 1280, win_h: int = 720):
        super().__init__()
        self._win_w, self._win_h = win_w, win_h

        # Window flags: frameless + Tool + StaysOnTop（spec §3.1）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(win_w, win_h)

        # central widget: 全黑背景 + 两个叠加层
        central = QWidget(self)
        central.setFixedSize(win_w, win_h)
        self.setCentralWidget(central)

        self.camera_label = CameraLabel(central)
        self.camera_label.setGeometry(0, 0, win_w, win_h)

        self.pet_overlay = PetOverlay(central)
        self.pet_overlay.move(win_w // 2 - 64, win_h // 2 - 64)

        self.hud_label = HUDLabel(central)
        self.hud_label.move(win_w - 160, 20)

        # 拖动窗口（点空白处）
        self._dragging_window = False
        self._drag_win_offset = QPoint()

    # ---- 鼠标：拖窗口（点 PetOverlay 之外的区域）----
    def mousePressEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self.childAt(ev.position().toPoint()) is not self.pet_overlay:
            self._dragging_window = True
            self._drag_win_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        if self._dragging_window:
            self.move(ev.globalPosition().toPoint() - self._drag_win_offset)
            ev.accept()

    def mouseReleaseEvent(self, ev: QMouseEvent) -> None:
        if ev.button() == Qt.MouseButton.LeftButton and self._dragging_window:
            self._dragging_window = False
            ev.accept()

    # ---- 外部 API（下阶段填具体逻辑）----
    def update_camera_frame(self, qimage: QImage) -> None:
        self.camera_label.setPixmap(QPixmap.fromImage(qimage).scaled(
            self._win_w, self._win_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def update_pet(self, position: QPoint, gif_path: str, scale: float = 1.0) -> None:
        """PetController → PetOverlay."""
        from PyQt6.QtGui import QMovie
        from pathlib import Path

        size = int(128 * scale)
        self.pet_overlay.setFixedSize(size, size)
        # GIF 切换
        if gif_path != self.pet_overlay._current_gif_path:
            full_path = _PROJECT_ROOT / gif_path if not Path(gif_path).is_absolute() else Path(gif_path)
            if full_path.exists():
                movie = QMovie(str(full_path))
                self.pet_overlay.setMovie(movie)
                movie.start()
                self.pet_overlay._movie = movie
                self.pet_overlay._current_gif_path = gif_path
        self.pet_overlay.move(position)

    def update_hud(self, text: str) -> None:
        self.hud_label.setText(text)
        if text:
            self.hud_label.show()
        else:
            self.hud_label.hide()


def main() -> int:
    """手动 demo：运行 `python -m src.camera.window` 看窗口骨架."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = CameraPetWindow(win_w=640, win_h=360)
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())