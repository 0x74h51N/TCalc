from __future__ import annotations

from typing import Callable, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QGridLayout,
    QHBoxLayout,
    QSizePolicy,
)

from .keypad_defins import NORMAL_MODE_KEYS
from ...core.ops import Operation


KeyHandler = Callable[[str, Operation], None]


class Keypad(QWidget):
    def __init__(self, on_key_pressed: KeyHandler, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._on_key_pressed: KeyHandler = on_key_pressed
        

        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(10, 30, 10, 10)
        hbox.setSpacing(18)

        left_grid = QGridLayout()
        right_grid = QGridLayout()

        for grid in (left_grid, right_grid):
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(6)
            grid.setVerticalSpacing(6)
        

        hbox.addLayout(left_grid, 8)
        hbox.addLayout(right_grid, 2)

        for role, keys in NORMAL_MODE_KEYS.items():
            for key_def in keys:
                row = key_def.get("row")
                col = key_def.get("col")
                if row is None or col is None:
                    continue

                rowspan = key_def.get("rowspan", 1)
                colspan = key_def.get("colspan", 1)

                button = QPushButton(key_def["label"], self)
                button.setObjectName("keypadButton")
                button.setProperty("keypadRole", role)
                button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                button.style().unpolish(button)
                button.style().polish(button)

                if col > 3:
                    right_grid.addWidget(button, row, 0, rowspan, colspan)
                else:
                    left_grid.addWidget(button, row, col, rowspan, colspan)

                button.clicked.connect(
                    lambda _=False, kd=key_def: self._handle_button_clicked(kd)
                )

    def _handle_button_clicked(self, key_def: Dict[str, Any]) -> None:
        label: str = key_def["label"]
        operation: Operation = key_def["operation"]
        self._on_key_pressed(label, operation)
