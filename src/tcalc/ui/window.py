#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings, QSize, QTimer
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

from tcalc.app_state import CalculatorMode, get_app_state
from tcalc.ui.keyboard import KeyboardHandler

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
        state_attr: str,
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
        dock.setVisible(getattr(get_app_state(), state_attr))
        dock.visibilityChanged.connect(
            lambda visible, attr=state_attr: self._on_dock_visibility_changed(attr, visible)
        )
        return dock

    def _setup_keypads(self) -> None:
        self.numpad = MainKeypad(parent=self)
        self._numpad_dock = self._make_dock(
            self.numpad,
            "Numpad",
            "numpadDock",
            state_attr="show_numpad",
            min_width=window["numpad_min_width"],
        )

        self.functions_keypad = FunctionsKeypad(parent=self)
        self._functions_dock = self._make_dock(
            self.functions_keypad,
            "Functions",
            "functionsDock",
            state_attr="show_funcpad",
            min_width=window["funcpad_min_width"],
        )

        self.trig_power_keypad = TrigPowerKeypad(parent=self)
        self._trig_power_dock = self._make_dock(
            self.trig_power_keypad,
            "Trig / Power",
            "trigPowerDock",
            state_attr="show_trigpad",
            min_width=window["trigpad_min_width"],
        )

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
            state_attr="show_history",
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

    def _on_dock_visibility_changed(self, attr: str, visible: bool) -> None:
        """Sync app_state and menu toggle when any registered dock is shown/hidden."""
        app_state = get_app_state()
        if getattr(app_state, attr) != visible:
            setattr(app_state, attr, visible)
        self.menubar.settings_menu.sync_toggle(attr, visible)

    # ------------------------------------------------------------------
    # Window state persistence
    # ------------------------------------------------------------------

    def _restore_window_state(self) -> None:
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

        self._on_dock_visibility_changed("show_numpad", self._numpad_dock.isVisible())
        self._on_dock_visibility_changed("show_funcpad", self._functions_dock.isVisible())
        self._on_dock_visibility_changed("show_trigpad", self._trig_power_dock.isVisible())
        self._on_dock_visibility_changed("show_history", self._history_dock.isVisible())

    def _save_window_state(self) -> None:
        settings = QSettings("TCalc", "TCalc")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState(self.WINDOW_STATE_VERSION))

    def _default_dock_layout(self) -> None:

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._trig_power_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._numpad_dock)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._functions_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._history_dock)

        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)

    def apply_def_dock_layout(self) -> None:
        self._default_dock_layout()
        self.update_layout()
        QTimer.singleShot(0, lambda: self.history.update_fonts(force_layout=True))

    # ------------------------------------------------------------------
    # Hints
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        return QSize(int(window["size_hint_width"]), int(window["size_hint_height"]))
