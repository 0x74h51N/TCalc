from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import SignalInstance
from PySide6.QtWidgets import QGridLayout, QWidget

from tcalc.core.ops import Operation

from ..common.types import KeyDef, ShiftedDef

__all__ = ["KeyDef", "ShiftedDef", "add_keys_to_grid", "handle_button_clicked", "make_grid"]


def make_grid(spacing: int, parent: Optional[QWidget] = None) -> QGridLayout:
    grid = QGridLayout(parent)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(spacing)
    grid.setVerticalSpacing(spacing)
    return grid


def add_keys_to_grid(
    roles_to_keys: dict[str, list[KeyDef]],
    grid: QGridLayout,
    add_key: Callable[[KeyDef, str, QGridLayout], None],
) -> None:
    for role, keys in roles_to_keys.items():
        for key_def in keys:
            add_key(key_def, role, grid)


def handle_button_clicked(key_pressed: SignalInstance, key_def: KeyDef) -> None:
    if key_def.operation is None:
        return
    value = (
        key_def.operation.symbol
        if isinstance(key_def.operation, Operation)
        else str(key_def.operation)
    )
    key_pressed.emit(value, key_def.operation)
