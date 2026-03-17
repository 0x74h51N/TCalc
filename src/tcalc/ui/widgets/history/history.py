#
#
#
# TCalc - Copyright (C) 2025 Tahsin Onemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

import logging
from typing import Optional

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.app_state import CalculatorMode, RenderMode, get_app_state
from tcalc.ui.config import history_math
from tcalc.ui.config import history_style as style
from tcalc.ui.widgets.common.button import OptionGroup
from tcalc.ui.widgets.common.utils import Align
from tcalc.ui.widgets.math.expression_node import ExpressionSlot, InputKind
from tcalc.ui.widgets.math.math_render import MathRender
from tcalc.ui.widgets.utils import InputAlign, apply_scaled_fonts

from ..common import IconButton, Toaster, ToastLevel
from .storage import HistoryEntry, clear_history_file, load_history, save_history
from .style import apply_history_style
from .utils import wrap_expression

_log = logging.getLogger(__name__)


class History(QWidget):
    """History panel with persistent storage."""

    items_changed = Signal()
    display_mode_changed = Signal(object)

    def __init__(
        self, parent: Optional[QWidget] = None, mode: CalculatorMode = CalculatorMode.SIMPLE
    ):
        super().__init__(parent)
        self.setObjectName("historyWidget")
        self._history_items: list[HistoryEntry] = []
        self._item_widgets: list[HistoryItem] = []
        self._is_batch_rendering = False
        self._updating_fonts = False

        self._calc_mode = mode
        self._app_state = get_app_state()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.list = QListWidget()
        apply_history_style(self.list)

        self.list.currentItemChanged.connect(self._on_current_changed)
        layout.addWidget(self.list, 1)

        btn_container = QHBoxLayout()

        btn_margin = style["btn_margin"]
        btn_container.setContentsMargins(0, btn_margin, 0, 0)

        # History item render modes
        self._history_modes = OptionGroup(
            [(RenderMode.MATH, "Math"), (RenderMode.FLAT, "Flat"), (RenderMode.RAW, "Raw")],
            self._app_state.history_mode,
            self,
            tooltips={
                RenderMode.FLAT: "Formatted text",
                RenderMode.MATH: "Math render",
                RenderMode.RAW: "Raw LaTeX",
            },
        )
        self._history_modes.selection_changed.connect(self.set_mode)

        btn_container.addWidget(self._history_modes)

        btn_container.addStretch(int(style["button_spacer_stretch"]))

        # Clear Button
        self.clear_button = IconButton(
            "edit-clear-history",
            tooltip="Clears all history permanently from local storage",
            text="Clear History",
            parent=self,
        )
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clear_button.clicked.connect(self.clear_history)
        btn_container.addWidget(self.clear_button, int(style["clear_button_stretch"]))

        layout.addLayout(btn_container)

        self.reload_from_storage(self._calc_mode)

    def set_mode(self, mode: RenderMode):
        self._history_modes.set_current(mode)
        self._app_state.history_mode = mode
        self._begin_batch_render()
        try:
            self.display_mode_changed.emit(mode)
        finally:
            self._end_batch_render()

    def reload_from_storage(self, mode: CalculatorMode) -> None:
        self._begin_batch_render()
        self._calc_mode = mode
        loaded = load_history(mode)
        self.list.clear()
        self._item_widgets.clear()
        self._history_items = []
        for entry in loaded:
            try:
                self._add_item_to_list(entry)
                self._history_items.append(entry)
            except Exception:
                _log.debug("Skipping corrupt history entry", exc_info=True)
        self._end_batch_render()

    def _begin_batch_render(self) -> None:
        self._is_batch_rendering = True

    def _end_batch_render(self) -> None:
        self._is_batch_rendering = False
        self.update_fonts(force_layout=True)
        self.items_changed.emit()

    def _add_item_to_list(self, entry: HistoryEntry) -> None:
        """Add item to list widget with proper formatting."""

        item_widget = HistoryItem(entry, self._app_state.history_mode, parrent=self)
        self.display_mode_changed.connect(item_widget.set_display_mode)

        self._item_widgets.append(item_widget)

        item = QListWidgetItem(self.list)
        item.setData(Qt.ItemDataRole.UserRole, entry.expression)
        item_widget._list_item = item

        item_widget.copy_clicked.connect(lambda i=item: self._copy_item(i))
        item_widget.remove_clicked.connect(lambda i=item: self._remove_item(i))

        item.setSizeHint(item_widget.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, item_widget)

    def _on_current_changed(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        if previous is not None:
            prev_widget = self.list.itemWidget(previous)
            if isinstance(prev_widget, HistoryItem):
                prev_widget.hide_actions()
        if current is not None:
            cur_widget = self.list.itemWidget(current)
            if isinstance(cur_widget, HistoryItem):
                cur_widget.show_actions()

    def _copy_item(self, item: QListWidgetItem) -> None:
        """Copy the raw expression to clipboard."""
        expression: str = item.data(Qt.ItemDataRole.UserRole)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(expression)
            item_widget = self.list.itemWidget(item)
            if isinstance(item_widget, HistoryItem):
                item_widget.toaster.show_toast("Copied!", ToastLevel.INFO)

    def _remove_item(self, item: QListWidgetItem) -> None:
        """Remove a single history item."""
        row = self.list.row(item)
        if row < 0:
            return

        self.list.takeItem(row)
        self._history_items.pop(row)
        self._item_widgets.pop(row)

        save_history(self._history_items, self._calc_mode)
        self.items_changed.emit()

    def highlight_item(self, index: int) -> None:
        """Highlight the item at the given index, scrolling it into view."""
        if 0 <= index < self.list.count():
            self.list.setCurrentRow(index)
            self.list.scrollToItem(self.list.item(index))
        else:
            self.list.setCurrentRow(-1)

    def clear_highlight(self) -> None:
        """Remove any selection highlight from the list."""
        self.list.setCurrentRow(-1)

    def update_history(self, entry: HistoryEntry) -> None:
        """Add a new entry to history and persist to storage."""
        self._begin_batch_render()
        try:
            self._add_item_to_list(entry)
            self._history_items.append(entry)
        finally:
            self._end_batch_render()
            self.list.scrollToBottom()
            save_history(self._history_items, self._calc_mode)

    def get_history_item(self, index: int) -> str:
        return self._history_items[index].expression

    def clear_history(self) -> None:
        """Clear history from UI and storage."""
        self.list.clear()
        self._history_items.clear()
        self._item_widgets.clear()
        clear_history_file(self._calc_mode)

    def update_fonts(self, force_layout: bool = False) -> None:
        """Update fonts for all history items."""
        if self._updating_fonts:
            return

        self._updating_fonts = True
        try:
            for widget in self._item_widgets:
                widget.update_fonts()
                widget.re_wrap()
                if force_layout:
                    widget.refresh_layout()
        finally:
            self._updating_fonts = False

    def get_result_labels(self) -> list[QLabel]:
        return [w.result_label for w in self._item_widgets]


class HistoryItem(QWidget):
    """Single history entry widget with copy/remove action buttons."""

    copy_clicked = Signal()
    remove_clicked = Signal()

    def __init__(
        self,
        entry: HistoryEntry,
        mode: RenderMode,
        parrent: History,
    ) -> None:
        super().__init__(parrent)
        self.parrent = parrent
        self._entry = entry
        self.setObjectName("historyItem")
        self.setMinimumHeight(int(style["item_min_height"]))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        self._current_render_mode: RenderMode | None = None
        self._list_item: QListWidgetItem

        self.renderer = MathRender(read_only=True)

        self._layout = QVBoxLayout(self)
        self.expression_label = QLabel(self)
        self.expression_label.setAlignment(InputAlign.RIGHT.value)

        self._display_widget: QWidget

        margin = int(style["item_margin"])
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(int(style["item_spacing"]))

        # Action buttons (absolute positioned, bottom-left, outside layout)
        self._btn_size = int(style["action_btn_size"])
        self._copy_btn = IconButton(
            "edit-copy", tooltip="Copy expression", size=self._btn_size, parent=self
        )
        self._copy_btn.hide()
        self._copy_btn.clicked.connect(self.copy_clicked)

        self._remove_btn = IconButton(
            "edit-delete", tooltip="Remove from history", size=self._btn_size, parent=self
        )
        self._remove_btn.hide()
        self._remove_btn.clicked.connect(self.remove_clicked)

        self.toaster = Toaster(self, horizontal=Align.LEFT, y_offset=-self._btn_size)

        self._expr_slot = ExpressionSlot(
            kind=InputKind.MAIN, key="historyExpr", align=InputAlign.RIGHTT
        )
        self._expr_slot._on_margin_updated = self.refresh_layout
        self._seg = self._expr_slot.default_input()
        self._seg.setReadOnly(True)
        self._seg.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._expr_scroll = QScrollArea(self)
        self._expr_scroll.setObjectName("historyExprScroll")
        self._expr_scroll.setWidgetResizable(True)
        self._expr_scroll.setWidget(self._expr_slot)
        self._expr_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._expr_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._expr_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        self.render_math(self._entry)
        # Result label
        self.result_label = QLabel(entry.result, self)
        self.result_label.setAlignment(InputAlign.RIGHT.value)

        self._layout.addWidget(self.expression_label)
        self._layout.addWidget(self._expr_scroll)
        self._layout.addWidget(self.result_label)

        self.set_display_mode(mode, defer_layout=True)

    def render_math(self, entry: HistoryEntry) -> None:
        """Render expression as math widgets (read-only)."""
        self.setUpdatesEnabled(False)
        self.renderer.is_rendering = True

        try:
            if not entry.tokenized.expr_indices and not entry.tokenized.open_paren_indices:
                self._seg.setText(entry.expression)
                return
            self.renderer.render_node(self._seg, entry.tokenized)
            self.update_fonts()
        finally:
            self.renderer.is_rendering = False
            self.setUpdatesEnabled(True)

    def set_display_mode(self, mode: RenderMode, defer_layout: bool = False) -> None:
        if mode == self._current_render_mode:
            return
        self.setUpdatesEnabled(False)
        try:
            if mode == RenderMode.MATH and self._entry.tokenized is not None:
                self._display_widget = self._expr_scroll
                self.expression_label.hide()
                self._expr_scroll.show()
                self.update_fonts()
                self._current_render_mode = mode
                if not defer_layout and not self.parrent._is_batch_rendering:
                    self.refresh_layout()
            else:
                self._display_widget = self.expression_label
                self._expr_scroll.hide()
                self.expression_label.show()
                self.update_fonts()
                self._current_render_mode = mode
                QTimer.singleShot(0, lambda m=mode: self._apply_label_text(m))
        finally:
            self.setUpdatesEnabled(True)

    def _apply_label_text(self, mode: RenderMode) -> None:
        self.expression_label.setText(self._expression_text(mode))
        self.refresh_layout()

    def _wrap_text(self, text: str) -> str:
        """Wrap text to fit the list viewport width w/semantic line breaks."""
        fm = self.expression_label.fontMetrics()
        layout_margins = self._layout.contentsMargins()
        max_width = (
            self.parrent.list.viewport().width() - layout_margins.left() - layout_margins.right()
        )
        return wrap_expression(text, fm, max_width - 4)

    def _expression_text(self, mode: RenderMode) -> str:
        if mode == RenderMode.RAW:
            return self._wrap_text(self._entry.expression)
        if mode == RenderMode.FLAT:
            return self._wrap_text(self._entry.flat_text)
        return self._wrap_text(self._entry.expression)

    def update_fonts(self) -> None:
        """Update font scaling for expression inputs."""
        sample = self.parrent
        apply_scaled_fonts(
            sample,
            [self.expression_label],
            int(style["expr_min_pt"]),
            int(style["expr_max_pt"]),
        )

        base_font = int(history_math["base_font"])
        max_pt = int(history_math["max_pt"])
        self.renderer.update_line_fonts(
            self._expr_slot.line_edits(), sample, base_font, max_pt, history_math
        )

    def refresh_layout(self) -> None:
        """Recalculate item row height for QListWidget after font/mode changes in disgusting way."""

        # TODO: find a better way, delegate and heightForWidth override was worse
        if self.renderer.is_rendering:
            return

        margin = int(style["item_margin"])
        spacing = int(style["item_spacing"])
        result_h = self.result_label.sizeHint().height()

        if self._current_render_mode is RenderMode.MATH:
            scroll_sh = self._expr_scroll.sizeHint().height()
            slot_h = self._expr_slot.sizeHint().height()
            sb_h = self._expr_scroll.horizontalScrollBar().sizeHint().height()
            expr_h = max(scroll_sh, slot_h + sb_h)
        else:
            expr_h = self.expression_label.sizeHint().height()

        total = (
            margin * 3 + expr_h + result_h + spacing
        )  # Why three wtf is three right? Because it is better than two XD
        hint = QSize(0, total)
        if self._list_item.sizeHint() != hint:
            self._list_item.setSizeHint(hint)

    def re_wrap(self) -> None:
        """Re-wrap expression label text using current font metrics."""
        if self._current_render_mode is not None:
            self.expression_label.setText(self._expression_text(self._current_render_mode))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)

        margin = int(style["item_margin"])
        y = self.height() - margin - self._btn_size
        self._copy_btn.move(margin, y)
        self._remove_btn.move(margin + self._btn_size + margin // 2, y)

    def show_actions(self) -> None:
        self._copy_btn.show()
        self._copy_btn.raise_()
        self._remove_btn.show()
        self._remove_btn.raise_()

    def hide_actions(self) -> None:
        self._copy_btn.hide()
        self._remove_btn.hide()
