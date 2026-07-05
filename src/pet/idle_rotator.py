"""ActionCarousel — cycles through 6 actions (idle1..idle4, drag, ameath)
while the pet is in IDLE state.

Why outside PetStateMachine: rotation is purely visual.  Keeping it
out of the SM keeps the state enum small and the rotation trivially
testable.

`trigger(name)` is called by the orchestrator when the user picks an
action from the '🎬 动作' submenu.  It jumps to that action, restarts
the timer, and the carousel keeps cycling.  See dev-doc/13 §3.

Music lock (Bug A / dev-doc/16 §3.2): when music is playing, the
carousel must NOT swap away from ameath until the lock is cleared.
`set_music_lock(True)` pins the carousel at the current action;
`set_music_lock(False)` resumes normal rotation.
"""
from __future__ import annotations
from typing import Callable, Optional

from PyQt6.QtCore import QTimer

from .state_machine import PetState


# Hard limits per dev-doc/17 §2.1 (2026-07-04)
_IDLE_ROT_MIN_S = 5
_IDLE_ROT_MAX_S = 1800


# ActionCarousel uses index 0..5 — wraps around the ACTIONS list.
# All 6 entries map directly onto ACTION_FILES in animation_player.
ACTIONS = ["idle1", "idle2", "idle3", "idle4", "drag", "ameath"]
COUNT = len(ACTIONS)


class IdleRotator:
    """Drive `set_variant_cb(idx)` every `interval_s` seconds while
    SM state is IDLE.  Use `trigger(name)` to fast-forward to a
    specific action (e.g. user clicked a 🎬 menu item).

    Kept the class name `IdleRotator` for source-compatibility with
    callers in src/aemeath/main.py — it now does a fuller carousel,
    not just idle, but renaming is a wider change than this fix
    warrants.
    """

    def __init__(self, current_state_provider: Callable[[], PetState],
                 set_variant_cb: Callable[[int], None],
                 interval_s: int = 15):
        self._state = current_state_provider
        self._set_variant = set_variant_cb
        self._interval_s = max(_IDLE_ROT_MIN_S, min(_IDLE_ROT_MAX_S, int(interval_s)))
        self._index = 0
        self._timer = QTimer()
        self._timer.setInterval(self._interval_s * 1000)
        self._timer.timeout.connect(self._on_tick)
        # Bug A / dev-doc/16 §3.2: music lock.  When True, _on_tick is
        # a no-op (carousel paused — the user explicitly requested the
        # current action via 🎵 播放音乐 / 🕶 ameath, and we shouldn't
        # rotate away until they break the lock themselves or the
        # track ends).
        self._music_locked: bool = False

    @property
    def interval_s(self) -> int:
        return self._interval_s

    @interval_s.setter
    def interval_s(self, v: int) -> None:
        """Live-update the rotation interval (clamped to [5, 1800])."""
        self._interval_s = max(_IDLE_ROT_MIN_S, min(_IDLE_ROT_MAX_S, int(v)))
        self._timer.setInterval(self._interval_s * 1000)
        if self._timer.isActive():
            self._timer.start()  # restart countdown from "now"

    @property
    def is_music_locked(self) -> bool:
        return self._music_locked

    @property
    def current_name(self) -> Optional[str]:
        idx = self._index % COUNT if COUNT else None
        return ACTIONS[idx] if idx is not None and 0 <= idx < COUNT else None

    def set_music_lock(self, on: bool) -> None:
        """Bug A / dev-doc/16 §3.2: when on, _on_tick is a no-op so
        the carousel pauses at the user's chosen action while music
        is playing.  When off, the carousel resumes from the current
        index — there is no forced reset."""
        self._music_locked = bool(on)

    def on_state_changed(self, s: PetState) -> None:
        if s == PetState.IDLE:
            # Reset to index 0 every time we (re)enter IDLE so the
            # user sees a consistent start.
            self._index = 0
            self._set_variant(0)
            self._timer.start()
        else:
            self._timer.stop()

    def trigger(self, name: str) -> None:
        """User picked `name` from the menu — jump there, restart the
        countdown so the carousel continues from this point.
        Carousel only proceeds while state == IDLE; if not IDLE the
        call is a no-op (caller should set_state first or accept
        that the swap is one-shot).
        """
        if name not in ACTIONS:
            # Unknown action — just advance by 1 like a normal tick.
            self._index = (self._index + 1) % COUNT
            self._set_variant(self._index)
            return
        self._index = ACTIONS.index(name)
        self._set_variant(self._index)
        if self._state() == PetState.IDLE:
            self._timer.start()  # restart countdown from "now"

    def stop(self) -> None:
        self._timer.stop()

    def _on_tick(self) -> None:
        # Bug A / dev-doc/16 §3.2: honour the music lock before anything
        # else.  Even if SM is still IDLE, we keep the carousel pinned
        # at the current index while the user is enjoying a song.
        if self._music_locked:
            print(f"[IdleRotator] tick blocked: music_locked=True")
            return
        if self._state() != PetState.IDLE:
            print(f"[IdleRotator] tick blocked: state={self._state().value}")
            self._timer.stop()
            return
        old = ACTIONS[self._index % COUNT]
        self._index = (self._index + 1) % COUNT
        new = ACTIONS[self._index % COUNT]
        print(f"[IdleRotator] tick: {old} -> {new}")
        self._set_variant(self._index)
