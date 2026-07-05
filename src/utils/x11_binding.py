"""Bind a child window (terminal) to the pet window as transient_for.

Original code for Aemeath; uses python-xlib.
SPDX-License-Identifier: GPL-3.0-or-later
"""
from __future__ import annotations
from Xlib import X, display, Xatom


def bind_pet_to_terminal(pet_xid: int, term_xid: int) -> bool:
    try:
        d = display.Display()
        pet = d.create_resource_object("window", pet_xid)
        pet.set_property(d.intern_atom("_NET_WM_WINDOW_TYPE"), Xatom.WM_WINDOW_TYPE,
                         Xatom.WM_WINDOW_TYPE_NORMAL)
        term = d.create_resource_object("window", term_xid)
        term.set_wm_transient_for(pet)
        d.flush()
        return True
    except Exception:
        return False