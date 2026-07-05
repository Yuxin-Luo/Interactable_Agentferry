"""get_logger — single-process logger init writing to ~/.config/agentferry/.

Copied from Reference/My_Code/Desktop_Agentferry/src/utils/log.py (GPL-3.0-or-later).
Used by SoundManager; other modules may adopt it later.

SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations

import logging
from pathlib import Path

_CFG_DONE = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger; initialize root once (file + stream handlers).

    Log file: ~/.config/agentferry/agentferry.log (auto-created).
    """
    global _CFG_DONE
    log = logging.getLogger(name)
    if not _CFG_DONE:
        cfg_dir = Path.home() / ".config" / "agentferry"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
            handlers=[
                logging.FileHandler(cfg_dir / "agentferry.log"),
                logging.StreamHandler(),
            ],
        )
        _CFG_DONE = True
    return log