#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QByteArray, QSettings, QSize, QTimer
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

from tcalc.app_state import CalculatorMode, get_app_state
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

    def _make_dock(
        self,
        widget: QWidget,
        title: str,
        object_name: str,
        initial_visible: bool,
        on_visibility: Callable[[bool], None],
        menu_toggle_fn: Callable,
        min_width: int,
        allowed: Qt.DockWidgetArea = (
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        ),
    ) -> QDockWidget:
        dock = QDockWidget(title, self)
        dock.setObjectName(object_name)
        dock.setWidget(widget)
        dock.setAllowedAreas(allowed)
        dock.setMinimumWidth(min_width)
        dock.setVisible(initial_visible)
        dock.visibilityChanged.connect(on_visibility)
        dock.visibilityChanged.connect(
            lambda visible: self.menubar.settings_menu.sync_toggle(menu_toggle_fn, visible)
        )
        return dock

    def _setup_keypads(self) -> None:
        app_state = get_app_state()

        self.numpad = MainKeypad(parent=self)
        self._numpad_dock = self._make_dock(
            self.numpad,
            "Numpad",
            "numpadDock",
            initial_visible=app_state.show_numpad,
            on_visibility=app_state.set_show_numpad,
            menu_toggle_fn=SettingsOperations.toggle_numpad,
            min_width=window["numpad_min_width"],
        )

        self.functions_keypad = FunctionsKeypad(parent=self)
        self._functions_dock = self._make_dock(
            self.functions_keypad,
            "Functions",
            "functionsDock",
            initial_visible=app_state.show_funcpad,
            on_visibility=app_state.set_show_funcpad,
            menu_toggle_fn=SettingsOperations.toggle_funcpad,
            min_width=window["funcpad_min_width"],
        )

        self.trig_power_keypad = TrigPowerKeypad(parent=self)
        self._trig_power_dock = self._make_dock(
            self.trig_power_keypad,
            "Trig / Power",
            "trigPowerDock",
            initial_visible=app_state.show_trigpad,
            on_visibility=app_state.set_show_trigpad,
            menu_toggle_fn=SettingsOperations.toggle_trigpad,
            min_width=window["trigpad_min_width"],
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

        self._history_dock = self._make_dock(
            self.side_panel,
            "History",
            "historyDock",
            initial_visible=app_state.show_history,
            on_visibility=app_state.set_show_history,
            menu_toggle_fn=SettingsOperations.toggle_history,
            min_width=window["history_min_width"],
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
            callback=self.history.update_fonts,
        )
        self.side_panel.register_font_targets(
            self.history.get_result_labels,
            int(history_style["result_min_pt"]),
            int(history_style["result_max_pt"]),
        )
        self.side_panel.register_font_targets(
            [self.history.clear_button],
            int(history_style["clr_btn_min_pt"]),
            int(history_style["clr_btn_max_pt"]),
        )
        self.history.items_changed.connect(self.side_panel.update_fonts)

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
        self._sync_dock_visibility(app_state)
        self._sync_mode_widgets(app_state)
        self._sync_memory_state(app_state)

    def _sync_dock_visibility(self, app_state) -> None:
        self._history_dock.setVisible(app_state.show_history)
        self._numpad_dock.setVisible(app_state.show_numpad)
        self._functions_dock.setVisible(app_state.show_funcpad)
        self._trig_power_dock.setVisible(app_state.show_trigpad)

    def _sync_mode_widgets(self, app_state) -> None:
        topbar = self.calc_widget.topbar

        topbar.set_angle_visible(app_state.mode == CalculatorMode.SCIENCE)
        topbar.set_angle(app_state.angle_unit)

    def _sync_memory_state(self, app_state) -> None:
        self.calc_widget.topbar.set_memory_available(app_state.memory is not None)
        self.memory_bar.set_memory(
            "" if app_state.memory is None else format_result(app_state.memory)
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
        app_state.set_show_numpad(self._numpad_dock.isVisible())
        app_state.set_show_funcpad(self._functions_dock.isVisible())
        app_state.set_show_trigpad(self._trig_power_dock.isVisible())
        app_state.set_show_history(self._history_dock.isVisible())

    def _save_window_state(self) -> None:
        settings = QSettings("TCalc", "TCalc")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState(self.WINDOW_STATE_VERSION))

    def _default_dock_layout(self) -> None:

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._trig_power_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._numpad_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._functions_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._history_dock)
        for _, dock in self._custom_pads.values():
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)

    def apply_def_dock_layout(self) -> None:
        self._default_dock_layout()
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
