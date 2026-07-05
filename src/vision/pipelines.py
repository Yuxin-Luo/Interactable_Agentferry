"""Vision pipelines: FaceTracker, GestureRecognizer, PinchDetector (spec §3.2).

每个 pipeline 暴露纯函数式 API，MediaPipe Tasks 推理结果作为入参传入。
MediaPipe Tasks 对象本身的初始化在 VisionWorker 中完成（需要文件路径 + frame）。
"""
from __future__ import annotations

from collections import deque
from typing import Optional, Tuple

from PyQt6.QtCore import QPoint, QSize


# ============== FaceTracker ==============

def landmarks_to_bbox_and_center(
    landmarks, frame_w: int, frame_h: int
) -> Tuple[QPoint, QSize, int]:
    """从 468 个 normalized landmarks 计算 (center, bbox_size, count).

    landmarks: sequence of objects with .x/.y normalized [0,1].
    """
    xs = [lm.x for lm in landmarks]
    ys = [lm.y for lm in landmarks]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx = (min_x + max_x) / 2 * frame_w
    cy = (min_y + max_y) / 2 * frame_h
    bw = (max_x - min_x) * frame_w
    bh = (max_y - min_y) * frame_h
    return (QPoint(int(round(cx)), int(round(cy))), QSize(int(round(bw)), int(round(bh))), len(landmarks))


class FaceTracker:
    """从 FaceLandmarker 输出提取 face center + bbox size，EMA 平滑."""

    def __init__(self, ema_alpha: float = 0.5):
        self._alpha = ema_alpha
        self._smoothed_center: Optional[QPoint] = None
        self._smoothed_size: Optional[QSize] = None

    def reset(self) -> None:
        self._smoothed_center = None
        self._smoothed_size = None

    def update(
        self, landmarks, frame_w: int, frame_h: int
    ) -> Tuple[Optional[QPoint], Optional[QSize]]:
        """更新一次，返回 (smoothed_center, smoothed_size) 或 (None, None) 当无 landmarks."""
        if not landmarks:
            # 无检测：返回最近一次平滑值（不立即归零，避免抖）
            return (self._smoothed_center, self._smoothed_size)

        center, size, _ = landmarks_to_bbox_and_center(landmarks, frame_w, frame_h)
        if self._smoothed_center is None:
            self._smoothed_center = center
            self._smoothed_size = size
        else:
            sx = self._alpha * center.x() + (1 - self._alpha) * self._smoothed_center.x()
            sy = self._alpha * center.y() + (1 - self._alpha) * self._smoothed_center.y()
            sw = self._alpha * size.width() + (1 - self._alpha) * self._smoothed_size.width()
            sh = self._alpha * size.height() + (1 - self._alpha) * self._smoothed_size.height()
            self._smoothed_center = QPoint(int(sx), int(sy))
            self._smoothed_size = QSize(int(sw), int(sh))
        return (self._smoothed_center, self._smoothed_size)
