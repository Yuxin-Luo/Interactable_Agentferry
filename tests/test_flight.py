"""Tests for FlightController (spec §3.1 flight animation)."""
from PyQt6.QtCore import QPoint
from src.pet.flight import FlightController


def test_step_towards_target():
    fc = FlightController(speed_px_per_s=100)
    new = fc.step(QPoint(0, 0), QPoint(100, 0), dt=0.5)
    assert new == QPoint(50, 0)


def test_step_overshoot_clamped():
    fc = FlightController(speed_px_per_s=100)
    new = fc.step(QPoint(0, 0), QPoint(30, 0), dt=0.5)
    assert new == QPoint(30, 0)  # 不能超出 target


def test_step_diagonal():
    fc = FlightController(speed_px_per_s=100)
    new = fc.step(QPoint(0, 0), QPoint(100, 100), dt=0.5)
    # 距离 141.42, 速度 100, 0.5s 走 50px → 各走 35.36
    assert abs(new.x() - 35) < 2
    assert abs(new.y() - 35) < 2


def test_arrived_within_tolerance():
    fc = FlightController(speed_px_per_s=100)
    assert fc.arrived(QPoint(100, 100), QPoint(101, 100))
    assert not fc.arrived(QPoint(100, 100), QPoint(110, 100))
