# 7 — Debug: Face/Hand detection + pet base size + drag GIF + initial drift

**Date:** 2026-07-05
**Author:** Claude (auto, after user-reported UX issues)

## 症状

User-reported (2026-07-05 复盘):

1. **桌宠初始大小较小** — 启动后桌宠看上去明显小于预期
2. **鼠标拖动时没有及时转变为 drag.gif** — 点 pet 后 GIF 不切换，要等鼠标动才换
3. **初始没有随机漂移** — 无脸时桌宠静止
4. **右侧 HUD 始终显示 `Face:✗ Hand:✗`** — 即便用户跑参考代码 `Reference/code/MediaPipe-Real-Time-Computer-Vision-Demos/face_detection.py` 和 `Reference/code/MonkeyMeme-Gesture_Tracker/gesture-tracker.py` 都能正常识别

## 根因分析

### R1: MediaPipe `running_mode` 缺失（最关键）

`src/vision/worker.py` 三个 model loader 都没设 `running_mode`：

```python
# 我们的（缺 running_mode）
options = mp.tasks.vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    ...
    num_faces=1,
)

# 参考 face_detection.py 的（有 running_mode=VIDEO）
options = vision.FaceDetectorOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
)
```

MediaPipe Tasks Python 默认 `running_mode=IMAGE`。在 IMAGE 模式下调用 `detect_for_video(mp_image, ts_ms)` 会**静默返回空结果**（不报错），所以 `result.face_landmarks` 永远空，`Face:✗ Hand:✗` 永不变。

GestureRecognizer 同理（`recognize_for_video()` 也要 VIDEO mode），HandLandmarker 同理。

### R2: Pet base size 硬编码 128

`src/camera/window.py:164`:

```python
size = int(128 * scale)
```

- `PetOverlay` 初始 `setFixedSize(192, 192)`（用户报告后改大）
- `update_pet` 用 `int(128 * scale)` 立即改成 `128 * 1.0 = 128`（mid 默认）
- 用户看到的 "初始 192" 其实是 MediaPipe 加载 + 首帧延迟那 ~0.5s 内的视觉，之后变成 128

### R3: `start_mouse_drag()` 不调 `_emit_render()`

`src/pet/controller.py:277-281`:

```python
def start_mouse_drag(self) -> None:
    if self._state == PetState.DRAG_PINCH:
        return
    self._state = PetState.DRAG_MOUSE
    # 缺：self._emit_render()
```

只设状态，没渲染。`update_mouse_drag` 才会 emit，但要求鼠标移动 → 静态点击不切换 GIF。

### R4: 无脸时 `drift_without_face` 已实现但没人调用

`_tick_default_fly` 在无脸时调 `_drift_without_face()`，但要求 `controller.update()` 被调用。如果 vision_update 一直没来（MediaPipe 没识别到脸就 emit），pet 不会动。

**但实际上**：即使 face 没识别到，vision_worker 仍每帧调用 `vision_update.emit(signal)` —— signal 中 `face_center=None` 也照样 emit。所以 R4 应该不是独立问题，但**配合 R1 修了之后**，drift 自然会发生（首帧 ~0.5s 之间桌宠会漂）。

### R5: Camera→Window 坐标未映射（衍生）

Worker 用 `frame_w=cam_w, frame_h=cam_h` 算 face_center。controller 当窗口坐标用。当前默认比例一致（`win_w/cam_w = 0.9`），但**语义不对**——一旦用户改分辨率就错位。

### R6: Audio state→gesture 映射残缺

`main.py:131-138` `state_to_gesture` 只有 3 项：THUMB_DOWN / VICTORY / DEFAULT_FLY。其他手势状态收 audio_command 时都被 early return → 不播放声音。

### R7: QMovie 切换不 stop 旧的

`update_pet` 创建新 QMovie 覆盖 `setMovie`，旧 movie 没 stop。60fps 切 GIF 漏内存 + 视觉混乱。

### R8: DRAG_PINCH 钳制边界用 `_pet_size=128`

`controller.py:143-145,154` 钳制 `pet_pos` 用 `self._pet_size`，但实际显示 size 是 `128*scale`。scale=1.5 时 pet_size 应=192，钳制按 128 算 → pet 会超出窗口边界。

## 决策记录

| ID | 决策 | 理由 |
|---|---|---|
| D1 | 加 `running_mode=RunningMode.VIDEO` 到 3 个 loader | MediaPipe 官方文档明确要求 `detect_for_video` 必须 VIDEO mode |
| D2 | Pet base size 引入常量 `PET_BASE_SIZE = 192`（统一） | 比 128 更易看见；用户也反馈初始较小 |
| D3 | `start_mouse_drag` 调 `_emit_render()` | 点 pet 立即切换 drag.gif |
| D4 | Camera→Window 映射：在 controller 端做 `pos * (win_w/cam_w)` | worker 只管相机坐标，controller 负责 window 坐标语义 |
| D5 | Audio 映射补全所有 state | 每个手势都该播对应 voice（如果有） |
| D6 | QMovie 切换前 `old_movie.stop()` | 内存/视觉卫生 |
| D7 | `_tick_render` 每帧调 `update()` 直到 `last_render` 设上 | 让 MediaPipe 加载期间桌宠就开始漂 |
| D8 | DRAG_PINCH 钳制用 `int(PET_BASE_SIZE * scale)` | 钳制边界与实际显示尺寸一致 |
| D9 | 删 `_render_camera_from_signal` dead code | camera_frame 已直连 |
| D10 | DRAG_PINCH 进入时调 `_emit_render()` | HUD 立即变 "Pinch" |

## 衍生风险

- 测试 `test_update_with_face_renders_command` 等用 `QPoint(640, 360)` 作为 face_center，**在加坐标映射后**会按 `(640 * win_w/cam_w, 360 * win_h/cam_h)` 缩放。需要更新测试或让 controller 测试用 cam coord (传入 cam_res)。
- 测试 `test_distance_tier_*` 依赖 `face_bbox_size` 是相机坐标系，但 tier 判定只看 width 像素值，**加 scale 不影响**。

## 测试影响预估

- `test_pet_controller.py`：可能需要更新 `set_window_size` 后调用 `set_camera_resolution` 或在测试 setup 里把 win_w=cam_w
- `test_apply_settings_*`：不受影响

## 修复状态

执行中（Task #48 ~ #58）。