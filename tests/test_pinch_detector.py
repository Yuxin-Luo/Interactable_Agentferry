"""Tests for PinchDetector (spec §3.2 / §4.2)."""
from PyQt6.QtCore import QPoint
from src.vision.pipelines import PinchDetector


class FakeLM:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def _hand(thumb_tip, index_tip, w=0.05):
    """21 landmarks; thumb_tip @ index 4, index_tip @ index 8."""
    lms = []
    for i in range(21):
        if i == 4:
            lms.append(FakeLM(*thumb_tip))
        elif i == 8:
            lms.append(FakeLM(*index_tip))
        else:
            lms.append(FakeLM(0.5, 0.5))
    return lms


def test_no_pinch_when_far():
    pd = PinchDetector(distance_threshold=0.05, hold_frames=3)
    active, pt = pd.update(_hand((0.3, 0.5), (0.7, 0.5)), 1280, 720)
    assert active is False
    assert pt is None


def test_pinch_after_hold_frames():
    pd = PinchDetector(distance_threshold=0.05, hold_frames=3)
    h = _hand((0.5, 0.5), (0.52, 0.5))
    for _ in range(3):
        active, pt = pd.update(h, 1280, 720)
    assert active is True
    assert pt is not None


def test_pinch_resets_when_released():
    pd = PinchDetector(distance_threshold=0.05, hold_frames=3)
    h_close = _hand((0.5, 0.5), (0.52, 0.5))
    h_far = _hand((0.3, 0.5), (0.7, 0.5))
    for _ in range(3):
        pd.update(h_close, 1280, 720)
    pd.update(h_far, 1280, 720)
    pd.update(h_far, 1280, 720)
    active, _ = pd.update(h_far, 1280, 720)
    assert active is False


def test_pinch_position_is_midpoint():
    pd = PinchDetector(distance_threshold=0.05, hold_frames=2)
    h = _hand((0.4, 0.4), (0.6, 0.4))
    for _ in range(2):
        pd.update(h, 1280, 720)
    # midpoint normalized = (0.5, 0.4); in 1280x720 → (640, 288)
    # NOTE: original coords gave dist=0.2 > threshold=0.05 (pinch never activated).
    # Fixed to use (0.49, 0.4)-(0.51, 0.4): dist=0.02 < 0.05, midpoint=(640, 288).
    h_fixed = _hand((0.49, 0.4), (0.51, 0.4))
    for _ in range(2):
        pd.update(h_fixed, 1280, 720)
    _, pt = pd.update(h_fixed, 1280, 720)
    assert pt == QPoint(640, 288)
