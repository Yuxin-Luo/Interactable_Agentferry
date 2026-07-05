"""Tests for SettingsDialog UI."""
import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox

from src.config.settings import VisionSettings
from src.pet.settings_store import SettingsStore
from src.pet.settings_dialog import SettingsDialog


@pytest.fixture
def vision():
    """Provide default VisionSettings."""
    return VisionSettings()


@pytest.fixture
def store(tmp_path):
    """Provide SettingsStore with temp path."""
    return SettingsStore(path=tmp_path / "settings.json")


def test_dialog_instantiates(vision, store, qtbot):
    """Dialog creates without error."""
    dialog = SettingsDialog(vision, store)
    assert dialog is not None
    assert dialog.windowTitle() == "Settings"


def test_dialog_loads_current_values(vision, store, qtbot):
    """Widgets are populated with vision defaults on open."""
    dialog = SettingsDialog(vision, store)
    assert dialog.check_flip.isChecked() == vision.flip_horizontal
    assert dialog.slider_speed_min.value() == vision.flight_speed_min
    assert dialog.slider_speed_max.value() == vision.flight_speed_max
    assert dialog.spin_tier_mid.value() == vision.face_tier_thresholds[0]
    assert dialog.spin_tier_near.value() == vision.face_tier_thresholds[1]
    assert dialog.spin_size_near.value() == int(vision.pet_size_near * 100)
    assert dialog.spin_size_mid.value() == int(vision.pet_size_mid * 100)
    assert dialog.spin_size_far.value() == int(vision.pet_size_far * 100)


def test_save_emits_signal_and_accepts(vision, store, qtbot):
    """Save button emits settings_changed with correct dict and accepts."""
    dialog = SettingsDialog(vision, store)
    captured = []

    def handler(d):
        captured.append(d)

    dialog.settings_changed.connect(handler)

    # Change a value via spinbox
    dialog.spin_speed_min.setValue(200)
    dialog.spin_tier_mid.setValue(90)
    dialog.spin_size_near.setValue(180)
    dialog.check_flip.setChecked(False)

    # Click Save
    qtbot.mouseClick(
        dialog.findChild(QDialogButtonBox)
        .button(QDialogButtonBox.StandardButton.Save),
        Qt.MouseButton.LeftButton,
    )

    assert len(captured) == 1
    ov = captured[0]
    assert ov["flight_speed_min"] == 200
    assert ov["face_tier_thresholds"] == [90, vision.face_tier_thresholds[1]]
    assert ov["pet_size_near"] == 1.8
    assert ov["flip_horizontal"] is False


def test_cancel_does_not_emit_signal(vision, store, qtbot):
    """Cancel button rejects without emitting signal."""
    dialog = SettingsDialog(vision, store)
    emitted = []

    def fail(d):
        emitted.append(d)

    dialog.settings_changed.connect(fail)

    dialog.spin_speed_min.setValue(999)
    qtbot.mouseClick(
        dialog.findChild(QDialogButtonBox)
        .button(QDialogButtonBox.StandardButton.Cancel),
        Qt.MouseButton.LeftButton,
    )

    assert len(emitted) == 0


def test_slider_spin_sync_min(vision, store, qtbot):
    """Min speed slider and spinbox stay synchronized."""
    dialog = SettingsDialog(vision, store)
    dialog.slider_speed_min.setValue(250)
    assert dialog.spin_speed_min.value() == 250
    dialog.spin_speed_min.setValue(300)
    assert dialog.slider_speed_min.value() == 300


def test_slider_spin_sync_max(vision, store, qtbot):
    """Max speed slider and spinbox stay synchronized."""
    dialog = SettingsDialog(vision, store)
    dialog.slider_speed_max.setValue(800)
    assert dialog.spin_speed_max.value() == 800
    dialog.spin_speed_max.setValue(900)
    assert dialog.slider_speed_max.value() == 900
