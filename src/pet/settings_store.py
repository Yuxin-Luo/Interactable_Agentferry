"""JSON 持久化存储（spec §2.1）."""
from __future__ import annotations
import json
from pathlib import Path


DEFAULT_PATH = Path.home() / ".config" / "interactable_agentferry" / "settings.json"


class SettingsStore:
    """持久化 VisionSettings 字段到 JSON."""

    def __init__(self, path: Path | None = None):
        self._path = path if path is not None else DEFAULT_PATH

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, overrides: dict) -> None:
        current = self.load()
        current.update(overrides)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(current, indent=2))
