# N=5 decision: copied utils/log.py from My_Code to src/utils/

Date: 2026-07-05
Action: decision

## 背景

跑 `python src/camera/main.py` 报：

```
ModuleNotFoundError: No module named 'utils'
  File "src/pet/sound_manager.py", line 27
    from utils.log import get_logger
```

## 根因（不是补 patch）

`src/pet/sound_manager.py` 是从 `Reference/My_Code/Desktop_Agentferry/src/pet/sound_manager.py` 抄过来的。原项目用扁平 layout，`utils/log.py` 在 `src/utils/`。我们 fork 时只抄了 `sound_manager.py`，**漏抄了它依赖的 `utils/log.py`**，import 也没加 `src.` 前缀。

声学管线测试（`tests/test_pet_controller.py` 等 70 个）不直接 `import` 这个模块，所以测试通过——只到运行 `main.py` 才暴露。

## 备选

1. **抄 `log.py` 到 `src/utils/`** + 改 import 加 `src.` 前缀 ✅
   - 优点：行为与原项目一致；与其他已抄文件（sound_manager / window / x11_binding）同源路径清晰
   - 缺点：依赖项目积累，需要 attribution
2. 用 stdlib `logging.getLogger(name)` 直接替
   - 优点：少一个文件
   - 缺点：丢失文件 handler + 单进程只 init 一次的语义；要改 `sound_manager.py` 的初始化调用方式（`_log = get_logger(...)` → 改成 `logging.getLogger(...)`，行为上仍然得到 logger，但每次调用都是 fresh logger，没问题）
3. 去掉 `_log` 字段
   - 缺点：删了原项目的日志能力，违反"找根因"

## 决策

选 **#1**——保持和 `sound_manager.py` 同样的"从 My_Code 抄过来"血统；加 attribution header + SPDX，符合 CLAUDE.md §8 "保留参考项目原作者的版权声明 / License / 署名"。

## 修改

- 新增 `src/utils/log.py`（22 行，从 `Reference/My_Code/Desktop_Agentferry/src/utils/log.py` 复制，加 attribution header）
- `src/pet/sound_manager.py:27` `from utils.log import get_logger` → `from src.utils.log import get_logger`

## 验证

- `python -c "import src.camera.main"` OK
- `pytest tests/ -q` 70/70 通过
- 路径一致：所有 `src/` 内文件都从 `src.` 开头导入

## 未解决

无。