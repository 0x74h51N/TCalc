#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QWidget

from tcalc.app_state import CalculatorMode, get_app_state
from tcalc.ui.keyboard import KeyboardHandler

from ..core import Calculator
from .config import get_history_width_from_total, history_style, memory_style, window
from .controller import CalculatorController, EditOperations
from .controller.utils import format_result
from .manubar.menu import Menubar
from .widgets import CalcWidget, History, MemoryBar, SidePanel


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        app_state = get_app_state()

        self.calculator: Calculator = Calculator()
        self.setWindowTitle("TCalc")

        central = QWidget(self)
        self.setCentralWidget(central)

        m_layout = QHBoxLayout(central)
        margins = int(window["layout_margins"])
        m_layout.setContentsMargins(margins, margins, margins, margins)
        m_layout.setSpacing(int(window["layout_spacing"]))

        # Calc widget (display + keypad)
        self.calc_widget = CalcWidget(parent=central)
        self.calc_widget.setMinimumSize(window["calc_min_width"], window["min_height"])
        m_layout.addWidget(self.calc_widget, window["calc_stretch"])

        self.menubar = Menubar(self)

        # Connect settings menu to visibility changes
        settings_menu = self.menubar.settings_menu
        if settings_menu is not None:
            settings_menu.window = self  # Pass window reference for UI updates

        self.divider = QFrame(self)
        self.divider.setFrameShape(QFrame.Shape.VLine)
        self.divider.setFrameShadow(QFrame.Shadow.Sunken)
        self.divider.setLineWidth(int(window["divider_line_width"]))
        self.divider.setVisible(app_state.show_history)

        # Side panel: memory bar + history
        self.memory_bar = MemoryBar()
        self.history = History(mode=app_state.mode)

        self.side_panel = SidePanel(parent=central)
        self.side_panel.add_widget(self.memory_bar)
        self.side_panel.add_widget(self.history, stretch=1)
        self.side_panel.setMinimumSize(window["history_min_width"], window["min_height"])
        self.side_panel.setVisible(app_state.show_history)

        # Add to layout
        m_layout.addWidget(self.divider)
        m_layout.addWidget(self.side_panel, window["history_stretch"])
        # Register font targets on side panel
        self.side_panel.register_font_targets(
            [self.memory_bar._memory_label, self.memory_bar._memory_value],
            int(memory_style["font_size"]),
            int(memory_style["max_pt"]),
        )
        self.side_panel.register_font_targets(
            [self.history.list],
            int(history_style["font_size"]),
            int(history_style["max_pt"]),
            callback=self.history._re_render_items,
        )
        self.side_panel.register_font_targets(
            self.history.get_expression_labels(),
            int(history_style["expr_min_pt"]),
            int(history_style["expr_max_pt"]),
        )
        self.side_panel.register_font_targets(
            self.history.get_result_labels(),
            int(history_style["result_min_pt"]),
            int(history_style["result_max_pt"]),
        )
        self.side_panel.register_font_targets(
            [self.history.clear_button],
            int(history_style["clr_btn_min_pt"]),
            int(history_style["clr_btn_max_pt"]),
        )
        self.history.items_changed.connect(self.side_panel._update_fonts)

        # Edit operations
        self.edit_ops = EditOperations(self)

        # Controller binding
        self.controller = CalculatorController(
            self.calculator,
            self.calc_widget.display,
            self.history,
            self.memory_bar,
            self.edit_ops,
            self.calc_widget.topbar,
        )

        self.calc_widget.keypad.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.key_pressed.connect(self.controller.handle_key)
        self.calc_widget.topbar.angle_changed.connect(self.controller.set_angle_unit)

        # Keyboard handler for global shortcuts
        self._keyboard_handler = KeyboardHandler(
            self.calc_widget.display.editor,
            self.calc_widget.keypad,
            self.controller,
        )

        # Sync initial keypad state and size constraints
        self.update_layout()
        self._update_history_size()

    def keyPressEvent(self, event):
        if self._keyboard_handler.handle_key_press(event):
            return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_history_size()
        self.side_panel._update_fonts()

    def _update_history_size(self):
        central = self.centralWidget()
        if central:
            width = central.width()
            history_width = get_history_width_from_total(width)
            self.side_panel.setMinimumWidth(history_width)

    def update_layout(self) -> None:
        app_state = get_app_state()
        self.side_panel.setVisible(app_state.show_history)
        self.divider.setVisible(app_state.show_history)

        is_science = app_state.mode == CalculatorMode.SCIENCE
        keypad = self.calc_widget.keypad
        topbar = self.calc_widget.topbar
        keypad._science_widget.setVisible(is_science)
        topbar._angle_group.setVisible(is_science)
        keypad._buttons["Shift"].setVisible(app_state.mode != CalculatorMode.SIMPLE)

        topbar.set_angle(app_state.angle_unit)

        hyp_btn = keypad.get_button("Hyp")
        if hyp_btn:
            hyp_btn.setChecked(bool(app_state.hyp))

        keypad._buttons["Shift"].setChecked(bool(app_state.shifted))

        for label in ("π", "e"):
            btn = keypad.get_button(label)
            if btn is not None:
                btn.setVisible(bool(app_state.show_constant_buttons))

        topbar.set_memory_available(app_state.memory is not None)
        self.memory_bar.set_memory(
            "" if app_state.memory is None else format_result(app_state.memory)
        )

        # Adjust minimum width based on visibility and mode
        calc_width = window["calc_min_width"]
        if app_state.mode == CalculatorMode.SCIENCE:
            calc_width += window["science_panel_width"]

        if app_state.show_history:
            min_width = calc_width + window["history_min_width"]
        else:
            min_width = calc_width

        self.setMinimumWidth(min_width)
        self.adjustSize()
        self.resize(self.minimumSizeHint())

    def sizeHint(self) -> QSize:
        central = self.centralWidget()
        if central:
            size = central.sizeHint()
        else:
            size = QSize(int(window["size_hint_width"]), int(window["size_hint_height"]))

        # Add menubar height if exists
        if self.menuBar():
            size.setHeight(size.height() + self.menuBar().height())

        return size
