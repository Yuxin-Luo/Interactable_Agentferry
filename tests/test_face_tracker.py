"""Tests for FaceTracker post-processing (bbox extraction + EMA smoothing)."""
from PyQt6.QtCore import QPoint, QSize
from src.vision.pipelines import FaceTracker, landmarks_to_bbox_and_center


class FakeLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def _gen_landmarks(cx_norm: float, cy_norm: float, half_w_norm: float, half_h_norm: float):
    """生成 468 个 normalized landmarks，bbox 中心 (cx,cy) 半宽 half_w 半高 half_h."""
    lms = []
    for i in range(468):
        # 简化：仅前 4 个点定义 bbox，其他点全部填中心
        if i == 0:
            lms.append(FakeLandmark(cx_norm - half_w_norm, cy_norm - half_h_norm))
        elif i == 1:
            lms.append(FakeLandmark(cx_norm + half_w_norm, cy_norm - half_h_norm))
        elif i == 2:
            lms.append(FakeLandmark(cx_norm + half_w_norm, cy_norm + half_h_norm))
        elif i == 3:
            lms.append(FakeLandmark(cx_norm - half_w_norm, cy_norm + half_h_norm))
        else:
            lms.append(FakeLandmark(cx_norm, cy_norm))
    return lms


def test_landmarks_to_bbox_center():
    lms = _gen_landmarks(cx_norm=0.5, cy_norm=0.5, half_w_norm=0.2, half_h_norm=0.15)
    center, size, count = landmarks_to_bbox_and_center(lms, frame_w=1280, frame_h=720)
    assert count == 468
    assert center == QPoint(640, 360)
    assert size == QSize(int(0.4 * 1280), int(0.3 * 720))  # (512, 216)


def test_face_tracker_first_update():
    ft = FaceTracker(ema_alpha=0.5)
    lms = _gen_landmarks(0.5, 0.5, 0.1, 0.1)
    center, size = ft.update(lms, frame_w=1280, frame_h=720)
    assert center == QPoint(640, 360)
    assert size == QSize(int(0.2 * 1280), int(0.2 * 720))  # 256x144


def test_face_tracker_ema_smoothing():
    """连续 2 次 update：第二次的中心应被第一次平滑影响."""
    ft = FaceTracker(ema_alpha=0.5)
    lms1 = _gen_landmarks(0.5, 0.5, 0.1, 0.1)
    lms2 = _gen_landmarks(0.7, 0.5, 0.1, 0.1)  # 中心移动到 (0.7, 0.5)
    ft.update(lms1, frame_w=1280, frame_h=720)
    center2, _ = ft.update(lms2, frame_w=1280, frame_h=720)
    # EMA: 0.5*640 + 0.5*896 = 768
    assert center2 == QPoint(768, 360)


def test_face_tracker_reset():
    ft = FaceTracker(ema_alpha=0.5)
    lms = _gen_landmarks(0.5, 0.5, 0.1, 0.1)
    ft.update(lms, frame_w=1280, frame_h=720)
    ft.reset()
    # 重置后第一次 update 应该等于原始值（无 EMA 衰减）
    center, _ = ft.update(lms, frame_w=1280, frame_h=720)
    assert center == QPoint(640, 360)
