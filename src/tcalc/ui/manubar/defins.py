from __future__ import annotations

from typing import Tuple

from PySide6.QtWidgets import QMessageBox

from tcalc.app_state import DockKind, KeypadPreset
from tcalc.ui.controller.menubar import EditOperations, FileOperations, ViewOperations

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

VIEW_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem | SubmenuItem, ...] = (
    SubmenuItem(
        text="Keypad Preset",
        icon="applications-system",
        items=(
            MenuActionItem(
                text="Simple",
                icon="accessories-calculator",
                checkable=True,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_preset(KeypadPreset.SIMPLE),
                preset=KeypadPreset.SIMPLE,
            ),
            MenuActionItem(
                text="Science",
                icon="applications-science",
                checkable=True,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_preset(KeypadPreset.SCIENCE),
                preset=KeypadPreset.SCIENCE,
            ),
            MenuActionItem(
                text="Statistic (Coming Soon)",
                icon="office-chart-bar",
                checkable=True,
                enabled=False,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_preset(KeypadPreset.STATISTIC),
                preset=KeypadPreset.STATISTIC,
            ),
        ),
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
                fn=ViewOperations.toggle_numpad,
            ),
            MenuActionItem(
                text="Functions Pad",
                icon="./assets/func.svg",
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.FUNCPAD),
                fn=ViewOperations.toggle_funcpad,
            ),
            MenuActionItem(
                text="Trig / Power Pad",
                icon="./assets/trig.svg",
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.TRIGPAD),
                fn=ViewOperations.toggle_trigpad,
            ),
            MenuActionItem(
                text="Constant Pad (Coming Soon)",
                icon="format-text-symbol",
                checkable=True,
                enabled=False,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.show_constant_buttons,
                fn=ViewOperations.toggle_constants,
            ),
            MenuSeparatorItem(),
            MenuActionItem(
                text="Add Custom Pad",
                icon="./assets/custom_pad.svg",
                item_type=MenuActionType.OPS,
                fn=ViewOperations.add_custom_pad,
            ),
        ),
    ),
    MenuActionItem(
        text="History",
        icon="document-open-recent",
        checkable=True,
        item_type=MenuActionType.TOGGLE,
        checked_getter=lambda s: s.is_dock_open(DockKind.HISTORY),
        fn=ViewOperations.toggle_history,
    ),
    MenuActionItem(
        text="Restore Default Layout",
        icon="view-restore",
        item_type=MenuActionType.OPS,
        fn=ViewOperations.restore_default_layout,
    ),
)

SETTINGS_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem | SubmenuItem, ...] = (
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
