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
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from tcalc.core.utils import CalcValue
from tcalc.theme import get_theme
from tcalc.ui.widgets.common.button import IconButton
from tcalc.ui.widgets.history.utils import wrap_expression
from tcalc.ui.widgets.math import ExpressionSlot, InputKind, MathRender
from tcalc.ui.widgets.utils import InputAlign, apply_scaled_fonts

from .style import apply_style, calc_config


class Result(QWidget):
    def __init__(self, parent: QWidget, config: calc_config):
        super().__init__(parent)

        self._config = config

        self.setFixedHeight(self._config["height"])
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.setLayout(self._layout)

        self._row_layout = QHBoxLayout()
        self._row_layout.setContentsMargins(0, 0, 0, 0)
        self._layout.addLayout(self._row_layout)

        self._res_render = MathRender(read_only=True)
        self._res_slot = ExpressionSlot(
            kind=InputKind.MAIN, key="fracResult", align=InputAlign.RIGHT
        )

        self._result_font = QFont()
        self._result_font.setPointSize(self._config["font_size"])
        self._result_font.setBold(True)

        self.result_label = QLabel("0")
        self.result_label.setObjectName("displayResult")
        self.result_label.setFont(self._result_font)
        self.result_label.setAlignment(InputAlign.RIGHT.value)
        self.result_label.setWordWrap(True)

        # Wrap the label in a vertical scroll area: if the wrapped Collection
        # outgrows the result widget's fixed height, the scrollbar appears
        # without expanding the panel.
        self._result_scroll = QScrollArea(self)
        self._result_scroll.setObjectName("displayResultScroll")
        self._result_scroll.setWidget(self.result_label)
        self._result_scroll.setWidgetResizable(True)
        self._result_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._result_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._result_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._result_scroll.viewport().setAutoFillBackground(False)
        self.result_label.setAutoFillBackground(False)

        self._row_layout.addWidget(self._result_scroll, 1)
        self._res_slot.hide()
        self._row_layout.addWidget(self._res_slot, 1)
        btn_size = self._config["btn_size"]
        btn_padding = self._config["btn_padding"]
        icon_base, _ = self._config["colors"]["frac_icon"]
        icon_tint = get_theme().colors[icon_base]
        self._frac_btn_tooltip = "Show as fraction"
        self._decimal_tooltip = "Show as decimal"
        self._frac_btn = IconButton(
            icon_name=self._config["frac_icon"],
            tooltip=self._frac_btn_tooltip,
            size=btn_size,
            padding=btn_padding,
            tint=icon_tint,
            parent=self,
        )
        self._frac_btn.setObjectName("fracToggleBtn")
        self._frac_btn.hide()
        self._frac_btn.clicked.connect(self._toggle_fraction_view)
        self._row_layout.addWidget(self._frac_btn, 0)

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(int(self._config.get("resize_debounce_ms", 30)))
        self._resize_timer.timeout.connect(self._on_resize_settled)

        self.status_label = QLabel("", self)
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(InputAlign.RIGHT.value)
        self.status_label.hide()
        self._layout.addWidget(self.status_label, 0)

        self._frac_visible = False

        apply_style(self)
        QTimer.singleShot(0, self._update_fonts)

    def update_res(
        self,
        result_text: str,
        result: CalcValue | None,
        status_text: str = "",
        status_kind: str = "",
    ) -> None:
        self.setUpdatesEnabled(False)
        try:
            self.result_label.setText(
                wrap_expression(
                    result_text,
                    self.result_label.fontMetrics(),
                    self._result_scroll.viewport().width(),
                )
            )

            # Check if result can be rendered as fraction
            if isinstance(result, calc_native.Rational):
                if result.denominator != 1:
                    self._create_fract(result.numerator, result.denominator)
                    self._frac_btn.show()
            else:
                self._frac_btn.hide()
                self._hide_fraction_view()

            self._apply_status(status_text, status_kind)
            self._update_fonts()
        finally:
            self.setUpdatesEnabled(True)

    def _apply_status(self, status_text: str, status_kind: str) -> None:
        if not status_text:
            self.status_label.hide()
            self.status_label.setText("")
            return
        self.status_label.setText(status_text)
        self.status_label.setProperty("statusKind", status_kind or "info")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.show()

    def _sync_fraction_ui(self) -> None:
        self._frac_btn.update_icon(
            self._config["decimal_icon"] if self._frac_visible else self._config["frac_icon"]
        )
        self._frac_btn.update_tooltip(
            self._decimal_tooltip if self._frac_visible else self._frac_btn_tooltip
        )

        if self._frac_visible:
            self._show_fraction_view()
        else:
            self._hide_fraction_view()

    def _toggle_fraction_view(self):
        self._frac_visible = not self._frac_visible
        self._sync_fraction_ui()
        self._update_fonts()

    def _show_fraction_view(self) -> None:

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
        self.update_res("", None)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._resize_timer.start()

    def _on_resize_settled(self) -> None:
        """Debounced resize handler: re-apply font scaling + re-flow the
        wrapped text against the now-stable viewport width."""
        self._update_fonts()
        self.result_label.setText(
            wrap_expression(
                self.result_label.text().replace("\n", ""),
                self.result_label.fontMetrics(),
                self._result_scroll.viewport().width(),
            )
        )
