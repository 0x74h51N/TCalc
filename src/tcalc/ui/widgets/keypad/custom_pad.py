#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import json
from dataclasses import dataclass, field

from PySide6.QtCore import QPoint, QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import Operation
from tcalc.theme import get_theme
from tcalc.ui.widgets.common.button import IconButton, KeyButton
from tcalc.ui.widgets.common.flow_layout import FlowLayout
from tcalc.ui.widgets.common.picker import SearchablePicker
from tcalc.ui.widgets.common.types import KeyDef

from ...config import custom_pad_config, keypad_config
from .style import apply_keypad_style

_cfg = custom_pad_config
_ALL_KEYS = (-1, -1)
_ROLE = "custom"


# ---------------------------------------------------------------------------
# GridData
# ---------------------------------------------------------------------------


@dataclass()
class GridData:
    """Key list for a single grid panel."""

    keys: list[KeyDef] = field(default_factory=list)

    @staticmethod
    def _make_key_def(op: Operation, row: int, col: int) -> KeyDef:
        return KeyDef(
            label=op.symbol,
            operation=op,
            row=row,
            col=col,
            tooltip=op.name.lower().replace("_", " "),
        )

    def add_operation(self, op: Operation, max_rows: int) -> None:
        idx = len(self.keys)
        self.keys.append(self._make_key_def(op, idx % max_rows, idx // max_rows))

    def replace_operation(self, index: int, op: Operation) -> None:
        if 0 <= index < len(self.keys):
            kd = self.keys[index]
            self.keys[index] = self._make_key_def(op, kd.row, kd.col)

    def remove_key(self, index: int, max_rows: int) -> None:
        if 0 <= index < len(self.keys):
            self.keys.pop(index)
            self._recalc_positions(max_rows)

    def _recalc_positions(self, max_rows: int) -> None:
        for i, kd in enumerate(self.keys):
            kd.row = i % max_rows
            kd.col = i // max_rows

    def set_color(self, index: int, bg: str | None = None, text: str | None = None) -> None:
        if 0 <= index < len(self.keys):
            kd = self.keys[index]
            if bg is not None:
                kd.bg_color = bg
            if text is not None:
                kd.text_color = text

    def serialize(self) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for kd in self.keys:
            entry: dict[str, str] = {
                "operation": kd.operation.name if isinstance(kd.operation, Operation) else ""
            }
            if kd.bg_color:
                entry["bg_color"] = kd.bg_color
            if kd.text_color:
                entry["text_color"] = kd.text_color
            result.append(entry)
        return result

    @staticmethod
    def deserialize(data: list[dict[str, str]], max_rows: int) -> GridData:
        gd = GridData()
        for entry in data:
            try:
                gd.add_operation(Operation[entry["operation"]], max_rows)
            except (KeyError, TypeError):
                continue
            kd = gd.keys[-1]
            if entry.get("bg_color"):
                kd.bg_color = entry["bg_color"]
            if entry.get("text_color"):
                kd.text_color = entry["text_color"]
        return gd


# ---------------------------------------------------------------------------
# KSGrid
# ---------------------------------------------------------------------------


class KSGrid(QWidget):
    """Single grid panel for CustomPad. Holds keys + optional add button."""

    key_clicked = Signal(str, object)  # (value, operation)
    add_requested = Signal(int)  # grid_index
    key_context_requested = Signal(int, int, QAbstractButton)  # grid_index, key_index, button

    def __init__(
        self,
        grid_index: int,
        data: GridData,
        max_rows: int,
        editing: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._grid_index = grid_index
        self._data = data
        self._max_rows = max_rows
        self._editing = editing
        self._buttons: list[QPushButton] = []
        self._add_button: IconButton | None = None

        spacing = int(keypad_config["grid_spacing"])
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(spacing)
        self._grid.setVerticalSpacing(spacing)

        self._build()

    # -- Properties --------------------------------------------------------

    @property
    def grid_index(self) -> int:
        return self._grid_index

    @grid_index.setter
    def grid_index(self, value: int) -> None:
        self._grid_index = value

    @property
    def data(self) -> GridData:
        return self._data

    @property
    def max_rows(self) -> int:
        return self._max_rows

    @max_rows.setter
    def max_rows(self, value: int) -> None:
        self._max_rows = value
        self._data._recalc_positions(value)
        self.rebuild()

    @property
    def editing(self) -> bool:
        return self._editing

    @editing.setter
    def editing(self, value: bool) -> None:
        self._editing = value
        self.rebuild()

    # -- Build / Rebuild ---------------------------------------------------

    def _build(self) -> None:
        for r in range(self._max_rows):
            self._grid.setRowStretch(r, 1)

        for ki, kd in enumerate(self._data.keys):
            btn = KeyButton(kd, _ROLE, self)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.place(self._grid, kd)
            btn.clicked.connect(self._make_key_handler(kd))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(self._make_context_handler(ki, btn))
            self._buttons.append(btn)

            # Per-key custom colors
            if kd.bg_color or kd.text_color:
                self._apply_key_color(btn, kd.bg_color, kd.text_color)

        if self._editing:
            idx = len(self._data.keys)
            self._add_button = IconButton("./assets/custom_pad.svg", tooltip="Add key", parent=self)
            self._add_button.setProperty("addButton", True)
            self._add_button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._grid.addWidget(self._add_button, idx % self._max_rows, idx // self._max_rows)
            self._add_button.clicked.connect(lambda: self.add_requested.emit(self._grid_index))

    def rebuild(self) -> None:
        """Tear down all widgets and rebuild from current data."""
        for btn in self._buttons:
            self._grid.removeWidget(btn)
            btn.deleteLater()
        self._buttons.clear()

        if self._add_button is not None:
            self._grid.removeWidget(self._add_button)
            self._add_button.deleteLater()
            self._add_button = None

        self._build()

    # -- Helpers -----------------------------------------------------------

    def _make_key_handler(self, kd: KeyDef):
        """Create a click handler for a key button."""

        def handler(_checked: bool = False) -> None:
            if kd.operation is None:
                return
            value = (
                kd.operation.symbol if isinstance(kd.operation, Operation) else str(kd.operation)
            )
            self.key_clicked.emit(value, kd.operation)

        return handler

    def _make_context_handler(self, key_index: int, button: QPushButton):
        """Create a right-click handler that emits key_context_requested."""

        def handler(_) -> None:
            self.key_context_requested.emit(self._grid_index, key_index, button)

        return handler

    @staticmethod
    def _apply_key_color(btn: QPushButton, bg: str, text: str) -> None:
        btn.setProperty("padKey", True)
        parts = ['QPushButton[padKey="true"] {']
        if bg:
            parts.append(f"background-color: {bg};")
        if text:
            parts.append(f"color: {text};")
        parts.append("}")
        btn.setStyleSheet(" ".join(parts))

    def button_at(self, key_index: int) -> QPushButton | None:
        """Return the button widget for the given key index."""
        if 0 <= key_index < len(self._buttons):
            return self._buttons[key_index]
        return None


# ===========================================================================
#
# Mighty CustomPad
#
# ===========================================================================


class CustomPad(QWidget):
    """User-configurable keypad with edit mode."""

    key_pressed = Signal(str, object)
    pad_removed = Signal()
    pad_renamed = Signal(str)

    def __init__(self, pad_id: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pad_id = pad_id
        self._settings_key = f"custom_pad/{pad_id}/layout"
        self._label = f"CustomPad {pad_id}"
        self._editing = False
        self._grid_count = int(_cfg["default_grid_count"])
        self._max_rows = int(_cfg["default_max_rows"])
        self._settings = QSettings("TCalc", "TCalc")
        self._grid_data: list[GridData] = [GridData()]
        self._load()
        self._grids: list[KSGrid] = []
        self._pending_edit: tuple[int, int] | None = None
        self._pending_grid_index: int = 0
        self._pending_color_target: str = "bg"
        kcfg = keypad_config
        margin = int(kcfg["side_margin"])
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(
            margin, int(kcfg["top_margin"]), margin, int(kcfg["bottom_margin"])
        )
        self._root.setSpacing(int(kcfg["grid_spacing"]))
        self._hbox = QHBoxLayout()
        self._hbox.setSpacing(int(kcfg["hbox_spacing"]))
        self._root.addLayout(self._hbox, int(kcfg["hbox_stretch"]))
        self._build_grids()
        # Pickers
        self._op_picker = self._make_picker(
            [(f"{op.symbol}  ({op.name.lower()})", op) for op in Operation],
        )
        self._op_picker.item_selected.connect(self._on_operation_picked)
        theme_colors = get_theme().colors
        self._color_picker = self._make_picker(
            [("Custom Color...", None)]
            + [(name, hex_val) for name, hex_val in theme_colors.items()],
            separator_after=0,
        )
        self._color_picker.item_selected.connect(self._on_color_picked)
        self._insert_toolbar()
        apply_keypad_style(self)

    # -- Properties --------------------------------------------------------
    @property
    def pad_id(self) -> int:
        return self._pad_id

    @property
    def label(self) -> str:
        return self._label

    # ------------------------------------------------------------------
    # Grid management
    # ------------------------------------------------------------------
    def _build_grids(self) -> None:
        for i, gd in enumerate(self._grid_data):
            grid = KSGrid(i, gd, self._max_rows, self._editing, self)
            self._wire_grid(grid)
            self._hbox.addWidget(grid, 1)
            self._grids.append(grid)

    def _rebuild_grids(self) -> None:
        for g in self._grids:
            self._hbox.removeWidget(g)
            g.deleteLater()
        self._grids.clear()
        self._build_grids()

    def _wire_grid(self, grid: KSGrid) -> None:
        grid.key_clicked.connect(self.key_pressed)
        grid.add_requested.connect(self._on_add_requested)
        grid.key_context_requested.connect(self._show_key_context_menu)

    # ------------------------------------------------------------------
    # Picker factory
    # ------------------------------------------------------------------
    def _make_picker(self, items, separator_after: int | None = None) -> SearchablePicker:
        return SearchablePicker(
            items=items,
            separator_after=separator_after,
            min_width=int(_cfg["picker_min_width"]),
            margin=int(_cfg["picker_margin"]),
            spacing=int(_cfg["picker_spacing"]),
            list_height=int(_cfg["picker_list_height"]),
            parent=self,
        )

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------
    @staticmethod
    def _make_toolbar_spin(prefix: str, min_val: int, max_val: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.PlusMinus)
        spin.setPrefix(prefix)
        spin.setRange(min_val, max_val)
        spin.setValue(value)
        spin.setProperty("customPadToolbar", True)
        spin.setFixedWidth(int(_cfg["spin_width"]))
        return spin

    def _insert_toolbar(self) -> None:
        self._toolbar_widget = QWidget(self)
        sp = self._toolbar_widget.sizePolicy()
        sp.setHeightForWidth(True)
        self._toolbar_widget.setSizePolicy(sp)
        self._toolbar_layout = FlowLayout(
            self._toolbar_widget,
            margin=int(_cfg["toolbar_margin"]),
            spacing=int(_cfg["toolbar_spacing"]),
        )
        self._grid_count_spin = self._make_toolbar_spin(
            "Grids: ",
            int(_cfg["min_grids"]),
            int(_cfg["max_grids"]),
            self._grid_count,
        )
        self._grid_count_spin.valueChanged.connect(self._on_grid_count_changed)
        self._toolbar_layout.addWidget(self._grid_count_spin)
        self._row_spin = self._make_toolbar_spin(
            "Rows: ",
            int(_cfg["min_rows"]),
            int(_cfg["max_rows"]),
            self._max_rows,
        )
        self._row_spin.valueChanged.connect(self._on_max_rows_changed)
        self._toolbar_layout.addWidget(self._row_spin)
        self._rename_btn = IconButton("document-edit", "Rename pad", "", None, self._toolbar_widget)
        self._rename_btn.clicked.connect(self._rename_pad)
        self._toolbar_layout.addWidget(self._rename_btn)
        self._toolbar_widget.hide()
        self._root.insertWidget(0, self._toolbar_widget)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------
    def _show_context_menu(self, pos: QPoint) -> None:
        menu = self._styled_menu(self)
        if self._editing:
            edit_all = self._styled_menu(self, parent_menu=menu, title="Edit Buttons")
            edit_all.addAction(
                "BG Color",
                lambda: self._open_color_picker(_ALL_KEYS, "bg", self.mapToGlobal(pos)),
            )
            edit_all.addAction(
                "Text Color",
                lambda: self._open_color_picker(_ALL_KEYS, "text", self.mapToGlobal(pos)),
            )
            edit_all.addSeparator()
            edit_all.addAction("Remove All Keys", self._confirm_remove_all_keys)
            menu.addAction("Rename", self._rename_pad)
            menu.addAction("Remove Pad", self._confirm_remove_pad)
            menu.addSeparator()
            menu.addAction("Done", lambda: self._toggle_edit(False))
        else:
            menu.addAction("Edit", lambda: self._toggle_edit(True))
        menu.exec(self.mapToGlobal(pos))

    def _show_key_context_menu(
        self, grid_index: int, key_index: int, button: QAbstractButton
    ) -> None:
        if not self._editing:
            return
        gi, ki = grid_index, key_index
        menu = self._styled_menu(self)
        edit_sub = self._styled_menu(self, parent_menu=menu, title="Edit")
        btn_pos = button.mapToGlobal(button.rect().bottomLeft())
        edit_sub.addAction("Operation", lambda: self._open_op_picker(btn_pos, edit=(gi, ki)))
        edit_sub.addAction("BG Color", lambda: self._open_color_picker((gi, ki), "bg", btn_pos))
        edit_sub.addAction("Text Color", lambda: self._open_color_picker((gi, ki), "text", btn_pos))
        menu.addAction("Remove", lambda: self._remove_key(gi, ki))
        menu.exec(button.mapToGlobal(button.rect().topRight()))

    def _on_add_requested(self, grid_index: int) -> None:
        if not self._editing:
            return
        if grid_index >= len(self._grids):
            return
        btn = self._grids[grid_index]._add_button
        if btn is None:
            return
        menu = self._styled_menu(btn)
        popup_pos = btn.mapToGlobal(btn.rect().bottomLeft())
        menu.addAction(
            "Add Operation", lambda: self._open_op_picker(popup_pos, grid_index=grid_index)
        )
        const_action = menu.addAction("Add Constant")
        const_action.setEnabled(False)
        menu.exec(popup_pos)

    @staticmethod
    def _styled_menu(
        parent: QWidget,
        parent_menu: QMenu | None = None,
        title: str = "",
    ) -> QMenu:
        if parent_menu is not None:
            menu = parent_menu.addMenu(title)
        else:
            menu = QMenu(parent)
        menu.setProperty("customPadMenu", True)
        return menu

    # ------------------------------------------------------------------
    # Edit mode
    # ------------------------------------------------------------------
    def _toggle_edit(self, editing: bool) -> None:
        self._editing = editing
        self._toolbar_widget.setVisible(editing)
        self._toolbar_layout.invalidate()
        self._toolbar_widget.updateGeometry()
        self._toolbar_layout.activate()
        if self._root is not None:
            self._root.invalidate()
            self._root.activate()
        for g in self._grids:
            g.editing = editing
        if not editing:
            self._save()

    # ------------------------------------------------------------------
    # Picker / color handlers
    # ------------------------------------------------------------------
    def _open_op_picker(
        self,
        global_pos: QPoint,
        grid_index: int = 0,
        edit: tuple[int, int] | None = None,
    ) -> None:
        self._pending_grid_index = grid_index
        self._pending_edit = edit
        self._op_picker.popup(global_pos)

    def _open_color_picker(self, loc: tuple[int, int], target: str, global_pos: QPoint) -> None:
        self._pending_edit = loc
        self._pending_color_target = target
        self._color_picker.popup(global_pos)

    def _on_operation_picked(self, op: Operation) -> None:
        if self._pending_edit is not None:
            gi, ki = self._pending_edit
            self._pending_edit = None
            if gi < len(self._grids):
                self._grids[gi].data.replace_operation(ki, op)
                self._grids[gi].rebuild()
        else:
            gi = self._pending_grid_index
            if gi < len(self._grids):
                self._grids[gi].data.add_operation(op, self._max_rows)
                self._grids[gi].rebuild()

    def _on_color_picked(self, color_value: str | None) -> None:
        if color_value is None:
            color = QColorDialog.getColor(parent=self)
            if not color.isValid():
                self._pending_edit = None
                return
            color_value = color.name()
        if self._pending_edit is None:
            return
        gi, ki = self._pending_edit
        self._pending_edit = None
        is_bg = self._pending_color_target == "bg"
        bg_val = color_value if is_bg else None
        text_val = color_value if not is_bg else None
        if (gi, ki) == _ALL_KEYS:
            for g in self._grids:
                for idx in range(len(g.data.keys)):
                    g.data.set_color(idx, bg=bg_val, text=text_val)
                g.rebuild()
        elif gi < len(self._grids):
            self._grids[gi].data.set_color(ki, bg=bg_val, text=text_val)
            self._grids[gi].rebuild()

    # ------------------------------------------------------------------
    # Key / pad removal
    # ------------------------------------------------------------------
    def _remove_key(self, grid_idx: int, key_idx: int) -> None:
        if grid_idx < len(self._grids):
            self._grids[grid_idx].data.remove_key(key_idx, self._max_rows)
            self._grids[grid_idx].rebuild()

    def _confirm_remove_all_keys(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Remove All Keys",
            "Are you sure you want to remove all keys?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for g in self._grids:
                g.data.keys.clear()
                g.rebuild()

    def _confirm_remove_pad(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Remove Pad",
            "Are you sure you want to remove this custom pad?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._settings.remove(self._settings_key)
            self.pad_removed.emit()

    def _rename_pad(self) -> None:
        name, ok = QInputDialog.getText(self, "Rename Pad", "Name:", text=self._label)
        if ok and name.strip():
            self._label = name.strip()
            self._save()
            self.pad_renamed.emit(self._label)

    # ------------------------------------------------------------------
    # Grid / row count changes
    # ------------------------------------------------------------------
    def _on_grid_count_changed(self, value: int) -> None:
        self._grid_count = value
        self._grid_data = [
            self._grids[i].data if i < len(self._grids) else GridData() for i in range(value)
        ]
        self._rebuild_grids()

    def _on_max_rows_changed(self, value: int) -> None:
        self._max_rows = value
        for g in self._grids:
            g.max_rows = value

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _save(self) -> None:
        data = {
            "label": self._label,
            "grid_count": self._grid_count,
            "max_rows": self._max_rows,
            "grids": [g.data.serialize() for g in self._grids],
        }
        self._settings.setValue(self._settings_key, json.dumps(data))

    def _load(self) -> None:
        raw = self._settings.value(self._settings_key, "")
        if not raw:
            return
        try:
            data = json.loads(str(raw))
        except (json.JSONDecodeError, TypeError):
            return
        self._label = data.get("label", self._label)
        self._grid_count = int(data.get("grid_count", _cfg["default_grid_count"]))
        self._max_rows = int(data.get("max_rows", _cfg["default_max_rows"]))
        grids_raw = data.get("grids", [])
        self._grid_data = [
            GridData.deserialize(grids_raw[i], self._max_rows) if i < len(grids_raw) else GridData()
            for i in range(self._grid_count)
        ]
