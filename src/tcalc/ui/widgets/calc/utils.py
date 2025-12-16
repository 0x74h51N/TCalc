from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import SignalInstance
from PySide6.QtWidgets import QAbstractButton, QGridLayout, QPushButton, QRadioButton, QWidget

from ....core import Operation


def make_grid(spacing: int, parent: Optional[QWidget] = None) -> QGridLayout:
    grid = QGridLayout(parent)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(spacing)
    grid.setVerticalSpacing(spacing)
    return grid


def add_keys_to_grid(
    roles_to_keys: Dict[str, list[Dict[str, Any]]],
    grid: QGridLayout,
    add_key: Callable[[Dict[str, Any], str, QGridLayout], None],
) -> None:
    for role, keys in roles_to_keys.items():
        for key_def in keys:
            add_key(key_def, role, grid)


def create_button(key_def: Dict[str, Any], role: str, parent: QWidget) -> QAbstractButton:
    is_radio = bool(key_def.get("radio"))
    label = str(key_def["label"])
    button: QAbstractButton = QRadioButton(label, parent) if is_radio else QPushButton(label, parent)

    tooltip = key_def.get("tooltip")
    if tooltip:
        button.setToolTip(str(tooltip).capitalize())

    button.setEnabled(bool(key_def.get("enabled", True)))

    if not is_radio and key_def.get("checkable"):
        button.setCheckable(True)

    button.setProperty("keypadRole", role)
    return button


def handle_button_clicked(key_pressed: SignalInstance, key_def: Dict[str, Any]) -> None:
    operation = key_def["operation"]
    value = operation.symbol if isinstance(operation, Operation) else str(operation)
    key_pressed.emit(value, operation)
