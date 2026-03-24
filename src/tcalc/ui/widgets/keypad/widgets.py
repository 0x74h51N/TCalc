from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget

from tcalc.app_state import get_app_state
from tcalc.core.ops import Operation

from ...config import keypad_config
from .keypad import GridDef, Keypad
from .keypad_defins import (
    FUNCTION_GROUP,
    NORMAL_MODE_KEYS,
    SIDEBAR_KEYS,
    TRIG_POWER_GROUP,
)


class MainKeypad(Keypad):
    """Core keypad: numbers/operators + sidebar (actions)."""

    def grid_defs(self) -> list[GridDef]:
        cfg = keypad_config
        return [
            (NORMAL_MODE_KEYS, int(cfg["normal_mode_keys_stretch"])),
            (SIDEBAR_KEYS, int(cfg["right_side_grid_stretch"])),
        ]


class FunctionsKeypad(Keypad):
    """Standalone functions panel (no shift, all keys flat)."""

    def grid_defs(self) -> list[GridDef]:
        return [(FUNCTION_GROUP, 1)]


class TrigPowerKeypad(Keypad):
    """Trig + power keys with shift/hyp support."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        shift_btn = self.get_button("Shift")
        if shift_btn is not None:
            shift_btn.toggled.connect(lambda _: QTimer.singleShot(0, self._sync_shift_state))
            shift_btn.setChecked(get_app_state().shifted)

        hyp_btn = self.get_button("Hyp")
        if hyp_btn is not None:
            hyp_btn.toggled.connect(lambda _: QTimer.singleShot(0, self._sync_trig_buttons))
            hyp_btn.setChecked(get_app_state().hyp)

    def grid_defs(self) -> list[GridDef]:
        return [(TRIG_POWER_GROUP, 1)]

    def _sync_shift_state(self) -> None:
        shifted = get_app_state().shifted
        self.apply_shift(shifted)
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
