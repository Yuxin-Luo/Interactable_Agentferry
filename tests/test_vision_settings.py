"""Tests for VisionSettings dataclass."""
from src.config.settings import VisionSettings, AppSettings


def test_vision_settings_defaults():
    v = VisionSettings()
    assert v.cam_resolution == (1280, 720)
    assert v.cam_fps == 30
    assert v.cam_device_index == 0
    assert v.flight_speed_min == 50
    assert v.flight_speed_max == 300
    assert v.gesture_hold_timeout == 2.0
    assert v.face_tier_thresholds == (80, 160)
    assert v.pet_size_near == 1.5
    assert v.pet_size_mid == 1.0
    assert v.pet_size_far == 0.6
    assert v.head_exclusion_padding == 0.2
    assert v.pinch_distance_threshold == 0.05
    assert v.pinch_hold_frames == 3
    assert v.settings_persistence_path == "~/.config/interactable_agentferry/settings.json"


def test_app_settings_contains_vision():
    s = AppSettings()
    assert hasattr(s, "vision")
    assert isinstance(s.vision, VisionSettings)
