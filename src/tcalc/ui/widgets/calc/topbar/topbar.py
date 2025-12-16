from __future__ import annotations

from typing import Any, Dict, Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QPushButton, QAbstractButton, QHBoxLayout, QSizePolicy, QButtonGroup

from .....app_state import AngleUnit
from ..config import keypad_config
from ..style import apply_button_style
from ..utils import add_keys_to_grid, create_button, handle_button_clicked, make_grid
from .defins import ANGLE_L_KEYS, MEMORY_L_KEYS
from .style import apply_topbar_style


class TopBar(QWidget):
    key_pressed = Signal(str, object)
    angle_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._buttons: Dict[str, QPushButton] = {}
        self._angle_buttons: Dict[AngleUnit, QAbstractButton] = {}

        apply_topbar_style(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            keypad_config["side_margin"],
            keypad_config["top_margin"],
            keypad_config["side_margin"],
            int(keypad_config["bottom_margin"] / 2),
        )
        layout.setSpacing(keypad_config["grid_spacing"])

        self._angle_widget = QWidget(self)
        self._angle_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        size_policy = self._angle_widget.sizePolicy()
        size_policy.setRetainSizeWhenHidden(False)
        self._angle_widget.setSizePolicy(size_policy)

        self._angle_group = QButtonGroup(self._angle_widget)
        angle_grid = make_grid(keypad_config["grid_spacing"], self._angle_widget)
        add_keys_to_grid(ANGLE_L_KEYS, angle_grid, self._add_key)
        layout.addWidget(self._angle_widget)

        layout.addStretch(1)

        self._memory_widget = QWidget(self)
        self._memory_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        memory_grid = make_grid(keypad_config["grid_spacing"], self._memory_widget)
        add_keys_to_grid(MEMORY_L_KEYS, memory_grid, self._add_key)
        layout.addWidget(self._memory_widget)

    def _add_key(self, key_def: Dict[str, Any], role: str, grid) -> None:
        is_radio = bool(key_def.get("radio"))
        button = create_button(key_def, role, grid.parentWidget() or self)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        if is_radio:
            unit = key_def["unit"]
            self._angle_group.addButton(button)
            self._angle_buttons[unit] = button
            button.toggled.connect(lambda checked, u=unit: checked and self.angle_changed.emit(u))
        else:
            apply_button_style(button, role)
            button.clicked.connect(lambda _=False, kd=key_def: handle_button_clicked(self.key_pressed, kd))
            self._buttons[str(key_def["label"])] = button

        grid.addWidget(
            button,
            key_def.get("row", 0),
            key_def.get("col", 0),
            key_def.get("rowspan", 1),
            key_def.get("colspan", 1),
        )

    def get_button(self, label: str) -> Optional[QPushButton]:
        return self._buttons.get(label)

    def set_memory_available(self, available: bool) -> None:
        for label in ("MC", "MR"):
            btn = self._buttons.get(label)
            btn.setEnabled(available)
