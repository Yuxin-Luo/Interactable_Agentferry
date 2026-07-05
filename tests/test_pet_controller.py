"""Tests for PetController state machine (spec §4)."""
from PyQt6.QtCore import QPoint, QSize
from src.config.settings import VisionSettings
from src.vision.worker import VisionSignal
from src.pet.controller import PetController, PetState


def _make_controller():
    v = VisionSettings()
    c = PetController(vision=v)
    c.set_window_size(640, 360)
    return c


def test_initial_state_default_fly():
    c = _make_controller()
    assert c.state == PetState.DEFAULT_FLY


def test_update_with_no_face_idle():
    """无 face → DEFAULT_FLY 保持，render_command 不必发（safe default）."""
    c = _make_controller()
    c.update(VisionSignal(face_center=None, face_bbox_size=None))


def test_update_with_face_renders_command(qtbot):
    c = _make_controller()
    c.update(VisionSignal(
        face_center=QPoint(640, 360), face_bbox_size=QSize(120, 120),
    ))
    # update 内会直接调用 _emit_render_command → 同步发 signal
    # 用 last_render 属性检查
    assert c.last_render is not None
    assert c.last_render.scale == 1.0  # mid tier


def test_distance_tier_near():
    c = _make_controller()
    c.update(VisionSignal(
        face_center=QPoint(640, 360), face_bbox_size=QSize(200, 200),
    ))
    assert c.last_render.scale == 1.5  # near


def test_distance_tier_far():
    c = _make_controller()
    c.update(VisionSignal(
        face_center=QPoint(640, 360), face_bbox_size=QSize(40, 40),
    ))
    assert c.last_render.scale == 0.6  # far


def test_gesture_open_palm_transitions(qtbot):
    c = _make_controller()
    c.update(VisionSignal(gesture_label="Open_Palm"))
    assert c.state == PetState.OPEN_PALM


def test_gesture_thumb_up_transitions(qtbot):
    c = _make_controller()
    c.update(VisionSignal(gesture_label="Thumb_Up"))
    assert c.state == PetState.THUMB_UP


def test_gesture_none_returns_to_default(qtbot):
    c = _make_controller()
    c.update(VisionSignal(gesture_label="Thumb_Up"))
    assert c.state == PetState.THUMB_UP
    # 模拟 2s 超时（用 monotonic time）
    import time
    c._last_gesture_change_ts = time.time() - 3.0
    c.update(VisionSignal(gesture_label="None"))
    assert c.state == PetState.DEFAULT_FLY


def test_gesture_render_uses_mapper(qtbot):
    c = _make_controller()
    c.update(VisionSignal(gesture_label="Thumb_Up"))
    assert "screen1.gif" in c.last_render.gif_path


def test_drag_states_not_entered_by_gesture(qtbot):
    """DRAG_MOUSE/DRAG_PINCH 仅由鼠标/捏合事件触发，gesture_label=Pinch 不直接进入."""
    c = _make_controller()
    c.update(VisionSignal(gesture_label="Pinch"))
    # Pinch 由 PinchDetector (VisionSignal.pinch_active) 触发，单独的 signal 字段
    # 此处 gesture_label="Pinch" 仅表示该帧被识别为 pinch-like；实际进入 DRAG_PINCH 在 P4 任务
    # 故状态仍是 DEFAULT_FLY
    assert c.state == PetState.DEFAULT_FLY