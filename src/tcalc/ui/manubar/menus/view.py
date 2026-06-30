from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QInputDialog, QMenu, QMenuBar, QMessageBox

from tcalc.app_state import get_app_state
from tcalc.ui.config import preset_config
from tcalc.ui.controller.menubar import ViewOperations
from tcalc.ui.utils import get_icon

from ...widgets.common.button import CustomPresetActions
from ..defins import VIEW_ACTIONS
from ..menu_builder import MenuActionType, ToggleMenuContext

if TYPE_CHECKING:
    from ...keyboard import ShortcutManager
    from ...window import MainWindow


def _separator(menu: QMenu) -> QAction:
    sep = QAction(menu)
    sep.setSeparator(True)
    return sep


class ViewMenu:
    def __init__(self, menu: QMenuBar, window: MainWindow, shortcuts: ShortcutManager):
        self.app_state = get_app_state()
        self.window = window
        self.ops = ViewOperations(window)
        self._preset_actions: dict = {}
        self._toggle_actions: dict[Callable, QAction] = {}
        self._custom_preset_actions: dict[int, QAction] = {}
        self._preset_bar: CustomPresetActions | None = None

        self._view_menu = menu.addMenu("View")

        ctx: ToggleMenuContext[ViewOperations] = ToggleMenuContext(
            window,
            shortcuts,
            ops=self.ops,
            app_state=self.app_state,
        )

        for item in VIEW_ACTIONS:
            for defn, action in item.add_to(self._view_menu, ctx):
                if defn.preset:
                    self._preset_actions[defn.preset] = action
                    action.triggered.connect(self._update_preset_selection)
                if defn.item_type == MenuActionType.TOGGLE:
                    self._toggle_actions[defn.fn] = action

        self._update_preset_selection()
        # The angle toggle is driven by presets (no signal), so re-sync its check on open.
        self._view_menu.aboutToShow.connect(self._sync_angle_toggle)

        self._keypads_action = self._find_action_with_menu(self._view_menu, "Keypads")
        if self._keypads_action is not None:
            keypads_menu = self._keypads_action.menu()
            assert isinstance(keypads_menu, QMenu)
            keypads_menu.aboutToShow.connect(self._populate_custom_pads)

        self._preset_action = self._find_action_with_menu(self._view_menu, "Keypad Preset")
        if self._preset_action is not None:
            preset_menu = self._preset_action.menu()
            assert isinstance(preset_menu, QMenu)
            # Custom presets are native checkable QActions (identical to the built-in
            # ones); the rename/update/delete bar floats over the active row.
            bar = CustomPresetActions(preset_config, preset_menu)
            bar.hide()
            bar.rename_requested.connect(self._on_rename_custom)
            bar.update_requested.connect(self._on_update_custom)
            bar.delete_requested.connect(self._on_delete_custom)
            self._preset_bar = bar
            preset_menu.aboutToShow.connect(self._populate_custom_presets)
            preset_menu.aboutToHide.connect(bar.hide)
            preset_menu.hovered.connect(self._on_preset_hover)

    @staticmethod
    def _find_action_with_menu(parent: QMenu, title: str) -> QAction | None:
        for action in parent.actions():
            if action.menu() is not None and action.text() == title:
                return action
        return None

    def _populate_custom_pads(self) -> None:
        menu = self._keypads_action.menu() if self._keypads_action is not None else None
        if not isinstance(menu, QMenu):
            return
        actions = []
        for _, (pad, dock) in getattr(self.window, "_custom_pads", {}).items():
            act = QAction(get_icon("./assets/custom_pad.svg"), pad.label, menu)
            act.setCheckable(True)
            act.setChecked(dock.isVisible())
            act.toggled.connect(dock.setVisible)
            actions.append(act)
        self._rebuild_dynamic(menu, "_custom_pad_dynamic", "Add Custom Pad", actions)

    def _populate_custom_presets(self) -> None:
        menu = self._preset_action.menu() if self._preset_action is not None else None
        if not isinstance(menu, QMenu):
            return
        self._custom_preset_actions.clear()
        active = self.app_state.active_custom_id
        actions = []
        for rec in self.window._layout_presets.list():
            act = QAction(get_icon(preset_config["row_icon"]), rec.name, menu)
            act.setCheckable(True)
            act.setChecked(rec.id == active)
            act.triggered.connect(lambda _=False, i=rec.id: self._on_apply_custom(i))
            self._custom_preset_actions[rec.id] = act
            actions.append(act)
        self._rebuild_dynamic(menu, "_custom_preset_dynamic", "Add Custom", actions)
        self._update_preset_selection()
        if self._preset_bar is not None:
            self._preset_bar.hide()  # revealed on hover of the active row

    @staticmethod
    def _rebuild_dynamic(menu: QMenu, tag: str, anchor_text: str, actions: list[QAction]) -> None:
        """Strip the previous <tag> rows, then wrap *actions* in separators just
        above the *anchor_text* item. Shared by the pads and presets submenus."""
        for action in list(menu.actions()):
            if action.data() == tag:
                menu.removeAction(action)
        if not actions:
            return
        anchor = next((a for a in menu.actions() if anchor_text in (a.text() or "")), None)

        def insert(action: QAction) -> None:
            action.setData(tag)
            if anchor is not None:
                menu.insertAction(anchor, action)
            else:
                menu.addAction(action)

        insert(_separator(menu))
        for act in actions:
            insert(act)
        insert(_separator(menu))

    def _on_preset_hover(self, action: QAction) -> None:
        active = self.app_state.active_custom_id
        act = self._custom_preset_actions.get(active) if active is not None else None
        if act is not None and action is act:
            self._refresh_bar()
            self._position_bar()
        elif self._preset_bar is not None:
            self._preset_bar.hide()

    def _refresh_bar(self) -> None:
        """Enable the update button only when the live layout differs from the saved one."""
        if self._preset_bar is None:
            return
        active = self.app_state.active_custom_id
        rec = self.window._layout_presets.get(active) if active is not None else None
        if rec is None:
            self._preset_bar.hide()
            return
        state, angle = self.window.capture_layout()
        self._preset_bar.set_update_enabled(not (state == rec.state and angle == rec.angle_visible))

    def _position_bar(self) -> None:
        """Float the action bar over the active custom preset's row (once per show)."""
        if self._preset_bar is None or self._preset_action is None:
            return
        menu = self._preset_action.menu()
        active = self.app_state.active_custom_id
        act = self._custom_preset_actions.get(active) if active is not None else None
        if act is None or not isinstance(menu, QMenu):
            self._preset_bar.hide()
            return
        rect = menu.actionGeometry(act)
        if rect.isEmpty():
            self._preset_bar.hide()
            return
        bar = self._preset_bar
        bar.adjustSize()
        offset = int(preset_config["bar_offset"])
        bar.move(
            rect.right() - bar.width() - offset, rect.y() + (rect.height() - bar.height()) // 2
        )
        bar.show()
        bar.raise_()

    def _on_apply_custom(self, preset_id: int) -> None:
        self.ops.apply_custom_preset(preset_id)
        self._update_preset_selection()
        self._view_menu.close()

    def _on_rename_custom(self) -> None:
        pid = self.app_state.active_custom_id
        if pid is None:
            return
        rec = self.window._layout_presets.get(pid)
        current = rec.name if rec is not None else ""
        name, ok = QInputDialog.getText(self.window, "Rename Preset", "Name:", text=current)
        if ok and name.strip():
            self.ops.rename_custom_preset(pid, name.strip())

    def _on_update_custom(self) -> None:
        pid = self.app_state.active_custom_id
        if pid is not None:
            self.ops.update_custom_preset(pid)
            self._refresh_bar()

    def _on_delete_custom(self) -> None:
        pid = self.app_state.active_custom_id
        if pid is None:
            return
        reply = QMessageBox.warning(
            self.window,
            "Delete Preset",
            "Delete this layout preset?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.ops.delete_custom_preset(pid)
            self._update_preset_selection()
            if self._preset_bar is not None:
                self._preset_bar.hide()

    def _update_preset_selection(self) -> None:
        active_custom = self.app_state.active_custom_id
        for preset, action in self._preset_actions.items():
            action.setChecked(active_custom is None and preset == self.app_state.keypad_preset)

    def _sync_angle_toggle(self) -> None:
        action = self._toggle_actions.get(ViewOperations.toggle_angle)
        if action is not None:
            action.blockSignals(True)
            action.setChecked(self.app_state.angle_visible)
            action.blockSignals(False)

    def sync_toggle(self, toggle_fn: Callable, value: bool) -> None:
        action = self._toggle_actions.get(toggle_fn)
        if action is None:
            return
        if action.isChecked() == value:
            return
        action.blockSignals(True)
        action.setChecked(value)
        action.blockSignals(False)
