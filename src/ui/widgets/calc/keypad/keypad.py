from __future__ import annotations

from typing import Callable, Dict, Any, Optional

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
from .....core import Operation
from .....app_state import get_app_state, CalculatorMode, AngleUnit
from ..config import keypad_config
from .style import apply_button_style, apply_keypad_style


KeyHandler = Callable[[str, Operation], None]


class Keypad(QWidget):
    def __init__(self, on_key_pressed: KeyHandler, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._on_key_pressed: KeyHandler = on_key_pressed
        self._buttons: Dict[str, QPushButton] = {}
        self._app_state = get_app_state()
        
        apply_keypad_style(self)

        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            keypad_config["side_margin"],
            keypad_config["top_margin"],
            keypad_config["side_margin"],
            keypad_config["bottom_margin"]
        )
        main_layout.setSpacing(keypad_config["grid_spacing"])

        # Angle unit selector
        self._angle_widget = QWidget()
        angle_layout = QHBoxLayout(self._angle_widget)
        angle_layout.setContentsMargins(0, 0, 0, 0)
        angle_layout.setSpacing(keypad_config["grid_spacing"])
        
        self._angle_group = QButtonGroup(self)
        self._angle_buttons: Dict = {}
        

        angle_units = [AngleUnit.DEG, AngleUnit.RAD, AngleUnit.GRAD]
        for unit in angle_units:
            radio = QRadioButton(str(unit.name).capitalize(), self)
            self._angle_group.addButton(radio)
            self._angle_buttons[unit] = radio
            angle_layout.addWidget(radio)
            radio.toggled.connect(lambda checked, u=unit: checked and self._set_angle_unit(u))
        
        angle_layout.addStretch()
        
        # Set initial selection
        self._angle_buttons[self._app_state.angle_unit].setChecked(True)
        
        # Retain size when hidden
        size_policy = self._angle_widget.sizePolicy()
        size_policy.setRetainSizeWhenHidden(True)
        self._angle_widget.setSizePolicy(size_policy)
        
        main_layout.addWidget(self._angle_widget)

        # Horizontal layout for keypads
        self._hbox = QHBoxLayout()
        self._hbox.setSpacing(keypad_config["hbox_spacing"])
        main_layout.addLayout(self._hbox, 1)

        # Science grid
        self._science_widget = QWidget()
        self._science_grid = QGridLayout(self._science_widget)
        self._science_grid.setContentsMargins(0, 0, 0, 0)
        self._science_grid.setHorizontalSpacing(keypad_config["grid_spacing"])
        self._science_grid.setVerticalSpacing(keypad_config["grid_spacing"])
        self._hbox.addWidget(self._science_widget, keypad_config.get("science_grid_stretch", 3))
        
        # Build science keys
        for role, keys in SCIENCE_MODE_KEYS.items():
            for key_def in keys:
                self._create_button(key_def, role, self._science_grid)

        # Normal mode grids
        left_grid = QGridLayout()
        right_grid = QGridLayout()

        for grid in (left_grid, right_grid):
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(keypad_config["grid_spacing"])
            grid.setVerticalSpacing(keypad_config["grid_spacing"])

        self._hbox.addLayout(left_grid, keypad_config["left_grid_stretch"])
        self._hbox.addLayout(right_grid, keypad_config["right_grid_stretch"])

        # Build normal mode keys
        for role, keys in NORMAL_MODE_KEYS.items():
            for key_def in keys:
                row = key_def.get("row")
                col = key_def.get("col")
                if row is None or col is None:
                    continue

                button = self._create_button(key_def, role)

                if col > keypad_config["column_split"]:
                    right_grid.addWidget(button, row, 0, key_def.get("rowspan", 1), key_def.get("colspan", 1))
                else:
                    left_grid.addWidget(button, row, col, key_def.get("rowspan", 1), key_def.get("colspan", 1))

        # Set initial visibility based on mode
        self._update_science_visibility()

    def _set_angle_unit(self, unit):
        """Set the angle unit for trig calculations."""
        self._app_state.angle_unit = unit

    def _create_button(self, key_def: Dict[str, Any], role: str, grid: Optional[QGridLayout] = None) -> QPushButton:
        """Create a button and optionally add to grid."""
        button = QPushButton(key_def["label"], self)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        apply_button_style(button, role)

        # Set tooltip if present (capitalize)
        tooltip = key_def.get("tooltip")
        if tooltip:
            button.setToolTip(tooltip.capitalize())

        button.clicked.connect(
            lambda _=False, kd=key_def: self._handle_button_clicked(kd)
        )

        self._buttons[key_def["label"]] = button

        if grid is not None:
            row = key_def.get("row", 0)
            col = key_def.get("col", 0)
            rowspan = key_def.get("rowspan", 1)
            colspan = key_def.get("colspan", 1)
            grid.addWidget(button, row, col, rowspan, colspan)

        return button

    def _update_science_visibility(self) -> None:
        """Show/hide science panel and angle selector based on mode."""
        is_science = self._app_state.mode == CalculatorMode.SCIENCE
        self._science_widget.setVisible(is_science)
        self._angle_widget.setVisible(is_science)

    def update_mode(self) -> None:
        """Called when calculator mode changes."""
        self._update_science_visibility()

    def get_button(self, label: str) -> Optional[QPushButton]:
        """Get button by label."""
        return self._buttons.get(label)

    def _handle_button_clicked(self, key_def: Dict[str, Any]) -> None:
        operation = key_def["operation"]
        if hasattr(operation, "symbol"):
            value = operation.symbol
        else:
            value = str(operation)
        self._on_key_pressed(value, operation)
