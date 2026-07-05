"""直线飞行插值（spec §3.1 flight animation）."""
from __future__ import annotations
import math
from PyQt6.QtCore import QPoint


class FlightController:
    """以固定速度向 target 推进，clamp 不超过 target."""

    def __init__(self, speed_px_per_s: float):
        self._speed = float(speed_px_per_s)

    def step(self, cur: QPoint, target: QPoint, dt: float) -> QPoint:
        dx = target.x() - cur.x()
        dy = target.y() - cur.y()
        dist = math.hypot(dx, dy)
        max_step = self._speed * dt
        if dist <= max_step or dist == 0:
            return QPoint(target)
        ratio = max_step / dist
        return QPoint(int(cur.x() + dx * ratio), int(cur.y() + dy * ratio))

    @staticmethod
    def arrived(cur: QPoint, target: QPoint, tol: float = 2.0) -> bool:
        return math.hypot(target.x() - cur.x(), target.y() - cur.y()) <= tol
