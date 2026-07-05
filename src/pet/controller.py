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
from src.pet.gesture_mapper import lookup as gesture_lookup, OPEN_PALM_GIFS


# Pet base size in pixels (used by both controller and window).
# Mirrors CameraPetWindow.PET_BASE_SIZE.  mid tier (scale=1.0) renders this.
PET_BASE_SIZE = 192


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
    render_command = pyqtSignal(QPoint, str, float)  # (position, gif_path, scale)
    hud_update = pyqtSignal(str)
    audio_command = pyqtSignal(str, dict)

    def __init__(self, vision: VisionSettings, parent: QObject | None = None):
        super().__init__(parent)
        self._vision = vision
        self._state = PetState.DEFAULT_FLY
        self._win_w = 0
        self._win_h = 0
        self._pet_size = PET_BASE_SIZE  # base; actual render = PET_BASE_SIZE * scale
        self._pet_pos = QPoint(0, 0)
        # Last computed render scale; used for clamp + sizing consistency.
        self._last_scale: float = 1.0
        self._flight = FlightController(speed_px_per_s=vision.flight_speed_min)
        self._face_bbox: Optional[QRect] = None
        self._face_center: Optional[QPoint] = None
        self._last_render: Optional[RenderCommand] = None
        self._target_pick_counter = 0
        self._current_target: Optional[QPoint] = None
        # OPEN_PALM 内部 idle 轮播计数器
        self._open_palm_index = 0
        self._last_gesture_ts: float = 0.0
        self._last_gesture_change_ts = time.time()
        # 最近一次 MediaPipe 检测到的原始手势（"None" = 没检测到手）
        self._last_gesture_label: str = "None"

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

    def apply_settings(self, overrides: dict) -> None:
        """实时应用设置变更."""
        v = self._vision
        if "flight_speed_min" in overrides:
            v.flight_speed_min = overrides["flight_speed_min"]
            self._flight = FlightController(speed_px_per_s=v.flight_speed_min)
        if "flight_speed_max" in overrides:
            v.flight_speed_max = overrides["flight_speed_max"]
        if "face_tier_thresholds" in overrides:
            v.face_tier_thresholds = tuple(overrides["face_tier_thresholds"])
        for k in ("pet_size_near", "pet_size_mid", "pet_size_far"):
            if k in overrides:
                setattr(v, k, overrides[k])
        if "head_exclusion_padding" in overrides:
            v.head_exclusion_padding = overrides["head_exclusion_padding"]

    def update(self, signal: VisionSignal) -> None:
        """主线程 tick — 每帧调用一次（与 QTimer.timeout 绑定）."""
        self._last_gesture_label = signal.gesture_label or "None"
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

        # DRAG_PINCH 处理（spec §4.2 + §11 Q5）
        if self._state == PetState.DRAG_PINCH:
            if signal.gesture_label == "Open_Palm":
                # OPEN_PALM 是唯一退出条件（spec §11 Q5）
                self._state = PetState.OPEN_PALM
                self._last_gesture_change_ts = time.time()
            elif signal.pinch_active and signal.pinch_position:
                # 跟随 pinch 位置（用 scaled size 钳制，与实际渲染一致）
                actual_size = int(PET_BASE_SIZE * self._last_scale)
                self._pet_pos = signal.pinch_position - QPoint(actual_size // 2, actual_size // 2)
                self._pet_pos.setX(max(0, min(self._pet_pos.x(), self._win_w - actual_size)))
                self._pet_pos.setY(max(0, min(self._pet_pos.y(), self._win_h - actual_size)))
                # 其他手势：忽略，继续保持 DRAG_PINCH
            else:
                # pinch 物理释放但未比 OPEN_PALM → 保持 DRAG_PINCH 直到 OPEN_PALM
                # 此时不更新位置（停在原地），等 OPEN_PALM 或重新 pinch
                pass
        elif signal.pinch_active and signal.pinch_position:
            # 进入 DRAG_PINCH
            self._state = PetState.DRAG_PINCH
            actual_size = int(PET_BASE_SIZE * self._last_scale)
            self._pet_pos = signal.pinch_position - QPoint(actual_size // 2, actual_size // 2)
            self._pinch_pos_last = signal.pinch_position
            self._emit_render()  # HUD 立即变 "Pinch"
        else:
            # 手势处理（spec §4.2）
            if signal.gesture_label and signal.gesture_label != "None":
                self._handle_gesture(signal.gesture_label)
            else:
                self._check_gesture_timeout()

        # 触发 render（每帧 emit，方便 CameraPetWindow 接收）
        self._emit_render()

    def _handle_gesture(self, label: str) -> None:
        """根据 spec §4.2 状态转移表切换状态."""
        # OPEN_PALM 终止 pinch（spec §11 Q5）— P9 任务正式接入
        # 当前任务：仅处理 6 内置手势（不含 Pinch/Pinch exit 逻辑）
        target_state = {
            "Open_Palm": PetState.OPEN_PALM,
            "Thumb_Up": PetState.THUMB_UP,
            "Thumb_Down": PetState.THUMB_DOWN,
            "Victory": PetState.VICTORY,
            "Closed_Fist": PetState.FIST,
            "Pointing_Up": PetState.POINTING,
        }.get(label)
        if target_state is None:
            return
        if self._state in (PetState.DRAG_MOUSE, PetState.DRAG_PINCH):
            return  # 拖动期间忽略手势（pinch 例外由 OPEN_PALM 在 P9 接入）
        if self._state != target_state:
            self._state = target_state
            self._last_gesture_change_ts = time.time()

    def _check_gesture_timeout(self) -> None:
        """2s 未再检测到非默认手势 → 回 DEFAULT_FLY."""
        if self._state == PetState.DEFAULT_FLY or self._state in (PetState.DRAG_MOUSE, PetState.DRAG_PINCH):
            return
        elapsed = time.time() - self._last_gesture_change_ts
        if elapsed >= self._vision.gesture_hold_timeout:
            self._state = PetState.DEFAULT_FLY

    # ---- DEFAULT_FLY ----
    def _tick_default_fly(self) -> None:
        if not self._face_center or not self._face_bbox:
            # 无脸：小幅度随机漂移（不让桌宠完全静止，看着更"活"）
            self._drift_without_face()
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

    def _drift_without_face(self) -> None:
        """无脸时随机漂移：选一个窗口内的随机目标，慢速移动过去。"""
        import random
        if self._win_w <= 0 or self._win_h <= 0:
            return
        if not self._current_target or FlightController.arrived(self._pet_pos, self._current_target):
            margin = max(40, self._pet_size)
            self._current_target = QPoint(
                random.randint(margin, max(margin + 1, self._win_w - self._pet_size - margin)),
                random.randint(margin, max(margin + 1, self._win_h - self._pet_size - margin)),
            )
        now = time.time()
        if not hasattr(self, "_last_tick_ts"):
            self._last_tick_ts = now
        dt = max(0.001, now - self._last_tick_ts)
        self._last_tick_ts = now
        # 用较慢速度（flight_speed_min）漂移
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
        self._last_scale = scale

        gif = self._gif_for_state()
        cmd = RenderCommand(position=self._pet_pos, gif_path=gif, scale=scale)
        self._last_render = cmd
        self.render_command.emit(cmd.position, cmd.gif_path, cmd.scale)
        # HUD：DEFAULT_FLY 时若 MediaPipe 已识别到手势，显示该手势标签（用户能立即看到识别在工作）
        # 否则保持 "—" 表示无活动
        face_mark = "Face:✓" if self._face_bbox else "Face:✗"
        hand_mark = "Hand:✓" if self._last_gesture_label and self._last_gesture_label != "None" else "Hand:✗"
        status_line = f"{face_mark}  {hand_mark}"

        if self._state == PetState.DEFAULT_FLY:
            gesture_line = self._last_gesture_label if (self._last_gesture_label and self._last_gesture_label != "None") else "—"
        else:
            gesture_line = {
                PetState.OPEN_PALM: "Open_Palm",
                PetState.THUMB_UP: "Thumb_Up",
                PetState.THUMB_DOWN: "Thumb_Down",
                PetState.VICTORY: "Victory",
                PetState.FIST: "Closed_Fist",
                PetState.POINTING: "Pointing_Up",
                PetState.DRAG_MOUSE: "(drag)",
                PetState.DRAG_PINCH: "Pinch",
            }.get(self._state, "?")
        self.hud_update.emit(f"{gesture_line}\n{status_line}")
        self.audio_command.emit(self._state.value, {"loop": True})

    def start_mouse_drag(self) -> None:
        """PetOverlay mousePressEvent 调用."""
        if self._state == PetState.DRAG_PINCH:
            return  # pinch 优先
        self._state = PetState.DRAG_MOUSE
        # 关键：立即 emit render 让 drag.gif 出现在点击瞬间（不等 mouseMove）
        self._emit_render()

    def update_mouse_drag(self, pos: QPoint) -> None:
        """PetOverlay mouseMoveEvent 调用."""
        if self._state != PetState.DRAG_MOUSE:
            return
        self._pet_pos = pos
        # 钳制到窗口内（用 scaled size 与实际渲染一致）
        actual_size = int(PET_BASE_SIZE * self._last_scale)
        self._pet_pos.setX(max(0, min(self._pet_pos.x(), self._win_w - actual_size)))
        self._pet_pos.setY(max(0, min(self._pet_pos.y(), self._win_h - actual_size)))
        # 关键：发 render_command 让桌宠视觉跟随光标
        self._emit_render()

    def end_mouse_drag(self) -> None:
        """PetOverlay mouseReleaseEvent 调用."""
        if self._state != PetState.DRAG_MOUSE:
            return
        self._state = PetState.DEFAULT_FLY
        # fly-back 目标：当前 face 位置（让桌宠松手后飞回头部附近）
        if self._face_center and self._face_bbox:
            r = max(self._face_bbox.width(), self._face_bbox.height()) // 2 + 80
            self._current_target = QPoint(
                self._face_center.x() + r,
                self._face_center.y(),
            )
            self._target_pick_counter = 0

    def _gif_for_state(self) -> str:
        if self._state == PetState.OPEN_PALM:
            # 轮播 idle1~4
            now = time.time()
            idx = int(now / 3) % len(OPEN_PALM_GIFS)  # 每 3s 切一张
            return OPEN_PALM_GIFS[idx]
        if self._state == PetState.DRAG_MOUSE or self._state == PetState.DRAG_PINCH:
            return _GIF_DRAG
        # 用 GestureMapper 查表（None / Thumb_Up / Thumb_Down / Victory / FIST / POINTING）
        # 用 _state.value 反查
        label_for_mapper = {
            PetState.DEFAULT_FLY: "None",
            PetState.THUMB_UP: "Thumb_Up",
            PetState.THUMB_DOWN: "Thumb_Down",
            PetState.VICTORY: "Victory",
            PetState.FIST: "Closed_Fist",
            PetState.POINTING: "Pointing_Up",
        }.get(self._state, "None")
        return gesture_lookup(label_for_mapper).gif
