from typing import Callable, List
from pathlib import Path

from PyQt6.QtWidgets import QMenu

ACTION_KEYS = {
    "open_chat": "💬 打开对话",
    "safe_zone": "📁 安全区设置",
    "cc_task": "🔌 Claude Code 任务",
    "toggle_mute": "🔊 静音",
    "settings": "⚙ 设置",
    "view_log": "📋 查看日志",
    "quit": "⏻ 退出",
}

# Right-click "🎬 动作" submenu — fixed-action one-shots.  See
# dev-doc/12 §3 for the GIF/voice pairings.
PLAY_ACTION_LABELS = {
    "idle1":  "🅰  idle1（叹气左顾右盼）",
    "idle2":  "🅱  idle2（睁大眼睛）",
    "idle3":  "🅲  idle3（举手跳跃）",
    "idle4":  "🅳  idle4（双手欢呼）",
    "drag":   "🪽  drag（扑动翅膀）",
    "ameath": "🕶  ameath（墨镜点头）",
}

_MAX_MUSIC_ITEMS = 15  # dev-doc/17 §2.2 hard limit


def build_music_submenu(
    tracks: List[Path],
    on_action: Callable[[str], None],
    parent_menu: QMenu,
) -> QMenu:
    """Build a '🎵 选曲' submenu from the available music tracks.

    - Scans `tracks` (sorted, stem display).
    - Max 15 items (dev-doc/17 §2.2).
    - Each item triggers `on_action("play_music:<filename>")`.
    - If tracks is empty, returns a placeholder "暂无" submenu.
    - parent_menu is passed to ensure proper Qt parenting.
    """
    sub = QMenu(parent_menu)
    sub.setTitle("🎵 选曲")
    if not tracks:
        a = sub.addAction("暂无")
        a.setEnabled(False)
        return sub

    for path in sorted(tracks)[:_MAX_MUSIC_ITEMS]:
        label = f"🎵 {path.stem}"
        a = sub.addAction(label)
        a.triggered.connect(lambda _=False, p=path: on_action(f"play_music:{p.name}"))
    return sub


def build_pet_menu(on_action, settings=None) -> QMenu:
    """Build the right-click menu.  `on_action(key)` is called for every
    leaf item.  The "🎬 动作" submenu uses key 'play:<action_name>' so
    a single dispatch in main.py can decide how to react.

    `settings` is read (not mutated) only to compute the 🔇 静音/🔊 静音
    label's checked state — keeps the menu visually in sync.

    dev-doc/17 §2.2: music menu is now a '🎵 选曲' submenu inside the
    '🎬 动作' submenu, replacing the old top-level toggle.
    """
    m = QMenu()
    for key in ("open_chat", "safe_zone", "cc_task"):
        a = m.addAction(ACTION_KEYS[key])
        a.triggered.connect(lambda _=False, k=key: on_action(k))
    m.addSeparator()
    mute = m.addAction(ACTION_KEYS["toggle_mute"])
    mute.setCheckable(True)
    if settings is not None:
        mute.setChecked(not settings.sound.voice_enabled)
    mute.triggered.connect(lambda _=False, k="toggle_mute": on_action(k))

    # 🎬 动作 submenu (dev-doc/12 §3) — manual one-shots.  Picking
    # 🕶 ameath here has the same effect as the old 🎵 toggle (Bug A+D).
    action_menu = m.addMenu("🎬 动作")
    for act in PLAY_ACTION_LABELS:
        a = action_menu.addAction(PLAY_ACTION_LABELS[act])
        a.triggered.connect(lambda _=False, ac=act: on_action(f"play:{ac}"))

    # dev-doc/20 §2: 🎵 选曲 is a top-level submenu (hover 右侧展开),
    # peer of 🎬 动作.  Tracks are loaded lazily here so test patches
    # on MusicPlayer can take effect.
    try:
        from pet.sound_manager import MusicPlayer
        tracks = MusicPlayer().tracks_available()
    except Exception:
        tracks = []
    # Use the helper function to build the music submenu with proper parenting
    music_sub = build_music_submenu(tracks, on_action, m)
    m.addMenu(music_sub)

    m.addSeparator()
    for key in ("settings", "view_log"):
        a = m.addAction(ACTION_KEYS[key])
        a.triggered.connect(lambda _=False, k=key: on_action(k))
    m.addSeparator()
    a = m.addAction(ACTION_KEYS["quit"])
    a.triggered.connect(lambda _=False, k="quit": on_action(k))
    return m
