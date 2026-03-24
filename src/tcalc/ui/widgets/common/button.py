#
#
#
# TCalc - Copyright (C) 2026 Tahsin Onemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import Mapping, Sequence

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QWidget,
)

from .types import KeyDef


class KeyButton(QPushButton):
    """Push button created from a ``KeyDef`` with grid placement support."""

    def __init__(self, key_def: KeyDef, role: str, parent: QWidget | None = None) -> None:
        super().__init__(str(key_def.get("label", "")), parent)

        tooltip = key_def.get("tooltip")
        if tooltip:
            self.setToolTip(str(tooltip).capitalize())

        self.setEnabled(key_def.get("enabled", True))
        if key_def.get("checkable"):
            self.setCheckable(True)

        self.setObjectName("keypadButton")
        self.setProperty("keypadRole", role)
        self.style().unpolish(self)
        self.style().polish(self)

    def place(self, grid: QGridLayout, key_def: KeyDef) -> None:
        """Add this button to *grid* at the position specified in *key_def*."""
        grid.addWidget(
            self,
            key_def.get("row", 0),
            key_def.get("col", 0),
            key_def.get("rowspan", 1),
            key_def.get("colspan", 1),
        )


class IconButton(QPushButton):
    """Themed push button with an icon and optional label text."""

    def __init__(
        self,
        icon_name: str,
        tooltip: str = "",
        text: str = "",
        size: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setIcon(QIcon.fromTheme(icon_name))

        if tooltip:
            self.setToolTip(tooltip)

        self.setProperty("uiRole", "iconButton")

        if size is not None:
            self.setFixedSize(size, size)
            self.setFlat(True)


class OptionGroup(QWidget):
    """Reusable radio-button group built from ``(key, label)`` pairs."""

    selection_changed = Signal(object)

    def __init__(
        self,
        options: Sequence[tuple[object, str]],
        current: object,
        parent: QWidget | None = None,
        tooltips: Mapping[object, str] | None = None,
    ) -> None:
        super().__init__(parent)

        sp = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sp.setRetainSizeWhenHidden(False)
        self.setSizePolicy(sp)

        self._buttons: dict[object, QRadioButton] = {}
        self._group = QButtonGroup(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for key, label in options:
            btn = QRadioButton(label, self)
            btn.setProperty("optionRole", "option")
            if tooltips is not None:
                tooltip = tooltips.get(key)
                if tooltip:
                    btn.setToolTip(tooltip)
            self._group.addButton(btn)
            self._buttons[key] = btn
            layout.addWidget(btn)

        if current in self._buttons:
            self._buttons[current].setChecked(True)

        self._group.buttonToggled.connect(self._on_toggled)

    def _on_toggled(self, button: QRadioButton, checked: bool) -> None:
        if not checked:
            return
        for key, btn in self._buttons.items():
            if btn is button:
                self.selection_changed.emit(key)
                return

    def current(self) -> object:
        """Return the key of the currently selected option."""
        for key, btn in self._buttons.items():
            if btn.isChecked():
                return key
        return next(iter(self._buttons))

    def set_current(self, key: object) -> None:
        """Programmatically select *key* without emitting the signal."""
        btn = self._buttons.get(key)
        if btn is None:
            return
        self._group.blockSignals(True)
        btn.setChecked(True)
        self._group.blockSignals(False)

    def buttons(self) -> dict[object, QRadioButton]:
        """Return the internal ``{key: QRadioButton}`` mapping."""
        return self._buttons
