from __future__ import annotations

from tcalc.app_state import CalculatorMode
from tcalc.ui.controller.menubar import EditOperations, FileOperations, SettingsOperations

FILE_MENU_ACTIONS = [
    {
        "id": FileOperations.quit,
        "icon": "application-exit",
        "text": "Quit",
        "checkable": False,
        "enabled": True,
    },
]

EDIT_MENU_ACTIONS = [
    {
        "id": EditOperations.undo,
        "icon": "edit-undo",
        "text": "Undo",
        "checkable": False,
        "enabled": True,
    },
    {
        "id": EditOperations.redo,
        "icon": "edit-redo",
        "text": "Redo",
        "checkable": False,
        "enabled": True,
    },
    {
        "id": EditOperations.cut,
        "icon": "edit-cut",
        "text": "Cut",
        "checkable": False,
        "enabled": True,
    },
    {
        "id": EditOperations.copy,
        "icon": "edit-copy",
        "text": "Copy",
        "checkable": False,
        "enabled": True,
    },
    {
        "id": EditOperations.paste,
        "icon": "edit-paste",
        "text": "Paste",
        "checkable": False,
        "enabled": True,
    },
]

SETTINGS_TOGGLE_ACTIONS = [
    {
        "id": SettingsOperations.toggle_history,
        "icon": "view-history",
        "text": "Show History",
        "checkable": True,
        "enabled": True,
    },
    {
        "id": SettingsOperations.toggle_constants,
        "icon": "format-text-symbol",
        "text": "Constant Buttons (Coming Soon)",
        "checkable": True,
        "enabled": False,
    },
]

MODE_ACTIONS = [
    {
        "id": CalculatorMode.SIMPLE,
        "icon": "accessories-calculator",
        "text": "Simple Mode",
        "checkable": True,
        "enabled": True,
    },
    {
        "id": CalculatorMode.SCIENCE,
        "icon": "applications-science",
        "text": "Science Mode (Coming Soon)",
        "checkable": True,
        "enabled": True,
    },
    {
        "id": CalculatorMode.STATISTIC,
        "icon": "office-chart-bar",
        "text": "Statistic Mode (Coming Soon)",
        "checkable": True,
        "enabled": False,
    },
]
