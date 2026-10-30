#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import dataclasses
from typing import Optional

from PySide6.QtCore import QEvent, QTimer, Signal
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
from tcalc.theme import PictureTarget
from tcalc.ui.widgets.keypad.utils import (
    KeyDef,
    add_keys_to_grid,
    handle_button_clicked,
    make_grid,
)

from ...config import keypad_config
from ...styles import app_fonts, theme_events
from ..common.button import KeyButton
from ..common.picture_layer import PictureLayer
from ..utils import apply_key_radius, apply_scaled_fonts, key_fit_timer, shrink_key_radius

GridDef = tuple[dict[str, list[KeyDef]], int]


class Keypad(QWidget):
    """Multi-grid keypad builder. Subclass and override ``grid_defs()``."""

    key_pressed = Signal(str, object)
    # Component name theme pictures can target; None takes none
    picture_target: PictureTarget | None = None

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
        # Scopes the keypad rules of the app stylesheet
        self.setProperty("uiRole", "keypad")
        theme_events.applied.connect(self._update_key_radius)

        cfg = keypad_config
        self._resize_timer = key_fit_timer(self, self._fit_keys)
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
        if self.picture_target is not None:
            PictureLayer(self, self.picture_target)

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
        # A theme may set its own key font range
        fonts = app_fonts()
        apply_scaled_fonts(self, self._buttons.values(), fonts.keypad_min_pt, fonts.keypad_max_pt)

    def _update_key_radius(self) -> None:
        apply_key_radius(self, self._buttons.values())

    def _fit_keys(self) -> None:
        self._update_button_fonts()
        self._update_key_radius()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        shrink_key_radius(self, self._buttons.values())
        self._resize_timer.start()

    def changeEvent(self, event: QEvent) -> None:
        super().changeEvent(event)
        # A theme switch sets a new app font; rescale the keys in it
        if event.type() == QEvent.Type.FontChange:
            self._update_button_fonts()
