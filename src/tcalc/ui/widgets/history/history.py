#
#
#
# TCalc - Copyright (C) 2025 Tahsin Onemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QResizeEvent
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
from tcalc.ui.widgets.math import MathPainter, PaintCanvas
from tcalc.ui.widgets.utils import InputAlign, apply_scaled_fonts

from ..common import IconButton, Toaster, ToastLevel
from .storage import HistoryEntry, clear_history_file, load_history, save_history
from .style import apply_history_style
from .utils import wrap_expression

_log = logging.getLogger(__name__)

_HISTORY_PAGE_SIZE = 20


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
        self._pending_entries: list[HistoryEntry] = []
        self._pending_timer: Optional[QTimer] = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._painter = MathPainter()

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
        self._cancel_pending_load()
        self._calc_mode = mode
        self.list.clear()
        self._item_widgets.clear()
        self._history_items = []
        self._pending_entries = load_history(mode)
        self._load_next_batch()

    def _schedule_next_batch(self) -> None:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self._load_next_batch)
        self._pending_timer = timer
        timer.start(0)

    def _cancel_pending_load(self) -> None:
        timer = self._pending_timer
        if timer is not None:
            timer.stop()
            self._pending_timer = None
        self._pending_entries = []

    def _load_next_batch(self) -> None:
        self._pending_timer = None
        if not self._pending_entries:
            return

        split = max(0, len(self._pending_entries) - _HISTORY_PAGE_SIZE)
        batch = self._pending_entries[split:]
        self._pending_entries = self._pending_entries[:split]

        sb = self.list.verticalScrollBar()
        at_bottom = sb.value() >= sb.maximum() - 1

        self._is_batch_rendering = True
        new_widgets: list[HistoryItem] = []
        for entry in reversed(batch):
            try:
                widget = self._add_item_to_list(entry, index=0)
                self._history_items.insert(0, entry)
                new_widgets.append(widget)
            except Exception:
                _log.debug("Skipping corrupt history entry", exc_info=True)
        self._is_batch_rendering = False

        self._update_widget_fonts(new_widgets, force_layout=True)

        if at_bottom:
            self.list.scrollToBottom()

        self.items_changed.emit()

        if self._pending_entries:
            self._schedule_next_batch()

    def _begin_batch_render(self) -> None:
        self._is_batch_rendering = True

    def _end_batch_render(self) -> None:
        self._is_batch_rendering = False
        self.update_fonts(force_layout=True)
        self.items_changed.emit()

    def _add_item_to_list(self, entry: HistoryEntry, index: Optional[int] = None) -> HistoryItem:
        """Add item to list widget. If index is None, append to end; else insert at index."""
        item_widget = HistoryItem(
            entry, self._app_state.history_mode, painter=self._painter, parrent=self
        )
        self.display_mode_changed.connect(item_widget.set_display_mode)

        if index is None:
            self._item_widgets.append(item_widget)
        else:
            self._item_widgets.insert(index, item_widget)

        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, entry.expression)
        item_widget._list_item = item

        item_widget.copy_clicked.connect(lambda i=item: self._copy_item(i))
        item_widget.remove_clicked.connect(lambda i=item: self._remove_item(i))

        item.setSizeHint(item_widget.sizeHint())
        if index is None:
            self.list.addItem(item)
        else:
            self.list.insertItem(index, item)
        self.list.setItemWidget(item, item_widget)
        return item_widget

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
        self._add_item_to_list(entry)
        self._history_items.append(entry)
        new_widget = self._item_widgets[-1]
        new_widget.update_fonts()
        new_widget.re_wrap()
        new_widget.refresh_layout()
        self.list.scrollToBottom()
        self.items_changed.emit()
        save_history(self._history_items, self._calc_mode)

    def get_history_item(self, index: int) -> str:
        return self._history_items[index].expression

    def clear_history(self) -> None:
        """Clear history from UI and storage."""
        self._cancel_pending_load()
        self.list.clear()
        self._history_items.clear()
        self._item_widgets.clear()
        clear_history_file(self._calc_mode)

    def update_fonts(self, force_layout: bool = False) -> None:
        """Update fonts for all history items."""
        self._update_widget_fonts(self._item_widgets, force_layout=force_layout)

    def _update_widget_fonts(
        self, widgets: list["HistoryItem"], force_layout: bool = False
    ) -> None:
        if self._updating_fonts:
            return

        self._updating_fonts = True
        try:
            for widget in widgets:
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
        painter: MathPainter,
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

        self.painter = painter

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

        self._paint_canvas = PaintCanvas(parent=self)
        self._paint_canvas.setObjectName("historyPaintWidget")

        self._expr_scroll = QScrollArea(self)
        self._expr_scroll.setObjectName("historyExprScroll")
        self._expr_scroll.setAlignment(InputAlign.RIGHT.value)

        self._expr_scroll.setWidgetResizable(True)
        self._expr_scroll.setWidget(self._paint_canvas)
        self._expr_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._expr_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._expr_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        # Result label
        self.result_label = QLabel(entry.result, self)
        self.result_label.setAlignment(InputAlign.RIGHT.value)

        self._layout.addWidget(self.expression_label)
        self._layout.addWidget(self._expr_scroll)
        self._layout.addWidget(self.result_label)

        self.set_display_mode(mode, defer_layout=True)

    def _math_paint(self) -> None:
        base_font = int(history_math["base_font"])
        f = QFont(self.parrent.font())
        f.setPointSize(base_font)
        self._font = f
        if self._entry.tokenized is not None:
            tree = self.painter.paint_tree(self._entry.tokenized, f)
            self._paint_canvas.set_tree(tree, f)

    def set_display_mode(self, mode: RenderMode, defer_layout: bool = False) -> None:
        if mode == self._current_render_mode:
            return
        self.setUpdatesEnabled(False)
        try:
            if mode == RenderMode.MATH and self._entry.tokenized is not None:
                self._display_widget = self._expr_scroll
                self.expression_label.hide()
                self._expr_scroll.show()
                self._math_paint()

                if not defer_layout and not self.parrent._is_batch_rendering:
                    self.refresh_layout()
            else:
                self._display_widget = self.expression_label
                self._expr_scroll.hide()
                self.expression_label.show()
                QTimer.singleShot(0, lambda m=mode: self._apply_label_text(m))
                self.update_fonts()

            self._current_render_mode = mode
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
        if self._current_render_mode is not RenderMode.MATH:
            apply_scaled_fonts(
                sample,
                self.expression_label,
                int(style["expr_min_pt"]),
                int(style["expr_max_pt"]),
            )

    def refresh_layout(self) -> None:
        """Recalculate item row height for QListWidget after font/mode changes in disgusting way."""

        # TODO: find a better way, delegate and heightForWidth override was worse
        if self.painter.is_painting:
            return

        margin = int(style["item_margin"])
        spacing = int(style["item_spacing"])
        result_h = self.result_label.sizeHint().height()

        if self._current_render_mode is RenderMode.MATH:
            scroll_sh = self._expr_scroll.sizeHint().height()
            inner = self._paint_canvas
            slot_h = inner.sizeHint().height()
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
        if self._current_render_mode in (RenderMode.FLAT, RenderMode.RAW):
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
