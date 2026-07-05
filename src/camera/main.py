"""AppOrchestrator — 启动 CameraPetWindow + VisionWorker + PetController (spec §3.1)."""
from __future__ import annotations

import sys
import time

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QGuiApplication

from src.config.settings import VisionSettings
from src.camera.window import CameraPetWindow
from src.vision.worker import VisionWorker, VisionSignal
from src.pet.controller import PetController
from src.pet.sound_manager import SoundManager
from src.pet.gesture_mapper import lookup as gesture_lookup
from src.pet.settings_store import SettingsStore
from src.pet.settings_dialog import SettingsDialog
from pathlib import Path


class AppOrchestrator:
    def __init__(self, vision: VisionSettings):
        self.vision = vision
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(True)

        # 强制 logging：basicConfig 在 absl/MediaPipe 配置过 root logger 后变 no-op，
        # 必须 force=True 才能拿到自己的 handler；否则 _log.info() 全被吞掉。
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
            force=True,
            handlers=[logging.StreamHandler(sys.stderr)],
        )

        # Window size: 90% of primary screen (not cam resolution — cameras
        # are usually 720p/1080p but screens are larger).
        screen = QGuiApplication.primaryScreen()
        if screen is not None:
            sw, sh = screen.size().width(), screen.size().height()
        else:
            sw, sh = 1280, 720
        win_w = int(sw * 0.9)
        win_h = int(sh * 0.9)
        # Move window to center of screen
        self.window = CameraPetWindow(win_w=win_w, win_h=win_h)
        if screen is not None:
            self.window.move(
                (sw - win_w) // 2,
                (sh - win_h) // 2,
            )
        self.controller = PetController(vision=vision)
        self.controller.set_window_size(win_w, win_h)

        # Wire signals
        self.controller.render_command.connect(self.window.update_pet)
        self.controller.hud_update.connect(self.window.update_hud)
        self.controller.audio_command.connect(self._on_audio_command)
        # 注入 controller 到 window
        self.window._controller = self.controller

        # 把窗口 viewport 尺寸传给 worker（用于 camera→window 坐标映射）
        self.worker.set_viewport_size(win_w, win_h)

        # 音频
        self.sound = SoundManager()

        # 设置持久化 + 启动加载
        self.store = SettingsStore(path=Path(self.controller._vision.settings_persistence_path).expanduser())
        persisted = self.store.load()
        if persisted:
            self.controller.apply_settings(persisted)

        # 右键菜单：添加 Settings 项
        self.window.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.window.customContextMenuRequested.connect(self._show_context_menu)

        # Vision worker
        self.worker = VisionWorker(vision=vision)
        self.worker.vision_update.connect(self._on_vision_update)
        self.worker.camera_error.connect(self._on_camera_error)
        self.worker.camera_frame.connect(self.window.update_camera_frame)

        # Tick timer (60fps) — 在没有 vision_update 时也维持 render 状态
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick_render)
        self._tick_timer.start(16)  # ~60fps

    def _show_context_menu(self, pos) -> None:
        from PyQt6.QtGui import QAction, QMenu
        menu = QMenu(self.window)
        act_settings = QAction("Settings...", menu)
        act_settings.triggered.connect(self._open_settings)
        menu.addAction(act_settings)
        act_quit = QAction("Quit", menu)
        act_quit.triggered.connect(self.app.quit)
        menu.addAction(act_quit)
        menu.exec(self.window.mapToGlobal(pos))

    def _open_settings(self) -> None:
        d = SettingsDialog(self.controller._vision, self.store, parent=self.window)
        d.settings_changed.connect(self._on_settings_changed)
        d.exec()

    def _on_settings_changed(self, overrides: dict) -> None:
        self.controller.apply_settings(overrides)
        self.store.save(overrides)

    def _on_vision_update(self, signal: VisionSignal) -> None:
        # Camera frame 已经直连到 window.update_camera_frame (via camera_frame signal)；
        # 这里只跑 controller 状态机。
        self.controller.update(signal)

    def _on_camera_error(self, msg: str) -> None:
        print(f"[camera error] {msg}", file=sys.stderr)

    def _tick_render(self) -> None:
        # 即使无新 vision frame，也按上一帧数据保持 render
        if self.controller.last_render is None:
            # 初始：把桌宠放在窗口中心
            self.controller.update(VisionSignal(face_center=None, face_bbox_size=None))

    def _on_audio_command(self, state_label: str, kwargs: dict) -> None:
        """state_label 是 PetState.value 字符串."""
        # 把 state 映射回 gesture label 用于查 GestureMapper + 播放 voice
        state_to_gesture = {
            "default_fly": "None",
            "open_palm":   "Open_Palm",
            "thumb_up":    "Thumb_Up",
            "thumb_down":  "Thumb_Down",
            "victory":     "Victory",
            "fist":        "Closed_Fist",
            "pointing":    "Pointing_Up",
            # drag 期间不重复播 voice
            "drag_mouse":  None,
            "drag_pinch":  "Pinch",
        }
        gesture_label = state_to_gesture.get(state_label)
        if gesture_label is None:
            return
        action = gesture_lookup(gesture_label)
        if not hasattr(self, "_last_audio_state") or self._last_audio_state != state_label:
            self._last_audio_state = state_label
            if action.voice and self.vision is not None:
                self.sound.play_voice_for_action(gesture_label)
            if action.music:
                self.sound.play_music_now()

    def run(self) -> int:
        self.window.show()
        self.worker.start()
        return self.app.exec()

    def shutdown(self) -> None:
        self.worker.stop()
        self.worker.wait(2000)


def main() -> int:
    vision = VisionSettings()
    orch = AppOrchestrator(vision=vision)
    try:
        return orch.run()
    finally:
        orch.shutdown()


if __name__ == "__main__":
    sys.exit(main())
