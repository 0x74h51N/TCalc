from __future__ import annotations

from typing import Dict, Any, Optional

from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
    QRadioButton,
    QButtonGroup,
)

from .keypad_defins import NORMAL_MODE_KEYS, SCIENCE_MODE_KEYS
from .....app_state import AngleUnit
from .....core import Operation
from ..config import keypad_config
from .style import apply_button_style, apply_keypad_style


class Keypad(QWidget):
    key_pressed = Signal(str, object)
    angle_changed = Signal(object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._buttons: Dict[str, QPushButton] = {}
        self._angle_buttons: Dict[AngleUnit, QRadioButton] = {}

        apply_keypad_style(self)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(
            keypad_config["side_margin"],
            keypad_config["top_margin"],
            keypad_config["side_margin"],
            keypad_config["bottom_margin"],
        )
        self._main_layout.setSpacing(keypad_config["grid_spacing"])

        self._angle_widget = self._build_angle_widget()
        self._main_layout.addWidget(self._angle_widget)

        self._hbox = QHBoxLayout()
        self._hbox.setSpacing(keypad_config["hbox_spacing"])
        self._main_layout.addLayout(self._hbox, 1)

        self._science_widget = QWidget(self)
        self._science_grid = self._make_grid(self._science_widget)
        self._add_keys_to_grid(SCIENCE_MODE_KEYS, self._science_grid)
        self._hbox.addWidget(self._science_widget, keypad_config.get("science_grid_stretch", 3))

        self._left_grid = self._make_grid()
        self._right_grid = self._make_grid()
        self._hbox.addLayout(self._left_grid, keypad_config["left_grid_stretch"])
        self._hbox.addLayout(self._right_grid, keypad_config["right_grid_stretch"])
        self._populate_normal_keys(self._left_grid, self._right_grid)
        self._update_button_fonts()
        QTimer.singleShot(0, self._update_button_fonts)

    def _create_button(self, key_def: Dict[str, Any], role: str, grid: Optional[QGridLayout] = None) -> QPushButton:
        button = QPushButton(key_def["label"], self)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        apply_button_style(button, role)

        tooltip = key_def.get("tooltip")
        if tooltip:
            button.setToolTip(tooltip.capitalize())

        button.clicked.connect(lambda _=False, kd=key_def: self._handle_button_clicked(kd))

        self._buttons[key_def["label"]] = button

        if grid is not None:
            row = key_def.get("row", 0)
            col = key_def.get("col", 0)
            rowspan = key_def.get("rowspan", 1)
            colspan = key_def.get("colspan", 1)
            grid.addWidget(button, row, col, rowspan, colspan)

        return button


    def get_button(self, label: str) -> Optional[QPushButton]:
        return self._buttons.get(label)

    def _handle_button_clicked(self, key_def: Dict[str, Any]) -> None:
        operation = key_def["operation"]
        value = operation.symbol if isinstance(operation, Operation) else str(operation)
        self.key_pressed.emit(value, operation)

    # -- Builders --------------------------------------------------------

    def _make_grid(self, parent: Optional[QWidget] = None) -> QGridLayout:
        grid = QGridLayout(parent)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(keypad_config["grid_spacing"])
        grid.setVerticalSpacing(keypad_config["grid_spacing"])
        return grid

    def _build_angle_widget(self) -> QWidget:
        widget = QWidget(self)
        angle_layout = QHBoxLayout(widget)
        angle_layout.setContentsMargins(0, 0, 0, 0)
        angle_layout.setSpacing(keypad_config["grid_spacing"])

        self._angle_group = QButtonGroup(widget)

        for unit in (AngleUnit.DEG, AngleUnit.RAD, AngleUnit.GRAD):
            radio = QRadioButton(unit.name.capitalize(), widget)
            self._angle_group.addButton(radio)
            self._angle_buttons[unit] = radio
            angle_layout.addWidget(radio)
            radio.toggled.connect(lambda checked, u=unit: checked and self.angle_changed.emit(u))

        angle_layout.addStretch()

        size_policy = widget.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        widget.setSizePolicy(size_policy)
        return widget

    def _populate_normal_keys(self, left_grid: QGridLayout, right_grid: QGridLayout) -> None:
        for role, keys in NORMAL_MODE_KEYS.items():
            for key_def in keys:
                row = key_def.get("row")
                col = key_def.get("col")
                if row is None or col is None:
                    continue

                button = self._create_button(key_def, role)
                target_grid = right_grid if col > keypad_config["column_split"] else left_grid
                target_col = 0 if target_grid is right_grid else col
                target_grid.addWidget(
                    button,
                    row,
                    target_col,
                    key_def.get("rowspan", 1),
                    key_def.get("colspan", 1),
                )

    def _add_keys_to_grid(self, roles_to_keys: Dict[str, list[Dict[str, Any]]], grid: QGridLayout) -> None:
        for role, keys in roles_to_keys.items():
            for key_def in keys:
                self._create_button(key_def, role, grid)

    # -- Font scaling ----------------------------------------------------

    def _update_button_fonts(self) -> None:
        if not self._buttons:
            return
        sample = next(iter(self._buttons.values()))
        size = sample.size()
        if not size.isValid():
            size = sample.sizeHint()
        dim = min(size.width(), size.height())
        if dim <= 0:
            dim = min(self.width(), self.height())
        point_size = max(10, min(24, dim // 3))
        font = QFont()
        font.setPointSize(point_size)
        for btn in self._buttons.values():
            btn.setFont(font)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_button_fonts()
