"""Letterbox coordinate mapping (spec §11 Q4).

Camera frame is letterboxed into window: keep aspect ratio, center, pad with
"black bars" on the longer side. Both forward and inverse mapping.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple


@dataclass
class LetterboxMap:
    cam_size: Tuple[int, int]  # (cw, ch)
    win_size: Tuple[int, int]  # (ww, wh)

    def __post_init__(self):
        cw, ch = self.cam_size
        ww, wh = self.win_size
        self.scale: float = min(ww / cw, wh / ch)
        self.offset_x: float = (ww - cw * self.scale) / 2
        self.offset_y: float = (wh - ch * self.scale) / 2

    def cam_to_win(self, pt_cam: Tuple[float, float]) -> Tuple[float, float]:
        x, y = pt_cam
        return (x * self.scale + self.offset_x, y * self.scale + self.offset_y)

    def win_to_cam(self, pt_win: Tuple[float, float]) -> Tuple[float, float]:
        x, y = pt_win
        return ((x - self.offset_x) / self.scale, (y - self.offset_y) / self.scale)

    def cam_rect_to_win(
        self, rect_cam: Tuple[float, float, float, float]
    ) -> Tuple[float, float, float, float]:
        x, y, w, h = rect_cam
        xw, yw = self.cam_to_win((x, y))
        return (xw, yw, w * self.scale, h * self.scale)
