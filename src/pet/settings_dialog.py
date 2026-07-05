"""SettingsDialog — 飞行速度 / 距离阈值 / pet 大小可视化调节 (spec §2.1)."""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSlider, QSpinBox,
    QDialogButtonBox, QFormLayout, QGroupBox, QCheckBox,
)

from src.config.settings import VisionSettings
from src.pet.settings_store import SettingsStore


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)

    def __init__(self, vision: VisionSettings, store: SettingsStore, parent=None):
        super().__init__(parent)
        self._vision = vision
        self._store = store
        self.setWindowTitle("Settings")
        self.setModal(True)
        self._build_ui()
        self._load_current()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Camera group (flip toggle)
        gb_cam = QGroupBox("摄像头")
        form_cam = QFormLayout(gb_cam)
        self.check_flip = QCheckBox("水平翻转（自拍模式）")
        form_cam.addRow(self.check_flip)
        layout.addWidget(gb_cam)

        # Flight speed group
        gb_flight = QGroupBox("飞行速度")
        form_flight = QFormLayout(gb_flight)
        self.slider_speed_min = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed_min.setRange(50, 500)
        self.spin_speed_min = QSpinBox()
        self.spin_speed_min.setRange(50, 500)
        self.slider_speed_min.valueChanged.connect(self.spin_speed_min.setValue)
        self.spin_speed_min.valueChanged.connect(self.slider_speed_min.setValue)
        form_flight.addRow("min (px/s):", self._h(self.slider_speed_min, self.spin_speed_min))

        self.slider_speed_max = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed_max.setRange(50, 1000)
        self.spin_speed_max = QSpinBox()
        self.spin_speed_max.setRange(50, 1000)
        self.slider_speed_max.valueChanged.connect(self.spin_speed_max.setValue)
        self.spin_speed_max.valueChanged.connect(self.slider_speed_max.setValue)
        form_flight.addRow("max (px/s):", self._h(self.slider_speed_max, self.spin_speed_max))

        layout.addWidget(gb_flight)

        # Distance tier group
        gb_tier = QGroupBox("距离档位 (face bbox width 阈值)")
        form_tier = QFormLayout(gb_tier)
        self.spin_tier_mid = QSpinBox()
        self.spin_tier_mid.setRange(20, 400)
        self.spin_tier_near = QSpinBox()
        self.spin_tier_near.setRange(80, 800)
        form_tier.addRow("mid_max (px):", self.spin_tier_mid)
        form_tier.addRow("near_min (px):", self.spin_tier_near)
        layout.addWidget(gb_tier)

        # Pet size group
        gb_size = QGroupBox("桌宠大小 (各档位缩放)")
        form_size = QFormLayout(gb_size)
        self.spin_size_near = self._size_spin()
        self.spin_size_mid = self._size_spin()
        self.spin_size_far = self._size_spin()
        form_size.addRow("near:", self.spin_size_near)
        form_size.addRow("mid:", self.spin_size_mid)
        form_size.addRow("far:", self.spin_size_far)
        layout.addWidget(gb_size)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _h(self, *widgets) -> QHBoxLayout:
        h = QHBoxLayout()
        for w in widgets:
            h.addWidget(w)
        return h

    def _size_spin(self) -> QSpinBox:
        s = QSpinBox()
        s.setRange(30, 300)
        s.setSingleStep(10)
        return s

    def _load_current(self) -> None:
        v = self._vision
        self.check_flip.setChecked(v.flip_horizontal)
        self.slider_speed_min.setValue(v.flight_speed_min)
        self.slider_speed_max.setValue(v.flight_speed_max)
        self.spin_tier_mid.setValue(v.face_tier_thresholds[0])
        self.spin_tier_near.setValue(v.face_tier_thresholds[1])
        self.spin_size_near.setValue(int(v.pet_size_near * 100))
        self.spin_size_mid.setValue(int(v.pet_size_mid * 100))
        self.spin_size_far.setValue(int(v.pet_size_far * 100))

    def _on_save(self) -> None:
        overrides = {
            "flip_horizontal": self.check_flip.isChecked(),
            "flight_speed_min": self.slider_speed_min.value(),
            "flight_speed_max": self.slider_speed_max.value(),
            "face_tier_thresholds": [self.spin_tier_mid.value(), self.spin_tier_near.value()],
            "pet_size_near": self.spin_size_near.value() / 100.0,
            "pet_size_mid": self.spin_size_mid.value() / 100.0,
            "pet_size_far": self.spin_size_far.value() / 100.0,
        }
        self._store.save(overrides)
        self.settings_changed.emit(overrides)
        self.accept()
