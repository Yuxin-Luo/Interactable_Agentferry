# 8 — Decision: Camera horizontal flip (selfie mode)

**Date:** 2026-07-05
**Author:** Claude (after user feedback "当前的画面并非镜像")

## Context

User reported the camera preview was **not mirrored** — i.e. it shows the
"raw" camera output where the user's right hand appears on the right side
of the screen. Most webcam / video-call apps default to **selfie mode**
(horizontal flip) because users expect their movements to feel natural —
when they raise their right hand, the pet on screen should be on the
right.

## Decision

Add a `flip_horizontal: bool = True` setting (default True = selfie mode)
applied in `VisionWorker.run()` right after `cap.read()`:

```python
if self._vision.flip_horizontal:
    frame_bgr = cv2.flip(frame_bgr, 1)  # 1 = horizontal flip
```

The flip is applied **once**, before:
- the display `QImage` is built (for `camera_label`)
- the MediaPipe `mp.Image` is built (for FaceLandmarker / GestureRecognizer / HandLandmarker)

So vision coordinates (`face_center`, `pinch_position`) and display
coordinates stay consistent — the pet flies toward the side of the
screen where the user perceives their face/hand, with no extra coordinate
translation needed.

## Alternatives considered

| Option | Pros | Cons | Decision |
|---|---|---|---|
| Flip raw frame in worker (chosen) | Single flip; vision & display consistent | None | ✅ |
| Flip only QImage at display; vision uses raw frame | Slightly cheaper | Pet flies to wrong side of face — UX bug | ❌ |
| Flip both image AND `x = cam_w - x` for coords | Same as chosen but more code | Two places to keep in sync | ❌ |
| Add to settings dialog only, no apply_settings | Less code | Setting won't take effect until restart | ❌ |

## Implementation

| File | Change |
|---|---|
| `src/config/settings.py` | Add `flip_horizontal: bool = True` to VisionSettings |
| `src/vision/worker.py` | Apply `cv2.flip(frame, 1)` when flag is on |
| `src/pet/settings_dialog.py` | New "摄像头" group + QCheckBox "水平翻转（自拍模式）" |
| `src/pet/controller.py` | `apply_settings` handles `flip_horizontal` |
| `tests/test_vision_settings.py` | Assert default is True |
| `tests/test_settings_dialog.py` | Assert checkbox loads + emits in save dict |

## Risk

- **Low** — flip is a single cv2 call per frame, ~0.1ms; no behavioral change for
  users who prefer raw mode (toggle off in settings).
- **Coord consistency** — verified: applying flip to both display + MediaPipe input
  means the same `(face_center.x, face_center.y)` value that drives the pet
  matches what the user sees.

## Verification

- pytest: 71/71 passed (added 2 test asserts for new field).
- Manual smoke: run app, confirm video is mirrored (user raises right hand →
  pet-side hand appears on right of screen).
- Toggle off in settings → live revert to raw mode (worker reads flag every frame).