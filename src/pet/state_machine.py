from __future__ import annotations
from enum import Enum, auto
from typing import Dict, Tuple, List


class PetState(Enum):
    IDLE = "idle"
    HOVER_BUBBLE = "hover_bubble"
    CHAT_ACTIVE = "chat_active"
    WAITING = "waiting"
    CLI_THINKING = "cli_thinking"
    CLI_CELEBRATE = "cli_celebrate"
    CLI_ERROR = "cli_error"
    CLI_LONG_WAIT = "cli_long_wait"


class EVENT(Enum):
    HOVER_2S = auto()
    TIMEOUT_3S = auto()
    TIMEOUT_5S = auto()
    TIMEOUT_2S = auto()
    TIMEOUT_60S = auto()
    OPEN_CHAT = auto()
    CLOSE_CHAT = auto()
    SEND_MSG = auto()
    CHAT_REPLY = auto()
    CC_START = auto()
    CC_THINKING = auto()
    CC_DONE = auto()
    CC_ERROR = auto()
    CC_LONG_WAIT = auto()


# --------------------------------------------------------------------
# Explicit transitions from the brief (intentional behaviours)
# --------------------------------------------------------------------
_EXPLICIT: Dict[Tuple[PetState, EVENT], PetState] = {
    # Hover bubble
    (PetState.IDLE, EVENT.HOVER_2S): PetState.HOVER_BUBBLE,
    (PetState.HOVER_BUBBLE, EVENT.TIMEOUT_3S): PetState.IDLE,
    # Chat
    (PetState.IDLE, EVENT.OPEN_CHAT): PetState.CHAT_ACTIVE,
    (PetState.CHAT_ACTIVE, EVENT.CLOSE_CHAT): PetState.IDLE,
    (PetState.CHAT_ACTIVE, EVENT.SEND_MSG): PetState.WAITING,
    (PetState.WAITING, EVENT.CHAT_REPLY): PetState.CHAT_ACTIVE,
    # CLI lifecycle
    # dev-doc/20 fix: removed CLI_THINKING + TIMEOUT_60S → IDLE transition
    # so CC stays in CLI states until CC_DONE or CC_ERROR events arrive.
    (PetState.IDLE, EVENT.CC_START): PetState.CLI_THINKING,
    (PetState.CLI_THINKING, EVENT.CC_THINKING): PetState.CLI_THINKING,
    (PetState.CLI_THINKING, EVENT.CC_DONE): PetState.CLI_CELEBRATE,
    (PetState.CLI_THINKING, EVENT.CC_ERROR): PetState.CLI_ERROR,
    (PetState.CLI_THINKING, EVENT.CC_LONG_WAIT): PetState.CLI_LONG_WAIT,
    (PetState.CLI_LONG_WAIT, EVENT.CC_DONE): PetState.CLI_CELEBRATE,
    (PetState.CLI_LONG_WAIT, EVENT.CC_ERROR): PetState.CLI_ERROR,
    (PetState.CLI_LONG_WAIT, EVENT.CC_LONG_WAIT): PetState.CLI_LONG_WAIT,
    (PetState.CLI_CELEBRATE, EVENT.TIMEOUT_5S): PetState.IDLE,
    (PetState.CLI_ERROR, EVENT.TIMEOUT_2S): PetState.IDLE,
    # Explicit fallbacks for IDLE on chat events
    (PetState.IDLE, EVENT.CHAT_REPLY): PetState.IDLE,
    (PetState.IDLE, EVENT.SEND_MSG): PetState.WAITING,
}

# --------------------------------------------------------------------
# Total transition table: fill every missing (state, event) pair with
# IDLE as the safe default (per user decision 2026-07-03).
# Specific transitions above take priority — they are tested individually.
# --------------------------------------------------------------------
_DEFAULT = PetState.IDLE

TRANSITIONS: Dict[Tuple[PetState, EVENT], PetState] = {
    **_EXPLICIT,
    **{
        (s, e): _DEFAULT
        for s in PetState
        for e in EVENT
        if (s, e) not in _EXPLICIT
    },
}


def next_state(cur: PetState, evt: EVENT) -> PetState:
    return TRANSITIONS.get((cur, evt), cur)


class PetStateMachine:
    def __init__(self):
        self._state = PetState.IDLE
        self._history: List[Tuple[PetState, EVENT]] = []

    @property
    def state(self) -> PetState:
        return self._state

    @property
    def history(self) -> List[Tuple[PetState, EVENT]]:
        return list(self._history)

    def on_event(self, evt: EVENT) -> PetState:
        new = next_state(self._state, evt)
        if new != self._state:
            self._history.append((self._state, evt))
            self._state = new
        return self._state
