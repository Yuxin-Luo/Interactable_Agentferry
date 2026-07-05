from __future__ import annotations
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel


class HoverBubble(QLabel):
    def __init__(self, parent, lines: list[str]):
        super().__init__("\n".join(lines), parent)
        self.setStyleSheet(
            "background: rgba(255,255,255,220); border: 1px solid #888;"
            " border-radius: 6px; padding: 6px; font-size: 14px;"
        )
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.adjustSize()
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_near(self, widget):
        self.adjustSize()
        rect = widget.geometry()
        self.move(rect.x() + rect.width() // 2 - self.width() // 2, max(0, rect.y() - self.height() - 4))
        self.show()
        self._hide_timer.start(3000)
