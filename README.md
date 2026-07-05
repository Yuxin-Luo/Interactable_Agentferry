# Interactable Agentferry

> Linux 平台**摄像头互动桌宠**——打开摄像头识别人脸位置，让桌宠跟随你的头部飞行；识别 6 个 MediaPipe 内置手势 + 自定义 pinch 触发对应 GIF / 语音 / 音乐；桌宠大小随距离自适应；鼠标或 pinch 拖动后自动飞回头部。

**Amearth** 是一只圆滚滚的小家伙。它看见你就飞过来；你冲它比手势，它会停下来回应你的情绪。

---

## ✨ 功能

- **人脸跟踪**：桌宠自动飞到屏幕中你头部附近（避开重叠 20% 边距）
- **6 个 MediaPipe 内置手势识别**：
  | 手势 | 桌宠反应 |
  |---|---|
  | 🖐️ `Open_Palm`（张开手掌） | 飞到掌心，循环 idle1~4 |
  | 👍 `Thumb_Up` | 原地 screen1.gif |
  | 👎 `Thumb_Down` | 原地 screen4.gif + 嘿嘿.wav |
  | ✌️ `Victory`（胜利） | 原地 ameath.gif + 随机一首 MP3 + 嘿嘿.wav |
  | ✊ `Closed_Fist`（握拳） | 原地 screen2.gif |
  | ☝️ `Pointing_Up`（食指） | 原地 screen3.gif |
- **自定义 pinch**（拇指 + 食指捏合）：拖动桌宠，松手自动飞回
- **三档距离自适应**：脸近 → 桌宠变大；脸远 → 桌宠变小（基于 face bbox 宽度）
- **鼠标拖动**：右键桌宠也能拖，松手自动飞回
- **设置面板**：右键菜单 → Settings，调飞行速度 / 距离阈值 / 桌宠大小（自动持久化到 `~/.config/interactable_agentferry/settings.json`）
- **HUD 角标**：右上角实时显示识别到的手势标签

---

## 🖥️ 系统要求

| 项目 | 要求 |
|---|---|
| OS | **Ubuntu 22.04.5 LTS**（其它 Linux 发行版未验证） |
| 窗口系统 | **X11**（Wayland 未测试） |
| Python | 3.10+ |
| 硬件 | 推荐 ≥ i5 + 8 GB RAM，RTX 4060 实测流畅；纯 CPU 也能跑（30fps 略掉） |
| 摄像头 | 任意 V4L2 兼容设备（笔记本内置 / USB） |

---

## 🚀 快速开始

### 1. 克隆 & 装依赖

```bash
git clone https://github.com/Yuxin-Luo/Interactable_Agentferry.git
cd Interactable_Agentferry
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 下载 MediaPipe 模型（首次运行必须）

```bash
bash scripts/download_models.sh
```

会下载 4 个模型到 `assets/models/`（共约 19 MB）：

| 模型 | 用途 |
|---|---|
| `face_landmarker.task` | 人脸检测 + 478 个关键点 |
| `hand_landmarker.task` | 手部 21 个关键点（pinch 用） |
| `gesture_recognizer.task` | 6 类手势分类 |
| `blaze_face_short_range.tflite` | 备用快速人脸检测 |

> ⚠️ 这 4 个模型已加入 `.gitignore`，请勿手动提交。

### 3. 启动

```bash
python src/camera/main.py
```

首次启动会自动创建 `~/.config/interactable_agentferry/settings.json`。窗口大小默认占主屏 ~90%，右上角出现 HUD，左上角显示摄像头画面，桌宠飞过来迎接你。

---

## 🎮 使用

| 操作 | 效果 |
|---|---|
| **靠近 / 远离摄像头** | 桌宠大小自动调整 |
| **挥挥手** | 桌宠飞过来跟你玩 |
| **比手势** | 桌宠切换到对应动画 + 播放语音/音乐 |
| **鼠标拖桌宠** | 进入拖动模式，松手后飞回头部 |
| **捏合（pinch）拖桌宠** | 同上，松手自动飞回 |
| **松开捏合（变 Open_Palm）** | 显式结束拖动 |
| **在窗口任意位置右键** | 弹出菜单 → Settings 打开设置面板 |
| **ESC / 关窗口** | 退出 |

### 设置面板可调

- **飞行速度**（min / max px/s）
- **距离档位阈值**（mid / near 分界 face bbox 宽度）
- **桌宠大小**（near / mid / far 三档相对比例）

改动实时生效并写回配置文件。

---

## 🏗️ 架构

```
src/
├── camera/        ← 主窗口 + 入口（PyQt6）
│   ├── window.py     CameraPetWindow（无边框 + 透明 + 始终置顶）
│   └── main.py       AppOrchestrator（组装所有组件）
├── vision/        ← 视觉管线（独立 QThread）
│   ├── worker.py     VisionWorker（摄像头读取 + 30fps 信号推送）
│   ├── pipelines.py  FaceTracker / PinchDetector
│   └── reference/    （保留参考实现）
├── pet/           ← 桌宠核心
│   ├── controller.py       状态机（9 个状态）+ 飞行控制
│   ├── gesture_mapper.py   手势 → 动作 数据表
│   ├── gesture_smoother.py N 帧投票去抖
│   ├── flight.py           速度钳制插值
│   ├── head_exclusion.py   避开头部 20% 边距
│   ├── distance_tier.py    三档距离判定
│   ├── settings_store.py   JSON 持久化
│   └── settings_dialog.py  设置面板 UI
├── config/
│   └── settings.py         AppSettings + VisionSettings dataclass
└── utils/
    ├── coordinate_map.py   摄像头坐标 → 窗口坐标（letterbox）
    └── x11_binding.py      X11 窗口绑定（来自参考项目）
```

**线程模型：**
- **主线程**：PyQt6 UI 渲染 + 桌宠动画 + 设置面板
- **VisionWorker QThread**：OpenCV 读摄像头 + MediaPipe 推理（face / hand / gesture 三模型并行），每帧通过 Qt Signal 推送 `VisionSignal` + `QImage`
- **PetController** 在主线程消费信号，做状态机 + 飞行插值 + 渲染指令

详见 `dev_doc/4-plan-camera-pet-v1-2026-07-05.md`（v1 完整实施规划，28 个任务）。

---

## 🧪 测试

```bash
pip install -r requirements.txt   # pytest + pytest-qt
python -m pytest tests/ -q
```

当前 **70 个单元测试** 通过（覆盖距离档位 / 坐标映射 / 人脸跟踪 / pinch / 飞行 / 状态机 / 设置存储 / 设置面板等纯逻辑模块）。

> 不含端到端摄像头测试（Agent Rules Rule 10：避免启动摄像头 → 等待识别 → 断言的慢测试）。视觉部分请手动跑 demo 验证。

---

## 📁 资源结构

```
assets/
├── ameath/
│   ├── gifs/      11 个桌宠 GIF（idle1~4 / drag / ameath / move / screen1~4）
│   └── sound/
│       ├── voice/ 8 个 WAV
│       └── music/ 5 个 MP3
└── models/        4 个 MediaPipe 模型（gitignore，运行时下载）
```

---

## 🛠️ 常见问题

**Q：启动后窗口全黑？**
A：摄像头未打开或被其它程序占用。检查 `dmesg | grep -i usb`、确认 `/dev/video0` 存在、关闭其它使用摄像头的应用。

**Q：识别不到手势？**
A：保持手在摄像头视野中央，距离 50-80 cm，光线充足。HUD 角标会显示当前识别状态。

**Q：模型下载失败？**
A：`scripts/download_models.sh` 用的是 Google Storage CDN。若网络不通，可手动从 [MediaPipe Models](https://developers.google.com/mediapipe) 下载 4 个文件到 `assets/models/`。

**Q：拖动后桌宠不飞回来？**
A：检查 Settings 面板里的飞行速度（min 不能为 0）；查看终端日志是否有 `PetController` 报错。

---

## 📜 协议

**GPL v3**。详见 [LICENSE](LICENSE)。

参考实现位于 `Reference/`（gitignore，~1.3 GB），仅作只读参考；要复用代码请抄到 `src/` 并保留原作者版权头。

---

## 🙏 致谢

- [MediaPipe](https://developers.google.com/mediapipe) — Face / Hand Landmarker + Gesture Recognizer
- [OpenCV](https://opencv.org/) — 摄像头读取
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — UI 框架
- `My_Code/Desktop_Agentferry` — 上一版桌宠基线（GPL v3）
- MediaPipe-Real-Time-Computer-Vision-Demos — 参考实现