"""AppOrchestrator — 启动 CameraPetWindow + VisionWorker + 退出处理.

spec §3.1 / §3.2
"""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.config.settings import VisionSettings, load_settings
from src.camera.window import CameraPetWindow


class AppOrchestrator:
    def __init__(self, vision: VisionSettings):
        self.vision = vision
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(True)

        # 窗口尺寸：默认主屏 90%（spec §2.1）
        cw, ch = vision.cam_resolution
        # 主屏探测留待 P10（设置 UI 里调）；v1 固定使用 90% cam 比例
        win_w = int(cw * 0.9)
        win_h = int(ch * 0.9)
        self.window = CameraPetWindow(win_w=win_w, win_h=win_h)

    def run(self) -> int:
        self.window.show()
        return self.app.exec()


def main() -> int:
    vision = VisionSettings()
    orch = AppOrchestrator(vision=vision)
    return orch.run()


if __name__ == "__main__":
    sys.exit(main())
