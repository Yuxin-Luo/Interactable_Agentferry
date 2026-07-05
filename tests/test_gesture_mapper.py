"""Tests for GestureMapper (spec §4.3)."""
from src.pet.gesture_mapper import lookup, GESTURE_ACTIONS


def test_lookup_known_labels():
    for label in ("Open_Palm", "Thumb_Up", "Thumb_Down", "Victory",
                  "Closed_Fist", "Pointing_Up", "Pinch"):
        assert lookup(label) is not None


def test_lookup_default_fly():
    a = lookup("None")
    assert a.gif == "assets/ameath/gifs/move.gif"
    assert a.loop is True
    assert a.music is False


def test_lookup_victory_plays_music():
    a = lookup("Victory")
    assert a.music is True
    assert a.gif == "assets/ameath/gifs/ameath.gif"


def test_lookup_pinch_uses_drag_gif():
    a = lookup("Pinch")
    assert a.gif == "assets/ameath/gifs/drag.gif"


def test_lookup_unknown_label_returns_default():
    a = lookup("SomeNewGesture")
    assert a.gif == "assets/ameath/gifs/move.gif"
