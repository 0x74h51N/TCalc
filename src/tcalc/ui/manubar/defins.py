from __future__ import annotations

from typing import Tuple

from PySide6.QtWidgets import QMessageBox

from tcalc.app_state import DockKind, KeypadPreset
from tcalc.theme import ThemeChoice, ThemeMode
from tcalc.ui.controller.menubar import EditOperations, FileOperations, ViewOperations
from tcalc.ui.icon import Icon

from .menu_builder import MenuActionItem, MenuActionType, MenuSeparatorItem, SubmenuItem


def _coming_soon(ctx) -> None:
    QMessageBox.information(ctx.window, "Coming soon", "Coming soon.")


FILE_MENU_ACTIONS: Tuple[MenuActionItem, ...] = (
    MenuActionItem(
        text="Quit",
        icon=Icon.APPLICATION_EXIT,
        item_type=MenuActionType.OPS,
        fn=FileOperations.quit,
    ),
)

EDIT_MENU_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem, ...] = (
    MenuActionItem(
        text="Undo",
        icon=Icon.EDIT_UNDO,
        item_type=MenuActionType.OPS,
        fn=EditOperations.undo,
    ),
    MenuActionItem(
        text="Redo",
        icon=Icon.EDIT_REDO,
        item_type=MenuActionType.OPS,
        fn=EditOperations.redo,
    ),
    MenuSeparatorItem(),
    MenuActionItem(
        text="Cut",
        icon=Icon.EDIT_CUT,
        item_type=MenuActionType.OPS,
        fn=EditOperations.cut,
    ),
    MenuActionItem(
        text="Copy",
        icon=Icon.EDIT_COPY,
        item_type=MenuActionType.OPS,
        fn=EditOperations.copy,
    ),
    MenuActionItem(
        text="Paste",
        icon=Icon.EDIT_PASTE,
        item_type=MenuActionType.OPS,
        fn=EditOperations.paste,
    ),
)


VIEW_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem | SubmenuItem, ...] = (
    SubmenuItem(
        text="Theme",
        icon=Icon.PALETTE,
        items=(
            MenuActionItem(
                text="Light",
                icon=Icon.LIGHT_MODE,
                checkable=True,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_theme(ThemeChoice(ThemeMode.LIGHT)),
                theme=ThemeChoice(ThemeMode.LIGHT),
            ),
            MenuActionItem(
                text="Dark",
                icon=Icon.DARK_MODE,
                checkable=True,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_theme(ThemeChoice(ThemeMode.DARK)),
                theme=ThemeChoice(ThemeMode.DARK),
            ),
            MenuActionItem(
                text="System Default",
                icon=Icon.COMPUTER,
                checkable=True,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_theme(ThemeChoice(ThemeMode.SYSTEM)),
                theme=ThemeChoice(ThemeMode.SYSTEM),
            ),
            # Custom themes go here, listed each time the menu opens (see menus/view.py)
            MenuActionItem(
                text="Add Custom Theme...",
                enabled=False,
                item_type=MenuActionType.OPS,
                fn=lambda ops: None,
            ),
        ),
    ),
    MenuSeparatorItem(),
    SubmenuItem(
        text="Keypad Preset",
        icon=Icon.APPLICATIONS_SYSTEM_SYMBOLIC,
        items=(
            MenuActionItem(
                text="Simple",
                icon=Icon.CALCULATE,
                checkable=True,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_preset(KeypadPreset.SIMPLE),
                preset=KeypadPreset.SIMPLE,
            ),
            MenuActionItem(
                text="Science",
                icon=Icon.APPLICATIONS_SCIENCE_SYMBOLIC,
                checkable=True,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_preset(KeypadPreset.SCIENCE),
                preset=KeypadPreset.SCIENCE,
            ),
            MenuActionItem(
                text="Statistic (Coming Soon)",
                icon=Icon.OFFICE_CHART_BAR,
                checkable=True,
                enabled=False,
                item_type=MenuActionType.OPS,
                fn=lambda ops: ops.set_preset(KeypadPreset.STATISTIC),
                preset=KeypadPreset.STATISTIC,
            ),
            MenuSeparatorItem(),
            MenuActionItem(
                text="Add Custom...",
                icon=Icon.CUSTOM_PAD,
                item_type=MenuActionType.OPS,
                fn=ViewOperations.add_custom_preset,
            ),
        ),
    ),
    MenuActionItem(
        text="Angle Buttons",
        icon=Icon.SNAP_ANGLE_SYMBOLIC,
        checkable=True,
        item_type=MenuActionType.TOGGLE,
        checked_getter=lambda s: s.angle_visible,
        fn=ViewOperations.toggle_angle,
    ),
    MenuSeparatorItem(),
    SubmenuItem(
        text="Keypads",
        icon=Icon.KEYPADS,
        items=(
            MenuActionItem(
                text="Numpad",
                icon=Icon.NUMPAD,
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.NUMPAD),
                fn=ViewOperations.toggle_numpad,
            ),
            MenuActionItem(
                text="Functions Pad",
                icon=Icon.FUNC,
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.FUNCPAD),
                fn=ViewOperations.toggle_funcpad,
            ),
            MenuActionItem(
                text="Trig / Power Pad",
                icon=Icon.TRIG,
                checkable=True,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.is_dock_open(DockKind.TRIGPAD),
                fn=ViewOperations.toggle_trigpad,
            ),
            MenuActionItem(
                text="Constant Pad (Coming Soon)",
                icon=Icon.FORMAT_TEXT_SYMBOL,
                checkable=True,
                enabled=False,
                item_type=MenuActionType.TOGGLE,
                checked_getter=lambda s: s.show_constant_buttons,
                fn=ViewOperations.toggle_constants,
            ),
            MenuSeparatorItem(),
            MenuActionItem(
                text="Add Custom Pad",
                icon=Icon.CUSTOM_PAD,
                item_type=MenuActionType.OPS,
                fn=ViewOperations.add_custom_pad,
            ),
        ),
    ),
    MenuActionItem(
        text="History",
        icon=Icon.DOCUMENT_OPEN_RECENT,
        checkable=True,
        item_type=MenuActionType.TOGGLE,
        checked_getter=lambda s: s.is_dock_open(DockKind.HISTORY),
        fn=ViewOperations.toggle_history,
    ),
    MenuActionItem(
        text="Restore Default Layout",
        icon=Icon.VIEW_RESTORE,
        item_type=MenuActionType.OPS,
        fn=ViewOperations.restore_default_layout,
    ),
)

SETTINGS_ACTIONS: Tuple[MenuActionItem | MenuSeparatorItem | SubmenuItem, ...] = (
    MenuActionItem(
        text="Configure Keyboard Shortcuts...",
        icon=Icon.INPUT_KEYBOARD,
        enabled=False,
        item_type=MenuActionType.BUTTON,
        fn=_coming_soon,
    ),
    MenuActionItem(
        text="Configure TCalc...",
        icon=Icon.CONFIGURE,
        enabled=False,
        item_type=MenuActionType.BUTTON,
        fn=_coming_soon,
    ),
)
