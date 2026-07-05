"""Tests for GestureSmoother (spec §3.2 N-frame voting)."""
from src.pet.gesture_smoother import GestureSmoother


def test_initial_returns_none():
    s = GestureSmoother(window_size=5)
    assert s.update("Open_Palm") == "Open_Palm"  # 窗口不满直接返回


def test_window_majority():
    s = GestureSmoother(window_size=5)
    for _ in range(3):
        s.update("Open_Palm")
    s.update("Closed_Fist")  # 4 vs 1
    assert s.update("Closed_Fist") == "Open_Palm"  # 3 vs 2


def test_tie_keeps_recent():
    s = GestureSmoother(window_size=4)
    s.update("Open_Palm")
    s.update("Closed_Fist")
    s.update("Open_Palm")
    s.update("Closed_Fist")  # tie 2 vs 2，最近是 Closed_Fist
    assert s.update("Closed_Fist") == "Closed_Fist"


def test_window_slides():
    s = GestureSmoother(window_size=3)
    s.update("Open_Palm")
    s.update("Open_Palm")
    s.update("Open_Palm")  # window [Palm, Palm, Palm] → Palm
    s.update("Closed_Fist")  # window [Palm, Palm, Fist] → Palm
    s.update("Closed_Fist")  # window [Palm, Fist, Fist] → Fist
    assert s.update("Closed_Fist") == "Closed_Fist"


def test_reset():
    s = GestureSmoother(window_size=3)
    s.update("Open_Palm")
    s.reset()
    assert s.update("None") == "None"
