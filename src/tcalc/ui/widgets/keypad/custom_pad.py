#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QBoxLayout,
    QColorDialog,
    QGridLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QWidget,
)

from tcalc.core.ops import Operation
from tcalc.theme import get_theme
from tcalc.ui.widgets.common.button import IconButton
from tcalc.ui.widgets.common.flow_layout import FlowLayout
from tcalc.ui.widgets.common.picker import SearchablePicker
from tcalc.ui.widgets.common.types import KeyDef

from ...config import custom_pad_config
from .keypad import GridDef, Keypad

_cfg = custom_pad_config

# ---------------------------------------------------------------------------
# GridData
# ---------------------------------------------------------------------------


@dataclass
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
            kd.update(self._make_key_def(op, kd["row"], kd["col"]))

    def remove_key(self, index: int, max_rows: int) -> None:
        if 0 <= index < len(self.keys):
            self.keys.pop(index)
            self._recalc_positions(max_rows)

    def _recalc_positions(self, max_rows: int) -> None:
        for i, kd in enumerate(self.keys):
            kd["row"] = i % max_rows
            kd["col"] = i // max_rows

    def set_color(self, index: int, *, bg: str | None = None, text: str | None = None) -> None:
        if 0 <= index < len(self.keys):
            kd = self.keys[index]
            if bg is not None:
                kd["bg_color"] = bg
            if text is not None:
                kd["text_color"] = text

    def serialize(self) -> list[dict]:
        result = []
        for kd in self.keys:
            op = kd.get("operation")
            entry: dict = {"operation": op.name if isinstance(op, Operation) else ""}
            if kd.get("bg_color"):
                entry["bg_color"] = kd["bg_color"]
            if kd.get("text_color"):
                entry["text_color"] = kd["text_color"]
            result.append(entry)
        return result

    @staticmethod
    def deserialize(data: list[dict], max_rows: int) -> GridData:
        gd = GridData()
        for entry in data:
            try:
                gd.add_operation(Operation[entry["operation"]], max_rows)
            except (KeyError, TypeError):
                continue
            kd = gd.keys[-1]
            if entry.get("bg_color"):
                kd["bg_color"] = entry["bg_color"]
            if entry.get("text_color"):
                kd["text_color"] = entry["text_color"]
        return gd


# ---------------------------------------------------------------------------
# CustomPad
# ---------------------------------------------------------------------------

_ROLE = "custom"
_ALL_KEYS = (-1, -1)


class CustomPad(Keypad):
    """User-configurable keypad with edit mode."""

    pad_removed = Signal()
    pad_renamed = Signal(str)

    def __init__(self, pad_id: int = 0, parent: Optional[QWidget] = None) -> None:
        self._pad_id = pad_id
        self._settings_key = f"custom_pad/{pad_id}/layout"
        self._label = f"CustomPad {pad_id}"
        self._editing = False
        self._grid_count = int(_cfg["default_grid_count"])
        self._max_rows = int(_cfg["default_max_rows"])
        self._grid_data: list[GridData] = [GridData()]

        self._settings = QSettings("TCalc", "TCalc")
        self._load()

        self._add_buttons: dict[int, QPushButton] = {}
        self._pending_edit: tuple[int, int] | None = None
        self._pending_grid_index: int = 0
        self._pending_color_target: str = "bg"
        self._button_location: dict[QAbstractButton, tuple[int, int]] = {}

        super().__init__(parent)

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

    # -- Properties --------------------------------------------------------

    @property
    def pad_id(self) -> int:
        return self._pad_id

    @property
    def label(self) -> str:
        return self._label

    # ------------------------------------------------------------------
    # Keypad overrides
    # ------------------------------------------------------------------

    def grid_defs(self) -> list[GridDef]:
        return [({_ROLE: gd.keys[:]}, 1) for gd in self._grid_data]

    def _build_grids(self) -> None:
        super()._build_grids()

        # Row constraints
        for wrapper in self._grid_widgets:
            gl = wrapper.layout()
            if isinstance(gl, QGridLayout):
                for r in range(self._max_rows):
                    gl.setRowStretch(r, 1)

        # Button lookup: id(key_def) → (grid_idx, key_idx)
        self._button_location.clear()
        kd_to_loc: dict[int, tuple[int, int]] = {
            id(kd): (gi, ki)
            for gi, gd in enumerate(self._grid_data)
            for ki, kd in enumerate(gd.keys)
        }
        for btn, kd in self._key_def_by_button.items():
            loc = kd_to_loc.get(id(kd))
            if loc is None:
                continue
            self._button_location[btn] = loc

            # Context menu per button
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn: self._show_key_context_menu(b, pos)
            )

            # Custom colors
            bg = kd.get("bg_color")
            tc = kd.get("text_color")
            if bg or tc:
                btn.setProperty("padKey", True)
                parts = ['QPushButton[padKey="true"] {']
                if bg:
                    parts.append(f"background-color: {bg};")
                if tc:
                    parts.append(f"color: {tc};")
                parts.append("}")
                btn.setStyleSheet(" ".join(parts))

    # ------------------------------------------------------------------
    # Picker factory
    # ------------------------------------------------------------------

    def _make_picker(self, items, *, separator_after=None) -> SearchablePicker:
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
        root = self.layout()
        if root is None or not isinstance(root, QBoxLayout):
            return

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

        self._toolbar_widget.hide()
        root.insertWidget(0, self._toolbar_widget)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos) -> None:
        """Main pad context menu (empty area right-click)."""
        menu = self._styled_menu(self)
        if self._editing:
            edit_all = self._styled_menu(self, parent_menu=menu, title="Edit Buttons")
            edit_all.addAction(
                "BG Color", lambda: self._open_color_picker(_ALL_KEYS, "bg", self.mapToGlobal(pos))
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

    def _show_key_context_menu(self, button: QAbstractButton, pos) -> None:
        """Per-key context menu (right-click on a button)."""
        if not self._editing:
            self._show_context_menu(button.mapTo(self, pos))
            return
        loc = self._button_location.get(button)
        if loc is None:
            return
        gi, ki = loc
        menu = self._styled_menu(self)
        edit_sub = self._styled_menu(self, parent_menu=menu, title="Edit")
        btn_pos = button.mapToGlobal(button.rect().bottomLeft())
        edit_sub.addAction("Operation", lambda: self._open_op_picker(btn_pos, edit=(gi, ki)))
        edit_sub.addAction("BG Color", lambda: self._open_color_picker((gi, ki), "bg", btn_pos))
        edit_sub.addAction("Text Color", lambda: self._open_color_picker((gi, ki), "text", btn_pos))
        menu.addAction("Remove", lambda: self._remove_key(gi, ki))
        menu.exec(button.mapToGlobal(pos))

    def _show_add_menu(self, grid_index: int, button: QPushButton) -> None:
        """'+' button menu — choose what to add."""
        menu = self._styled_menu(button)
        popup_pos = button.mapToGlobal(button.rect().bottomLeft())
        menu.addAction(
            "Add Operation", lambda: self._open_op_picker(popup_pos, grid_index=grid_index)
        )
        const_action = menu.addAction("Add Constant")
        const_action.setEnabled(False)
        menu.exec(popup_pos)

    @staticmethod
    def _styled_menu(
        parent: QWidget,
        *,
        parent_menu: QMenu | None = None,
        title: str = "",
    ) -> QMenu:
        """Create a QMenu with the customPadMenu property set."""
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
        # Force flow layout to recalculate wrap height
        self._toolbar_layout.invalidate()
        self._toolbar_widget.updateGeometry()
        self._toolbar_layout.activate()
        root = self.layout()
        if root is not None:
            root.invalidate()
            root.activate()
        if editing:
            self._place_add_buttons()
        else:
            self._remove_add_buttons()
            self._save()

    def _place_add_buttons(self) -> None:
        self._remove_add_buttons()
        for gi, wrapper in enumerate(self._grid_widgets):
            gl = wrapper.layout()
            if not isinstance(gl, QGridLayout):
                continue
            idx = len(self._grid_data[gi].keys) if gi < len(self._grid_data) else 0
            btn = IconButton("./assets/custom_pad.svg", tooltip="Add key", parent=wrapper)
            btn.setProperty("addButton", True)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            gl.addWidget(btn, idx % self._max_rows, idx // self._max_rows)
            btn.clicked.connect(lambda _=False, g=gi, b=btn: self._show_add_menu(g, b))
            self._add_buttons[gi] = btn

    def _remove_add_buttons(self) -> None:
        for btn in self._add_buttons.values():
            btn.deleteLater()
        self._add_buttons.clear()

    # ------------------------------------------------------------------
    # Picker / color handlers
    # ------------------------------------------------------------------

    def _open_op_picker(
        self,
        global_pos,
        *,
        grid_index: int = 0,
        edit: tuple[int, int] | None = None,
    ) -> None:
        self._pending_grid_index = grid_index
        self._pending_edit = edit
        self._op_picker.popup(global_pos)

    def _open_color_picker(self, loc: tuple[int, int], target: str, global_pos) -> None:
        self._pending_edit = loc
        self._pending_color_target = target
        self._color_picker.popup(global_pos)

    def _on_operation_picked(self, op: Operation) -> None:
        if self._pending_edit is not None:
            gi, ki = self._pending_edit
            self._pending_edit = None
            if gi < len(self._grid_data):
                self._grid_data[gi].replace_operation(ki, op)
        else:
            gi = self._pending_grid_index
            if gi < len(self._grid_data):
                self._grid_data[gi].add_operation(op, self._max_rows)
        self._full_refresh()

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
            for gd in self._grid_data:
                for idx in range(len(gd.keys)):
                    gd.set_color(idx, bg=bg_val, text=text_val)
        elif gi < len(self._grid_data):
            self._grid_data[gi].set_color(ki, bg=bg_val, text=text_val)
        self._full_refresh()

    # ------------------------------------------------------------------
    # Key / pad removal
    # ------------------------------------------------------------------

    def _remove_key(self, grid_idx: int, key_idx: int) -> None:
        if grid_idx < len(self._grid_data):
            self._grid_data[grid_idx].remove_key(key_idx, self._max_rows)
        self._full_refresh()

    def _confirm_remove_all_keys(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Remove All Keys",
            "Are you sure you want to remove all keys?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._grid_data = [GridData() for _ in range(self._grid_count)]
            self._full_refresh()

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
            self._grid_data[i] if i < len(self._grid_data) else GridData() for i in range(value)
        ]
        self._full_refresh()

    def _on_max_rows_changed(self, value: int) -> None:
        self._max_rows = value
        for gd in self._grid_data:
            gd._recalc_positions(value)
        self._full_refresh()

    # ------------------------------------------------------------------
    # Shared refresh
    # ------------------------------------------------------------------

    def _full_refresh(self) -> None:
        self._rebuild_grids()
        if self._editing:
            self._place_add_buttons()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        data = {
            "label": self._label,
            "grid_count": self._grid_count,
            "max_rows": self._max_rows,
            "grids": [gd.serialize() for gd in self._grid_data],
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
