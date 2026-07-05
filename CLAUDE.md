# Interactable Agentferry / Amearth Camera — CLAUDE.md

> 这是给 **所有 Claude agent**（包括我自己）的工作手册。接到本项目任何任务前，**先读本文件 + `Agent Rules.txt` + `Reference/README.md` §3 检索表**。

---

## 1. 项目是什么（一句话）

**Linux 平台摄像头互动桌宠**：打开摄像头识别人脸位置让桌宠跟随头部飞行；识别 6 个 MediaPipe 内置手势（Open_Palm / Thumb_Up / Thumb_Down / Victory / Closed_Fist / Pointing_Up）+ 自定义 pinch，触发对应 GIF / 语音 / 音乐；桌宠大小随人脸距离近/中/远三档自适应；鼠标或 pinch 拖动后桌宠播放 move.gif 自动飞回头部。**不结合 Claude Code**，定位为陪伴与娱乐。开源协议 **GPL v3**。

详细需求与设计约束见 `Reference/README.md`（已包含参考代码的逐项导读与"按需求检索"表）。

---

## 2. ⛔ 最高指令：`Agent Rules.txt` 是不可越线的

**`Agent Rules.txt` 是项目宪法。** 10 条规则逐条要遵守；任何与本文件冲突时，**以 Rules.txt 为准**。摘要：

| # | 规则 | 关键动作 |
|---|------|---------|
| 1 | 目标不清 → 停下来问 | 不假设用户知道自己想要什么 |
| 2 | 路径不是最短 → 告诉我 | 主动建议更优解 |
| 3 | 找根因，不打补丁 | 每个决策都能回答"为什么" |
| 4 | 输出说重点 | 砍掉不改变决策的信息 |
| 5 | API 限速 | RPM < 200, TPM < 10,000,000 |
| 6 | **每个开发/调研任务都要留 dev-doc** | 命名：`N-<action>-<desc>-YYYY-MM-DD.md` |
| 7 | **调研时维护参考资料索引** | XML 或 JSON 格式，存到 `dev_doc/` |
| 8 | **代码全部在 `src/`**；连续 5 报错 → 退自动模式 + 写 debug 报告 + 等人工 | 见 §6 |
| 9 | 运行环境 | Ubuntu 22.04.5 LTS / X11 / i5-13600KF / 32GB / RTX 4060 |
| 10 | 迅捷开发为主 | 不做长时间大规模测试，最多小规模验证性测试 |

---

## 3. 目录结构与工作流

```
Interactable_Agentferry/
├── Agent Rules.txt            ← 项目宪法，最高指令
├── CLAUDE.md                  ← 你正在读的文件
├── LICENSE                    ← GPL v3
├── README.md                  ← 用户面向的项目说明（待开发时写）
├── src/                       ← **所有代码放这里**（Rule 8）
│   ├── camera/                ← 主窗口 + 入口
│   │   ├── window.py          ← CameraPetWindow：单窗口 + 摄像头画面 + 桌宠叠加
│   │   └── main.py            ← AppOrchestrator：组装所有组件
│   ├── vision/                ← 视觉管线（独立 QThread 跑）
│   │   ├── worker.py          ← VisionWorker：摄像头读取 + 信号推送
│   │   ├── pipelines.py       ← FaceTracker / GestureRecognizer / PinchDetector
│   │   └── reference/         ← 参考实现（不动）
│   ├── pet/                   ← 桌宠核心（自 My_Code 复用）
│   │   ├── window.py          ← 底层 QMainWindow 实现（鼠标拖动基类）
│   │   ├── state_machine.py
│   │   ├── animation_player.py
│   │   ├── idle_rotator.py
│   │   ├── sound_manager.py
│   │   ├── hover_bubble.py
│   │   ├── music_timer.py
│   │   ├── menu.py
│   │   └── controller.py      ← 【新建】PetController：状态机 + 飞行动画
│   ├── config/settings.py     ← AppSettings（自 My_Code 复用 + 新增视觉字段）
│   └── utils/
│       └── x11_binding.py     ← 自 My_Code 复用
├── assets/
│   ├── ameath/
│   │   ├── gifs/              ← 11 个 GIF（idle1~4 / drag / ameath / move / screen1~4）
│   │   └── sound/
│   │       ├── voice/         ← 8 个 WAV
│   │       └── music/         ← 5 个 MP3
│   └── models/                ← MediaPipe 模型
│       ├── face_landmarker.task
│       ├── hand_landmarker.task
│       └── blaze_face_short_range.tflite
├── Reference/                 ← 只读参考区
│   ├── README.md              ← **必读**：项目目标 + 参考代码导读 + 复用映射
│   ├── My_Code/Desktop_Agentferry/  ← 上一版桌宠（GPL v3）
│   └── code/                  ← 6 个外部开源参考项目
└── dev_doc/                   ← **所有过程文档放这里**（Rule 6、7）
    ├── N-research-xxx-YYYY-MM-DD.md
    ├── N-design-xxx-YYYY-MM-DD.md
    ├── N-debug-xxx-YYYY-MM-DD.md
    ├── N-decision-xxx-YYYY-MM-DD.md
    └── references.json        ← 调研时的参考资料索引（Rule 7）
```

**关键流转**：
- 接到任务 → 读 `Reference/README.md` §3（"我要做 X，先看 Y"）→ 定位 1-2 个最相关参考
- 调研结果写 `dev_doc/N-research-xxx-YYYY-MM-DD.md` + 更新 `dev_doc/references.json`
- 开发任务先在 `dev_doc/` 写设计稿（"为什么选 X 而不选 Y"），再动 `src/`
- **不要**在 `Reference/` 任何子项目里直接改代码；它们是只读参考。要抄就抄到 `src/`，并在文件头部加 attribution header
- 调研引用的外部 URL 一律写进 `dev_doc/references.json`

---

## 4. 接到任务时的标准动作清单

按顺序执行，缺一不可：

1. **复读** `Agent Rules.txt` 与本文件。
2. **检索** `Reference/README.md` §3（"我要做 X，先看 Y"），定位 1-2 个最相关参考。
3. **新建** `dev_doc/N-<action>-<desc>-YYYY-MM-DD.md`（`<action>` ∈ `research` / `design` / `plan` / `debug` / `decision`），记下目标、动机、备选、决策理由。
4. **如果是调研任务**：在 `dev_doc/references.json` 维护参考链接与要点（Rule 7）。
5. **如果是开发任务**：先在 `dev_doc/` 写设计稿（"为什么选 X 而不选 Y"），再动 `src/`。
6. **过程中输出**：说重点（Rule 4），砍掉客套话。
7. **完成后**：在 dev_doc 末尾追加"结论 / 决策记录 / 未解决问题"。

---

## 5. 关键技术决策（截至 v1 设计阶段）

- **形态**：单 QMainWindow（frameless + transparent + Tool + StaysOnTop），摄像头画面是底图，桌宠 GIF 用透明 QLabel 叠在上面。窗口默认占主屏 ~90%，用户可拖动/缩放。
- **不结合 Claude Code**：与上一版 `My_Code/Desktop_Agentferry` 相比，移除 `src/cli/`、`src/chat/`、`src/llm/` 子树；`src/aemeath/main.py` 的 Orchestrator 角色由新的 `src/camera/main.py` 取代。
- **视觉管线（双模型）**：
  - **GestureRecognizer**（MediaPipe Tasks API）负责 6 个内置手势：Open_Palm / Thumb_Up / Thumb_Down / Victory / Closed_Fist / Pointing_Up
  - **HandLandmarker**（MediaPipe Tasks API）负责 pinch 检测（thumb tip ↔ index tip 距离 + 持续帧数确认）
  - **FaceLandmarker**（MediaPipe Tasks API）负责脸部跟踪（face_center + face_bbox_size 用于近/中/远档位判定）
- **距离估算策略**：粗粒度三档（near / mid / far），基于 face bbox 宽度阈值，不做绝对距离折算。
- **手势→动作 映射**（来自 `dev_doc/1-Ameath-Respursed-Introduction.txt`）：

  | 手势 | 桌宠动作 | 结束条件 |
  |---|---|---|
  | 默认 | move.gif 飞绕头部（不重叠） | — |
  | OPEN_PALM | 飞到掌心循环 idle1~4 | 2s 未检测到 → 回默认 |
  | THUMBS_DOWN | 原地 screen4.gif | 2s 未检测到 → 回默认 |
  | THUMBS_UP | 原地 screen1.gif | 2s 未检测到 → 回默认 |
  | FIST | 原地 screen2.gif | 2s 未检测到 → 回默认 |
  | POINTING | 原地 screen3.gif | 2s 未检测到 → 回默认 |
  | VICTORY (PEACE) | 原地 ameath.gif + 随机音乐 | 被打断 or 音乐结束 → 回默认 |
  | PINCH（自定义） | drag.gif + 跟随食拇指尖 | 松手 → 回默认 |

- **拖动机制**：鼠标或 pinch 都进入拖动模式（drag.gif），松手后播放 move.gif 飞回头部位置。
- **音频**：复用 `My_Code/src/pet/sound_manager.py` 的 `VOICE_BY_ACTION` 映射；新增手势未指定时静音。PEACE 手势时额外随机播放一首 MP3。
- **多线程**：VisionWorker 在独立 QThread 跑，通过 Qt Signal 把 `face_position` / `face_size` / `gesture_label` / `pinch_active` / `pinch_position` 推给主线程的 PetController。
- **平台**：Linux 优先（X11），**不**做 Windows / macOS 兼容。
- **协议**：GPL v3。

---

## 6. 🚨 停止条件（必须遵守）

### 6.1 连续 5 个报错（Rule 8）
当使用**当前方法**连续遇到 5 个报错时：
1. **立刻停止自动模式**。
2. 在 `dev_doc/N-debug-xxx-YYYY-MM-DD.md` 写简短 debug 报告（错误列表、当前方法是什么、为什么失败、根因猜想）。
3. **等用户手动确认**后再继续。

不要继续在同一个方法上加补丁；这正是 Rule 3 反对的。

### 6.2 目标不清（Rule 1）
当用户说"我想做 X"但 X 模糊、动机不明、有多种合理解读时：
1. **不要动手**，先用 1-2 个问题确认。
2. 把"我的理解"写下来，让用户确认/纠正。

### 6.3 决策缺"为什么"（Rule 3）
任何"我选 X 不选 Y"的决定，**必须**能在 dev_doc 或回复里说清理由。说不清 → 重新调研。

### 6.4 pytest hang ≥ 2 次
当**同一次** `pytest` 调用或同一测试集合 hang / 失败 ≥ 2 次时：
1. **立刻停止**继续调 `-k` / `--co` / 二分定位。Rule 8 的 5 次上限对 pytest **太宽松**——每次输出都进 context，token 爆炸。
2. 写 `dev_doc/N-debug-xxx-YYYY-MM-DD.md`，记下：症状、已尝试的组合、失败边界、根因猜想。
3. 标 deferred，**转去做用户交代的事**；不要当场修。
4. workaround：`pytest-forked` / 子目录 / CI skip。

### 6.5 测试调用纪律（5 条铁律）
每次 `pytest` 之前必须答 3 个问题：
1. 这次跑的哪一行输出会改变我的下一步？
2. 如果失败了我会做什么？
3. 能不能用更小的子集？

默认只跑刚改的源文件的测试。**不维护手写 XML 跳过表**——用纪律 + 必要时 `pytest-testmon`。

### 6.6 单测 vs 验证性测试（Rule 10）
- **单测**：写有意义的小用例（边界、状态转换、距离档位判定等），可纳入 CI。
- **验证性测试**：手动跑 demo（`python src/camera/main.py`）观察摄像头画面是否符合预期；不写自动测试。
- **禁止**：写端到端自动化测试（启动摄像头 → 等待识别 → 断言 → 关闭），太慢、token 消耗大、与 Rule 10 冲突。

---

## 7. 与用户沟通的样式

- **说中文**（除非用户切到英文）。
- **说重点**（Rule 4）—— 列表、代码块、最短路径。
- **每个建议都带理由**（Rule 3）。
- **指出更优解**（Rule 2）—— 如果用户提的方案不是最短路径，直接说"还有更短的：…"。
- **每个候选方案都附难度评级 + 主要风险点**（用户偏好）。
- **别重复用户说过的话**、别加"好的，我来帮您…"这类客套。

---

## 8. 不要做的事

- ❌ 把代码写到 `src/` 之外。
- ❌ 在 `Reference/` 下任何子项目里改文件（它们是只读参考；要抄就抄到 `src/`）。
- ❌ 跳过 dev_doc 记录（Rule 6）。
- ❌ 跳过参考资料索引维护（Rule 7）。
- ❌ 删除或模糊化参考项目原作者的版权声明 / License / 署名。
- ❌ 自行决定技术栈而不写设计稿。
- ❌ 在同一方法上连续打 5 个补丁（→ §6.1）。
- ❌ 引入 Claude Code 相关依赖（anthropic / claude-code CLI / OpenCode 等）—— 本项目**不**结合 Claude Code。
- ❌ 写端到端自动化测试（→ §6.6）。

---

## 9. 自我更新

当本项目的核心约束（形态、手势集合、识别后端、协议、技术栈）发生变更时，**同步更新本文件**。变更点要在 `dev_doc/` 留一份决策记录（命名 `N-decision-xxx-YYYY-MM-DD.md`）。

---

*最后更新：2026-07-05 · v1 设计阶段（架构已确认；代码尚未实现）*