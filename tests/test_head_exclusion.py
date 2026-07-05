"""Tests for HeadExclusionZone (spec §3.1 + §6)."""
from PyQt6.QtCore import QPoint, QRect
from src.pet.head_exclusion import HeadExclusionZone


def test_contains_inside():
    """bbox (100,100,200,200) padding=0.2 → exclusion (80,80,240,240)."""
    z = HeadExclusionZone(QRect(100, 100, 200, 200), padding_ratio=0.2)
    assert z.contains(QPoint(200, 200))  # 中心


def test_contains_outside():
    z = HeadExclusionZone(QRect(100, 100, 200, 200), padding_ratio=0.2)
    assert not z.contains(QPoint(500, 500))


def test_contains_in_padding_band():
    """padding=0.2 → 外扩 40px，bbox 边缘外 30px 仍在排除区."""
    z = HeadExclusionZone(QRect(100, 100, 200, 200), padding_ratio=0.2)
    # bbox 右边界 x=300, 排除区右边界 x=300 + 40 = 340
    assert z.contains(QPoint(330, 200))


def test_find_safe_target_first_valid():
    z = HeadExclusionZone(QRect(100, 100, 200, 200), padding_ratio=0.2)
    cands = [QPoint(500, 500), QPoint(600, 600), QPoint(700, 700)]
    assert z.find_safe_target(QPoint(0, 0), cands) == QPoint(500, 500)


def test_find_safe_target_all_excluded_returns_preferred():
    z = HeadExclusionZone(QRect(100, 100, 200, 200), padding_ratio=0.2)
    cands = [QPoint(200, 200), QPoint(300, 200), QPoint(150, 150)]
    assert z.find_safe_target(QPoint(800, 800), cands) == QPoint(800, 800)
