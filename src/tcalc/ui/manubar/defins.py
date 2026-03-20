from __future__ import annotations

from typing import Tuple

from PySide6.QtWidgets import QMessageBox

from tcalc.app_state import CalculatorMode
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations

from .menu_builder import MenuActionItem, MenuActionType, MenuSeparatorItem


def _open_keyboard_shortcuts(ctx) -> None:
    QMessageBox.information(ctx.window, "Keyboard Shortcuts", "Coming soon.")


def _open_tcalc_config(ctx) -> None:
    QMessageBox.information(ctx.window, "TCalc Settings", "Coming soon.")


FILE_MENU_ACTIONS: Tuple[MenuActionItem, ...] = (
    MenuActionItem(
        text="Quit",
        icon="application-exit",
        item_type=MenuActionType.OPS,
        fn=FileOperations.quit,
    ),
)

EDIT_MENU_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem, ...] = (
    MenuActionItem(
        text="Undo",
        icon="edit-undo",
        item_type=MenuActionType.OPS,
        fn=EditOperations.undo,
    ),
    MenuActionItem(
        text="Redo",
        icon="edit-redo",
        item_type=MenuActionType.OPS,
        fn=EditOperations.redo,
    ),
    MenuSeparatorItem(),
    MenuActionItem(
        text="Cut",
        icon="edit-cut",
        item_type=MenuActionType.OPS,
        fn=EditOperations.cut,
    ),
    MenuActionItem(
        text="Copy",
        icon="edit-copy",
        item_type=MenuActionType.OPS,
        fn=EditOperations.copy,
    ),
    MenuActionItem(
        text="Paste",
        icon="edit-paste",
        item_type=MenuActionType.OPS,
        fn=EditOperations.paste,
    ),
)

SETTINGS_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem, ...] = (
    MenuActionItem(
        text="Simple Mode",
        icon="accessories-calculator",
        checkable=True,
        item_type=MenuActionType.OPS,
        fn=lambda ops: ops.set_mode(CalculatorMode.SIMPLE),
        mode=CalculatorMode.SIMPLE,
    ),
    MenuActionItem(
        text="Science Mode",
        icon="applications-science",
        checkable=True,
        item_type=MenuActionType.OPS,
        fn=lambda ops: ops.set_mode(CalculatorMode.SCIENCE),
        mode=CalculatorMode.SCIENCE,
    ),
    MenuActionItem(
        text="Statistic Mode (Coming Soon)",
        icon="office-chart-bar",
        checkable=True,
        enabled=False,
        item_type=MenuActionType.OPS,
        fn=lambda ops: ops.set_mode(CalculatorMode.STATISTIC),
        mode=CalculatorMode.STATISTIC,
    ),
    MenuSeparatorItem(),
    MenuActionItem(
        text="Show Keypad",
        icon="input-keyboard",
        checkable=True,
        item_type=MenuActionType.TOGGLE,
        checked_attr="show_keypad",
        fn=SettingsOperations.toggle_keypad,
    ),
    MenuActionItem(
        text="Show History",
        icon="document-open-recent",
        checkable=True,
        item_type=MenuActionType.TOGGLE,
        checked_attr="show_history",
        fn=SettingsOperations.toggle_history,
    ),
    MenuActionItem(
        text="Constant Buttons (Coming Soon)",
        icon="format-text-symbol",
        checkable=True,
        enabled=False,
        item_type=MenuActionType.TOGGLE,
        checked_attr="show_constant_buttons",
        fn=SettingsOperations.toggle_constants,
    ),
    MenuSeparatorItem(),
    MenuActionItem(
        text="Configure Keyboard Shortcuts...",
        icon="input-keyboard",
        item_type=MenuActionType.BUTTON,
        fn=_open_keyboard_shortcuts,
    ),
    MenuActionItem(
        text="Configure TCalc...",
        icon="configure",
        item_type=MenuActionType.BUTTON,
        fn=_open_tcalc_config,
    ),
)
