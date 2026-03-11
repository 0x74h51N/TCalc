from __future__ import annotations

from enum import Enum

import calc_native

ANGLE_OPTIONS: list[tuple[calc_native.AngleUnit, str]] = [
    (calc_native.AngleUnit.DEG, "Deg"),
    (calc_native.AngleUnit.RAD, "Rad"),
    (calc_native.AngleUnit.GRAD, "Grad"),
]


class MemoryKey(str, Enum):
    MC = "MC"
    MR = "MR"
    MS = "MS"
    M_PLUS = "M+"
    M_MINUS = "M-"


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

__all__ = ["ANGLE_OPTIONS", "MEMORY_L_KEYS", "MemoryKey", "MEMORY_KEYS"]
