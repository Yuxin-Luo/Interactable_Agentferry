from __future__ import annotations
import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional


@dataclass
class CodeCli:
    base_url: str = "https://api.anthropic.com"
    api_key: str = ""
    model: str = "claude-sonnet-5"


@dataclass
class ChatApi:
    base_url: str = "https://api.anthropic.com"
    api_key: str = ""
    model: str = "claude-haiku-4-5-20251001"


@dataclass
class SafeZone:
    name: str
    path: str
    default: bool = False

    def is_relative_to_zone(self, p: Path) -> bool:
        """Check if path p is inside this safe zone (blocks traversal attacks)."""
        try:
            return Path(p).resolve().is_relative_to(Path(self.path).resolve())
        except (OSError, ValueError):
            return False


@dataclass
class Sound:
    """Voice + music playback settings (see dev-doc/11)."""
    voice_enabled: bool = True
    music_enabled: bool = True
    # How often (seconds) the IDLE state cycles between idle1~idle4.gif.
    idle_rotation_seconds: int = 15
    # After entering IDLE for this many minutes, play ONE random mp3
    # one-shot.  Music does not loop — it's a passive presence cue.
    music_interval_minutes: int = 5
    # 0..100, applied to QAudioOutput.setVolume().
    voice_volume: int = 80
    music_volume: int = 60


@dataclass
class CcConfig:
    """Claude Code sub-config — see dev-doc/20 §3.5 + makocode SAFE_TOOLS.

    safe_tools: extra tools (beyond the strict default `{Read, Glob, Grep, LS}`)
    to auto-allow without prompting.  Anything side-effectful (Write/Edit/Copy/
    Delete/Bash/...) MUST NOT be added here — by policy those always prompt.
    """
    safe_tools: List[str] = field(default_factory=list)


@dataclass
class VisionSettings:
    """Camera/vision pipeline configuration (see dev_doc/3-design §5.3)."""
    cam_resolution: tuple = (1280, 720)
    cam_fps: int = 30
    cam_device_index: int = 0
    flight_speed_min: int = 50       # px/s
    flight_speed_max: int = 300      # px/s
    gesture_hold_timeout: float = 2.0  # s
    face_tier_thresholds: tuple = (80, 160)  # (mid_max, near_min) face bbox width px
    pet_size_near: float = 1.5
    pet_size_mid: float = 1.0
    pet_size_far: float = 0.6
    head_exclusion_padding: float = 0.2  # face bbox 外扩比例
    pinch_distance_threshold: float = 0.05  # thumb_tip ↔ index_tip 归一化距离
    pinch_hold_frames: int = 3       # 连续多少帧确认 pinch
    settings_persistence_path: str = "~/.config/interactable_agentferry/settings.json"


@dataclass
class AppSettings:
    code_cli: CodeCli = field(default_factory=CodeCli)
    chat_api: ChatApi = field(default_factory=ChatApi)
    safe_zones: List[SafeZone] = field(default_factory=list)
    sound: Sound = field(default_factory=Sound)
    cc: CcConfig = field(default_factory=CcConfig)
    vision: VisionSettings = field(default_factory=VisionSettings)


def load_settings(path: Path) -> AppSettings:
    if not path.exists():
        return AppSettings()
    data = json.loads(path.read_text())
    return AppSettings(
        code_cli=CodeCli(**data.get("code_cli", {})),
        chat_api=ChatApi(**data.get("chat_api", {})),
        safe_zones=[SafeZone(**z) for z in data.get("safe_zones", [])],
        sound=Sound(**data.get("sound", {})),
        cc=CcConfig(**data.get("cc", {})),
    )


def save_settings(app: AppSettings, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(app), indent=2))
