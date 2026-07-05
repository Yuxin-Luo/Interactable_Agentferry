"""VisionWorker — QThread that grabs frames + runs FaceLandmarker (spec §3.2)."""
from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
from PyQt6.QtCore import QThread, pyqtSignal, QPoint, QSize
import logging
_log = logging.getLogger("interactable_agentferry.vision")
from PyQt6.QtGui import QImage

from src.config.settings import VisionSettings
from src.vision.pipelines import FaceTracker, PinchDetector


@dataclass
class VisionSignal:
    """VisionWorker → PetController (spec §5.1)."""
    face_center: Optional[QPoint] = None
    face_bbox_size: Optional[QSize] = None
    gesture_label: str = "None"
    gesture_hand_pos: Optional[QPoint] = None
    pinch_active: bool = False
    pinch_position: Optional[QPoint] = None
    timestamp_ms: int = 0  # 用于调试


class VisionWorker(QThread):
    """摄像头 + MediaPipe FaceLandmarker (手势/pinch 在 P3/P4 接入)."""

    vision_update = pyqtSignal(object)  # VisionSignal
    camera_error = pyqtSignal(str)
    camera_frame = pyqtSignal(object)  # QImage

    def __init__(self, vision: VisionSettings, parent=None):
        super().__init__(parent)
        self._vision = vision
        self._stopping = False
        self._face_tracker = FaceTracker(ema_alpha=0.5)
        self._landmarker = None
        self._gesture_recognizer = None
        self._hand_landmarker = None
        self._pinch_detector = PinchDetector(
            distance_threshold=vision.pinch_distance_threshold,
            hold_frames=vision.pinch_hold_frames,
        )

    def stop(self) -> None:
        self._stopping = True

    def _load_landmarker(self):
        """懒加载 FaceLandmarker; 若失败 → 抛错由 caller 处理."""
        import mediapipe as mp
        from pathlib import Path

        model_path = (
            Path(__file__).resolve().parents[2]
            / "assets" / "models" / "face_landmarker.task"
        )
        if not model_path.exists():
            raise FileNotFoundError(f"FaceLandmarker model not found: {model_path}")

        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
        )
        return mp.tasks.vision.FaceLandmarker.create_from_options(options)

    def _load_gesture_recognizer(self):
        """懒加载 GestureRecognizer."""
        import mediapipe as mp
        from pathlib import Path

        model_path = (
            Path(__file__).resolve().parents[2]
            / "assets" / "models" / "gesture_recognizer.task"
        )
        if not model_path.exists():
            raise FileNotFoundError(f"GestureRecognizer model not found: {model_path}")

        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=base_options,
        )
        return mp.tasks.vision.GestureRecognizer.create_from_options(options)

    def _load_hand_landmarker(self):
        """懒加载 HandLandmarker."""
        import mediapipe as mp
        from pathlib import Path

        model_path = (
            Path(__file__).resolve().parents[2]
            / "assets" / "models" / "hand_landmarker.task"
        )
        if not model_path.exists():
            raise FileNotFoundError(f"HandLandmarker model not found: {model_path}")

        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
        )
        return mp.tasks.vision.HandLandmarker.create_from_options(options)

    def run(self) -> None:
        try:
            self._landmarker = self._load_landmarker()
            self._gesture_recognizer = self._load_gesture_recognizer()
            self._hand_landmarker = self._load_hand_landmarker()
        except Exception as e:
            self.camera_error.emit(f"Model load failed: {e}")
            return

        cam_w, cam_h = self._vision.cam_resolution
        cap = cv2.VideoCapture(self._vision.cam_device_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_w)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_h)
        cap.set(cv2.CAP_PROP_FPS, self._vision.cam_fps)

        if not cap.isOpened():
            self.camera_error.emit("Cannot open camera (device index 0)")
            return

        import mediapipe as mp

        consecutive_error_count = 0
        debug_frame_counter = 0
        try:
            while not self._stopping:
                ok, frame_bgr = cap.read()
                if not ok:
                    consecutive_error_count += 1
                    if consecutive_error_count >= 30:
                        self.camera_error.emit("Camera frames lost (30 frames)")
                        break
                    time.sleep(0.01)
                    continue
                consecutive_error_count = 0
                debug_frame_counter += 1

                # Emit BGR→RGB QImage for camera preview (before MediaPipe processing)
                frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                h, w = frame_rgb.shape[:2]
                qimage = QImage(frame_rgb.data, w, h, w * 3, QImage.Format.Format_RGB888)
                self.camera_frame.emit(qimage.copy())

                # BGR → RGB for MediaPipe (reuse frame_rgb from camera_frame emit above)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
                ts_ms = int(time.time() * 1000)
                try:
                    result = self._landmarker.detect_for_video(mp_image, ts_ms)
                except Exception:
                    # 单帧异常：跳过；30 帧连续异常由 consecutive_error_count 检测
                    continue

                landmarks = result.face_landmarks[0] if result.face_landmarks else None
                center, size = self._face_tracker.update(
                    landmarks, frame_w=cam_w, frame_h=cam_h
                )

                # GestureRecognizer
                gesture_result = self._gesture_recognizer.recognize_for_video(mp_image, ts_ms)
                gesture_label = "None"
                gesture_hand_pos: Optional[QPoint] = None
                if gesture_result.gestures:
                    top = gesture_result.gestures[0]
                    if top:
                        gesture_label = top[0].category_name
                        # 取归一化手心坐标 → 像素坐标
                        hlm = gesture_result.hand_landmarks[0] if gesture_result.hand_landmarks else None
                        if hlm:
                            # 手腕 (wrist, landmark 0) 作为手位置
                            wrist = hlm[0]
                            gesture_hand_pos = QPoint(int(wrist.x * cam_w), int(wrist.y * cam_h))

                # HandLandmarker + PinchDetector
                hand_result = self._hand_landmarker.detect_for_video(mp_image, ts_ms)
                hand_landmarks = hand_result.hand_landmarks[0] if hand_result.hand_landmarks else None
                pinch_active, pinch_pos = self._pinch_detector.update(hand_landmarks, cam_w, cam_h)

                # 调试 log：每 30 帧打印一次（避免刷屏）
                if debug_frame_counter % 30 == 0:
                    face_ok = bool(landmarks)
                    hand_ok = bool(hand_landmarks)
                    _log.info(
                        "frame=%d face=%s hand=%s gesture=%s pinch=%s",
                        debug_frame_counter, face_ok, hand_ok, gesture_label, pinch_active,
                    )

                signal = VisionSignal(
                    face_center=center,
                    face_bbox_size=size,
                    gesture_label=gesture_label,
                    gesture_hand_pos=gesture_hand_pos,
                    pinch_active=pinch_active,
                    pinch_position=pinch_pos,
                    timestamp_ms=ts_ms,
                )
                self.vision_update.emit(signal)
        finally:
            cap.release()
