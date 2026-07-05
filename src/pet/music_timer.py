"""MusicTimer — schedule a one-shot random-song play after N minutes of IDLE.

Per dev-doc/11 §2.5: each time SM enters IDLE, we (re)start a single-shot
timer.  When it fires, MusicPlayer.play_random_now() picks one mp3 and
plays it (no loop).  Leaving IDLE (e.g. user opens chat) stops the timer.

`on_ameath_cb` (added 2026-07-04 per dev-doc/13 §3) lets the orchestrator
swap the window GIF to ameath whenever the music fires — implementing the
"music ⇄ ameath" linkage the user asked for in Issue 3.
"""
from __future__ import annotations
from typing import Callable, Optional

from PyQt6.QtCore import QTimer

from .state_machine import PetState


# Hard limits per dev-doc/17 §2.1 (2026-07-04)
_MUSIC_INT_MIN_MIN = 1
_MUSIC_INT_MAX_MIN = 3000


class MusicTimer:
    def __init__(self, current_state_provider: Callable[[], PetState],
                 play_cb: Callable[[], None],
                 interval_min: int = 5,
                 on_ameath_cb: Optional[Callable[[], None]] = None):
        self._state = current_state_provider
        self._play = play_cb
        self._on_ameath = on_ameath_cb
        self._interval_min = max(_MUSIC_INT_MIN_MIN, min(_MUSIC_INT_MAX_MIN, int(interval_min)))
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(self._interval_min * 60 * 1000)
        self._timer.timeout.connect(self._on_fire)

    @property
    def interval_min(self) -> int:
        return self._interval_min

    @interval_min.setter
    def interval_min(self, v: int) -> None:
        """Live-update the interval (clamped to [1, 3000]).  Restarts the
        timer if it was running so the new countdown starts from "now"."""
        self._interval_min = max(_MUSIC_INT_MIN_MIN, min(_MUSIC_INT_MAX_MIN, int(v)))
        self._timer.setInterval(self._interval_min * 60 * 1000)
        if self._timer.isActive():
            self._timer.start()

    def on_state_changed(self, s: PetState) -> None:
        if s == PetState.IDLE:
            self._timer.start()
        else:
            self._timer.stop()

    def stop(self) -> None:
        self._timer.stop()

    def _on_fire(self) -> None:
        if self._state() != PetState.IDLE:
            return
        self._play()
        # Issue 3: music ⇄ ameath linkage — show ameath.gif alongside
        # the music.  The orchestrator wires on_ameath_cb to call
        # window.play_action('ameath') (which sets the GIF; carousel
        # will pick up from there on its next tick).
        if self._on_ameath is not None:
            self._on_ameath()
