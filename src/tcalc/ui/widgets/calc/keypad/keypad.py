from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.app_state import CalculatorMode, get_app_state
from tcalc.core import Operation

from ...utils import apply_scaled_fonts
from ..config import font_scale_config, keypad_config
from ..style import apply_button_style
from ..utils import KeyDef, add_keys_to_grid, create_button, handle_button_clicked, make_grid
from .keypad_defins import NORMAL_MODE_KEYS, SCIENCE_MODE_KEYS, SIDEBAR_KEYS
from .style import apply_keypad_style


class Keypad(QWidget):
    key_pressed = Signal(str, object)

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}
        self._shiftable_buttons: list[QPushButton] = []
        self._op_buttons: dict[Operation, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(False)
        self._button_group.buttonClicked.connect(self._on_button_clicked)
        self._base_key_def_by_button: dict[QAbstractButton, KeyDef] = {}
        self._key_def_by_button: dict[QAbstractButton, KeyDef] = {}

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
        self._main_layout.addLayout(self._hbox, keypad_config["hbox_stretch"])

        # Science keys
        self._science_widget = QWidget(self)
        self._science_grid = make_grid(keypad_config["grid_spacing"], self._science_widget)
        add_keys_to_grid(SCIENCE_MODE_KEYS, self._science_grid, self._add_key)
        self._hbox.addWidget(self._science_widget, keypad_config["science_grid_stretch"])

        # Main keys
        self._normal_grid = make_grid(keypad_config["grid_spacing"])
        self._sidebar_grid = make_grid(keypad_config["grid_spacing"])

        self._hbox.addLayout(self._normal_grid, keypad_config["normal_mode_keys_stretch"])
        self._hbox.addLayout(self._sidebar_grid, keypad_config["right_side_grid_stretch"])

        add_keys_to_grid(NORMAL_MODE_KEYS, self._normal_grid, self._add_key)

        # Sidebar keys
        add_keys_to_grid(SIDEBAR_KEYS, self._sidebar_grid, self._add_key)
        self._buttons["Shift"].setVisible(get_app_state().mode != CalculatorMode.SIMPLE)
        show_constants = get_app_state().show_constant_buttons
        for label in ("π", "e"):
            btn = self._buttons.get(label)
            if btn is not None:
                btn.setVisible(show_constants)

        self._update_button_fonts()
        QTimer.singleShot(0, self._update_button_fonts)

        shift_btn = self._buttons.get("Shift")
        if shift_btn is not None:
            shift_btn.toggled.connect(lambda _checked: QTimer.singleShot(0, self._sync_shift_state))
            shift_btn.setChecked(get_app_state().shifted)

        hyp_btn = self._buttons.get("Hyp")
        if hyp_btn is not None:
            hyp_btn.toggled.connect(lambda _checked: QTimer.singleShot(0, self._sync_trig_buttons))
            hyp_btn.setChecked(get_app_state().hyp)

    def _on_button_clicked(self, button: QAbstractButton) -> None:
        key_def = self._key_def_by_button.get(button)
        if not isinstance(key_def, dict):
            return
        handle_button_clicked(self.key_pressed, key_def)

    def _add_key(self, key_def: KeyDef, role: str, grid) -> None:
        button = create_button(key_def, role, grid.parentWidget() or self)
        assert isinstance(button, QPushButton)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        apply_button_style(button, role)
        self._button_group.addButton(button)
        self._base_key_def_by_button[button] = key_def
        self._key_def_by_button[button] = key_def
        self._buttons[str(key_def["label"])] = button
        op = key_def.get("operation")
        if isinstance(op, Operation):
            self._op_buttons[op] = button

        if key_def.get("shifted"):
            self._shiftable_buttons.append(button)

        grid.addWidget(
            button,
            key_def.get("row", 0),
            key_def.get("col", 0),
            key_def.get("rowspan", 1),
            key_def.get("colspan", 1),
        )

    def _sync_shift_state(self) -> None:
        shifted = get_app_state().shifted
        for button in self._shiftable_buttons:
            base = self._base_key_def_by_button.get(button, {})
            shifted_def = base.get("shifted")
            active = {**base, **shifted_def} if shifted and isinstance(shifted_def, dict) else base
            self._key_def_by_button[button] = active
            button.setText(str(active.get("label", "")))
            tooltip = active.get("tooltip")
            button.setToolTip(str(tooltip).capitalize() if tooltip else "")
        self._sync_trig_buttons()

    def _sync_trig_buttons(self) -> None:
        state = get_app_state()
        shifted = state.shifted
        hyp = state.hyp

        base_op = {
            Operation.SIN: Operation.ASIN if shifted else Operation.SIN,
            Operation.COS: Operation.ACOS if shifted else Operation.COS,
            Operation.TAN: Operation.ATAN if shifted else Operation.TAN,
        }
        hyp_op = {
            Operation.SIN: Operation.ASINH if shifted else Operation.SINH,
            Operation.COS: Operation.ACOSH if shifted else Operation.COSH,
            Operation.TAN: Operation.ATANH if shifted else Operation.TANH,
        }

        for op in (Operation.SIN, Operation.COS, Operation.TAN):
            btn = self._op_buttons.get(op)
            if btn is None:
                continue
            shown = hyp_op[op] if hyp else base_op[op]
            btn.setText(shown.symbol)

    def get_button(self, label: str) -> Optional[QPushButton]:
        return self._buttons.get(label)

    #
    # -- Font scaling ----------------------------------------------------
    #
    def _update_button_fonts(self) -> None:
        sample = self._buttons.get("7")
        if sample is None:
            return
        scale = font_scale_config["keypad_buttons"]
        apply_scaled_fonts(
            [
                (
                    sample,
                    self._buttons.values(),
                    int(scale["min_pt"]),
                    int(scale["max_pt"]),
                    int(scale["divisor"]),
                )
            ]
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_button_fonts()
