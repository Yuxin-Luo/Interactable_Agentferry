from __future__ import annotations
from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QSize, QTimer
from PyQt6.QtGui import QMovie
from PyQt6.QtWidgets import QLabel, QMainWindow

from .state_machine import PetState
from .animation_player import (
    gif_for_state, gif_for_idle_variant, gif_for_drag, gif_for_action,
    ACTION_FILES,
)


# All GIFs are scaled to fit within MAX_GIF_PX (largest dimension).
# ameath.gif source is 1000×1000 (dev-doc/11 §2.2); smaller GIFs are
# 200~400px.  Cap at 240 so the pet stays compact regardless of source
# size (Issue 4 / dev-doc/13 §1).
MAX_GIF_PX = 240


def _clamp_size(natural: QSize, cap: int = MAX_GIF_PX) -> QSize:
    """Scale `natural` down to fit within `cap` (largest dimension),
    preserving aspect ratio.  Empty / zero sizes fall back to cap×cap."""
    if not natural.isValid() or natural.width() <= 0 or natural.height() <= 0:
        return QSize(cap, cap)
    m = max(natural.width(), natural.height())
    if m <= cap:
        return natural
    scale = cap / m
    return QSize(int(natural.width() * scale), int(natural.height() * scale))


class PetWindow(QMainWindow):
    def __init__(self, state_changed_cb):
        super().__init__()
        self._state = PetState.IDLE
        self._state_changed_cb = state_changed_cb
        self._drag_pos: QPoint | None = None
        self._scale = 1.0
        self._pass_through = True
        # When True, the current GIF is drag.gif regardless of state.
        self._dragging_visual = False
        # Base size after GIF clamp — drives wheel scaling (was hardcoded
        # 200 before; ameath.gif would 5x the window on every wheel tick).
        self._base_size: QSize = QSize(200, 200)

        self.label = QLabel(self)
        self.setCentralWidget(self.label)
        self._movie = gif_for_state(PetState.IDLE)
        self.label.setMovie(self._movie)
        self._movie.start()
        # Initial size reset
        self._swap_to_movie(self._movie)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        if self._pass_through:
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    # --- state + visual swappers ---
    def _swap_to_movie(self, new_movie: QMovie) -> None:
        """Stop current, swap, start new.  Resize label+window to the
        GIF's natural-frame size **capped at MAX_GIF_PX** (Issue 4)."""
        self._movie.stop()
        self._movie = new_movie
        self.label.setMovie(self._movie)
        if self._movie.fileName() and self._movie.frameCount() > 0:
            self._movie.jumpToFrame(0)
            natural = self._movie.frameRect().size()
            target = _clamp_size(natural)
            self._movie.setScaledSize(target)
            self.label.resize(target)
            self.resize(target)
            self._base_size = target
        # Diagnostic: log every GIF swap
        from pathlib import Path as _P
        fname = _P(self._movie.fileName()).name if self._movie.fileName() else "(empty)"
        import traceback
        _tb = traceback.format_stack(limit=3)[:-1]
        print(f"[PetWindow._swap_to_movie] -> {fname} | state={self._state.value} | call_chain:")
        for line in _tb:
            print(f"  {line.rstrip()}")
        self._movie.start()

    def set_state(self, s: PetState):
        if s != self._state:
            self._state = s
        # Drag overlay always wins while the user is holding LMB.
        if self._dragging_visual:
            self._state_changed_cb(s)
            return
        self._swap_to_movie(gif_for_state(s))
        self._state_changed_cb(s)

    def set_idle_variant(self, idx: int) -> None:
        """ActionCarousel entry point.

        idx 0..5 maps to ACTIONS in idle_rotator.py (the 6-action
        carousel: idle1..idle4, drag, ameath).  Out-of-range idx falls
        back to the legacy mod-4 idle behaviour for backward-compat
        with any caller that wasn't updated (Bug 1 / dev-doc/14 §1).
        """
        if self._state != PetState.IDLE or self._dragging_visual:
            return
        # Lazy import avoids any module-load circular dep risk.
        from .idle_rotator import ACTIONS
        if 0 <= idx < len(ACTIONS):
            self._swap_to_movie(gif_for_action(ACTIONS[idx]))
        else:
            self._swap_to_movie(gif_for_idle_variant(idx))

    def set_drag_visual(self, on: bool) -> None:
        """Mouse handler entry point.  While on, every frame is drag.gif."""
        if on == self._dragging_visual:
            return
        self._dragging_visual = on
        if on:
            self._swap_to_movie(gif_for_drag())
        else:
            self._swap_to_movie(gif_for_state(self._state))

    def play_action(self, name: str) -> None:
        """Show `name` GIF (no self-revert timer — ActionCarousel manages
        rotation; see dev-doc/13 §3).  Does NOT change PetState."""
        if name not in ACTION_FILES:
            return
        self._swap_to_movie(gif_for_action(name))

    def state(self) -> PetState:
        return self._state

    def base_size(self) -> QSize:
        return QSize(self._base_size)

    def set_pass_through(self, on: bool):
        self._pass_through = on
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, on)

    # --- mouse ---
    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.set_pass_through(False)
            self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.set_drag_visual(True)

    def mouseMoveEvent(self, ev):
        if ev.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(ev.globalPosition().toPoint() - self._drag_pos)
            if not self._dragging_visual:
                self.set_drag_visual(True)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.set_drag_visual(False)
            QTimer.singleShot(2000, lambda: self.set_pass_through(True))

    def wheelEvent(self, ev):
        delta = ev.angleDelta().y()
        factor = 1.1 if delta > 0 else 1/1.1
        self._scale = max(0.5, min(2.0, self._scale * factor))
        # Scale relative to whatever GIF is currently shown — was hardcoded
        # 200, which broke the ameath.gif 1000x1000 size.
        self.resize(int(self._base_size.width() * self._scale),
                    int(self._base_size.height() * self._scale))

    def sizeHint(self):
        return self.size()
