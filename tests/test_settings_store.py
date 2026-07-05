"""Tests for SettingsStore JSON persistence."""
import json
from pathlib import Path
import tempfile

from src.pet.settings_store import SettingsStore


def test_load_returns_empty_when_missing(tmp_path):
    s = SettingsStore(path=tmp_path / "nope.json")
    assert s.load() == {}


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    s = SettingsStore(path=path)
    s.save({"flight_speed_min": 100, "pet_size_near": 1.8})
    loaded = s.load()
    assert loaded["flight_speed_min"] == 100
    assert loaded["pet_size_near"] == 1.8


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "settings.json"
    s = SettingsStore(path=path)
    s.save({"flight_speed_min": 75})
    assert path.exists()
    assert json.loads(path.read_text())["flight_speed_min"] == 75


def test_save_only_persists_provided_keys(tmp_path):
    """save(overrides) 不应覆盖未指定的字段（merge 语义）."""
    path = tmp_path / "settings.json"
    s = SettingsStore(path=path)
    s.save({"flight_speed_min": 100})
    s.save({"pet_size_near": 2.0})
    loaded = s.load()
    assert loaded["flight_speed_min"] == 100  # 保留
    assert loaded["pet_size_near"] == 2.0
