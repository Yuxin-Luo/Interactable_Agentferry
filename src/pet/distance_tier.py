"""Face distance tier from face bbox width (spec §5.3 + §4.1 DEFAULT_FLY)."""
from __future__ import annotations
from typing import Tuple


def compute_tier(
    bbox_w: int,
    thresholds: Tuple[int, int] = (80, 160),
    sizes: Tuple[float, float, float] = (1.5, 1.0, 0.6),
) -> Tuple[str, float]:
    """Map face bbox width to (tier, scale).

    Args:
        bbox_w: face bounding box width in pixels (0 = no face).
        thresholds: (mid_max, near_min). bbox_w >= near_min → near.
        sizes: (near, mid, far) pet scales.

    Returns:
        ("near"|"mid"|"far", scale).
    """
    mid_max, near_min = thresholds
    near_scale, mid_scale, far_scale = sizes
    if bbox_w >= near_min:
        return ("near", near_scale)
    if bbox_w >= mid_max:
        return ("mid", mid_scale)
    return ("far", far_scale)
