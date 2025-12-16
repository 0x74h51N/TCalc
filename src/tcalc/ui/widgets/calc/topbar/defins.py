from __future__ import annotations

from .....app_state import AngleUnit


ANGLE_KEYS = [
    {"label": "Deg", "unit": AngleUnit.DEG, "radio": True, "row": 0, "col": 0},
    {"label": "Rad", "unit": AngleUnit.RAD, "radio": True, "row": 0, "col": 1},
    {"label": "Grad", "unit": AngleUnit.GRAD, "radio": True, "row": 0, "col": 2},
]

ANGLE_L_KEYS = {"angle": ANGLE_KEYS}


MEMORY_KEYS = [
    {"label": "MC", "operation": "MC", "enabled": False, "row": 0, "col": 0, "tooltip": "memory clear"},
    {"label": "MR", "operation": "MR", "enabled": False, "row": 0, "col": 1, "tooltip": "memory recall"},
    {"label": "MS", "operation": "MS", "row": 0, "col": 2, "tooltip": "memory store"},
    {"label": "M+", "operation": "M+", "row": 0, "col": 3, "tooltip": "memory add"},
]

MEMORY_L_KEYS = {"memory": MEMORY_KEYS}

__all__ = ["ANGLE_L_KEYS", "MEMORY_L_KEYS"]
