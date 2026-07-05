"""SoundManager — voice (short WAVs) + music (mp3) playback.

Design (dev-doc/11-design-sound-and-actions-2026-07-04.md §2.1,
         dev-doc/13-fix-sound-still-silent-2026-07-04.md §2):
- One PyQt6 QMediaPlayer + QAudioOutput per player.  Both voice and
  music use Qt's built-in FFmpeg backend.
- BOTH the QMediaPlayer AND the QAudioOutput must be held by Python
  attributes, else Python GC will destroy the QAudioOutput between
  `_mk_player()` returning and `_play()` calling `setSource`.  Same
  root cause as Issue 4 / dev-doc/12 §4, except the AudioOutput
  variant escaped the previous fix.
- Voice playback is one-shot: after `play_for_action()` we let the
  player run to completion (or stop on next call).
- Music is also one-shot: `play_random_now()` picks one mp3 and
  plays it through, then sits idle.
- Tests substitute `player_factory` so they can drive playback without
  real QMediaPlayer instances.
"""
from __future__ import annotations
import random
from pathlib import Path
from typing import Callable, Dict, List, Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices

from src.utils.log import get_logger

_log = get_logger("aemeath.sound")


# Pair each pet action / state with one or more voice WAVs.
# Per dev-doc/9-Ameath-Respursed-Introduction.txt.
VOICE_BY_ACTION: Dict[str, List[str]] = {
    "idle1":        ["嗯.wav"],
    "idle2":        ["看这里.wav", "你，看见我了.wav"],
    "idle3":        ["嗯，嘿嘿.wav", "嗯，哼哼.wav"],
    "idle4":        ["嗯，嘿嘿.wav", "嗯，哼哼.wav"],
    "drag":         ["嘿嘿.wav"],
    "ameath":       ["现实系统，侵入完成.wav", "一起去拯救世界吧.wav"],
    "move":         ["嘿嘿.wav", "看这里.wav"],
}


ASSET_ROOT = Path(__file__).resolve().parents[2] / "assets" / "ameath" / "sound"


def _list_files(dir_path: Path, suffix: str) -> List[Path]:
    if not dir_path.exists():
        return []
    return sorted(p for p in dir_path.iterdir()
                  if p.is_file() and p.suffix.lower() == suffix)


class VoicePlayer:
    """Plays one short WAV for an 'action' key (e.g. 'idle2', 'drag')."""

    def __init__(self, voice_dir: Optional[Path] = None,
                 player_factory: Optional[Callable[[], QMediaPlayer]] = None):
        # Default to the upstream-style VOICE_BY_ACTION paths under our
        # assets/ameath/sound/voice mirror.
        self.voice_dir = Path(voice_dir) if voice_dir else ASSET_ROOT / "voice"
        self._files: Dict[str, Path] = {}
        for action, names in VOICE_BY_ACTION.items():
            for n in names:
                p = self.voice_dir / n
                if p.exists():
                    self._files[n] = p  # last-write-wins; only one n per action matters
        # Collapse: per action, keep only the files that exist on disk.
        self._available: Dict[str, List[Path]] = {}
        for action, names in VOICE_BY_ACTION.items():
            self._available[action] = [self.voice_dir / n for n in names
                                       if (self.voice_dir / n).exists()]
        self._last_path: Optional[Path] = None
        self._consec = 0
        self.enabled = True
        self.volume_pct = 80

        # QMediaPlayer may not exist in headless test runs that never
        # touch play_for_action; lazy-create so import is cheap.
        self._player_factory = player_factory
        self._player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None

    def _mk_player(self) -> Optional[QMediaPlayer]:
        if self._player is None:
            if self._player_factory is not None:
                self._player = self._player_factory()
            else:
                p = QMediaPlayer()
                if p is None:
                    # Audio backend unavailable (headless / no PulseAudio).
                    self._player = None
                    return None
                # CRITICAL: keep QAudioOutput as a self attribute.
                # Without this the AudioOutput is GC'd between
                # setAudioOutput() and play(), and Qt destroys the
                # underlying device too.  Same root cause as Issue 4
                # but for QAudioOutput (dev-doc/13 §2).
                self._audio_output = QAudioOutput()
                p.setAudioOutput(self._audio_output)
                self._player = p
                # Log which device we connected to so user can debug if
                # audio goes to the wrong sink (HDMI / headphone / etc.).
                dev = QMediaDevices.defaultAudioOutput()
                if dev.isNull():
                    _log.warning("audio: no default audio output device")
                else:
                    _log.info(f"audio device: {dev.description()!r}")
            if self._audio_output is not None:
                self._audio_output.setVolume(self.volume_pct / 100.0)
                self._audio_output.setMuted(False)
        return self._player

    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        if not on:
            self.stop()

    def set_volume(self, pct: int) -> None:
        pct = max(0, min(100, pct))
        self.volume_pct = pct
        if self._audio_output is not None:
            self._audio_output.setVolume(pct / 100.0)

    def play_for_action(self, action: str) -> Optional[Path]:
        """Pick a WAV from VOICE_BY_ACTION[action] and play it.

        Returns the Path actually played (for test introspection), or
        None if disabled / no asset / out-of-assets.
        """
        if not self.enabled:
            return None
        candidates = self._available.get(action, [])
        if not candidates:
            return None
        # Avoid playing the same file 3 times in a row (parity w/ ref upstream).
        if self._consec >= 2 and self._last_path is not None and len(candidates) > 1:
            others = [p for p in candidates if p != self._last_path]
            chosen = random.choice(others) if others else candidates[0]
        else:
            chosen = random.choice(candidates)

        if chosen == self._last_path:
            self._consec += 1
        else:
            self._last_path = chosen
            self._consec = 0

        self._play(chosen)
        return chosen

    def _play(self, p: Path) -> None:
        # Subclasses / test stubs override; default uses real QMediaPlayer.
        pl = self._mk_player()
        if pl is None:
            return  # audio backend unavailable
        pl.stop()
        pl.setSource(QUrl.fromLocalFile(str(p)))
        pl.play()

    def stop(self) -> None:
        if self._player is not None:
            self._player.stop()


class MusicPlayer:
    """One QMediaPlayer for mp3s in assets/ameath/sound/music.

    No looping — `play_random_now()` picks one song and plays it once.
    Schedule the next play via `schedule_idle_play(minutes)` which
    starts a single-shot QTimer (caller-managed).

    Bug A / dev-doc/16 §3.4: natural-track-end detection.  Wire
    `set_on_finished_cb(cb)` BEFORE the first call to
    `play_random_now()` so the orchestrator can clear the music lock
    when a track finishes.  The cb fires when QMediaPlayer
    transitions to StoppedState AFTER having played at least one
    frame (so user-initiated `stop()` doesn't fire the cb — but
    callers should clear the cb first via set_on_finished_cb(None)).
    """

    # QMediaPlayer.PlaybackState values (PyQt6):
    # 0 = StoppedState, 1 = PlayingState, 2 = PausedState.
    # We avoid the symbolic import to keep this module free of
    # multimedia-binding overhead when only the facade is used.
    _PLAYBACK_STOPPED = 0
    _PLAYBACK_PLAYING = 1

    def __init__(self, music_dir: Optional[Path] = None,
                 player_factory: Optional[Callable[[], QMediaPlayer]] = None):
        self.music_dir = Path(music_dir) if music_dir else ASSET_ROOT / "music"
        self._tracks = _list_files(self.music_dir, ".mp3")
        self._last_track: Optional[Path] = None
        self.enabled = True
        self.volume_pct = 60
        self._player_factory = player_factory
        self._player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None
        # Bug A / dev-doc/16 §3.4 — natural-finish callback.
        self._on_finished_cb: Optional[Callable[[], None]] = None
        self._state_conn_armed: bool = False
        self._was_playing: bool = False
        self._exhausted: bool = False

    def tracks_available(self) -> List[Path]:
        """Public helper for tests + future 'import more' UI."""
        return list(self._tracks)

    def _mk_player(self) -> Optional[QMediaPlayer]:
        if self._player is None:
            if self._player_factory is not None:
                self._player = self._player_factory()
            else:
                p = QMediaPlayer()
                if p is None:
                    self._player = None  # audio backend unavailable
                    return self._player
                # CRITICAL: keep QAudioOutput alive too — see dev-doc/13 §2.
                self._audio_output = QAudioOutput()
                p.setAudioOutput(self._audio_output)
                self._player = p
                dev = QMediaDevices.defaultAudioOutput()
                if dev.isNull():
                    _log.warning("audio: no default audio output device")
                else:
                    _log.info(f"audio device: {dev.description()!r}")
            if self._audio_output is not None:
                self._audio_output.setVolume(self.volume_pct / 100.0)
                self._audio_output.setMuted(False)
        return self._player

    def set_enabled(self, on: bool) -> None:
        self.enabled = on
        if not on:
            self.stop()

    def set_volume(self, pct: int) -> None:
        pct = max(0, min(100, pct))
        self.volume_pct = pct
        if self._player is not None and self._audio_output is not None:
            self._audio_output.setVolume(pct / 100.0)

    def set_on_finished_cb(self, cb: Optional[Callable[[], None]]) -> None:
        """Bug A / dev-doc/16 §3.4: install a callback that fires when
        a track ends NATURALLY (reaches EndOfMedia → StoppedState after
        having been PlayingState at some point).  Pass `None` to clear
        (e.g. before an explicit `stop()`)."""
        self._on_finished_cb = cb

    def _ensure_state_connection(self) -> None:
        """Hook QMediaPlayer.stateChanged so we can detect natural
        End-of-Media transitions.  Idempotent."""
        if self._state_conn_armed:
            return
        pl = self._mk_player()
        if pl is None:
            return
        try:
            pl.stateChanged.connect(self._on_player_state_changed)
            self._state_conn_armed = True
        except Exception as e:
            _log.warning(f"failed to connect stateChanged: {e}")

    def _on_player_state_changed(self, state) -> None:
        """stateChanged handler.  Fires `cb` once per play, only when
        we transitioned PlayingState → StoppedState naturally."""
        if state == self._PLAYBACK_PLAYING:
            self._was_playing = True
        elif state == self._PLAYBACK_STOPPED and self._was_playing and not self._exhausted:
            self._exhausted = True
            self._was_playing = False
            cb = self._on_finished_cb
            if cb is not None:
                try:
                    cb()
                except Exception as e:
                    _log.warning(f"on_finished_cb raised: {e}")

    def play_random_now(self) -> Optional[Path]:
        if not self.enabled or not self._tracks:
            return None
        # Prefer not to repeat the most recent track.
        pool = [t for t in self._tracks if t != self._last_track] or self._tracks
        chosen = random.choice(pool)
        return self._play_and_reset(chosen)

    def play_specific(self, path: Path) -> Optional[Path]:
        """Play the given track path (must be in _tracks).  Reuses
        _play_and_reset bookkeeping so natural-end cb fires correctly."""
        if not self.enabled or not self._tracks:
            return None
        if path not in self._tracks:
            return None
        return self._play_and_reset(path)

    def _play_and_reset(self, chosen: Path) -> Path:
        """Shared body: set last_track, reset was_playing/exhausted, play."""
        self._last_track = chosen
        self._was_playing = False
        self._exhausted = False
        self._play(chosen)
        self._ensure_state_connection()
        return chosen

    def _play(self, p: Path) -> None:
        pl = self._mk_player()
        if pl is None:
            return  # audio backend unavailable
        pl.stop()
        pl.setSource(QUrl.fromLocalFile(str(p)))
        pl.play()

    def stop(self) -> None:
        """User-initiated stop.  Marks exhausted so the StoppedState
        transition that this call triggers does NOT fire
        `on_finished_cb`."""
        if self._player is not None:
            self._exhausted = True
            self._was_playing = False
            self._player.stop()


class SoundManager:
    """Thin facade: Orchestrator owns one of these; calls come from
    IdleRotator (voice on rotation) and MusicTimer (schedule on IDLE)."""

    def __init__(self, voice_dir: Optional[Path] = None,
                 music_dir: Optional[Path] = None,
                 voice_player_factory: Optional[Callable[[], QMediaPlayer]] = None,
                 music_player_factory: Optional[Callable[[], QMediaPlayer]] = None):
        self.voice = VoicePlayer(voice_dir=voice_dir,
                                 player_factory=voice_player_factory)
        self.music = MusicPlayer(music_dir=music_dir,
                                 player_factory=music_player_factory)

    # --- voice ---
    def play_voice_for_action(self, action: str) -> Optional[Path]:
        return self.voice.play_for_action(action)

    def mute_voice(self, on: bool) -> None:
        self.voice.set_enabled(not on)

    # --- music ---
    def play_music_now(self) -> Optional[Path]:
        return self.music.play_random_now()

    def enable_music(self, on: bool) -> None:
        self.music.set_enabled(on)
