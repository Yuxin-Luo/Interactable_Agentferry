"""N-frame 投票平滑（spec §3.2 GestureRecognizer）."""
from __future__ import annotations
from collections import deque, Counter
from typing import Optional


class GestureSmoother:
    def __init__(self, window_size: int = 5):
        self._window_size = window_size
        self._buf: deque[str] = deque(maxlen=window_size)

    def reset(self) -> None:
        self._buf.clear()

    def update(self, label: str) -> str:
        self._buf.append(label)
        if len(self._buf) < self._buf.maxlen:
            return label
        # 投票：频次最高；ties 保留最近一次
        counts = Counter(self._buf)
        top_count = max(counts.values())
        candidates = [l for l, c in counts.items() if c == top_count]
        if len(candidates) == 1:
            return candidates[0]
        # tie → 取 buf 中最近出现的一个
        for l in reversed(self._buf):
            if l in candidates:
                return l
        return label
