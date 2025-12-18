from __future__ import annotations

from enum import Enum

from tcalc.app_state import AngleUnit


class MemoryKey(str, Enum):
    MC = "MC"
    MR = "MR"
    MS = "MS"
    M_PLUS = "M+"
    M_MINUS = "M-"


ANGLE_KEYS = [
    {"label": "Deg", "unit": AngleUnit.DEG, "radio": True, "row": 0, "col": 0},
    {"label": "Rad", "unit": AngleUnit.RAD, "radio": True, "row": 0, "col": 1},
    {"label": "Grad", "unit": AngleUnit.GRAD, "radio": True, "row": 0, "col": 2},
]

ANGLE_L_KEYS = {"angle": ANGLE_KEYS}


MEMORY_KEYS = [
    {
        "label": MemoryKey.MC.value,
        "operation": MemoryKey.MC.value,
        "enabled": False,
        "row": 0,
        "col": 0,
        "tooltip": "memory clear",
    },
    {
        "label": MemoryKey.MR.value,
        "operation": MemoryKey.MR.value,
        "enabled": False,
        "row": 0,
        "col": 1,
        "tooltip": "memory recall",
    },
    {
        "label": MemoryKey.MS.value,
        "operation": MemoryKey.MS.value,
        "row": 0,
        "col": 2,
        "tooltip": "memory store",
    },
    {
        "label": MemoryKey.M_PLUS.value,
        "operation": MemoryKey.M_PLUS.value,
        "row": 0,
        "col": 3,
        "tooltip": "memory add",
    },
]

MEMORY_L_KEYS = {"memory": MEMORY_KEYS}

__all__ = ["ANGLE_L_KEYS", "MEMORY_L_KEYS", "MemoryKey", "MEMORY_KEYS"]
