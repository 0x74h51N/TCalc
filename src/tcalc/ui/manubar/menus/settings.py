from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMenuBar

from tcalc.app_state import get_app_state
from tcalc.ui.controller.menubar import SettingsOperations
from tcalc.ui.utils import get_icon

from ..defins import SETTINGS_ACTIONS
from ..menu_builder import MenuActionType, ToggleMenuContext

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


class SettingsMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.app_state = get_app_state()
        self.window = window
        self.ops = SettingsOperations(window)
        self._mode_actions: dict = {}
        self._toggle_actions: dict[Callable, QAction] = {}

        self._settings_menu = menu.addMenu("Settings")

        ctx: ToggleMenuContext[SettingsOperations] = ToggleMenuContext(
            window,
            shortcuts,
            ops=self.ops,
            app_state=self.app_state,
        )

        for item in SETTINGS_ACTIONS:
            for defn, action in item.add_to(self._settings_menu, ctx):
                if defn.mode:
                    self._mode_actions[defn.mode] = action
                    action.triggered.connect(self._update_mode_selection)
                if defn.item_type == MenuActionType.TOGGLE:
                    self._toggle_actions[defn.fn] = action

        self._update_mode_selection()

        # Hook into Keypads submenu for dynamic custom pad entries
        self._keypads_action = self._find_action_with_menu(self._settings_menu, "Keypads")
        if self._keypads_action is not None:
            keypads_menu = self._keypads_action.menu()
            assert isinstance(keypads_menu, QMenu)
            keypads_menu.aboutToShow.connect(self._populate_custom_pads)

    @staticmethod
    def _find_action_with_menu(parent: QMenu, title: str) -> QAction | None:
        for action in parent.actions():
            if action.menu() is not None and action.text() == title:
                return action
        return None

    def _populate_custom_pads(self) -> None:
        """Rebuild dynamic custom pad toggle entries in the Keypads submenu."""
        if self._keypads_action is None:
            return
        obj = self._keypads_action.menu()
        if not isinstance(obj, QMenu):
            return
        menu: QMenu = obj

        # Remove old dynamic actions (tagged with _custom_pad_dynamic property)
        for action in list(menu.actions()):
            if action.data() == "_custom_pad_dynamic":
                menu.removeAction(action)

        add_action = None
        for action in menu.actions():
            if "Add Custom Pad" in (action.text() or ""):
                add_action = action
                break

        custom_pads = getattr(self.window, "_custom_pads", {})
        if not custom_pads:
            return

        sep = QAction(menu)
        sep.setSeparator(True)
        sep.setData("_custom_pad_dynamic")
        if add_action is not None:
            menu.insertAction(add_action, sep)
        else:
            menu.addAction(sep)

        for _, (pad, dock) in custom_pads.items():
            action = QAction(get_icon("./assets/custom_pad.svg"), pad.label, menu)
            action.setCheckable(True)
            action.setChecked(dock.isVisible())
            action.setData("_custom_pad_dynamic")
            action.toggled.connect(dock.setVisible)
            if add_action is not None:
                menu.insertAction(add_action, action)
            else:
                menu.addAction(action)

        sep2 = QAction(menu)
        sep2.setSeparator(True)
        sep2.setData("_custom_pad_dynamic")
        if add_action is not None:
            menu.insertAction(add_action, sep2)
        else:
            menu.addAction(sep2)

    def _update_mode_selection(self) -> None:
        for mode, action in self._mode_actions.items():
            action.setChecked(mode == self.app_state.mode)

    def sync_toggle(self, toggle_fn: Callable, value: bool) -> None:
        action = self._toggle_actions.get(toggle_fn)
        if action is None:
            return
        if action.isChecked() == value:
            return
        action.blockSignals(True)
        action.setChecked(value)
        action.blockSignals(False)
