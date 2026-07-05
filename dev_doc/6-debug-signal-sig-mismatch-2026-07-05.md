# N=6 debug + decision: render_command signal signature mismatch (启动 segfault 根因)

Date: 2026-07-05
Action: debug + decision

## 症状

`python src/camera/main.py` 立即输出 `Aborted (core dumped)`，无 Python traceback。pip install -e . 后持续出现两次（fix #1 加 pyproject.toml 之后、fix #2 加 utils/log.py 之后都重现）。

## 隔离过程（5 轮 diag）

| 测试 | 范围 | 结果 |
|---|---|---|
| A | CameraPetWindow 单独 + show | ✓ |
| B | SoundManager 单独 + QApp | ✓ |
| C | 完整 AppOrchestrator | ✗ abort |
| D | VisionWorker 单独 in QThread + 5s 跑 | ✓ |
| E | MediaPipe 三个模型单独加载 | ✓ |
| F | cv2.VideoCapture(0) + 设 1280x720 | ✓ |
| G | AppOrchestrator 断开 `camera_frame → update_camera_frame` | ✗ abort |
| H/I/J | 未跑（G 已否定 camera_frame 嫌疑） |

**关键观察**：单独跑每个组件都 OK，只有完整 AppOrchestrator 崩 → 不是组件问题，是组件组合时的某条 wiring。

## 根因

在 headless offscreen 环境下重跑 `python src/camera/main.py`（用 QT_QPA_PLATFORM=offscreen + auto-quit），抓到了完整 traceback：

```
TypeError: CameraPetWindow.update_pet() missing 1 required positional argument: 'gif_path'
```

**`PetController.render_command` 信号签名和 `CameraPetWindow.update_pet` 槽签名不匹配：**

```python
# src/pet/controller.py:63
render_command = pyqtSignal(object)               # 1 arg
# src/pet/controller.py:231
self.render_command.emit(cmd)                      # 发 1 个 RenderCommand
# src/camera/window.py:143
def update_pet(self, position, gif_path, scale=1.0):   # 期望 3 个位置参数
# src/camera/main.py:38
self.controller.render_command.connect(self.window.update_pet)   # 1→3
```

启动时 `_emit_render` 触发 `emit(cmd)` → Qt 调用 `update_pet(cmd)` → Python TypeError（缺 `gif_path` / `scale`）→ Qt signal dispatch 内部未捕获异常 → **C 层 abort**（Qt 文档：slot 内未捕获异常 = undefined behavior；某些 Qt/Python 版本表现为 core dump，offscreen 下表现为可捕获的 Python traceback）。

为什么 70 个测试没发现：
- 测试都不连接 `render_command → update_pet`（只验证 controller 内部状态）
- 测试用 `last_render` 属性检查，不触发 signal

## 修复

### 1. `src/pet/controller.py:63`
```python
# 旧：render_command = pyqtSignal(object)  # RenderCommand
# 新：
render_command = pyqtSignal(QPoint, str, float)  # (position, gif_path, scale)
```

### 2. `src/pet/controller.py:231`
```python
# 旧：self.render_command.emit(cmd)
# 新：
self.render_command.emit(cmd.position, cmd.gif_path, cmd.scale)
```

### 3. 顺带修：`src/camera/window.py:152` GIF 路径重复拼接

```python
# 旧：
_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "ameath"
full_path = _ASSETS.parent / gif_path  # → <project>/assets/assets/ameath/... 不存在

# 新：
_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "ameath"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
full_path = _PROJECT_ROOT / gif_path  # → <project>/assets/ameath/... 正确
```

不直接引发 segfault，但导致桌宠永远不显示（`exists()` 返回 False 跳过 `setMovie`）。

### 4. 回归测试 `tests/test_pet_controller.py::test_render_command_signal_carries_three_positional_args`

直接 connect 一个 `(position, gif_path, scale)` 签名 slot，验证 signal 触发时不抛 TypeError。

## 验证

- `pytest tests/ -q` → 71 passed (原 70 + 1 新)
- offscreen 跑 main.py + auto-quit → clean exit rc=0，无 TypeError
- 用户在 X11 真机需要复跑 `python src/camera/main.py` 验证 segfault 消失 + 桌宠正常显示

## 教训 / 决策

- **Signal/slot 签名必须 1:1 对齐**——任何不一致都可能在 Qt dispatch 中表现为 native crash。这是 Qt 跨语言绑定的一个 footgun，应该在 connect 处用 type stub 或 lint 强制（PyQt6 没现成方案；用 pytest 回归测试守住）。
- **测试设计遗漏**：70 个测试都没碰 signal wiring。补 test_render_command_signal_carries_three_positional_args 作为此类回归的范本。
- **诊断代价**：5 轮 diag 才定位信号不匹配。如果一开始就 offscreen + auto-quit 跑一次，offscreen 会暴露 Python traceback，省 4 轮。建议：以后类似"启动崩"问题，先在 offscreen 跑一次看是不是 Python 层错误，再上真机。

## 未解决

无（用户 X11 真机验证留作下一步）。