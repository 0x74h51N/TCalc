#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings, QSize
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

from tcalc.app_state import CalculatorMode, get_app_state
from tcalc.ui.keyboard import KeyboardHandler

from ..core import Calculator
from .config import history_style, memory_style, window
from .controller import CalculatorController, EditOperations
from .controller.utils import format_result
from .manubar.menu import Menubar
from .widgets import CalcWidget, History, Keypad, MemoryBar, SidePanel


class MainWindow(QMainWindow):
    WINDOW_STATE_VERSION = 2

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.calculator: Calculator = Calculator()
        self.setWindowTitle("TCalc")

        self.calc_widget = CalcWidget(parent=self)
        self.setCentralWidget(self.calc_widget)

        self.menubar = Menubar(self)

        self._setup_keypad_dock()
        self._setup_history_dock()
        self._setup_controller()
        self._setup_keyboard()

        self.update_layout()
        self._restore_window_state()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _setup_keypad_dock(self) -> None:
        app_state = get_app_state()
        self.keypad = Keypad(parent=self)

        self._keypad_dock = QDockWidget("Keypad", self)
        self._keypad_dock.setObjectName("keypadDock")
        self._keypad_dock.setWidget(self.keypad)
        self._keypad_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea
            | Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._keypad_dock.setMinimumWidth(window["calc_min_width"])
        self._keypad_dock.setVisible(app_state.show_keypad)
        self._keypad_dock.visibilityChanged.connect(self._on_keypad_visibility_changed)

    def _setup_history_dock(self) -> None:
        app_state = get_app_state()

        self.memory_bar = MemoryBar()
        self.history = History(mode=app_state.mode)

        self.side_panel = SidePanel(parent=self)
        self.side_panel.add_widget(self.memory_bar)
        self.side_panel.add_widget(self.history, stretch=1)

        self._register_font_targets()

        self._history_dock = QDockWidget("History", self)
        self._history_dock.setObjectName("historyDock")
        self._history_dock.setWidget(self.side_panel)
        self._history_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self._history_dock.setMinimumWidth(window["history_min_width"])
        self._history_dock.setVisible(app_state.show_history)
        self._history_dock.visibilityChanged.connect(self._on_history_visibility_changed)

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

        self.keypad.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.angle_changed.connect(self.controller.set_angle_unit)

    def _setup_keyboard(self) -> None:
        self._keyboard_handler = KeyboardHandler(
            self.calc_widget.display.editor,
            self.keypad,
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
        self._keypad_dock.setVisible(app_state.show_keypad)

    def _sync_mode_widgets(self, app_state) -> None:
        is_science = app_state.mode == CalculatorMode.SCIENCE
        topbar = self.calc_widget.topbar

        self.keypad.set_science_visible(is_science)
        topbar.set_angle_visible(is_science)
        self.keypad.set_shift_visible(app_state.mode != CalculatorMode.SIMPLE)

        topbar.set_angle(app_state.angle_unit)

        hyp_btn = self.keypad.get_button("Hyp")
        if hyp_btn:
            hyp_btn.setChecked(bool(app_state.hyp))

        self.keypad.set_shift_checked(bool(app_state.shifted))

        for label in ("π", "e"):
            btn = self.keypad.get_button(label)
            if btn is not None:
                btn.setVisible(bool(app_state.show_constant_buttons))

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

    def _on_history_visibility_changed(self, visible: bool) -> None:
        """Sync app_state when history dock is shown/hidden."""
        app_state = get_app_state()
        if app_state.show_history != visible:
            app_state.show_history = visible
        self.menubar.settings_menu.sync_toggle("show_history", visible)

    def _on_keypad_visibility_changed(self, visible: bool) -> None:
        """Sync app_state when keypad dock is shown/hidden."""
        app_state = get_app_state()
        if app_state.show_keypad != visible:
            app_state.show_keypad = visible
        self.menubar.settings_menu.sync_toggle("show_keypad", visible)

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
            self._apply_default_dock_layout()

        self._on_history_visibility_changed(self._history_dock.isVisible())
        self._on_keypad_visibility_changed(self._keypad_dock.isVisible())

    def _save_window_state(self) -> None:
        settings = QSettings("TCalc", "TCalc")
        settings.setValue("window/geometry", self.saveGeometry())
        settings.setValue("window/state", self.saveState(self.WINDOW_STATE_VERSION))

    def _apply_default_dock_layout(self) -> None:
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._keypad_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._history_dock)

        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)

    # ------------------------------------------------------------------
    # Hints
    # ------------------------------------------------------------------

    def sizeHint(self) -> QSize:
        return QSize(int(window["size_hint_width"]), int(window["size_hint_height"]))
