from __future__ import annotations

from typing import Dict, Any, Optional

from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QSizePolicy

from .keypad_defins import NORMAL_MODE_KEYS, SIDEBAR_KEYS, SCIENCE_MODE_KEYS
from .....app_state import CalculatorMode, get_app_state
from ..config import keypad_config
from ...utils import apply_scaled_fonts
from ..style import apply_button_style
from ..utils import add_keys_to_grid, create_button, handle_button_clicked, make_grid
from .style import apply_keypad_style


class Keypad(QWidget):
    key_pressed = Signal(str, object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._buttons: Dict[str, QPushButton] = {}

        apply_keypad_style(self)

        # Root layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(
            keypad_config["side_margin"],
            keypad_config["top_margin"],
            keypad_config["side_margin"],
            keypad_config["bottom_margin"],
        )
        self._main_layout.setSpacing(keypad_config["grid_spacing"])

        # Keypad body: science panel + normal keypad + right sidebar
        self._hbox = QHBoxLayout()
        self._hbox.setSpacing(keypad_config["hbox_spacing"])
        self._main_layout.addLayout(self._hbox, 1)

        # Science keys
        self._science_widget = QWidget(self)
        self._science_grid = make_grid(keypad_config["grid_spacing"], self._science_widget)
        add_keys_to_grid(SCIENCE_MODE_KEYS, self._science_grid, self._add_key)
        self._hbox.addWidget(self._science_widget, keypad_config.get("science_grid_stretch", 3))

        # Main keys
        self._normal_grid = make_grid(keypad_config["grid_spacing"])
        self._sidebar_grid = make_grid(keypad_config["grid_spacing"])

        self._hbox.addLayout(self._normal_grid, keypad_config["normal_mode_keys_stretch"])
        self._hbox.addLayout(self._sidebar_grid, keypad_config["right_side_grid_stretch"])

        add_keys_to_grid(NORMAL_MODE_KEYS, self._normal_grid, self._add_key)
        # Sidebar keys
        add_keys_to_grid(SIDEBAR_KEYS, self._sidebar_grid, self._add_key)
        self._buttons["Shift"].setVisible(get_app_state().mode != CalculatorMode.SIMPLE)

        self._update_button_fonts()
        QTimer.singleShot(0, self._update_button_fonts)

        hyp_btn = self._buttons.get("Hyp")
        if hyp_btn is not None:
            hyp_btn.toggled.connect(self._on_hyp_toggled)
    def _add_key(self, key_def: Dict[str, Any], role: str, grid) -> None:
        button = create_button(key_def, role, grid.parentWidget() or self)
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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

    def _on_hyp_toggled(self, checked: bool) -> None:
        for base in ("sin", "cos", "tan"):
            btn = self._buttons.get(base)
            if btn is not None:
                btn.setText(f"{base}h" if checked else base)

    def get_button(self, label: str) -> Optional[QPushButton]:
        return self._buttons.get(label)


    #
    # -- Font scaling ----------------------------------------------------
    #
    def _update_button_fonts(self) -> None:
        sample = self._buttons.get("7")
        apply_scaled_fonts([(sample, self._buttons.values(), 9, 20, 5)])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_button_fonts()
