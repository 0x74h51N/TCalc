from __future__ import annotations

from typing import Tuple

from PySide6.QtWidgets import QMessageBox

from tcalc.app_state import CalculatorMode
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations

from .menu_builder import (
    MenuButtonItem,
    MenuModeItem,
    MenuOpsActionItem,
    MenuSeparatorItem,
    MenuToggleItem,
)


def _open_keyboard_shortcuts(ctx) -> None:
    QMessageBox.information(ctx.window, "Keyboard Shortcuts", "Coming soon.")


def _open_tcalc_config(ctx) -> None:
    QMessageBox.information(ctx.window, "TCalc Settings", "Coming soon.")


FILE_MENU_ACTIONS: Tuple[MenuOpsActionItem[FileOperations], ...] = (
    MenuOpsActionItem(
        action_id=FileOperations.quit,
        fn=FileOperations.quit,
        icon="application-exit",
        text="Quit",
        checkable=False,
        enabled=True,
    ),
)

EDIT_MENU_ACTIONS: Tuple[MenuOpsActionItem[EditOperations] | MenuSeparatorItem, ...] = (
    MenuOpsActionItem(
        action_id=EditOperations.undo,
        fn=EditOperations.undo,
        icon="edit-undo",
        text="Undo",
        checkable=False,
        enabled=True,
    ),
    MenuOpsActionItem(
        action_id=EditOperations.redo,
        fn=EditOperations.redo,
        icon="edit-redo",
        text="Redo",
        checkable=False,
        enabled=True,
    ),
    MenuSeparatorItem(),
    MenuOpsActionItem(
        action_id=EditOperations.cut,
        fn=EditOperations.cut,
        icon="edit-cut",
        text="Cut",
        checkable=False,
        enabled=True,
    ),
    MenuOpsActionItem(
        action_id=EditOperations.copy,
        fn=EditOperations.copy,
        icon="edit-copy",
        text="Copy",
        checkable=False,
        enabled=True,
    ),
    MenuOpsActionItem(
        action_id=EditOperations.paste,
        fn=EditOperations.paste,
        icon="edit-paste",
        text="Paste",
        checkable=False,
        enabled=True,
    ),
)

SETTINGS_ACTIONS: Tuple[
    MenuToggleItem[SettingsOperations] | MenuSeparatorItem | MenuButtonItem, ...
] = (
    MenuToggleItem(
        toggle_fn=SettingsOperations.toggle_history,
        checked_attr="show_history",
        icon="view-history",
        text="Show History",
        checkable=True,
        enabled=True,
    ),
    MenuToggleItem(
        toggle_fn=SettingsOperations.toggle_constants,
        checked_attr="show_constant_buttons",
        icon="format-text-symbol",
        text="Constant Buttons (Coming Soon)",
        checkable=True,
        enabled=False,
    ),
    MenuSeparatorItem(),
    MenuButtonItem(
        icon="input-keyboard",
        text="Configure Keyboard Shortcuts...",
        checkable=False,
        enabled=True,
        on_trigger=_open_keyboard_shortcuts,
    ),
    MenuButtonItem(
        icon="configure",
        text="Configure TCalc...",
        checkable=False,
        enabled=True,
        on_trigger=_open_tcalc_config,
    ),
)

MODE_ACTIONS: Tuple[MenuModeItem, ...] = (
    MenuModeItem(
        mode=CalculatorMode.SIMPLE,
        icon="accessories-calculator",
        text="Simple Mode",
        checkable=True,
        enabled=True,
    ),
    MenuModeItem(
        mode=CalculatorMode.SCIENCE,
        icon="applications-science",
        text="Science Mode (Coming Soon)",
        checkable=True,
        enabled=True,
    ),
    MenuModeItem(
        mode=CalculatorMode.STATISTIC,
        icon="office-chart-bar",
        text="Statistic Mode (Coming Soon)",
        checkable=True,
        enabled=False,
    ),
)
