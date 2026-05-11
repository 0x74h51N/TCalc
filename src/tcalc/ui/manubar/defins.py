from __future__ import annotations

from typing import Tuple

from PySide6.QtWidgets import QMessageBox

from tcalc.app_state import CalculatorMode, DockKind
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations

from .menu_builder import MenuActionItem, MenuActionType, MenuSeparatorItem, SubmenuItem


def _coming_soon(ctx) -> None:
    QMessageBox.information(ctx.window, "Coming soon", "Coming soon.")


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

SETTINGS_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem | SubmenuItem, ...] = (
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
    SubmenuItem(
        text="Keypads",
        icon="./assets/keypads.svg",
        items=(
            MenuActionItem(
                text="Numpad",
                icon="./assets/numpad.svg",
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.NUMPAD),
                fn=SettingsOperations.toggle_numpad,
            ),
            MenuActionItem(
                text="Functions Pad",
                icon="./assets/func.svg",
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.FUNCPAD),
                fn=SettingsOperations.toggle_funcpad,
            ),
            MenuActionItem(
                text="Trig / Power Pad",
                icon="./assets/trig.svg",
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.TRIGPAD),
                fn=SettingsOperations.toggle_trigpad,
            ),
            MenuActionItem(
                text="Constant Pad (Coming Soon)",
                icon="format-text-symbol",
                checkable=True,
                enabled=False,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.show_constant_buttons,
                fn=SettingsOperations.toggle_constants,
            ),
            MenuSeparatorItem(),
            MenuActionItem(
                text="Add Custom Pad",
                icon="./assets/custom_pad.svg",
                item_type=MenuActionType.OPS,
                fn=SettingsOperations.add_custom_pad,
            ),
        ),
    ),
    MenuActionItem(
        text="History",
        icon="document-open-recent",
        checkable=True,
        item_type=MenuActionType.TOGGLE,
        checked_getter=lambda s: s.is_dock_open(DockKind.HISTORY),
        fn=SettingsOperations.toggle_history,
    ),
    MenuActionItem(
        text="Restore Default Layout",
        icon="view-restore",
        item_type=MenuActionType.OPS,
        fn=SettingsOperations.restore_default_layout,
    ),
    MenuSeparatorItem(),
    MenuActionItem(
        text="Configure Keyboard Shortcuts...",
        icon="input-keyboard",
        enabled=False,
        item_type=MenuActionType.BUTTON,
        fn=_coming_soon,
    ),
    MenuActionItem(
        text="Configure TCalc...",
        icon="configure",
        enabled=False,
        item_type=MenuActionType.BUTTON,
        fn=_coming_soon,
    ),
)
