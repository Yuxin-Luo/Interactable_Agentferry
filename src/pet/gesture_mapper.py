"""手势→动作 映射（spec §4.3）."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GestureAction:
    gif: str
    voice: Optional[str] = None
    music: bool = False
    loop: bool = True


_GIF_OPEN_PALM = "assets/ameath/gifs/idle1.gif"  # idle 序列在 P3 轮播
_GIF_DRAG = "assets/ameath/gifs/drag.gif"
_GIF_AMEATH = "assets/ameath/gifs/ameath.gif"
_GIF_MOVE = "assets/ameath/gifs/move.gif"
_GIF_SCREEN1 = "assets/ameath/gifs/screen1.gif"
_GIF_SCREEN2 = "assets/ameath/gifs/screen2.gif"
_GIF_SCREEN3 = "assets/ameath/gifs/screen3.gif"
_GIF_SCREEN4 = "assets/ameath/gifs/screen4.gif"


# OPEN_PALM 用 idle1 占位；轮播由 PetController 决定（每 N 秒切到下一帧）
GESTURE_ACTIONS: dict[str, GestureAction] = {
    "None":        GestureAction(gif=_GIF_MOVE, voice=None, music=False, loop=True),
    "Open_Palm":   GestureAction(gif=_GIF_OPEN_PALM, voice=None, music=False, loop=True),
    "Thumb_Up":    GestureAction(gif=_GIF_SCREEN1, voice=None, music=False, loop=True),
    "Thumb_Down":  GestureAction(gif=_GIF_SCREEN4, voice="嘿嘿.wav", music=False, loop=True),
    "Victory":     GestureAction(gif=_GIF_AMEATH, voice="现实系统，侵入完成.wav", music=True, loop=True),
    "Closed_Fist": GestureAction(gif=_GIF_SCREEN2, voice=None, music=False, loop=True),
    "Pointing_Up": GestureAction(gif=_GIF_SCREEN3, voice=None, music=False, loop=True),
    "Pinch":       GestureAction(gif=_GIF_DRAG, voice="嘿嘿.wav", music=False, loop=False),
}

# Open_Palm 的 idle 轮播候选
OPEN_PALM_GIFS = (
    "assets/ameath/gifs/idle1.gif",
    "assets/ameath/gifs/idle2.gif",
    "assets/ameath/gifs/idle3.gif",
    "assets/ameath/gifs/idle4.gif",
)


def lookup(label: str) -> GestureAction:
    return GESTURE_ACTIONS.get(label, GESTURE_ACTIONS["None"])
