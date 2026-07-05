"""头部排除区（spec §3.1 + §6）: 桌宠默认飞行目标不可与人脸 bbox 重叠."""
from __future__ import annotations
from typing import List
from PyQt6.QtCore import QPoint, QRect


class HeadExclusionZone:
    def __init__(self, face_bbox: QRect, padding_ratio: float = 0.2):
        self._bbox = face_bbox
        pad_x = int(face_bbox.width() * padding_ratio)
        pad_y = int(face_bbox.height() * padding_ratio)
        self._exclusion = face_bbox.adjusted(-pad_x, -pad_y, pad_x, pad_y)

    def contains(self, point: QPoint) -> bool:
        return self._exclusion.contains(point)

    def find_safe_target(self, preferred: QPoint, candidates: List[QPoint]) -> QPoint:
        for c in candidates:
            if not self.contains(c):
                return c
        return preferred
