from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from tcalc.app_state import AngleUnit

from ..config import keypad_config, topbar_config
from ..style import apply_button_style
from ..utils import KeyDef, add_keys_to_grid, create_button, handle_button_clicked, make_grid
from .defins import ANGLE_L_KEYS, MEMORY_L_KEYS, MemoryKey
from .style import apply_topbar_style


class TopBar(QWidget):
    key_pressed = Signal(str, object)
    angle_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}
        self._angle_buttons: dict[AngleUnit, QAbstractButton] = {}

        apply_topbar_style(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            keypad_config["side_margin"],
            keypad_config["top_margin"],
            keypad_config["side_margin"],
            int(keypad_config["bottom_margin"] * float(topbar_config["bottom_margin_factor"])),
        )
        layout.setSpacing(keypad_config["grid_spacing"])

        self._angle_widget = QWidget(self)
        self._angle_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        size_policy = self._angle_widget.sizePolicy()
        size_policy.setRetainSizeWhenHidden(False)
        self._angle_widget.setSizePolicy(size_policy)

        self._angle_group = QButtonGroup(self._angle_widget)
        angle_grid = make_grid(keypad_config["grid_spacing"], self._angle_widget)
        add_keys_to_grid(ANGLE_L_KEYS, angle_grid, self._add_key)
        layout.addWidget(self._angle_widget)

        layout.addStretch(int(topbar_config["spacer_stretch"]))

        self._memory_widget = QWidget(self)
        self._memory_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        memory_grid = make_grid(keypad_config["grid_spacing"], self._memory_widget)
        add_keys_to_grid(MEMORY_L_KEYS, memory_grid, self._add_key)
        layout.addWidget(self._memory_widget)

    def _add_key(self, key_def: KeyDef, role: str, grid) -> None:
        is_radio = bool(key_def.get("radio"))
        button = create_button(key_def, role, grid.parentWidget() or self)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        if is_radio:
            unit = key_def.get("unit")
            if not isinstance(unit, AngleUnit):
                return
            self._angle_group.addButton(button)
            self._angle_buttons[unit] = button
            button.toggled.connect(
                lambda checked, u=unit: self.angle_changed.emit(u) if checked else None
            )
        else:
            assert isinstance(button, QPushButton)
            apply_button_style(button, role)
            button.clicked.connect(
                lambda _=False, kd=key_def: handle_button_clicked(self.key_pressed, kd)
            )
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
        for key in (MemoryKey.MC, MemoryKey.MR):
            btn = self._buttons.get(key.value)
            if btn is not None:
                btn.setEnabled(available)
