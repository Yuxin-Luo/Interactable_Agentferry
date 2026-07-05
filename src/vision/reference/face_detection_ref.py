"""Reference code copy — DO NOT MODIFY for production logic.

Origin:
  Source: Reference/code/MediaPipe-Real-Time-Computer-Vision-Demos/face_detection.py
  Origin license: MIT (declared in source repo README badge).
Purpose in this project:
  Reference implementation of MediaPipe Tasks API FaceDetector usage.
  Used to inform the design of src/vision/face_tracker.py.
  Kept verbatim for traceability.

This file is NOT a runtime dependency — production code lives in src/vision/.
"""

"""Real-time face detection demo (MediaPipe Tasks API).

Migrated from the legacy ``mp.solutions.face_detection`` (removed in
MediaPipe >= 0.10) to ``mediapipe.tasks.vision.FaceDetector``.

Run:
    /home/ruo/anaconda3/envs/video2txt/bin/python face_detection.py
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- Mirror toggle ----------------------------------------------------------
# By default webcams show a raw (non-mirrored) video: when you raise your LEFT
# hand, the figure on screen also raises their LEFT hand — counter-intuitive for
# a selfie-style webcam where users expect the on-screen image to follow their
# own movements as a mirror. Flip the video horizontally so the on-screen image
# is a self-mirror of the user.
#
# Set FLIP = False to pass the raw camera matrix through unchanged (useful for
# debugging hand/pose correspondence, where inference should match what the
# camera sensor actually saw).
FLIP = True
# ---------------------------------------------------------------------------

MODEL_PATH = "models/blaze_face_short_range.tflite"

WINDOW_NAME = "Face Detection"


def draw_detections(frame, detections):
    """Draw bounding boxes + keypoints on a BGR frame using cv2 primitives."""
    h, w = frame.shape[:2]
    for det in detections:
        bbox = det.bounding_box
        x, y, ww, hh = bbox.origin_x, bbox.origin_y, bbox.width, bbox.height
        cv2.rectangle(frame, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
        for kp in det.keypoints:
            cx, cy = int(kp.x * w), int(kp.y * h)
            cv2.circle(frame, (cx, cy), 3, (0, 128, 255), -1)


def main():
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceDetectorOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
    )
    detector = vision.FaceDetector.create_from_options(options)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam (index 0). Try cv2.VideoCapture(1) or a video file.")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if FLIP:
                frame = cv2.flip(frame, 1)  # horizontal mirror — selfie view.
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect_for_video(mp_image, timestamp_ms)
            draw_detections(frame, result.detections)
            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()


if __name__ == "__main__":
    main()
