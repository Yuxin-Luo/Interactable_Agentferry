"""PetController — 状态机 + 飞行动画 + 策略 (spec §3.2 / §4).

信号:
- render_command(QPoint, str, float) → PetOverlay
- hud_update(str) → HUDLabel
- audio_command(str, dict) → SoundManager (P7)

输入:
- VisionSignal (从 VisionWorker)
- 鼠标拖动事件 (P5 接入)
"""
from __future__ import annotations
import math
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List

from PyQt6.QtCore import QObject, pyqtSignal, QPoint, QSize, QRect

from src.config.settings import VisionSettings
from src.vision.worker import VisionSignal
from src.pet.distance_tier import compute_tier
from src.pet.flight import FlightController
from src.pet.head_exclusion import HeadExclusionZone


class PetState(str, Enum):
    DEFAULT_FLY = "default_fly"
    OPEN_PALM = "open_palm"
    THUMB_UP = "thumb_up"
    THUMB_DOWN = "thumb_down"
    VICTORY = "victory"
    FIST = "fist"
    POINTING = "pointing"
    DRAG_MOUSE = "drag_mouse"
    DRAG_PINCH = "drag_pinch"


@dataclass
class RenderCommand:
    position: QPoint
    gif_path: str
    scale: float


# 资源路径（相对项目根）
_GIF_OPEN_PALM_1 = "assets/ameath/gifs/idle1.gif"
_GIF_OPEN_PALM_2 = "assets/ameath/gifs/idle2.gif"
_GIF_OPEN_PALM_3 = "assets/ameath/gifs/idle3.gif"
_GIF_OPEN_PALM_4 = "assets/ameath/gifs/idle4.gif"
_GIF_DRAG = "assets/ameath/gifs/drag.gif"
_GIF_AMEATH = "assets/ameath/gifs/ameath.gif"
_GIF_MOVE = "assets/ameath/gifs/move.gif"
_GIF_SCREEN1 = "assets/ameath/gifs/screen1.gif"
_GIF_SCREEN2 = "assets/ameath/gifs/screen2.gif"
_GIF_SCREEN3 = "assets/ameath/gifs/screen3.gif"
_GIF_SCREEN4 = "assets/ameath/gifs/screen4.gif"


class PetController(QObject):
    render_command = pyqtSignal(object)  # RenderCommand
    hud_update = pyqtSignal(str)
    audio_command = pyqtSignal(str, dict)

    def __init__(self, vision: VisionSettings, parent: QObject | None = None):
        super().__init__(parent)
        self._vision = vision
        self._state = PetState.DEFAULT_FLY
        self._win_w = 0
        self._win_h = 0
        self._pet_size = 128  # base
        self._pet_pos = QPoint(0, 0)
        self._flight = FlightController(speed_px_per_s=vision.flight_speed_min)
        self._face_bbox: Optional[QRect] = None
        self._face_center: Optional[QPoint] = None
        self._last_render: Optional[RenderCommand] = None
        self._target_pick_counter = 0
        self._current_target: Optional[QPoint] = None
        # OPEN_PALM 内部 idle 轮播计数器
        self._open_palm_index = 0
        self._last_gesture_ts: float = 0.0
        # gesture_hold_timeout 用于 P3 接入

    @property
    def state(self) -> PetState:
        return self._state

    @property
    def last_render(self) -> Optional[RenderCommand]:
        return self._last_render

    def set_window_size(self, w: int, h: int) -> None:
        self._win_w = w
        self._win_h = h
        # 初始化桌宠位置：窗口中心
        self._pet_pos = QPoint(w // 2 - self._pet_size // 2, h // 2 - self._pet_size // 2)

    def update(self, signal: VisionSignal) -> None:
        """主线程 tick — 每帧调用一次（与 QTimer.timeout 绑定）."""
        self._face_center = signal.face_center
        if signal.face_bbox_size:
            self._face_bbox = QRect(
                signal.face_center.x() - signal.face_bbox_size.width() // 2,
                signal.face_center.y() - signal.face_bbox_size.height() // 2,
                signal.face_bbox_size.width(),
                signal.face_bbox_size.height(),
            )
        else:
            self._face_bbox = None

        if self._state == PetState.DEFAULT_FLY:
            self._tick_default_fly()

        # 触发 render（每帧 emit，方便 CameraPetWindow 接收）
        self._emit_render()

    # ---- DEFAULT_FLY ----
    def _tick_default_fly(self) -> None:
        if not self._face_center or not self._face_bbox:
            # 无脸：保持当前位置
            return
        # 候选目标点：头部周围 8 个点（弧线分布）
        if not self._current_target or FlightController.arrived(self._pet_pos, self._current_target):
            self._pick_new_target()
        # 飞向当前目标
        now = time.time()
        if not hasattr(self, "_last_tick_ts"):
            self._last_tick_ts = now
        dt = max(0.001, now - self._last_tick_ts)
        self._last_tick_ts = now
        self._pet_pos = self._flight.step(self._pet_pos, self._current_target, dt)

    def _pick_new_target(self) -> None:
        """从头部周围 8 个候选点中选一个不在 head exclusion zone 的."""
        if not self._face_center or not self._face_bbox:
            return
        cx, cy = self._face_center.x(), self._face_center.y()
        r = max(self._face_bbox.width(), self._face_bbox.height()) // 2 + 80
        angles = [i * (2 * math.pi / 8) for i in range(8)]
        candidates = [
            QPoint(int(cx + r * math.cos(a)), int(cy + r * math.sin(a)))
            for a in angles
        ]
        zone = HeadExclusionZone(self._face_bbox, padding_ratio=self._vision.head_exclusion_padding)
        self._current_target = zone.find_safe_target(candidates[self._target_pick_counter % 8], candidates)
        self._target_pick_counter += 1

    # ---- Render ----
    def _emit_render(self) -> None:
        # 距离档位
        bbox_w = self._face_bbox.width() if self._face_bbox else 0
        tier, scale = compute_tier(bbox_w, self._vision.face_tier_thresholds, (self._vision.pet_size_near, self._vision.pet_size_mid, self._vision.pet_size_far))

        gif = self._gif_for_state()
        cmd = RenderCommand(position=self._pet_pos, gif_path=gif, scale=scale)
        self._last_render = cmd
        self.render_command.emit(cmd)
        # HUD
        self.hud_update.emit(self._state.value)
        self.audio_command.emit(self._state.value, {"loop": True})

    def _gif_for_state(self) -> str:
        if self._state == PetState.DEFAULT_FLY:
            return _GIF_MOVE
        # 其他状态在后续任务填充
        return _GIF_MOVE
