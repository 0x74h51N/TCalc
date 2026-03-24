from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from tcalc.app_state import AngleUnit
from tcalc.ui.widgets.common import KeyButton, OptionGroup
from tcalc.ui.widgets.common.types import KeyDef

from ....config import calc_config
from ...keypad.utils import (
    add_keys_to_grid,
    handle_button_clicked,
    make_grid,
)
from .defins import ANGLE_OPTIONS, MEMORY_L_KEYS, MemoryKey
from .style import apply_topbar_style


class TopBar(QWidget):
    key_pressed = Signal(str, object)
    angle_changed = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}

        topbar = calc_config["topbar"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            topbar["side_margin"],
            topbar["top_margin"],
            topbar["side_margin"],
            topbar["bottom_margin"],
        )
        layout.setSpacing(topbar["grid_spacing"])

        self._angle_group = OptionGroup(
            options=ANGLE_OPTIONS,
            current=AngleUnit.DEG,
            parent=self,
            tooltips={
                AngleUnit.DEG: "Degrees",
                AngleUnit.RAD: "Radians",
                AngleUnit.GRAD: "Gradians",
            },
        )
        self._angle_group.selection_changed.connect(self.angle_changed)
        layout.addWidget(self._angle_group)

        layout.addStretch(int(topbar["spacer_stretch"]))

        # Memory keys
        self._memory_widget = QWidget(self)
        self._memory_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        apply_topbar_style(self._memory_widget)

        memory_grid = make_grid(topbar["grid_spacing"], self._memory_widget)
        add_keys_to_grid(MEMORY_L_KEYS, memory_grid, self._add_key)
        layout.addWidget(self._memory_widget)

    def _add_key(self, key_def: KeyDef, role: str, grid) -> None:
        button = KeyButton(key_def, role, grid.parentWidget() or self)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        button.clicked.connect(
            lambda _=False, kd=key_def: handle_button_clicked(self.key_pressed, kd)
        )
        self._buttons[str(key_def.get("label", ""))] = button
        button.place(grid, key_def)

    def get_button(self, label: str) -> Optional[QPushButton]:
        return self._buttons.get(label)

    def set_angle_visible(self, visible: bool) -> None:
        self._angle_group.setVisible(visible)

    def set_angle(self, unit: AngleUnit) -> None:
        self._angle_group.set_current(unit)

    def set_memory_available(self, available: bool) -> None:
        for key in (MemoryKey.MC, MemoryKey.MR):
            btn = self._buttons.get(key.value)
            if btn is not None:
                btn.setEnabled(available)
