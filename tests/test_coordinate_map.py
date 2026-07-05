"""Tests for letterbox coordinate mapping (spec §11 Q4)."""
from src.utils.coordinate_map import LetterboxMap


def test_cam_to_win_center():
    m = LetterboxMap(cam_size=(1280, 720), win_size=(640, 360))
    # 摄像头中心 (640, 360) → 窗口中心 (320, 180)（letterbox 全填充）
    assert m.cam_to_win((640, 360)) == (320, 180)


def test_cam_to_win_with_letterbox():
    """窗口比例不同 → 出现 letterbox 黑边."""
    m = LetterboxMap(cam_size=(1280, 720), win_size=(1920, 1080))
    # scale = min(1920/1280, 1080/720) = min(1.5, 1.5) = 1.5
    # offset_x = (1920 - 1280*1.5)/2 = 0
    # offset_y = 0
    assert m.cam_to_win((640, 360)) == (960, 540)


def test_win_to_cam_round_trip():
    m = LetterboxMap(cam_size=(1280, 720), win_size=(640, 360))
    p_cam = (320, 180)
    p_win = m.cam_to_win(p_cam)
    p_back = m.win_to_cam(p_win)
    assert abs(p_back[0] - p_cam[0]) < 1e-6
    assert abs(p_back[1] - p_cam[1]) < 1e-6


def test_cam_rect_to_win():
    """人脸 bbox 在摄像头 (100, 100, 200, 200) → 窗口 (50, 50, 100, 100) under 0.5x scale."""
    m = LetterboxMap(cam_size=(1280, 720), win_size=(640, 360))
    out = m.cam_rect_to_win((100, 100, 200, 200))
    assert out == (50.0, 50.0, 100.0, 100.0)


def test_aspect_mismatch_letterbox_side():
    """窗口更宽 → 上下黑边."""
    m = LetterboxMap(cam_size=(1280, 720), win_size=(1280, 200))
    # scale = min(1.0, 200/720) = 200/720 ≈ 0.2778
    # offset_x = 0
    # offset_y = (200 - 720 * 0.2778)/2 = (200 - 200)/2 = 0
    assert abs(m.cam_to_win((640, 360))[0] - 640) < 1e-6
    assert abs(m.cam_to_win((640, 360))[1] - 100) < 1e-6
