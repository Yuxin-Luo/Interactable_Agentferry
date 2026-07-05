"""Reference code copy — DO NOT MODIFY for production logic.

Origin:
  Source: Reference/code/MediaPipe-Real-Time-Computer-Vision-Demos/holistic_tracking.py
  Origin license: MIT (declared in source repo README badge).
Purpose in this project:
  Reference implementation of MediaPipe Holistic (face + pose + hands) pipeline.
  Consulted for camera-frame processing layout; not directly copied because we
  split face and hand into independent pipelines for latency reasons.

This file is NOT a runtime dependency — production code lives in src/vision/.
"""

"""Real-time holistic tracking demo (MediaPipe Tasks API).

MediaPipe 0.10+ dropped the unified ``mp.solutions.holistic`` namespace.
The Tasks API has no single ``HolisticLandmarker``, so this demo composes
three independent landmarks — Face / Pose / Hands — on the same frame
with a shared timestamp, which is functionally equivalent to the legacy
``Holistic`` pipeline for visualization purposes.
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

FACE_MODEL = "models/face_landmarker.task"
POSE_MODEL = "models/pose_landmarker_lite.task"
HAND_MODEL = "models/hand_landmarker.task"

WINDOW_NAME = "Holistic Tracking"

FACE_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 13), (13, 15), (15, 17),
    (12, 14), (14, 16), (16, 18), (11, 12),
]
POSE_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (27, 29),
    (24, 26), (26, 28), (28, 30), (15, 17), (15, 19), (15, 21),
    (16, 18), (16, 20), (16, 22),
]
HAND_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
    (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17),
]


def _draw_skeleton(frame, landmarks, edges, color):
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]
    for a, b in edges:
        if a < len(pts) and b < len(pts):
            cv2.line(frame, pts[a], pts[b], color, 2)
    for x, y in pts:
        cv2.circle(frame, (x, y), 3, (0, 128, 255), -1)


def draw_face(frame, landmarks):
    _draw_skeleton(frame, landmarks, FACE_EDGES, (255, 0, 0))


def draw_pose(frame, landmarks):
    _draw_skeleton(frame, landmarks, POSE_EDGES, (0, 255, 0))


def draw_hand(frame, landmarks):
    _draw_skeleton(frame, landmarks, HAND_EDGES, (0, 0, 255))


def main():
    face = vision.FaceLandmarker.create_from_options(
        vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=FACE_MODEL),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
        )
    )
    pose = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=POSE_MODEL),
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
    )
    hands = vision.HandLandmarker.create_from_options(
        vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=HAND_MODEL),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
    )
    detectors = (face, pose, hands)
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Cannot open webcam (index 0).")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            if FLIP:
                frame = cv2.flip(frame, 1)  # horizontal mirror — selfie view.
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            face_result = face.detect_for_video(mp_image, timestamp_ms)
            pose_result = pose.detect_for_video(mp_image, timestamp_ms)
            hand_result = hands.detect_for_video(mp_image, timestamp_ms)

            for fl in face_result.face_landmarks:
                draw_face(frame, fl)
            for pl in pose_result.pose_landmarks:
                draw_pose(frame, pl)
            for hl in hand_result.hand_landmarks:
                draw_hand(frame, hl)

            cv2.imshow(WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        for d in detectors:
            d.close()


if __name__ == "__main__":
    main()
