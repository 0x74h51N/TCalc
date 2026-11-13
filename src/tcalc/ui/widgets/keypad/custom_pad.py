#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import dataclasses
import json
import logging
from collections.abc import Callable, Sequence

import calc_native
from PySide6.QtCore import QPoint, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QFont, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractButton,
    QColorDialog,
    QFrame,
    QGridLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.constants import CONST_BY_ID
from tcalc.core.ops import Operation
from tcalc.theme import PictureTarget, get_theme
from tcalc.typed_tables import TableError, build
from tcalc.ui.icon import Icon
from tcalc.ui.props import KeypadRole, Prop, UiRole
from tcalc.ui.styles import theme_events
from tcalc.ui.utils import split_camel
from tcalc.ui.widgets.common.button import IconButton, KeyButton, KSSpinBox
from tcalc.ui.widgets.common.constants_menu import ConstEntry, build_constant_menu
from tcalc.ui.widgets.common.picker import SearchablePicker
from tcalc.ui.widgets.common.picture_layer import PictureLayer
from tcalc.ui.widgets.common.toolbar import Toolbar
from tcalc.ui.widgets.common.types import GridLayout, KeyDef, KeySettings, PadLayout
from tcalc.ui.widgets.utils import apply_key_radius, key_fit_timer, set_raised, shrink_key_radius

from ...config import CONFIG
from ...look import DEFAULT_LOOK, ColorName

_cfg = CONFIG.keypad.custom

_log = logging.getLogger(__name__)
_ALL_KEYS = (-1, -1)
_ROLE = KeypadRole.CUSTOM


def _spin_font() -> QFont:
    # The default look, not the theme: a theme font would overflow the fixed spin box width
    return QFont(DEFAULT_LOOK.fonts.family_default, _cfg.spin_font_size)


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


def _add_constant(keys: list[KeyDef], entry: ConstEntry, max_rows: int) -> None:
    idx = len(keys)
    keys.append(
        KeyDef(
            label=entry.symbol,
            operation=entry.id,
            row=idx % max_rows,
            col=idx // max_rows,
            tooltip=entry.name,
        )
    )


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


def _key_color(value: str) -> str:
    """A key's stored color as QSS: "$name" is the active theme's color of that name."""
    if value.startswith("$"):
        return get_theme().colors.get(ColorName(value[1:]), "")
    return value


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


def _resolve_key(name: str, row: int, col: int) -> KeyDef | None:
    """Rebuild a KeyDef from a saved key name (an Operation or a constant)."""
    if name in Operation.__members__:
        return KeyDef.from_op(Operation[name], row, col)

    cid = calc_native.ConstId.__members__.get(name)
    if cid is not None:
        spec = CONST_BY_ID[cid]
        return KeyDef(
            label=spec.symbol,
            operation=cid,
            row=row,
            col=col,
            tooltip=split_camel(cid.name),
        )
    return None


def _load_keys(saved: tuple[KeySettings, ...], max_rows: int) -> list[KeyDef]:
    keys: list[KeyDef] = []
    # A key whose operation is gone is skipped but keeps its slot, so the others stay put
    for i, entry in enumerate(saved):
        kd = _resolve_key(entry.operation, i % max_rows, i // max_rows)
        if kd is None:
            continue
        kd.bg_color = entry.bg_color
        kd.text_color = entry.text_color
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
        self._key_radius: int | None = None
        self._add_button: IconButton | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)

        grid_widget = QWidget(self)
        spacing = CONFIG.keypad.grid_spacing
        self._grid = QGridLayout(grid_widget)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(spacing)
        self._grid.setVerticalSpacing(spacing)
        root.addWidget(grid_widget, 1)

        self._insert_toolbar(root, max_rows, editing)

        self._build()
        self._resize_timer = key_fit_timer(self, self._fit_key_radius)

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

    def _insert_toolbar(self, root: QVBoxLayout, max_rows: int, editing: bool) -> None:
        self._toolbar = Toolbar(
            self, margin=0, spacing=4, collapsible=True, toggle_tooltip="Grid options"
        )

        self._row_spin = KSSpinBox(
            "Rows: ",
            "Max rows",
            _cfg.min_rows,
            _cfg.max_rows,
            max_rows,
            _spin_font(),
            _cfg.spin_width,
            self._toolbar,
        )
        self._row_spin.valueChanged.connect(self._on_max_rows_changed)
        self._toolbar.addWidget(self._row_spin)

        self._edit_btn = IconButton(Icon.DOCUMENT_EDIT, "Edit keys", "", None, self._toolbar)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        self._toolbar.addWidget(self._edit_btn)

        self._remove_btn = IconButton(Icon.EDIT_DELETE, "Delete keys", "", None, self._toolbar)
        self._remove_btn.clicked.connect(self._confirm_remove_grid_keys)
        self._toolbar.addWidget(self._remove_btn)

        self._toolbar.setVisible(editing)
        root.addWidget(self._toolbar)

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
        # The toolbar and the add button resize the keys inside a grid that keeps its size
        self._resize_timer.start()

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
            self._place_add_button()

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
        # The new keys get their size once the layout shows them
        self._resize_timer.start()

    # -- Add button management ---------------------------------------------

    def _place_add_button(self) -> None:
        if self._add_button is not None:
            return
        self._add_button = IconButton(
            Icon.CUSTOM_PAD,
            tooltip="Add key",
            parent=self,
            tint=lambda look: look.custom_pad.add_key.text.color,
        )
        self._add_button.setProperty(Prop.ADD_BUTTON, True)
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

    def _make_key_handler(self, kd: KeyDef) -> Callable[[bool], None]:
        """Create a click handler for a key button."""

        def handler(_: bool = False) -> None:
            op = kd.operation
            if op is None:
                return
            if isinstance(op, Operation):
                value = op.symbol
            elif isinstance(op, calc_native.ConstId):
                value = CONST_BY_ID[op].symbol
            else:
                value = str(op)
            self.key_clicked.emit(value, op)

        return handler

    def _make_context_handler(
        self, key_index: int, button: QPushButton
    ) -> Callable[[QPoint], None]:
        """Create a right-click handler that emits key_context_requested."""

        def handler(_: QPoint) -> None:
            self.key_context_requested.emit(self._grid_index, key_index, button)

        return handler

    def apply_color(self, key_index: int, bg: str | None = None, text: str | None = None) -> None:
        """Update color on data + button for a single key."""
        _set_key_color(self._keys, key_index, bg=bg, text=text)
        if 0 <= key_index < len(self._buttons):
            kd = self._keys[key_index]
            self._style_button(self._buttons[key_index], kd.bg_color, kd.text_color)

    def restyle(self) -> None:
        for kd, btn in zip(self._keys, self._buttons):
            if kd.bg_color or kd.text_color:
                self._style_button(btn, kd.bg_color, kd.text_color)
        self._fit_key_radius()

    def _fit_key_radius(self) -> None:
        self._key_radius = apply_key_radius(self, self._buttons, self._key_radius)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._key_radius = shrink_key_radius(self, self._buttons, self._key_radius)
        self._resize_timer.start()

    def apply_color_all(self, bg: str | None = None, text: str | None = None) -> None:
        """Update color on data + button for all keys."""
        for i in range(len(self._keys)):
            self.apply_color(i, bg=bg, text=text)

    def _style_button(self, btn: QPushButton, bg: str, text: str) -> None:
        btn.setProperty(Prop.PAD_KEY, True)
        parts = ['QPushButton[padKey="true"] {']
        if bg := _key_color(bg):
            parts.append(f"background-color: {bg};")
        if text := _key_color(text):
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
        # Scopes the keypad rules of the app stylesheet
        self.setProperty(Prop.UI_ROLE, UiRole.KEYPAD)
        self._update_raised()
        theme_events.applied.connect(self._update_raised)
        PictureLayer(self, PictureTarget.CUSTOM_PAD)
        self._settings_key = f"custom_pad/{pad_id}/layout"
        self._label = f"CustomPad {pad_id}"
        self._editing = False
        self._cols = _cfg.default_cols
        self._rows = _cfg.default_rows
        self._settings = QSettings("TCalc", "TCalc")
        self._grid_keys: list[list[KeyDef]] = [[]]
        self._grid_max_rows: list[int] = [_cfg.default_max_rows]
        self._load()
        self._grids: list[KSGrid] = []
        self._pending_edit: tuple[int, int] | None = None
        self._pending_grid_index: int = 0
        self._pending_color_target: str = "bg"
        kcfg = CONFIG.keypad
        margin = kcfg.side_margin
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(margin, kcfg.top_margin, margin, kcfg.bottom_margin)
        self._root.setSpacing(kcfg.grid_spacing)
        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(kcfg.hbox_spacing)
        self._root.addLayout(self._grid_layout, kcfg.hbox_stretch)
        self._build_grids()
        # Pickers
        self._op_picker = self._make_picker(
            [(f"{op.symbol}  ({op.name.lower()})", op) for op in Operation],
        )
        self._op_picker.item_selected.connect(self._on_operation_picked)
        self._color_picker: SearchablePicker | None = None
        # A key colored by name follows the theme
        theme_events.applied.connect(self._restyle_keys)
        self._insert_toolbar()

    def _update_raised(self) -> None:
        set_raised(self, get_theme().look.keypad.button.edge.width > 0)

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
        default_max = _cfg.default_max_rows
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
    def _make_picker(
        self,
        items: Sequence[tuple[str, object] | tuple[str, object, QColor]],
        separator_after: int | None = None,
    ) -> SearchablePicker:
        return SearchablePicker(
            items=items,
            separator_after=separator_after,
            min_width=_cfg.picker_min_width,
            margin=_cfg.picker_margin,
            spacing=_cfg.picker_spacing,
            list_height=_cfg.picker_list_height,
            parent=self,
        )

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------
    def _insert_toolbar(self) -> None:
        self._toolbar = Toolbar(
            self,
            margin=_cfg.toolbar_margin,
            spacing=_cfg.toolbar_spacing,
            collapsible=True,
            toggle_tooltip="Pad options",
        )

        spin_width = _cfg.spin_width + 7
        font = _spin_font()
        self._cols_spin = KSSpinBox(
            "vGrids: ",
            "Vertical Grids",
            _cfg.min_cols,
            _cfg.max_cols,
            self._cols,
            font,
            spin_width,
            self._toolbar,
        )
        self._cols_spin.valueChanged.connect(self._on_cols_changed)
        self._toolbar.addWidget(self._cols_spin)

        self._rows_spin = KSSpinBox(
            "hGrids: ",
            "Horizontal Grids",
            _cfg.min_grid_rows,
            _cfg.max_grid_rows,
            self._rows,
            font,
            spin_width,
            self._toolbar,
        )
        self._rows_spin.valueChanged.connect(self._on_rows_changed)
        self._toolbar.addWidget(self._rows_spin)

        rename_btn = IconButton(Icon.INSERT_TEXT, "Rename pad", "", None, self._toolbar)
        rename_btn.clicked.connect(self._rename_pad)
        self._toolbar.addWidget(rename_btn)

        save_btn = IconButton(Icon.DOCUMENT_SAVE, "Save pad", "", None, self._toolbar)
        save_btn.clicked.connect(lambda: self._toggle_edit(False))
        self._toolbar.addWidget(save_btn)

        remove_keys_btn = IconButton(Icon.EDIT_DELETE, "Remove keys", "", None, self._toolbar)
        remove_keys_btn.clicked.connect(self._confirm_remove_all_keys)
        self._toolbar.addWidget(remove_keys_btn)

        remove_pad_btn = IconButton(Icon.EDIT_DELETE_SHRED, "Remove pad", "", None, self._toolbar)
        remove_pad_btn.clicked.connect(self._confirm_remove_pad)
        self._toolbar.addWidget(remove_pad_btn)

        self._toolbar_sep = QFrame(self)
        self._toolbar_sep.setObjectName("toolbarSeparator")
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
        const_sub = self._styled_menu(btn, parent_menu=menu, title="Add Constant")
        build_constant_menu(const_sub, lambda e: self._on_constant_picked(e, grid_index))
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
        menu.setProperty(Prop.CUSTOM_PAD_MENU, True)
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
        # Built on open, so it lists the active theme's colors
        if self._color_picker is not None:
            self._color_picker.deleteLater()
        colors = [(name, QColor(value)) for name, value in get_theme().colors.items()]
        self._color_picker = self._make_picker(
            [("Custom Color...", None)]
            + [(name, f"${name}", color) for name, color in colors if color.isValid()],
            separator_after=0,
        )
        self._color_picker.item_selected.connect(self._on_color_picked)
        self._color_picker.popup(global_pos)

    def _restyle_keys(self) -> None:
        for grid in self._grids:
            grid.restyle()

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

    def _on_constant_picked(self, entry: ConstEntry, grid_index: int) -> None:
        if grid_index < len(self._grids):
            grid = self._grids[grid_index]
            _add_constant(grid.keys, entry, grid.max_rows)
            grid.rebuild()

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
        default_max = _cfg.default_max_rows

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
        layout = PadLayout(
            self._label,
            self._cols,
            self._rows,
            tuple(
                GridLayout(g.max_rows, tuple(kd.to_settings() for kd in g.keys))
                for g in self._grids
            ),
        )
        self._settings.setValue(self._settings_key, json.dumps(dataclasses.asdict(layout)))

    def _load(self) -> None:
        raw = self._settings.value(self._settings_key, "")
        # A pad the GUI just created has nothing saved yet
        if not raw:
            return
        where = f"custom pad {self._pad_id}"
        try:
            layout = build(PadLayout, json.loads(str(raw)), where)
        except json.JSONDecodeError as error:
            _log.warning("%s: %s", where, error)
            return
        except TableError as error:
            _log.warning("%s", error)
            return

        self._label = layout.label
        self._cols = layout.cols
        self._rows = layout.rows
        total = self._rows * self._cols
        grids = layout.grids[:total]
        self._grid_keys = [_load_keys(g.keys, g.max_rows) for g in grids]
        self._grid_max_rows = [g.max_rows for g in grids]
        for _ in range(total - len(grids)):
            self._grid_keys.append([])
            self._grid_max_rows.append(_cfg.default_max_rows)
