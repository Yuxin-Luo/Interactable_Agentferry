# 设计稿：v1 摄像头互动桌宠（Camera Pet v1）

**日期**：2026-07-05
**Action**：design
**状态**：✅ 设计确认，进入实施规划阶段

---

## 1. 目标

为 Linux 平台实现一个**摄像头互动桌宠**：打开摄像头识别人脸位置让桌宠跟随头部飞行；识别 6 个 MediaPipe 内置手势（Open_Palm / Thumb_Up / Thumb_Down / Victory / Closed_Fist / Pointing_Up）+ 自定义 pinch，触发对应 GIF / 语音 / 音乐；桌宠大小随人脸距离近/中/远三档自适应；鼠标或 pinch 拖动后桌宠播放 move.gif 自动飞回头部。

**不结合 Claude Code**。定位为陪伴与娱乐。开源协议 **GPL v3**。

---

## 2. 范围

### 2.1 In Scope（v1 必须）

- 单 QMainWindow（frameless + transparent + Tool + StaysOnTop），摄像头画面是底图，桌宠 GIF 透明叠加
- 默认窗口尺寸占主屏 ~90%
- VisionWorker（独立 QThread）：摄像头读取 + FaceLandmarker + GestureRecognizer + HandLandmarker
- PetController（状态机）：DEFAULT_FLY / OPEN_PALM / THUMB_UP / THUMB_DOWN / VICTORY / FIST / POINTING / DRAG_MOUSE / DRAG_PINCH
- 7 类手势响应（6 内置 + pinch），每个手势对应 1 个或多个 GIF + 可选语音
- 鼠标拖动：drag.gif 播放 + 跟随鼠标；松手 move.gif 自动飞回头部
- pinch 拖动：drag.gif 播放 + 跟随食拇指尖；松手 move.gif 自动飞回头部
- 距离档位（near/mid/far）→ pet 缩放（face bbox 宽度阈值）
- 头部排除区：DEFAULT_FLY 时目标点不与脸 bbox 重叠
- 飞行速度可配（默认 50-300 px/s）
- 2s 手势超时回默认
- PEACE 手势触发 ameath.gif + 随机音乐；被打断或音乐结束回默认
- **pinch 鲁棒性**：进入 pinch 状态后保持手部跟踪，**只有 OPEN_PALM 才能终止 pinch**（其他手势在 pinch 期间被忽略）
- **HUD**：画面右上角显示当前识别的手势标签（透明文字，便于用户操作）
- **设置 UI**（飞行速度、距离阈值、pet 大小可视化调节）+ **JSON 持久化**到本地
- 窗口坐标映射：摄像头坐标系 ↔ 窗口坐标系（letterbox 处理）
- 错误处理：摄像头断开 / 模型缺失 / 推理异常（见 §6）

### 2.2 Out of Scope（v1 不做）

- Claude Code 集成（明确不做）
- Galgame 大窗口 / 立绘过场 / BGM 切换
- Windows / macOS 兼容
- 多用户多脸跟踪（只取最近的 1 张脸）
- 端到端自动化测试（按 Rule 10 + CLAUDE.md §6.6）
- macOS / Windows 兼容
- 多用户多脸跟踪（只取最近的 1 张脸）
- 窗口缩放（v1 固定宽高比，仅可拖动）

---

## 3. 架构

### 3.1 总体结构

```
┌─────────────────────────────────────────────────┐
│ CameraPetWindow（单 QMainWindow）                 │
│  ┌─────────────────────────────────────────────┐ │
│  │ CameraLabel（摄像头画面，全窗口背景）         │ │
│  │   ↑                                          │ │
│  │ PetOverlay（透明 QLabel，叠在摄像头之上）     │ │
│  │   ↑                                          │ │
│  │ PetRenderer（维护 pet_position + 当前 GIF）   │ │
│  └─────────────────────────────────────────────┘ │
│                                                  │
│ VisionWorker（独立 QThread）                      │
│   ├─ OpenCV VideoCapture                          │
│   ├─ FaceLandmarker → face_pos / face_size        │
│   ├─ GestureRecognizer → gesture_label            │
│   ├─ HandLandmarker → pinch_active + pinch_pos    │
│   └─ 通过 Qt Signal 把上述结果喂给 PetController  │
│                                                  │
│ PetController（状态机，QObject）                   │
│   输入：gesture_label + pinch_active + mouse_event │
│         + face_pos / face_size                    │
│   输出：pet_position + current_gif + scale        │
└─────────────────────────────────────────────────┘
```

### 3.2 组件职责

| 组件 | 职责 | 复用/新建 |
|---|---|---|
| **CameraPetWindow** | frameless 透明全窗口（**固定宽高比**，不可缩放，可拖动）；显示摄像头画面（letterbox 处理）；鼠标事件 → PetController；订阅 VisionWorker 信号更新 pet 位置与 GIF | 新建 |
| **VisionWorker** (QThread) | 摄像头读取 + 3 个 MediaPipe 推理器；以 ~30fps 推流数据；包含失败处理 | 新建 |
| **FaceTracker** | FaceLandmarker → face_center + face_bbox_size + 平滑（EMA） | 新建 |
| **GestureRecognizer** | MediaPipe GestureRecognizer → 7 类内置手势；N 帧投票平滑 | 新建 |
| **PinchDetector** | HandLandmarker → thumb_tip↔index_tip 距离 + 持续帧数确认 | 新建 |
| **PetController** | 状态机 + 飞行动画插值 + 头部排除区 + 距离档位 | 新建 |
| **GestureMapper** | 手势→动作(GIF + 语音 + 是否循环) 映射表（数据驱动） | 新建 |
| **AppOrchestrator** | main 入口；组装所有组件 + 信号绑定；启动/退出 | 新建（取代 aemeath.main.py） |
| **ConfigManager** | AppSettings 加载/保存 + 视觉字段 | **复用自 My_Code**（扩展字段） |
| **AudioBridge** | 语音/音乐播放 | **复用自 My_Code**（扩展手势方法） |
| **PetRenderer** | 底层 QMainWindow 渲染 | **复用自 My_Code** (`src/pet/window.py`) |

### 3.3 数据流

```
摄像头 (30fps)
   ↓ OpenCV.VideoCapture
VisionWorker.process_frame()
   ├─→ FaceLandmarker.detect_for_video()  → face_center + face_bbox_size
   ├─→ GestureRecognizer.recognize_for_video() → gesture_label (7-class)
   └─→ HandLandmarker.detect_for_video() → pinch_active + pinch_position
   ↓ Qt Signal: vision_update.emit(face, gesture, pinch)
PetController.update()  (主线程)
   ├─→ 状态机：DEFAULT_FLY / OPEN_PALM / THUMB_* / VICTORY / FIST / POINTING / DRAG_MOUSE / DRAG_PINCH
   ├─→ 选择 GIF (animation_player.py)
   ├─→ 飞行动画插值（贝塞尔/直线，速度 50-300 px/s 可配）
   ├─→ 头部排除区判定（DEFAULT_FLY 时目标点不可与脸 bbox 重叠）
   └─→ 距离档位（near/mid/far）→ pet 缩放
   ↓ Qt Signal: pet_render.emit(position, gif, scale)
PetOverlay.update()  (主线程)
   └─→ QLabel.move() + QMovie 切换
```

**关键解耦点**：VisionWorker 只产数据，不下指令；PetController 决定如何响应。

---

## 4. 状态机

### 4.1 状态枚举

```
DEFAULT_FLY       — 默认：move.gif 飞绕头部（不重叠）
OPEN_PALM         — 飞到掌心循环 idle1~4
THUMB_UP          — 原地 screen1.gif
THUMB_DOWN        — 原地 screen4.gif
VICTORY           — 原地 ameath.gif + 随机音乐
FIST              — 原地 screen2.gif
POINTING          — 原地 screen3.gif
DRAG_MOUSE        — drag.gif + 跟随鼠标
DRAG_PINCH        — drag.gif + 跟随食拇指尖
```

### 4.2 状态转移表

| 当前状态 | 事件 | 下一状态 | 备注 |
|---|---|---|---|
| * | 用户鼠标按下 pet | DRAG_MOUSE | drag.gif |
| * | 检测到 PINCH | DRAG_PINCH | drag.gif |
| DRAG_MOUSE | 鼠标松开 | DEFAULT_FLY | move.gif 飞回头部 |
| DRAG_PINCH | PINCH 释放（距离 > 阈值） | DEFAULT_FLY | move.gif 飞回头部 |
| * (非 DRAG_*) | 检测到 OPEN_PALM | OPEN_PALM | idle1~4 循环 |
| * (非 DRAG_*) | 检测到 THUMB_UP | THUMB_UP | screen1.gif 循环 |
| * (非 DRAG_*) | 检测到 THUMB_DOWN | THUMB_DOWN | screen4.gif 循环 |
| * (非 DRAG_*) | 检测到 VICTORY | VICTORY | ameath.gif + 随机音乐 |
| * (非 DRAG_*) | 检测到 FIST | FIST | screen2.gif 循环 |
| * (非 DRAG_*) | 检测到 POINTING | POINTING | screen3.gif 循环 |
| * (非 DRAG_*, 非 VICTORY) | 任何手势 2s 未再检测 | DEFAULT_FLY | move.gif 飞回 |
| VICTORY | 检测到其他手势（除 VICTORY） | 对应手势状态 | 停止音乐 |
| VICTORY | 当前音乐播放完毕 | DEFAULT_FLY | move.gif 飞回 |
| * | 摄像头断开 | IDLE_STANDBY | 桌宠原地待机（move.gif 原地循环） |

### 4.3 手势→动作 映射（来自 dev_doc/1-Ameath-Respursed-Introduction.txt）

| 手势标签 | GIF | 语音 | 是否循环 | 是否启动音乐 |
|---|---|---|---|---|
| OPEN_PALM | idle1~4 轮播 | （无） | 是 | 否 |
| THUMB_UP | screen1.gif | （无） | 是 | 否 |
| THUMB_DOWN | screen4.gif | 嘿嘿.wav | 是 | 否 |
| VICTORY (PEACE) | ameath.gif | 现实系统，侵入完成.wav | 是 | 是（随机选 1 首 MP3） |
| FIST | screen2.gif | （无） | 是 | 否 |
| POINTING_UP | screen3.gif | （无） | 是 | 否 |
| PINCH (自定义) | drag.gif | 嘿嘿.wav | 跟随中 | 否 |
| DEFAULT_FLY | move.gif | 看这里.wav / 你，看见我了.wav / 嘿嘿.wav / 嗯，嘿嘿.wav（随机 1 首） | 是 | 否 |

---

## 5. 数据结构

### 5.1 VisionSignal（VisionWorker 输出）

```python
@dataclass
class VisionSignal:
    face_center: Optional[QPoint]   # 摄像头画面坐标系；None = 未检测到脸
    face_bbox_size: Optional[QSize] # 脸 bounding box 大小（px）；用于档位判定
    gesture_label: str              # "None" / "Open_Palm" / "Thumb_Up" / "Thumb_Down" /
                                    #  "Victory" / "Closed_Fist" / "Pointing_Up" / "PINCH"
    gesture_hand_pos: Optional[QPoint]  # 手势对应的手部中心（摄像头画面坐标系）
    pinch_active: bool              # 是否捏合
    pinch_position: Optional[QPoint]    # 食拇指尖中点（摄像头画面坐标系）
```

### 5.2 RenderCommand（PetController 输出）

```python
@dataclass
class RenderCommand:
    position: QPoint    # 桌宠左上角（窗口坐标系）
    gif_path: str       # 资源相对路径
    scale: float        # 缩放系数 0.5~2.0
```

### 5.3 AppSettings 新增字段

```python
@dataclass
class VisionSettings:
    cam_resolution: tuple = (1280, 720)
    cam_fps: int = 30
    cam_device_index: int = 0
    flight_speed_min: int = 50       # px/s
    flight_speed_max: int = 300      # px/s
    gesture_hold_timeout: float = 2.0  # s
    face_tier_thresholds: tuple = (80, 160)  # (mid_max, near_min) in px
    pet_size_near: float = 1.5
    pet_size_mid: float = 1.0
    pet_size_far: float = 0.6
    head_exclusion_padding: float = 0.2  # 脸 bbox 外扩比例
    pinch_distance_threshold: float = 0.05  # 归一化距离（thumb tip ↔ index tip）
    pinch_hold_frames: int = 3       # 连续多少帧确认 pinch
    settings_persistence_path: str = "~/.config/interactable_agentferry/settings.json"  # JSON 持久化路径
```

---

## 6. 错误处理

| 错误场景 | 应对 |
|---|---|
| 摄像头无法打开 | 启动时显示错误对话框，提示"无摄像头设备"；可选择"重试"或"退出" |
| 摄像头中途断开 | 桌宠切回"idle 待机"（move.gif 原地循环），提示用户检查摄像头 |
| MediaPipe 模型加载失败 | 启动报错退出，附带"模型文件缺失"提示和 assets/models/ 路径 |
| 模型文件缺失 | assets/models/ 缺失 .task → 启动时报错退出（不自动下载，避免引入网络依赖） |
| MediaPipe 推理异常（极少见） | 单帧异常 → 跳过该帧，输出上一帧结果；连续 30 帧异常 → 切回"idle 待机" |
| 配置加载失败 | 用默认值启动 + 警告日志 |
| 鼠标拖出窗口边界 | 钳制到窗口内（不允许飞出，与 A1 决策一致） |
| 窗口拖动后坐标映射错误 | 摄像头坐标系 (1280×720) → 窗口坐标系（letterbox）→ 屏幕坐标系；用 `scale = min(ww/cw, wh/ch)` + 偏移量计算（详见 §11 Q4） |
| 人脸走出画面 | pet_size → 0.6 (far)；face 完全消失 → pet 隐藏（直到重新检测到） |

---

## 7. 分阶段交付

| 阶段 | 内容 | 验证方式 |
|---|---|---|
| **P1** | 单窗口骨架：frameless + 摄像头画面 | 手动跑 `python src/camera/main.py`，看到摄像头预览 |
| **P2** | FaceLandmarker 接入 → 桌宠默认 follow face（move.gif） | 手动跑，前后移动看桌宠大小变化 |
| **P3** | GestureRecognizer 接入 → 6 个手势触发对应 GIF | 手动逐个手势测试 |
| **P4** | HandLandmarker + PinchDetector → pinch 拖动模式 | 手动捏合手指看 drag.gif 跟随 |
| **P5** | 鼠标拖动 + 自动飞回（drag.gif + move.gif） | 手动鼠标拖动桌宠 |
| **P6** | 距离档位（near/mid/far）→ pet 缩放 | 手动前后移动 |
| **P7** | 语音/音乐集成（PEACE → 随机音乐） | 手动比 PEACE 手势 |
| **P8** | 头部排除区 + 飞行速度可配 | 手动看桌宠是否绕开脸部 |
| **P9** | pinch 鲁棒性（OPEN_PALM 终止）+ HUD 显示 | 手动捏合 + 比其他手势，看是否保持 pinch |
| **P10** | 设置 UI（飞行速度、距离阈值、pet 大小）+ JSON 持久化 | 手动调节参数 → 关闭重启 → 验证保留 |

---

## 8. 测试纪律（CLAUDE.md §6.5/§6.6）

### 8.1 单元测试（白盒，可纳入 CI）

| 测试目标 | 测试方法 |
|---|---|
| 距离档位判定（near/mid/far） | 给定 face_bbox_size，断言返回的 tier |
| 状态机转换 | 给定当前状态 + 事件，断言下一状态 |
| 头部排除区计算 | 给定 face bbox，断言所有候选目标点都不在排除区 |
| 飞行动画插值 | 给定起点 + 终点 + 速度 + 时间，断言中点位置 |
| 手势平滑窗口 | 模拟 N 帧序列，断言最终输出 |
| Pinch 距离判定 | 给定 21 个 landmarks，断言 pinch_active |

### 8.2 集成测试（不做）

启动摄像头 → 等待识别 → 断言 → 关闭。**禁止**（太慢 + Rule 10 + CLAUDE.md §6.6）。

### 8.3 验证方式（手动 demo）

每个 P 阶段完成后，手动跑 `python src/camera/main.py`，观察摄像头画面是否符合预期。

---

## 9. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| MediaPipe 模型文件丢失或版本不匹配 | 中 | 高（v1 阻塞） | 启动时校验文件存在；提供下载脚本到 assets/models/ |
| GestureRecognizer 误判率高 | 中 | 中（手 1 / 手 2） | N=5 帧投票平滑；置信度阈值 |
| 摄像头帧率不足（<20fps） | 低 | 高（识别卡顿） | 摄像头分辨率降到 640x480；CPU 推理够用，无需 GPU |
| PyQt6 透明窗口在某些 WM 下不渲染 | 低 | 中 | v1 仅承诺 X11 兼容；Wayland 不在范围 |
| 用户长时间不互动导致音乐循环单调 | 低 | 低 | music_timer.py 已有随机选曲逻辑 |
| PetController 状态机 bug | 中 | 中 | 单元测试覆盖所有状态转换 |

---

## 10. 复用与依赖

### 10.1 复用来源

| 来源 | 复用内容 | License |
|---|---|---|
| My_Code/Desktop_Agentferry | `src/pet/window.py`、state_machine、animation_player、sound_manager、config/settings、x11_binding、assets/ameath/* | GPL v3（自有版权） |
| MediaPipe-Real-Time-Computer-Vision-Demos | 模型 .task 文件 + demo 参考 | MIT |
| MonkeyMeme-Gesture_Tracker | 手势分类算法参考（`src/vision/reference/gesture_classifier_ref.py`） | 无显式 LICENSE，按 MIT-like 处理 |

详见 `Reference/README.md` §4。

### 10.2 新增 Python 依赖

```text
PyQt6>=6.6
python-xlib>=0.33
mediapipe>=0.10.14
opencv-python>=4.8
```

---

## 11. 开放问题（实施时确认）

- **Q1**（已确认）：双手检测冲突时取置信度最高的手。
- **Q2**（已确认）：VICTORY 手势的音乐打断定义为"检测到任何其他手势（除 VICTORY）→ 停止音乐"。
- **Q3**（已确认）：桌宠保留 10% 安全边距（不超出画面 90%）。
- **Q4**（已确认）：v1 窗口**固定宽高比**，禁止缩放（仅可拖动）；拖动窗口后坐标系转换通过 letterbox 偏移量计算。公式：给定窗口尺寸 `(ww, wh)` 和摄像头尺寸 `(cw, ch)`，`scale = min(ww/cw, wh/ch)`，`offset_x = (ww - cw*scale)/2`，`offset_y = (wh - ch*scale)/2`；窗口坐标 `(x_win, y_win)` ↔ 摄像头坐标 `(x_cam, y_cam) = ((x_win - offset_x)/scale, (y_win - offset_y)/scale)`。
- **Q5**（已确认）：pinch 鲁棒性采用**状态机锁定**：进入 pinch 状态后，**只要手部仍在画面内，无论什么手势都保持 pinch** 并持续跟踪手部坐标进行移动；**只有 OPEN_PALM 才能终止 pinch 状态**。同时 HUD（画面右上角透明文字）显示当前识别的手势标签，便于用户确认操作状态。

---

## 12. 后续版本（v2+ 备选）

- 多人模式（多只桌宠 + 跟人脸分配）
- 自定义 GIF 资源上传
- 窗口缩放（v1 固定比例）
- macOS / Windows 兼容（需要重写透明窗口层）
- 录制互动视频 / GIF 分享

---

*设计者：Claude · 决策依据：用户对话 + dev_doc/1-Ameath-Respursed-Introduction.txt + dev_doc/2-decision-bootstrap-copy-and-scaffold-2026-07-05.md*