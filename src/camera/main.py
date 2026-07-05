"""AppOrchestrator — 启动 CameraPetWindow + VisionWorker + PetController (spec §3.1)."""
from __future__ import annotations

import sys
import time

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage

from src.config.settings import VisionSettings
from src.camera.window import CameraPetWindow
from src.vision.worker import VisionWorker, VisionSignal
from src.pet.controller import PetController


class AppOrchestrator:
    def __init__(self, vision: VisionSettings):
        self.vision = vision
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(True)

        # Window size: 90% of cam resolution
        cw, ch = vision.cam_resolution
        win_w = int(cw * 0.9)
        win_h = int(ch * 0.9)

        self.window = CameraPetWindow(win_w=win_w, win_h=win_h)
        self.controller = PetController(vision=vision)
        self.controller.set_window_size(win_w, win_h)

        # Wire signals
        self.controller.render_command.connect(self.window.update_pet)
        self.controller.hud_update.connect(self.window.update_hud)
        # 注入 controller 到 window（PetOverlay 鼠标事件需要）
        self.window._controller = self.controller

        # Vision worker
        self.worker = VisionWorker(vision=vision)
        self.worker.vision_update.connect(self._on_vision_update)
        self.worker.camera_error.connect(self._on_camera_error)

        # Tick timer (60fps) — 在没有 vision_update 时也维持 render 状态
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._tick_render)
        self._tick_timer.start(16)  # ~60fps

    def _on_vision_update(self, signal: VisionSignal) -> None:
        # 同时把摄像头帧送 window
        # (P1.5 之后可改为在 worker 中 emit QImage；目前由 controller 节流更新)
        self.controller.update(signal)
        # 渲染摄像头画面（BGR → QImage）
        self._render_camera_from_signal(signal)

    def _render_camera_from_signal(self, signal: VisionSignal) -> None:
        # P2 简化：camera frame 由 worker 单独 emit；这里仅占位
        # P3 重构：worker emit (VisionSignal, QImage) tuple
        pass

    def _on_camera_error(self, msg: str) -> None:
        print(f"[camera error] {msg}", file=sys.stderr)

    def _tick_render(self) -> None:
        # 即使无新 vision frame，也按上一帧数据保持 render
        if self.controller.last_render is None:
            # 初始：把桌宠放在窗口中心
            self.controller.update(VisionSignal(face_center=None, face_bbox_size=None))

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
