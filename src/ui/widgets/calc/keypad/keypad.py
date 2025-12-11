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
from .....core import Operation
from ..config import keypad_config
from .style import apply_button_style


KeyHandler = Callable[[str, Operation], None]


class Keypad(QWidget):
    def __init__(self, on_key_pressed: KeyHandler, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._on_key_pressed: KeyHandler = on_key_pressed
        

        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(
            keypad_config["side_margin"],
            keypad_config["top_margin"],
            keypad_config["side_margin"],
            keypad_config["bottom_margin"]
        )
        hbox.setSpacing(keypad_config["hbox_spacing"])

        left_grid = QGridLayout()
        right_grid = QGridLayout()

        for grid in (left_grid, right_grid):
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(keypad_config["grid_spacing"])
            grid.setVerticalSpacing(keypad_config["grid_spacing"])
        

        hbox.addLayout(left_grid, keypad_config["left_grid_stretch"])
        hbox.addLayout(right_grid, keypad_config["right_grid_stretch"])

        for role, keys in NORMAL_MODE_KEYS.items():
            for key_def in keys:
                row = key_def.get("row")
                col = key_def.get("col")
                if row is None or col is None:
                    continue

                rowspan = key_def.get("rowspan", 1)
                colspan = key_def.get("colspan", 1)

                button = QPushButton(key_def["label"], self)
                button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                
                # Apply styling
                apply_button_style(button, role)

                if col > keypad_config["column_split"]:
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
