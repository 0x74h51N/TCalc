#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import dataclasses
from typing import Optional

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import Operation
from tcalc.ui.widgets.keypad.utils import (
    KeyDef,
    add_keys_to_grid,
    handle_button_clicked,
    make_grid,
)

from ...config import keypad_config
from ..common.button import KeyButton
from ..utils import apply_scaled_fonts
from .style import apply_keypad_style

GridDef = tuple[dict[str, list[KeyDef]], int]


class Keypad(QWidget):
    """Multi-grid keypad builder. Subclass and override ``grid_defs()``."""

    key_pressed = Signal(str, object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._buttons: dict[str, QPushButton] = {}
        self._shiftable_buttons: list[QPushButton] = []
        self._op_buttons: dict[Operation, QPushButton] = {}

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(False)
        self._button_group.buttonClicked.connect(self._on_button_clicked)

        self._base_key_def_by_button: dict[QAbstractButton, KeyDef] = {}
        self._key_def_by_button: dict[QAbstractButton, KeyDef] = {}

        self._grid_widgets: list[QWidget] = []

        cfg = keypad_config
        margin = int(cfg["side_margin"])
        grid_spacing = int(cfg["grid_spacing"])
        gap = int(cfg["hbox_spacing"])

        root = QVBoxLayout(self)
        root.setContentsMargins(margin, int(cfg["top_margin"]), margin, int(cfg["bottom_margin"]))
        root.setSpacing(grid_spacing)

        self._hbox = QHBoxLayout()
        self._hbox.setSpacing(gap)
        root.addLayout(self._hbox, int(cfg["hbox_stretch"]))

        self._build_grids()
        self._update_button_fonts()
        QTimer.singleShot(0, self._update_button_fonts)
        apply_keypad_style(self)

    def grid_defs(self) -> list[GridDef]:
        """Return [(key_defs_dict, stretch), ...] for each grid column."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Grid construction
    # ------------------------------------------------------------------

    def _build_grids(self) -> None:
        """Populate ``_hbox`` from ``grid_defs()``."""
        cfg = keypad_config
        grid_spacing = int(cfg["grid_spacing"])

        for keys, stretch in self.grid_defs():
            wrapper = QWidget(self)
            grid = make_grid(grid_spacing, wrapper)
            add_keys_to_grid(keys, grid, self._add_key)
            self._hbox.addWidget(wrapper, stretch)
            self._grid_widgets.append(wrapper)

    def _rebuild_grids(self) -> None:
        """Tear down existing grids and rebuild from ``grid_defs()``."""
        # Remove old grid widgets
        for w in self._grid_widgets:
            self._hbox.removeWidget(w)
            w.deleteLater()
        self._grid_widgets.clear()

        # Clear button tracking
        for btn in list(self._button_group.buttons()):
            self._button_group.removeButton(btn)
        self._buttons.clear()
        self._shiftable_buttons.clear()
        self._op_buttons.clear()
        self._base_key_def_by_button.clear()
        self._key_def_by_button.clear()

        # Rebuild
        self._build_grids()
        self._update_button_fonts()
        QTimer.singleShot(0, self._update_button_fonts)

    def _add_key(self, key_def: KeyDef, role: str, grid: QGridLayout) -> None:
        button = KeyButton(key_def, role, grid.parentWidget() or self)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._button_group.addButton(button)
        self._base_key_def_by_button[button] = key_def
        self._key_def_by_button[button] = key_def
        self._buttons[key_def.label] = button

        if isinstance(key_def.operation, Operation):
            self._op_buttons[key_def.operation] = button

        if key_def.shifted is not None:
            self._shiftable_buttons.append(button)

        button.place(grid, key_def)

    # ------------------------------------------------------------------
    # Click handling
    # ------------------------------------------------------------------

    def _on_button_clicked(self, button: QAbstractButton) -> None:
        key_def = self._key_def_by_button.get(button)
        if key_def is None:
            return
        handle_button_clicked(self.key_pressed, key_def)

    def apply_shift(self, shifted: bool) -> None:
        for button in self._shiftable_buttons:
            base = self._base_key_def_by_button.get(button)
            if base is None:
                continue
            shifted_def = base.shifted
            if shifted and shifted_def is not None:
                active = dataclasses.replace(
                    base,
                    label=shifted_def.label,
                    operation=shifted_def.operation,
                    tooltip=shifted_def.tooltip,
                )
            else:
                active = base
            self._key_def_by_button[button] = active
            button.setText(active.label)
            button.setToolTip(active.tooltip.capitalize() if active.tooltip else "")

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    def get_button(self, label: str) -> Optional[QPushButton]:
        return self._buttons.get(label)

    def get_op_button(self, op: Operation) -> Optional[QPushButton]:
        return self._op_buttons.get(op)

    @property
    def buttons(self) -> dict[str, QPushButton]:
        return self._buttons

    @property
    def op_buttons(self) -> dict[Operation, QPushButton]:
        return self._op_buttons

    # ------------------------------------------------------------------
    # Font scaling
    # ------------------------------------------------------------------

    def _update_button_fonts(self) -> None:
        apply_scaled_fonts(
            self,
            self._buttons.values(),
            int(keypad_config["min_pt"]),
            int(keypad_config["max_pt"]),
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_button_fonts()
