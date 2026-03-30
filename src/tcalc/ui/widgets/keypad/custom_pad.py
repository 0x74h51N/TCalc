#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import json

from PySide6.QtCore import QPoint, QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractButton,
    QColorDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.ops import Operation
from tcalc.theme import get_theme
from tcalc.ui.widgets.common.button import IconButton, KeyButton, KSSpinBox
from tcalc.ui.widgets.common.flow_layout import FlowLayout
from tcalc.ui.widgets.common.picker import SearchablePicker
from tcalc.ui.widgets.common.types import KeyDef

from ...config import custom_pad_config, keypad_config
from .style import apply_keypad_style

_cfg = custom_pad_config
_ALL_KEYS = (-1, -1)
_ROLE = "custom"


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def _recalc_positions(keys: list[KeyDef], max_rows: int) -> None:
    for i, kd in enumerate(keys):
        kd.row = i % max_rows
        kd.col = i // max_rows


def _add_operation(keys: list[KeyDef], op: Operation, max_rows: int) -> None:
    idx = len(keys)
    keys.append(KeyDef.from_op(op, idx % max_rows, idx // max_rows))


def _replace_operation(keys: list[KeyDef], index: int, op: Operation) -> None:
    if not (0 <= index < len(keys)):
        return

    old = keys[index]
    new = KeyDef.from_op(op, old.row, old.col)
    new.bg_color = old.bg_color
    new.text_color = old.text_color
    keys[index] = new


def _remove_key(keys: list[KeyDef], index: int, max_rows: int) -> None:
    if not (0 <= index < len(keys)):
        return
    keys.pop(index)
    _recalc_positions(keys, max_rows)


def _set_key_color(
    keys: list[KeyDef],
    index: int,
    bg: str | None = None,
    text: str | None = None,
) -> None:
    if not (0 <= index < len(keys)):
        return

    kd = keys[index]
    if bg is not None:
        kd.bg_color = bg
    if text is not None:
        kd.text_color = text


def _load_keys(data: list[dict[str, str]], max_rows: int) -> list[KeyDef]:
    keys: list[KeyDef] = []

    for i, entry in enumerate(data):
        op_name = entry.get("operation")
        if not op_name:
            continue

        try:
            op = Operation[op_name]
        except KeyError:
            continue

        kd = KeyDef.from_op(op, i % max_rows, i // max_rows)
        kd.bg_color = entry.get("bg_color", "")
        kd.text_color = entry.get("text_color", "")
        keys.append(kd)

    return keys


# ---------------------------------------------------------------------------
# KuStomGrid
# ---------------------------------------------------------------------------


class KSGrid(QWidget):
    """Kustom grid panel for CustomPad. Holds keys + optional add button."""

    key_clicked = Signal(str, object)
    add_requested = Signal(int)
    key_context_requested = Signal(int, int, QAbstractButton)
    edit_menu_requested = Signal(int, QPoint)  # grid_index, global_pos

    def __init__(
        self,
        grid_index: int,
        keys: list[KeyDef],
        max_rows: int,
        editing: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._grid_index = grid_index
        self._keys = keys
        self._max_rows = max_rows
        self._editing = editing
        self._buttons: list[QPushButton] = []
        self._add_button: IconButton | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        self._toolbar = QWidget(self)
        toolbar_layout = QHBoxLayout(self._toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(4)

        spin_width = int(_cfg["spin_width"])
        self._row_spin = KSSpinBox(
            "Rows: ",
            "Max rows",
            int(_cfg["min_rows"]),
            int(_cfg["max_rows"]),
            max_rows,
            spin_width,
            self._toolbar,
        )
        self._row_spin.valueChanged.connect(self._on_max_rows_changed)
        toolbar_layout.addWidget(self._row_spin)

        self._edit_btn = IconButton("document-edit", "Edit keys", "", None, self._toolbar)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        toolbar_layout.addWidget(self._edit_btn)

        self._remove_btn = IconButton("edit-delete", "Delete keys", "", None, self._toolbar)
        self._remove_btn.clicked.connect(self._confirm_remove_grid_keys)
        toolbar_layout.addWidget(self._remove_btn)

        toolbar_layout.addStretch()
        self._toolbar.setVisible(editing)
        root.addWidget(self._toolbar)

        grid_widget = QWidget(self)
        spacing = int(keypad_config["grid_spacing"])
        self._grid = QGridLayout(grid_widget)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(spacing)
        self._grid.setVerticalSpacing(spacing)
        root.addWidget(grid_widget, 1)

        self._build()

    # -- Properties --------------------------------------------------------

    @property
    def grid_index(self) -> int:
        return self._grid_index

    @grid_index.setter
    def grid_index(self, value: int) -> None:
        self._grid_index = value

    @property
    def keys(self) -> list[KeyDef]:
        return self._keys

    @property
    def max_rows(self) -> int:
        return self._max_rows

    @max_rows.setter
    def max_rows(self, value: int) -> None:
        self._max_rows = value
        _recalc_positions(self._keys, value)
        self._relayout()

    def _on_max_rows_changed(self, value: int) -> None:
        self.max_rows = value

    def _on_edit_clicked(self) -> None:
        pos = self._edit_btn.mapToGlobal(self._edit_btn.rect().bottomLeft())
        self.edit_menu_requested.emit(self._grid_index, pos)

    @property
    def editing(self) -> bool:
        return self._editing

    @editing.setter
    def editing(self, value: bool) -> None:
        self._editing = value
        self._toolbar.setVisible(value)
        if value:
            self._place_add_button()
        else:
            self._remove_add_button()

    # -- Build / Rebuild ---------------------------------------------------

    def _build(self) -> None:
        for r in range(max(self._grid.rowCount(), self._max_rows)):
            self._grid.setRowStretch(r, 1 if r < self._max_rows else 0)

        for ki, kd in enumerate(self._keys):
            btn = KeyButton(kd, _ROLE, self)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.place(self._grid, kd)
            btn.clicked.connect(self._make_key_handler(kd))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(self._make_context_handler(ki, btn))
            self._buttons.append(btn)

            if kd.bg_color or kd.text_color:
                self._style_button(btn, kd.bg_color, kd.text_color)

        if self._editing:
            idx = len(self._keys)
            self._add_button = IconButton("./assets/custom_pad.svg", tooltip="Add key", parent=self)
            self._add_button.setProperty("addButton", True)
            self._add_button.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            self._grid.addWidget(self._add_button, idx % self._max_rows, idx // self._max_rows)
            self._add_button.clicked.connect(lambda: self.add_requested.emit(self._grid_index))

    def _relayout(self) -> None:
        for r in range(max(self._grid.rowCount(), self._max_rows)):
            self._grid.setRowStretch(r, 1 if r < self._max_rows else 0)

        for btn, kd in zip(self._buttons, self._keys):
            self._grid.addWidget(btn, kd.row, kd.col, kd.rowspan, kd.colspan)

        if self._add_button is not None:
            idx = len(self._keys)
            self._grid.addWidget(self._add_button, idx % self._max_rows, idx // self._max_rows)

        self._grid.invalidate()
        self._grid.activate()

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

    # -- Add button management ---------------------------------------------

    def _place_add_button(self) -> None:
        if self._add_button is not None:
            return
        self._add_button = IconButton("./assets/custom_pad.svg", tooltip="Add key", parent=self)
        self._add_button.setProperty("addButton", True)
        self._add_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._add_button.clicked.connect(lambda: self.add_requested.emit(self._grid_index))
        self._move_add_button()

    def _remove_add_button(self) -> None:
        if self._add_button is None:
            return
        self._grid.removeWidget(self._add_button)
        self._add_button.deleteLater()
        self._add_button = None

    def _move_add_button(self) -> None:
        if self._add_button is None:
            return
        idx = len(self._keys)
        self._grid.addWidget(self._add_button, idx % self._max_rows, idx // self._max_rows)

    # -- Helpers -----------------------------------------------------------

    def _make_key_handler(self, kd: KeyDef):
        """Create a click handler for a key button."""

        def handler(_: bool = False) -> None:
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

    def apply_color(self, key_index: int, bg: str | None = None, text: str | None = None) -> None:
        """Update color on data + button for a single key."""
        _set_key_color(self._keys, key_index, bg=bg, text=text)
        if 0 <= key_index < len(self._buttons):
            kd = self._keys[key_index]
            self._style_button(self._buttons[key_index], kd.bg_color, kd.text_color)

    def apply_color_all(self, bg: str | None = None, text: str | None = None) -> None:
        """Update color on data + button for all keys."""
        for i in range(len(self._keys)):
            self.apply_color(i, bg=bg, text=text)

    def _style_button(self, btn: QPushButton, bg: str, text: str) -> None:
        btn.setProperty("padKey", True)
        parts = ['QPushButton[padKey="true"] {']
        if bg:
            parts.append(f"background-color: {bg};")
        if text:
            parts.append(f"color: {text};")
        parts.append("}")
        btn.setStyleSheet(" ".join(parts))

    def _confirm_remove_grid_keys(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Remove Grid Keys",
            "Are you sure you want to remove all keys in this grid?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._keys.clear()
            self.rebuild()


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
        self._cols = int(_cfg["default_cols"])
        self._rows = int(_cfg["default_rows"])
        self._settings = QSettings("TCalc", "TCalc")
        self._grid_keys: list[list[KeyDef]] = [[]]
        self._grid_max_rows: list[int] = [int(_cfg["default_max_rows"])]
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
        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(int(kcfg["hbox_spacing"]))
        self._root.addLayout(self._grid_layout, int(kcfg["hbox_stretch"]))
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
        default_max = int(_cfg["default_max_rows"])
        for i, keys in enumerate(self._grid_keys):
            max_rows = self._grid_max_rows[i] if i < len(self._grid_max_rows) else default_max
            grid = KSGrid(i, keys, max_rows, self._editing, self)
            self._wire_grid(grid)
            row, col = divmod(i, self._cols)
            self._grid_layout.addWidget(grid, row, col)
            self._grids.append(grid)

    def _rebuild_grids(self) -> None:
        for g in self._grids:
            self._grid_layout.removeWidget(g)
            g.deleteLater()
        self._grids.clear()
        self._build_grids()

    def _wire_grid(self, grid: KSGrid) -> None:
        grid.key_clicked.connect(self.key_pressed)
        grid.add_requested.connect(self._on_add_requested)
        grid.key_context_requested.connect(self._show_key_context_menu)
        grid.edit_menu_requested.connect(self._show_grid_edit_menu)

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
    def _insert_toolbar(self) -> None:
        self._toolbar = QWidget(self)
        sp = self._toolbar.sizePolicy()
        sp.setHeightForWidth(True)
        self._toolbar.setSizePolicy(sp)

        toolbar_layout = FlowLayout(
            self._toolbar,
            margin=int(_cfg["toolbar_margin"]),
            spacing=int(_cfg["toolbar_spacing"]),
        )

        spin_width = int(_cfg["spin_width"])
        padding = 7
        self._cols_spin = KSSpinBox(
            "vGrids: ",
            "Vertical Grids",
            int(_cfg["min_cols"]),
            int(_cfg["max_cols"]),
            self._cols,
            spin_width + padding,
            self._toolbar,
        )
        self._cols_spin.valueChanged.connect(self._on_cols_changed)
        toolbar_layout.addWidget(self._cols_spin)

        self._rows_spin = KSSpinBox(
            "hGrids: ",
            "Horizontal Grids",
            int(_cfg["min_grid_rows"]),
            int(_cfg["max_grid_rows"]),
            self._rows,
            spin_width + padding,
            self._toolbar,
        )
        self._rows_spin.valueChanged.connect(self._on_rows_changed)
        toolbar_layout.addWidget(self._rows_spin)

        rename_btn = IconButton("insert-text", "Rename pad", "", None, self._toolbar)
        rename_btn.clicked.connect(self._rename_pad)
        toolbar_layout.addWidget(rename_btn)

        remove_keys_btn = IconButton("edit-delete", "Remove keys", "", None, self._toolbar)
        remove_keys_btn.clicked.connect(self._confirm_remove_all_keys)
        toolbar_layout.addWidget(remove_keys_btn)

        remove_pad_btn = IconButton("edit-delete-shred", "Remove pad", "", None, self._toolbar)
        remove_pad_btn.clicked.connect(self._confirm_remove_pad)
        toolbar_layout.addWidget(remove_pad_btn)

        self._toolbar_sep = QFrame(self)
        self._toolbar_sep.setFrameShape(QFrame.Shape.HLine)
        self._toolbar_sep.hide()

        self._toolbar.hide()
        self._root.insertWidget(0, self._toolbar_sep)
        self._root.insertWidget(0, self._toolbar)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    # ------------------------------------------------------------------
    # Context menus
    # ------------------------------------------------------------------
    def _show_context_menu(self, pos: QPoint) -> None:
        menu = self._styled_menu(self)
        if self._editing:
            global_pos = self.mapToGlobal(pos)
            self._add_edit_submenu(menu, _ALL_KEYS, global_pos)
            menu.addAction("Rename", self._rename_pad)
            menu.addAction("Remove Pad", self._confirm_remove_pad)
            menu.addSeparator()
            menu.addAction("Done", lambda: self._toggle_edit(False))
        else:
            menu.addAction("Edit", lambda: self._toggle_edit(True))
        menu.exec(self.mapToGlobal(pos))

    def _show_grid_edit_menu(self, grid_index: int, global_pos: QPoint) -> None:
        """Edit menu for a single grid."""
        menu = self._styled_menu(self)
        loc = (grid_index, -1)
        self._add_edit_submenu(menu, loc, global_pos, inline=True)
        menu.exec(global_pos)

    def _add_edit_submenu(
        self,
        menu: QMenu,
        loc: tuple[int, int],
        global_pos: QPoint,
        inline: bool = False,
    ) -> None:
        """Populate *menu* with BG Color / Teinsert-textRemove All Keys actions."""
        target = menu if inline else self._styled_menu(self, parent_menu=menu, title="Edit Buttons")
        target.addAction("BG Color", lambda: self._open_color_picker(loc, "bg", global_pos))
        target.addAction("Text Color", lambda: self._open_color_picker(loc, "text", global_pos))
        target.addSeparator()
        if loc == _ALL_KEYS:
            target.addAction("Remove All Keys", self._confirm_remove_all_keys)
        else:
            gi = loc[0]
            target.addAction("Remove All Keys", lambda: self._grids[gi]._confirm_remove_grid_keys())

    def _show_key_context_menu(
        self, grid_index: int, key_index: int, button: QAbstractButton
    ) -> None:
        if not self._editing:
            pos = button.mapTo(self, button.rect().center())
            self._show_context_menu(pos)
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
        self._toolbar.setVisible(editing)
        self._toolbar_sep.setVisible(editing)
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
                _replace_operation(self._grids[gi].keys, ki, op)
                self._grids[gi].rebuild()
        else:
            gi = self._pending_grid_index
            if gi < len(self._grids):
                _add_operation(self._grids[gi].keys, op, self._grids[gi].max_rows)
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
                g.apply_color_all(bg=bg_val, text=text_val)
        elif gi < len(self._grids) and ki == -1:
            self._grids[gi].apply_color_all(bg=bg_val, text=text_val)
        elif gi < len(self._grids):
            self._grids[gi].apply_color(ki, bg=bg_val, text=text_val)

    # ------------------------------------------------------------------
    # Key / pad removal
    # ------------------------------------------------------------------
    def _remove_key(self, grid_idx: int, key_idx: int) -> None:
        if grid_idx < len(self._grids):
            _remove_key(self._grids[grid_idx].keys, key_idx, self._grids[grid_idx].max_rows)
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
                g.keys.clear()
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
    def _on_cols_changed(self, value: int) -> None:
        self._cols = value
        self._sync_grid_count()

    def _on_rows_changed(self, value: int) -> None:
        self._rows = value
        self._sync_grid_count()

    def _sync_grid_count(self) -> None:
        total = self._rows * self._cols
        default_max = int(_cfg["default_max_rows"])

        self._grid_keys = [
            self._grids[i].keys if i < len(self._grids) else [] for i in range(total)
        ]
        self._grid_max_rows = [
            self._grids[i].max_rows if i < len(self._grids) else default_max for i in range(total)
        ]

        self._rebuild_grids()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _save(self) -> None:
        data = {
            "label": self._label,
            "cols": self._cols,
            "rows": self._rows,
            "grids": [
                {
                    "max_rows": g.max_rows,
                    "keys": [kd.to_settings() for kd in g.keys],
                }
                for g in self._grids
            ],
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
        self._cols = int(data.get("cols", _cfg["default_cols"]))
        self._rows = int(data.get("rows", _cfg["default_rows"]))

        default_max = int(_cfg["default_max_rows"])
        total = self._rows * self._cols

        self._grid_keys = []
        self._grid_max_rows.clear()

        for entry in data.get("grids", [])[:total]:
            max_rows = int(entry.get("max_rows", default_max))
            keys = _load_keys(entry.get("keys", []), max_rows)
            self._grid_keys.append(keys)
            self._grid_max_rows.append(max_rows)

        for _ in range(total - len(self._grid_keys)):
            self._grid_keys.append([])
            self._grid_max_rows.append(default_max)
