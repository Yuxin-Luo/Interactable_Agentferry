"""Mapping PetState → GIF file on disk.

Per dev-doc/9 + the existing idle rotation design (dev-doc/11):
- IDLE base mapping is `idle1.gif` so `gif_for_state(IDLE)` keeps
  working (test backwards-compat).  IdleRotator overrides the GIF via
  `gif_for_idle_variant(i)` when it ticks.
- drag is a transient visual (`gif_for_drag()`) and is NOT a state;
  PetWindow swaps to it during real mouse drag, then swaps back.
- screen3 is currently unmapped — reserved for v2 "claude asking" state.
"""
from pathlib import Path
from PyQt6.QtGui import QMovie

from .state_machine import PetState


ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets" / "ameath" / "gifs"


# Mapping for the 7 states that have a fixed GIF.  IDLE is intentionally
# NOT in this dict — it's handled by gif_for_idle_variant() so the
# idle rotator can override without mutating global state.
STATE_GIFS: dict[PetState, str] = {
    PetState.HOVER_BUBBLE:  "idle2.gif",
    PetState.CHAT_ACTIVE:   "idle3.gif",
    PetState.WAITING:       "idle4.gif",
    PetState.CLI_THINKING:  "screen1.gif",
    PetState.CLI_CELEBRATE: "ameath.gif",
    PetState.CLI_ERROR:     "drag.gif",
    PetState.CLI_LONG_WAIT: "screen2.gif",
}


# Action name (str) → GIF file basename.  Used by both the state machine
# mapping and the right-click "🎬 动作" submenu.
ACTION_FILES: dict[str, str] = {
    "idle1":  "idle1.gif",
    "idle2":  "idle2.gif",
    "idle3":  "idle3.gif",
    "idle4":  "idle4.gif",
    "drag":   "drag.gif",
    "ameath": "ameath.gif",
}


# Idle has 4 variants; we use idle1..idle4.gif.  Index 0 → idle1, etc.
IDLE_VARIANT_FILES = ["idle1.gif", "idle2.gif", "idle3.gif", "idle4.gif"]
DRAG_FILE = "drag.gif"


def _safe_load(rel: str) -> QMovie:
    """Build QMovie(rel); fall back to empty QMovie if file is missing."""
    p = ASSET_ROOT / rel
    if not p.exists():
        return QMovie()
    return QMovie(str(p))


def gif_for_state(s: PetState) -> QMovie:
    """Return GIF for non-IDLE states.  IDLE defaults to idle1.gif
    so callers that don't yet know about idle rotation just work."""
    if s == PetState.IDLE:
        return _safe_load(IDLE_VARIANT_FILES[0])
    rel = STATE_GIFS.get(s)
    if rel is None:
        return _safe_load(IDLE_VARIANT_FILES[0])
    return _safe_load(rel)


def gif_for_idle_variant(idx: int) -> QMovie:
    """Idle-rotator entry point.  idx mod 4 → idle{idx+1}.gif."""
    i = idx % len(IDLE_VARIANT_FILES)
    return _safe_load(IDLE_VARIANT_FILES[i])


def gif_for_drag() -> QMovie:
    return _safe_load(DRAG_FILE)


def gif_for_action(name: str) -> QMovie:
    """Resolve an ACTION_FILES name to a QMovie.

    Used by PetWindow.play_action() for the right-click '🎬 动作' menu.
    Unknown names fall back to idle1.
    """
    return _safe_load(ACTION_FILES.get(name, IDLE_VARIANT_FILES[0]))


# Public alias preserved for backwards compatibility with existing tests.
GIF_PATHS: dict[PetState, str] = {s: f for s, f in STATE_GIFS.items()}
GIF_PATHS[PetState.IDLE] = IDLE_VARIANT_FILES[0]
