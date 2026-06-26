#
#
#   TCalc is a native-powered scientific desktop calculator designed
#   for high-performance, precision, and a superior user experience.
#   Copyright (C) <2025>  <Tahsin Önemli>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QByteArray, QSettings, QSize, QTimer
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

from tcalc.app_state import CalculatorMode, DockKind, get_app_state
from tcalc.ui.controller.menubar import SettingsOperations
from tcalc.ui.keyboard import KeyboardHandler
from tcalc.ui.widgets.keypad.custom_pad import CustomPad

from ..core import Calculator
from .config import history_style, memory_style, window
from .controller import CalculatorController, EditOperations
from .controller.utils import format_result
from .manubar.menu import Menubar
from .widgets import (
    CalcWidget,
    FunctionsKeypad,
    History,
    MainKeypad,
    MemoryBar,
    SidePanel,
    TrigPowerKeypad,
)


class MainWindow(QMainWindow):
    WINDOW_STATE_VERSION = 3

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.calculator: Calculator = Calculator()
        self.setWindowTitle("TCalc")

        self.calc_widget = CalcWidget(parent=self)
        self.setCentralWidget(self.calc_widget)

        self.menubar = Menubar(self)

        self._setup_keypads()
        self._setup_history_dock()
        self._setup_controller()
        self._restore_custom_pads()
        self._setup_keyboard()

        self.update_layout()
        self._restore_window_state()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    _DOCK_ALLOWED: Qt.DockWidgetArea = (
        Qt.DockWidgetArea.BottomDockWidgetArea
        | Qt.DockWidgetArea.LeftDockWidgetArea
        | Qt.DockWidgetArea.RightDockWidgetArea
    )

    _DOCK_MENU_TOGGLES: dict[DockKind, Callable] = {
        DockKind.NUMPAD: SettingsOperations.toggle_numpad,
        DockKind.FUNCPAD: SettingsOperations.toggle_funcpad,
        DockKind.TRIGPAD: SettingsOperations.toggle_trigpad,
        DockKind.HISTORY: SettingsOperations.toggle_history,
    }

    def _register_dock(
        self,
        kind: DockKind,
        widget: QWidget,
        title: str,
        object_name: str,
        min_width_key: str,
    ) -> QDockWidget:
        app_state = get_app_state()
        dock = QDockWidget(title, self)
        dock.setObjectName(object_name)
        dock.setWidget(widget)
        dock.setAllowedAreas(self._DOCK_ALLOWED)
        dock.setMinimumWidth(window[min_width_key])
        dock.setVisible(app_state.is_dock_open(kind))

        toggle_fn = self._DOCK_MENU_TOGGLES[kind]

        def _on_vis_changed(_: bool, d: QDockWidget = dock, k: DockKind = kind) -> None:
            opened = not d.isHidden()
            app_state.set_dock_open(k, opened)
            self.menubar.settings_menu.sync_toggle(toggle_fn, opened)

        dock.visibilityChanged.connect(_on_vis_changed)
        self._docks[kind] = dock
        return dock

    def _setup_keypads(self) -> None:
        self._docks: dict[DockKind, QDockWidget] = {}
        self.numpad = MainKeypad(parent=self)
        self._register_dock(
            DockKind.NUMPAD, self.numpad, "Numpad", "numpadDock", "numpad_min_width"
        )

        self.functions_keypad = FunctionsKeypad(parent=self)
        self._register_dock(
            DockKind.FUNCPAD,
            self.functions_keypad,
            "Functions",
            "functionsDock",
            "funcpad_min_width",
        )

        self.trig_power_keypad = TrigPowerKeypad(parent=self)
        self._register_dock(
            DockKind.TRIGPAD,
            self.trig_power_keypad,
            "Trig / Power",
            "trigPowerDock",
            "trigpad_min_width",
        )
        # Dynamic custom pads (restored after controller is ready)
        self._custom_pads: dict[int, tuple[CustomPad, QDockWidget]] = {}
        self._settings = QSettings("TCalc", "TCalc")

    def _setup_history_dock(self) -> None:
        app_state = get_app_state()

        self.memory_bar = MemoryBar()
        self.history = History(mode=app_state.mode)

        self.side_panel = SidePanel(parent=self)
        self.side_panel.add_widget(self.memory_bar)
        self.side_panel.add_widget(self.history, stretch=1)

        self._register_font_targets()

        self._register_dock(
            DockKind.HISTORY,
            self.side_panel,
            "History",
            "historyDock",
            "history_min_width",
        )

    def _register_font_targets(self) -> None:
        self.side_panel.register_font_targets(
            self.memory_bar.font_targets,
            int(memory_style["font_size"]),
            int(memory_style["max_pt"]),
        )
        self.side_panel.register_font_targets(
            [self.history.list],
            int(history_style["font_size"]),
            int(history_style["max_pt"]),
            # Debounced side-panel resize: re-wrap + force refresh_layout so
            # each item's QListWidget cell size is recomputed against the
            # final viewport width (initial wrap can lock in a too-tall hint
            # before the panel has settled on its real size).
            callback=lambda: self.history.update_fonts(force_layout=True),
        )
        self.side_panel.register_font_targets(
            [self.history.clear_button],
            int(history_style["clr_btn_min_pt"]),
            int(history_style["clr_btn_max_pt"]),
        )

    def _setup_controller(self) -> None:
        self.edit_ops = EditOperations(self)
        self.controller = CalculatorController(
            self.calculator,
            self.calc_widget.display,
            self.history,
            self.memory_bar,
            self.edit_ops,
            self.calc_widget.topbar,
        )

        self.numpad.key_pressed.connect(self.controller.handle_key)
        self.functions_keypad.key_pressed.connect(self.controller.handle_key)
        self.trig_power_keypad.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.angle_changed.connect(self.controller.set_angle_unit)

    def _setup_keyboard(self) -> None:
        self._keyboard_handler = KeyboardHandler(
            self.calc_widget.display.editor,
            self.numpad,
            self.controller,
        )

    # ------------------------------------------------------------------
    # Layout & state sync
    # ------------------------------------------------------------------

    def update_layout(self) -> None:
        app_state = get_app_state()
        self._sync_mode_widgets(app_state)
        self._sync_memory_state(app_state)

    def sync_all_docks(self) -> None:
        app_state = get_app_state()
        for kind, dock in self._docks.items():
            self._apply_dock_state(dock, app_state.is_dock_open(kind))

    def sync_dock(self, kind: DockKind, opened: bool) -> None:
        self._apply_dock_state(self._docks[kind], opened)

    @staticmethod
    def _apply_dock_state(dock: QDockWidget, should_show: bool) -> None:
        if should_show:
            if dock.isHidden():
                dock.show()
                dock.raise_()
        elif not dock.isHidden():
            dock.close()

    def _sync_mode_widgets(self, app_state) -> None:
        topbar = self.calc_widget.topbar

        topbar.set_angle_visible(app_state.mode == CalculatorMode.SCIENCE)
        topbar.set_angle(app_state.angle_unit)

    def _sync_memory_state(self, app_state) -> None:
        self.calc_widget.topbar.set_memory_available(app_state.memory is not None)
        self.memory_bar.set_memory(
            "" if app_state.memory is None else format_result(app_state.memory, group=True)
        )

    # ------------------------------------------------------------------
    # Events & signals
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        if self._keyboard_handler.handle_key_press(event):
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._save_window_state()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Window state persistence
    # ------------------------------------------------------------------

    def _restore_window_state(self) -> None:

        self._default_dock_layout()
        settings = QSettings("TCalc", "TCalc")

        geometry = settings.value("window/geometry", None)
        if isinstance(geometry, QByteArray) and not geometry.isEmpty():
            self.restoreGeometry(geometry)

        restored = False
        state = settings.value("window/state", None)
        if isinstance(state, QByteArray) and not state.isEmpty():
            restored = self.restoreState(state, self.WINDOW_STATE_VERSION)

        if not restored:
            self._default_dock_layout()

        app_state = get_app_state()
        for kind, dock in self._docks.items():
            app_state.set_dock_open(kind, not dock.isHidden())

    def _save_window_state(self) -> None:
        settings = QSettings("TCalc", "TCalc")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState(self.WINDOW_STATE_VERSION))

    _DEFAULT_DOCK_AREAS: dict[DockKind, Qt.DockWidgetArea] = {
        DockKind.TRIGPAD: Qt.DockWidgetArea.BottomDockWidgetArea,
        DockKind.NUMPAD: Qt.DockWidgetArea.BottomDockWidgetArea,
        DockKind.FUNCPAD: Qt.DockWidgetArea.BottomDockWidgetArea,
        DockKind.HISTORY: Qt.DockWidgetArea.RightDockWidgetArea,
    }

    def _default_dock_layout(self) -> None:
        for kind, area in self._DEFAULT_DOCK_AREAS.items():
            self.addDockWidget(area, self._docks[kind])
        for _, dock in self._custom_pads.values():
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)

    def apply_def_dock_layout(self) -> None:
        self._default_dock_layout()
        self.sync_all_docks()
        self.update_layout()
        QTimer.singleShot(0, lambda: self.history.update_fonts(force_layout=True))

    # ------------------------------------------------------------------
    # Dynamic custom pads
    # ------------------------------------------------------------------

    _CUSTOM_PAD_IDS_KEY = "custom_pads/ids"

    def _next_pad_id(self) -> int:
        if not self._custom_pads:
            return 0
        return max(self._custom_pads) + 1

    def _setup_custom_pad(self, pad_id: int) -> tuple[CustomPad, QDockWidget]:
        """Create a CustomPad + dock, wire signals, register internally."""
        pad = CustomPad(pad_id=pad_id, parent=self)
        dock = QDockWidget(pad.label, self)
        dock.setObjectName(f"customPad_{pad_id}")
        dock.setWidget(pad)
        dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        pad.key_pressed.connect(self.controller.handle_key)
        pad.pad_removed.connect(lambda pid=pad_id: self._remove_custom_pad(pid))
        pad.pad_renamed.connect(dock.setWindowTitle)
        self._custom_pads[pad_id] = (pad, dock)
        return pad, dock

    def add_custom_pad(self) -> CustomPad:
        """Create a new custom pad, dock it, and connect to controller."""
        pad_id = self._next_pad_id()
        pad, dock = self._setup_custom_pad(pad_id)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self._save_custom_pad_ids()
        return pad

    def _remove_custom_pad(self, pad_id: int) -> None:
        entry = self._custom_pads.pop(pad_id, None)
        if entry is None:
            return
        pad, dock = entry
        pad.key_pressed.disconnect(self.controller.handle_key)
        self.removeDockWidget(dock)
        dock.deleteLater()
        self._save_custom_pad_ids()

    def _save_custom_pad_ids(self) -> None:
        self._settings.setValue(self._CUSTOM_PAD_IDS_KEY, list(self._custom_pads.keys()))

    def _restore_custom_pads(self) -> None:
        raw = self._settings.value(self._CUSTOM_PAD_IDS_KEY, [])
        ids = [int(i) for i in raw] if isinstance(raw, list) else []
        for pad_id in ids:
            _, dock = self._setup_custom_pad(pad_id)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def sizeHint(self) -> QSize:
        return QSize(int(window["size_hint_width"]), int(window["size_hint_height"]))
