# Reference — 来源与复用索引

> **本目录是只读参考区**。所有代码/资源如需复用，按 `Agent Rules.txt` §8 与本目录 README 的"复用映射"表操作（深复制到 `src/` 或 `assets/`，**禁止原地修改 Reference 内任何文件**）。

---

## 1. 目录布局

```
Reference/
├── My_Code/Desktop_Agentferry/    ← 用户上一版桌宠实现（GPL v3，本项目基石）
└── code/                          ← 6 个外部开源参考项目
    ├── ameath/                    MIT — 形象/动效/状态机（资源已通过 My_Code 复用）
    ├── banban-desktop-pet/         无 LICENSE — 借鉴架构（Python↔桌宠闭环）
    ├── gum-gum-hand-stretch/       无 LICENSE — 借鉴 ARAP 思路（未直接复用）
    ├── makocode/                   MIT — Galgame 风格 UI（不适用）
    ├── MediaPipe-Real-Time-Computer-Vision-Demos/   MIT — MediaPipe Tasks API 参考 + 模型
    └── MonkeyMeme-Gesture_Tracker/ 无 LICENSE — 手势分类算法参考
```

---

## 2. 项目目标（一句话）

**Linux 平台摄像头互动桌宠**：打开摄像头识别人脸位置让桌宠跟随；识别 6 个 MediaPipe 内置手势 + 自定义 pinch，触发对应 GIF/语音/音乐动作；桌宠大小随距离自适应；鼠标/捏合拖动后自动飞回脸部。**不结合 Claude Code**，定位为陪伴与娱乐。开源协议 **GPL v3**。

---

## 3. 按需求检索（"我要做 X，先看 Y"）

| 需求 | 优先看 | 次要看 |
|---|---|---|
| 摄像头开启 + 预览 | Reference/code/MediaPipe-Real-Time-Computer-Vision-Demos/face_detection.py | Reference/code/banban-desktop-pet/emotion_watch.py |
| 人脸检测与跟随 | MediaPipe-Real-Time-Computer-Vision-Demos/face_detection.py | MonkeyMeme-Gesture_Tracker/gesture-tracker.py (face landmark 用法) |
| 手势识别（6 类内置） | MediaPipe-Real-Time-Computer-Vision-Demos/hand_tracking.py | MonkeyMeme-Gesture_Tracker/gesture-tracker.py (自定义分类思路) |
| Pinch（食拇捏）检测 | gum-gum-hand-stretch/gumgum.py (抓取状态机) | MonkeyMeme-Gesture_Tracker/gesture-tracker.py (指尖距离判定) |
| 桌宠 GIF 渲染 + 拖动 | My_Code/Desktop_Agentferry/src/pet/window.py | Reference/code/ameath (Tkinter 版本，不直接复用) |
| 桌宠状态机 | My_Code/Desktop_Agentferry/src/pet/state_machine.py | — |
| 语音/音乐播放 | My_Code/Desktop_Agentferry/src/pet/sound_manager.py | — |
| 配置持久化 | My_Code/Desktop_Agentferry/src/config/settings.py | — |
| 透明置顶窗口 + X11 集成 | My_Code/Desktop_Agentferry/src/utils/x11_binding.py | banban-desktop-pet (Electron, 思路借鉴) |
| 资源（GIF/WAV/MP3） | My_Code/Desktop_Agentferry/assets/ameath/ | Reference/code/ameath/gifs (相同资源，ameath 原始出处) |

---

## 4. 复用映射（已深复制到本项目 `src/` / `assets/`）

每条复制都附带 attribution header（在文件首部），保留原作者版权与 License 声明。

### 4.1 从 My_Code/Desktop_Agentferry（GPL v3，作者本人）

| 来源 | 目标 | 备注 |
|---|---|---|
| `src/pet/window.py` | `src/pet/window.py` | frameless 透明窗口 + 鼠标拖动 |
| `src/pet/animation_player.py` | `src/pet/animation_player.py` | GIF 状态映射 |
| `src/pet/state_machine.py` | `src/pet/state_machine.py` | 状态机基类 |
| `src/pet/idle_rotator.py` | `src/pet/idle_rotator.py` | IDLE 轮播（本项目默认不用 idle 轮播，保留备用） |
| `src/pet/sound_manager.py` | `src/pet/sound_manager.py` | 语音/音乐 |
| `src/pet/hover_bubble.py` | `src/pet/hover_bubble.py` | 悬停气泡（v1 可选） |
| `src/pet/music_timer.py` | `src/pet/music_timer.py` | 音乐定时（v1 可选） |
| `src/pet/menu.py` | `src/pet/menu.py` | 右键菜单 |
| `src/config/settings.py` | `src/config/settings.py` | 配置（需新增视觉字段） |
| `src/utils/x11_binding.py` | `src/utils/x11_binding.py` | X11 绑定（v1 可选） |
| `assets/ameath/gifs/*.gif` | `assets/ameath/gifs/*.gif` | 11 个 GIF |
| `assets/ameath/sound/voice/*.wav` | `assets/ameath/sound/voice/*.wav` | 8 个语音 |
| `assets/ameath/sound/music/*.mp3` | `assets/ameath/sound/music/*.mp3` | 5 个背景乐 |

**不复制（与新项目无关）**：My_Code 下的 `src/cli/`、`src/chat/`、`src/llm/`、`src/aemeath/main.py`（Claude Code 子树）。`src/aemeath/main.py` 的 Orchestrator 角色由本项目新的 `src/camera/main.py` 取代。

### 4.2 从 MediaPipe-Real-Time-Computer-Vision-Demos（MIT）

| 来源 | 目标 | 备注 |
|---|---|---|
| `models/face_landmarker.task` | `assets/models/face_landmarker.task` | 3.6 MB，官方模型 |
| `models/hand_landmarker.task` | `assets/models/hand_landmarker.task` | 7.5 MB，官方模型 |
| `models/blaze_face_short_range.tflite` | `assets/models/blaze_face_short_range.tflite` | 备用轻量脸检测 |
| `face_detection.py` | `src/vision/reference/face_detection_ref.py` | 参考实现，不参与运行 |
| `hand_tracking.py` | `src/vision/reference/hand_tracking_ref.py` | 参考实现 |
| `holistic_tracking.py` | `src/vision/reference/holistic_tracking_ref.py` | 参考 pipeline 布局 |

### 4.3 从 MonkeyMeme-Gesture_Tracker（无显式 LICENSE，按 MIT-like 处理）

| 来源 | 目标 | 备注 |
|---|---|---|
| `gesture-tracker.py` | `src/vision/reference/gesture_classifier_ref.py` | 手势分类算法参考 |

### 4.4 仅借鉴、不复制

| 项目 | 借鉴点 | 不复制原因 |
|---|---|---|
| `banban-desktop-pet` | Python↔Electron 通过 JSON 文件轮询的解耦模式 | 本项目全 Python，IPC 用 Qt Signal 即可 |
| `gum-gum-hand-stretch` | ARAP 网格变形 + GrabFX 状态机 | 不需要 ARAP；捏取用 MediaPipe Hand Landmarker 距离判定 |
| `makocode` | Galgame 风格 UI（角色立绘 + BGM） | 本项目是轻量桌宠，不需要 Galgame 大窗口 |
| `ameath` (Tkinter 版本) | 动效语义表（已在 dev_doc/1 中整理） | 不同技术栈（Tkinter），代码不可直接复用；资源已通过 My_Code 复用 |

---

## 5. 资源总览（本项目 `assets/ameath/`）

### 5.1 GIF（11 个）

| 文件 | 用途（dev_doc/1 标注） |
|---|---|
| `idle1.gif` | 叹气左顾右盼（OPEN_PALM 循环变体） |
| `idle2.gif` | 睁大眼睛看（OPEN_PALM 循环变体） |
| `idle3.gif` | 开心举右手跳（OPEN_PALM 循环变体） |
| `idle4.gif` | 不断举手欢呼（OPEN_PALM 循环变体） |
| `drag.gif` | 扑动翅膀（鼠标拖动 / pinch 拖动期间） |
| `ameath.gif` | 戴墨镜随音乐点头（PEACE 手势 + 音乐） |
| `move.gif` | ameath 自己飞行（默认头部附近飞行） |
| `screen1.gif` | 跃跃欲试（THUMBS_UP） |
| `screen2.gif` | 按按钮（FIST） |
| `screen3.gif` | 疑惑不解（POINTING_UP） |
| `screen4.gif` | 嚎啕大哭（THUMBS_DOWN） |

### 5.2 Voice WAV（8 个）

| 文件 | 触发动作 |
|---|---|
| `嘿嘿.wav` | drag / move |
| `看这里.wav` | idle2 / move |
| `嗯.wav` | idle1 |
| `嗯，嘿嘿.wav` | idle3 / idle4 / move |
| `嗯，哼哼.wav` | idle3 / idle4 / move |
| `你，看见我了.wav` | idle2 / move |
| `现实系统，侵入完成.wav` | ameath / move |
| `一起去拯救世界吧.wav` | ameath |

### 5.3 Music MP3（5 个）

`那颗星梦见的春日.mp3`、`碎花.mp3`、`远航星的告别.mp3`、`纸飞机.mp3`、`DJ花荣Remix - 岁月无声（DJ花荣版）.mp3` — PEACE 手势触发时随机播放一首。

### 5.4 模型文件（3 个）

`face_landmarker.task`（脸检测 + 468 landmarks）、`hand_landmarker.task`（手部 21 landmarks）、`blaze_face_short_range.tflite`（备用轻量脸检测）。

---

## 6. License 合规摘要

| 复用来源 | License | 是否需要署名 | 是否影响本项目 GPL v3 |
|---|---|---|---|
| My_Code/Desktop_Agentferry（自己的代码） | GPL v3 | 不需要（自有版权） | 保持 GPL v3 |
| MediaPipe-Real-Time-Computer-Vision-Demos | MIT | 是（已在 attribution header） | 不影响 GPL v3 |
| MonkeyMeme-Gesture_Tracker | 无显式声明（按 MIT-like） | 是（已在 attribution header） | 不影响 |
| ameath（资源） | MIT | 资源随 My_Code 一并复制，My_Code 内部已署名 | 不影响 |

**GPL v3 兼容性结论**：MIT 与 GPL v3 兼容。所有复制到本项目的参考代码与资源，符合本项目 GPL v3 协议。

---

## 7. 禁止事项

- ❌ 在 `Reference/` 任何子目录下修改文件（只读参考区）
- ❌ 删除或模糊化已复制文件顶部的 attribution header
- ❌ 复制未在本表 §4 列出的参考项目代码（要复制先更新本 README）
- ❌ 引入新依赖而不在 `requirements.txt` 中登记