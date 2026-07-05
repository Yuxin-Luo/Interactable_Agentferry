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


def test_pinch_other_gesture_keeps_drag(qtbot):
    """spec §11 Q5: DRAG_PINCH 期间其他手势不退出."""
    c = _make_controller()
    # 进入 DRAG_PINCH
    c.update(VisionSignal(pinch_active=True, pinch_position=QPoint(100, 100)))
    assert c.state == PetState.DRAG_PINCH
    # 其他手势（Thumb_Up）→ 仍保持 DRAG_PINCH
    c.update(VisionSignal(pinch_active=True, pinch_position=QPoint(150, 150), gesture_label="Thumb_Up"))
    assert c.state == PetState.DRAG_PINCH


def test_pinch_open_palm_terminates(qtbot):
    """spec §11 Q5: OPEN_PALM 是唯一退出条件."""
    c = _make_controller()
    c.update(VisionSignal(pinch_active=True, pinch_position=QPoint(100, 100)))
    assert c.state == PetState.DRAG_PINCH
    c.update(VisionSignal(pinch_active=True, pinch_position=QPoint(150, 150), gesture_label="Open_Palm"))
    assert c.state == PetState.OPEN_PALM


def test_hud_update_emits_gesture_label_not_state_value(qtbot):
    """T-25: hud_update signal payload must contain the user-facing gesture label string.

    Previously emitted state.value (e.g. "open_palm"). Now must emit the
    user-facing label from the spec mapping (e.g. "Open_Palm", "Thumb_Up").

    The HUD also includes a second line "Face:✓/✗ Hand:✓/✗" status, so we
    assert on the gesture line only (split on \n, take [0]).
    """
    c = _make_controller()
    emitted = []
    c.hud_update.connect(emitted.append)

    def gesture_line():
        return emitted[-1].split("\n", 1)[0]

    # DEFAULT_FLY → "—"
    c.update(VisionSignal(face_center=QPoint(640, 360), face_bbox_size=QSize(120, 120)))
    assert gesture_line() == "—", f"expected '—', got {gesture_line()!r}"

    # OPEN_PALM → "Open_Palm"
    c.update(VisionSignal(gesture_label="Open_Palm"))
    assert gesture_line() == "Open_Palm", f"expected 'Open_Palm', got {gesture_line()!r}"

    # THUMB_UP → "Thumb_Up"
    c.update(VisionSignal(gesture_label="Thumb_Up"))
    assert gesture_line() == "Thumb_Up", f"expected 'Thumb_Up', got {gesture_line()!r}"

    # THUMB_DOWN → "Thumb_Down"
    c.update(VisionSignal(gesture_label="Thumb_Down"))
    assert gesture_line() == "Thumb_Down", f"expected 'Thumb_Down', got {gesture_line()!r}"

    # VICTORY → "Victory"
    c.update(VisionSignal(gesture_label="Victory"))
    assert gesture_line() == "Victory", f"expected 'Victory', got {gesture_line()!r}"

    # FIST → "Closed_Fist"
    c.update(VisionSignal(gesture_label="Closed_Fist"))
    assert gesture_line() == "Closed_Fist", f"expected 'Closed_Fist', got {gesture_line()!r}"

    # POINTING → "Pointing_Up"
    c.update(VisionSignal(gesture_label="Pointing_Up"))
    assert gesture_line() == "Pointing_Up", f"expected 'Pointing_Up', got {gesture_line()!r}"


def test_hud_update_drag_states(qtbot):
    """T-25: drag states emit their drag label, not a state value.

    Mouse drag methods don't call _emit_render directly; they rely on the
    next update() tick to emit.  We simulate that with a no-op VisionSignal.
    """
    c = _make_controller()
    emitted = []
    c.hud_update.connect(emitted.append)

    def gesture_line():
        return emitted[-1].split("\n", 1)[0]

    # Enter DRAG_MOUSE via mouse drag; tick to trigger emit
    c.start_mouse_drag()
    c.update_mouse_drag(QPoint(200, 200))
    c.update(VisionSignal(face_center=None, face_bbox_size=None))
    assert gesture_line() == "(drag)", f"expected '(drag)', got {gesture_line()!r}"

    # Enter DRAG_PINCH via VisionSignal; tick already calls _emit_render
    c.update(VisionSignal(pinch_active=True, pinch_position=QPoint(100, 100)))
    assert gesture_line() == "Pinch", f"expected 'Pinch', got {gesture_line()!r}"


def test_apply_settings_updates_vision_fields():
    """T-28: apply_settings mutates live _vision fields."""
    v = VisionSettings()
    c = PetController(vision=v)
    c.set_window_size(640, 360)

    # Override flight_speed_min → should recreate _flight
    c.apply_settings({"flight_speed_min": 300})
    assert c._vision.flight_speed_min == 300
    assert c._flight._speed == 300

    # Override pet sizes
    c.apply_settings({"pet_size_near": 2.0, "pet_size_mid": 1.5, "pet_size_far": 0.5})
    assert c._vision.pet_size_near == 2.0
    assert c._vision.pet_size_mid == 1.5
    assert c._vision.pet_size_far == 0.5

    # Override tier thresholds
    c.apply_settings({"face_tier_thresholds": [50, 120]})
    assert c._vision.face_tier_thresholds == (50, 120)


def test_apply_settings_unknown_keys_do_not_crash():
    """T-28: unknown keys are silently ignored."""
    v = VisionSettings()
    c = PetController(vision=v)
    c.set_window_size(640, 360)
    c.apply_settings({"unknown_key": 123, "another": "foo"})  # must not raise


def test_apply_settings_updates_head_exclusion_padding():
    """head_exclusion_padding is forwarded to _vision and used by HeadExclusionZone."""
    v = VisionSettings()
    c = PetController(vision=v)
    c.set_window_size(640, 360)

    # Verify default value
    assert v.head_exclusion_padding == 0.2  # spec default

    # Override and check it propagates
    c.apply_settings({"head_exclusion_padding": 0.6})
    assert c._vision.head_exclusion_padding == 0.6


def test_render_command_signal_carries_three_positional_args(qtbot):
    """Regression test (dev_doc/6-debug-signal-sig-mismatch-2026-07-05):

    render_command MUST be (QPoint, str, float) so the slot
    CameraPetWindow.update_pet(position, gif_path, scale) matches.
    Mismatched signal/slot raises TypeError inside Qt dispatch → segfault.
    """
    v = VisionSettings()
    c = PetController(vision=v)
    c.set_window_size(640, 360)

    captured = []
    # Slot with exact (position, gif_path, scale) signature must accept the signal
    def slot(position, gif_path, scale):
        captured.append((position, gif_path, scale))

    c.render_command.connect(slot)
    c.update(VisionSignal(
        face_center=QPoint(640, 360), face_bbox_size=QSize(120, 120),
    ))

    assert len(captured) == 1
    pos, gif, scale = captured[0]
    assert isinstance(pos, QPoint)
    assert isinstance(gif, str) and gif.endswith(".gif")
    assert isinstance(scale, float)