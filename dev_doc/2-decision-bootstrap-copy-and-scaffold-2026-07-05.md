# 决策记录：v1 启动 — 复制复用与脚手架

**日期**：2026-07-05
**阶段**：v1 设计阶段（架构已确认，代码尚未实现）
**Action**：decision
**状态**：✅ 已执行

---

## 1. 决策概要

为 `Interactable_Agentferry` 项目 v1 启动做了三件事：

1. **深复制** 从 `Reference/My_Code/Desktop_Agentferry` 和 `Reference/code/*` 中可直接复用的代码、资源、模型到 `src/` 与 `assets/`
2. **创建** `Reference/README.md`：项目目标 + 按需求检索表 + 复用映射 + License 合规
3. **创建** 项目根 `CLAUDE.md`：基于 My_Code 的 CLAUDE.md 模板，移除 Claude Code 相关约束，加入视觉管线约束

---

## 2. 关键决策记录

### D-1：项目定位为新建项目（不扩展 My_Code）

| 选项 | 选择 |
|---|---|
| 扩展 My_Code（在原项目加 camera 子模块） | ❌ |
| 新建 Interactable_Agentferry 项目，剔除 Claude Code 子树 | ✅ |

**Why**：用户明确"这个版本的 Ameath 不结合 Claude Code"。新项目结构清晰，避免误引入 Claude Code 依赖（anthropic SDK、CLI 子进程等）。

### D-2：手势识别后端 = 双管线（GestureRecognizer + HandLandmarker）

| 选项 | 选择 |
|---|---|
| 单 HandLandmarker + 自写规则 | ❌ |
| 双管线（GestureRecognizer 6 内置 + HandLandmarker pinch） | ✅ |
| 仅 GestureRecognizer | ❌（pinch 无法识别） |

**Why**：6 个内置手势走官方分类器准确率高；pinch 必须 HandLandmarker 算关键点距离。

### D-3：人脸距离估算 = 粗粒度三档（near/mid/far）

| 选项 | 选择 |
|---|---|
| 假设脸宽 15cm + 摄像头 FOV 算绝对距离 | ❌ |
| 纯脸部宽度相对量 | ❌ |
| 首次校准 + 脸宽 | ❌ |
| 粗粒度档位（near/mid/far 阈值） | ✅ |

**Why**：避免不准确的物理计算；最简；用户需求是"大小自适应"而非"精确测量"。

### D-4：窗口架构 = 单 QMainWindow（摄像头画面 + 桌宠叠加）

| 选项 | 选择 |
|---|---|
| 双窗口（摄像头 + 桌宠独立透明窗口） | ❌ |
| 单窗口叠加 | ✅ |

**Why**：用户场景是"纯娱乐陪伴"，摄像头画面默认接近全屏是主舞台；双窗口会让桌面交互复杂化；A1 决策（鼠标拖动后飞回，无跨窗口需求）。

### D-5：复用策略 = 深复制 + attribution header

| 选项 | 选择 |
|---|---|
| 仅 import（保留 Reference/ 原文件） | ❌ |
| 深复制到 src/ + attribution header | ✅ |

**Why**：用户明确"都需直接深复制到 src 目录下"；物理复制让 src/ 自包含，便于开源发布；attribution header 满足 License 要求。

### D-6：pinch 保留为拖动模式（不放进 6 个 MediaPipe 内置手势）

**Why**：MediaPipe GestureRecognizer 内置 7 类不含 pinch；pinch 必须 HandLandmarker + 自定义距离判定。决策：保留 pinch 作为第 7 类手势（自定义）。

### D-7：场景 A — 纯娱乐/陪伴专用

| 选项 | 选择 |
|---|---|
| 场景 A：纯娱乐，摄像头默认全屏 | ✅ |
| 场景 B：工作间隙可切换 | ❌ |
| 场景 C：工作时也看摄像头 | ❌ |

**Why**：用户选择 A；摄像头画面作为主舞台是核心卖点。

---

## 3. 已执行的操作清单

### 3.1 复制的代码（来自 My_Code/Desktop_Agentferry，GPL v3）

- `src/pet/window.py` — frameless 透明窗口基类
- `src/pet/animation_player.py` — GIF 状态映射
- `src/pet/state_machine.py` — 状态机基类
- `src/pet/idle_rotator.py` — IDLE 轮播（备用）
- `src/pet/sound_manager.py` — 语音/音乐
- `src/pet/hover_bubble.py` — 悬停气泡（备用）
- `src/pet/music_timer.py` — 音乐定时（备用）
- `src/pet/menu.py` — 右键菜单
- `src/config/settings.py` — 配置（待扩展视觉字段）
- `src/utils/x11_binding.py` — X11 绑定（备用）
- `assets/ameath/gifs/*.gif` — 11 个 GIF
- `assets/ameath/sound/voice/*.wav` — 8 个语音
- `assets/ameath/sound/music/*.mp3` — 5 个背景乐
- `LICENSE` — GPL v3

### 3.2 复制的参考代码（带 attribution header）

- `src/vision/reference/face_detection_ref.py` ← `Reference/code/MediaPipe-Real-Time-Computer-Vision-Demos/face_detection.py`（MIT）
- `src/vision/reference/hand_tracking_ref.py` ← `MediaPipe-Real-Time-Computer-Vision-Demos/hand_tracking.py`（MIT）
- `src/vision/reference/holistic_tracking_ref.py` ← `MediaPipe-Real-Time-Computer-Vision-Demos/holistic_tracking.py`（MIT）
- `src/vision/reference/gesture_classifier_ref.py` ← `Reference/code/MonkeyMeme-Gesture_Tracker/gesture-tracker.py`（无显式 LICENSE，按 MIT-like 处理）

### 3.3 复制的模型

- `assets/models/face_landmarker.task` ← `MediaPipe-Real-Time-Computer-Vision-Demos/models/face_landmarker.task`
- `assets/models/hand_landmarker.task` ← `MediaPipe-Real-Time-Computer-Vision-Demos/models/hand_landmarker.task`
- `assets/models/blaze_face_short_range.tflite` ← `MediaPipe-Real-Time-Computer-Vision-Demos/models/blaze_face_short_range.tflite`（备用）

### 3.4 创建的文档

- `CLAUDE.md` — 项目 agent 手册
- `Reference/README.md` — 参考代码索引与复用映射
- `requirements.txt` — Python 依赖（移除 anthropic，新增 mediapipe + opencv-python）

---

## 4. 待办（进入开发阶段前）

- [ ] 在 `src/config/settings.py` 中新增视觉相关字段（flight_speed, gesture_hold_timeout, face_tier_thresholds, pet_size_near/mid/far, cam_resolution, cam_fps）
- [ ] 实现 `src/vision/worker.py`（VisionWorker QThread）
- [ ] 实现 `src/vision/pipelines.py`（FaceTracker / GestureRecognizer / PinchDetector）
- [ ] 实现 `src/pet/controller.py`（PetController 状态机）
- [ ] 实现 `src/camera/window.py`（CameraPetWindow 单窗口）
- [ ] 实现 `src/camera/main.py`（AppOrchestrator 入口）
- [ ] 写 `dev_doc/3-design-camera-pet-v1-2026-07-05.md`（详细设计稿）
- [ ] 写 `dev_doc/4-plan-camera-pet-v1-2026-07-05.md`（实施计划）
- [ ] 初始化 git 仓库 + 提交

---

## 5. 未解决问题

- **Q1**：双手检测冲突时取谁？默认取置信度最高的手。需在实现时验证 MediaPipe GestureRecognizer 的输出格式。
- **Q2**：PEACE 手势的音乐播放打断逻辑——"被打断"如何定义？是检测到任何其他手势？还是任意帧的脸部丢失？需要在 PetController 中明确。
- **Q3**：桌宠在摄像头画面边缘被裁剪时如何处理？建议保留"安全边距"（pet 不超出画面 90%）。

---

*记录人：Claude · 决策依据：用户对话 + dev_doc/1-Ameath-Respursed-Introduction.txt*