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