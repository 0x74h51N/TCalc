#
#
#
# TCalc - Copyright (C) 2025 Tahsin Onemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import calc_native
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)

from tcalc.theme import get_theme
from tcalc.ui.widgets.common.button import IconButton
from tcalc.ui.widgets.math.expression_node import ExpressionSlot, InputKind
from tcalc.ui.widgets.math.math_render import MathRender
from tcalc.ui.widgets.utils import InputAlign, apply_scaled_fonts

from .style import apply_style, calc_config


class Result(QWidget):
    def __init__(self, parent: QWidget, config: calc_config):
        super().__init__(parent)

        self._config = config

        self.setFixedHeight(self._config["height"])
        self._layout = QHBoxLayout()
        self.setLayout(self._layout)
        self._res_render = MathRender(read_only=True)
        self._res_slot = ExpressionSlot(
            kind=InputKind.MAIN, key="fracResult", align=InputAlign.RIGHT
        )

        self._result_font = QFont()
        self._result_font.setPointSize(self._config["font_size"])
        self._result_font.setBold(True)

        self.result_label = QLabel("0", self)
        self.result_label.setObjectName("displayResult")
        self.result_label.setFont(self._result_font)
        self.result_label.setAlignment(InputAlign.RIGHT.value)

        self._layout.addWidget(self.result_label, 1)
        self._res_slot.hide()
        self._layout.addWidget(self._res_slot, 1)
        btn_size = self._config["btn_size"]
        btn_padding = self._config["btn_padding"]
        icon_base, _ = self._config["colors"]["frac_icon"]
        icon_tint = get_theme().colors[icon_base]
        self._frac_btn = IconButton(
            icon_name="./assets/frac.svg",
            tooltip="Show as fraction",
            size=btn_size,
            padding=btn_padding,
            tint=icon_tint,
            parent=self,
        )
        self._frac_btn.setObjectName("fracToggleBtn")
        self._frac_btn.hide()
        self._frac_btn.clicked.connect(self._toggle_fraction_view)
        self._layout.addWidget(self._frac_btn, 0)

        self._frac_visible = False
        self._frac_renderable = False

        apply_style(self)
        QTimer.singleShot(0, self._update_fonts)

    def update_res(self, result_text: str, renderable: bool = False) -> None:
        self.result_label.setText(result_text)
        self._frac_renderable = renderable
        self._update_fonts()
        if not renderable:
            self._frac_btn.hide()
            self._hide_fraction_view()
        else:
            self._frac_btn.show()

    def set_fraction(self, numerator: int, denominator: int) -> None:
        """Render fraction widget into the result slot."""
        self._create_fract(numerator, denominator)

    def _toggle_fraction_view(self) -> None:
        if self._frac_visible:
            self._hide_fraction_view()
        else:
            self._show_fraction_view()
        self._update_fonts()

    def _show_fraction_view(self) -> None:
        if not self._frac_renderable:
            return
        self._frac_visible = True
        self._res_slot.show()
        self.result_label.hide()

    def _hide_fraction_view(self) -> None:
        self._frac_visible = False
        self._res_slot.hide()
        self.result_label.show()

    def _update_fonts(self) -> None:
        norm = self._config["font_norm"]
        base_font = self._config["font_size"]
        max_pt = int(self._config["max_pt"])
        line_edits = self._res_slot.line_edits()
        self._res_render.update_line_fonts(line_edits, self, base_font - norm, max_pt - norm)
        for le in line_edits:
            f = le.font()
            if not f.bold():
                f.setBold(True)
                le.setFont(f)

        apply_scaled_fonts(
            self,
            [self.result_label],
            base_font,
            max_pt,
        )

    def _create_fract(self, numerator: int, denominator: int) -> None:
        self._clear_slot()
        frac = f"\\frac{{{numerator}}}{{{denominator}}}"
        if numerator < 0:
            frac = f"-\\frac{{{numerator * -1}}}{{{denominator}}}"
        tok = calc_native.tokenize_string(frac)
        _res_seg = self._res_slot.default_input()
        _res_seg.setReadOnly(True)
        _res_seg.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._res_render.render_node(_res_seg, tok)

    def _clear_slot(self) -> None:
        self._res_slot.remove_segments(self._res_slot._segments)

    def clear_result(self) -> None:
        self._clear_slot()
        self.update_res("", False)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fonts()
