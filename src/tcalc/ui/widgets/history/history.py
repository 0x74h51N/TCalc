#
#
#
# TCalc - Copyright (C) 2025 Tahsin Onemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from typing import Optional, cast

import calc_native
from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from tcalc.app_state import CalculatorMode
from tcalc.ui.config import history_style as style
from tcalc.ui.widgets.common.utils import Align
from tcalc.ui.widgets.utils import InputAlign

from ..common import IconButton, Toaster, ToastLevel
from .storage import HistoryEntry, clear_history_file, load_history, save_history
from .style import apply_history_style
from .utils import wrap_expression


class History(QWidget):
    """History panel with persistent storage."""

    items_changed = Signal()

    def __init__(
        self, parent: Optional[QWidget] = None, mode: CalculatorMode = CalculatorMode.SIMPLE
    ):
        super().__init__(parent)
        self.setObjectName("historyWidget")
        self._history_items: list[HistoryEntry] = []
        self._expr_labels: list[QLabel] = []
        self._result_labels: list[QLabel] = []
        self._is_rendering = False
        self._mode = mode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.list = QListWidget()
        self.list.setItemDelegate(HistoryItemDelegate(self.list))
        apply_history_style(self.list)

        self.list.currentItemChanged.connect(self._on_current_changed)
        layout.addWidget(self.list, 1)

        button_container = QHBoxLayout()
        button_container.addStretch(int(style["button_spacer_stretch"]))

        self.clear_button = IconButton(
            "edit-clear-history",
            tooltip="Clears all history permanently from local storage",
            text="Clear History",
            parent=self,
        )
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clear_button.clicked.connect(self.clear_history)
        button_container.addWidget(self.clear_button, int(style["clear_button_stretch"]))

        layout.addLayout(button_container)

        self._toaster = Toaster(self, horizontal=Align.LEFT)

        self.reload_from_storage(mode)

    def reload_from_storage(self, mode: CalculatorMode) -> None:
        self._mode = mode
        self._history_items = load_history(mode)
        self.list.clear()
        self._expr_labels.clear()
        self._result_labels.clear()
        for entry in self._history_items:
            self._add_item_to_list(entry)
        self.items_changed.emit()

    def _format_display(self, tokens: list[calc_native.Token]) -> str:
        """Build flat display text from a history entry."""
        flat = calc_native.tokens_to_flat_text(tokens)

        fm = self.list.fontMetrics()
        max_width = (
            self.list.viewport().width() - int(style["wrap_padding_factor"]) * style["item_padding"]
        )

        return wrap_expression(flat, fm, max_width)

    def _add_item_to_list(self, entry: HistoryEntry) -> None:
        """Add item to list widget with proper formatting."""
        flat_exprs = self._format_display(entry.tokens)
        item_widget = HistoryItemWidget(flat_exprs, entry.result, parent=self)

        self._expr_labels.append(item_widget.expression_label)
        self._result_labels.append(item_widget.result_label)

        item = QListWidgetItem(self.list)
        item.setData(Qt.ItemDataRole.UserRole, entry.expression)

        item_widget.copy_clicked.connect(lambda i=item: self._copy_item(i))
        item_widget.remove_clicked.connect(lambda i=item: self._remove_item(i))

        min_height = int(style["item_min_height"])
        item.setSizeHint(QSize(0, min_height))
        self.list.addItem(item)
        self.list.setItemWidget(item, item_widget)

        if not self._is_rendering:
            self.items_changed.emit()

    def _on_current_changed(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        if previous is not None:
            prev_widget = self.list.itemWidget(previous)
            if isinstance(prev_widget, HistoryItemWidget):
                prev_widget.hide_actions()
        if current is not None:
            cur_widget = self.list.itemWidget(current)
            if isinstance(cur_widget, HistoryItemWidget):
                cur_widget.show_actions()

    def _copy_item(self, item: QListWidgetItem) -> None:
        """Copy the raw expression to clipboard."""
        expression: str = item.data(Qt.ItemDataRole.UserRole)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(expression)
            self._toaster.show_toast("Copied!", ToastLevel.INFO)

    def _remove_item(self, item: QListWidgetItem) -> None:
        """Remove a single history item."""
        row = self.list.row(item)
        if row < 0:
            return

        self.list.takeItem(row)
        self._history_items.pop(row)
        self._expr_labels.pop(row)
        self._result_labels.pop(row)

        save_history(self._history_items, self._mode)
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

    def update_history(
        self,
        expression: str,
        result: str,
        tokens: list[calc_native.Token],
    ) -> None:
        """Add a new entry to history and persist to storage."""
        entry = HistoryEntry(expression, result, tokens)
        self._history_items.append(entry)
        self._add_item_to_list(entry)
        self.list.scrollToBottom()

        save_history(self._history_items, self._mode)

    def get_history_item(self, index: int) -> str:
        return self._history_items[index].expression

    def clear_history(self) -> None:
        """Clear history from UI and storage."""
        self.list.clear()
        self._history_items.clear()
        self._expr_labels.clear()
        self._result_labels.clear()
        clear_history_file(self._mode)

    def _re_render_items(self) -> None:
        """Re-render all history items with current font metrics."""
        model = self.list.model()
        if model is not None:
            model.blockSignals(True)

        self._is_rendering = True
        self.list.clear()
        self._expr_labels.clear()
        self._result_labels.clear()
        for entry in self._history_items:
            self._add_item_to_list(entry)
        self._is_rendering = False

        if model is not None:
            model.blockSignals(False)

    def get_expression_labels(self) -> list[QLabel]:
        return self._expr_labels

    def get_result_labels(self) -> list[QLabel]:
        return self._result_labels


class HistoryItemWidget(QWidget):
    """Single history entry widget with copy/remove action buttons."""

    copy_clicked = Signal()
    remove_clicked = Signal()

    def __init__(
        self,
        expression_text: str,
        result_text: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("historyItem")
        self.setMinimumHeight(int(style["item_min_height"]))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        layout = QVBoxLayout(self)
        margin = int(style["item_margin"])
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(int(style["item_spacing"]))

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

        # Expression label
        self.expression_label = QLabel(expression_text, self)
        self.expression_label.setAlignment(InputAlign.RIGHT.value)
        self.expression_label.setWordWrap(True)
        expr_font = self.expression_label.font()
        expr_font.setBold(True)
        self.expression_label.setFont(expr_font)

        # Result label
        self.result_label = QLabel(result_text, self)
        self.result_label.setAlignment(InputAlign.RIGHT.value)

        layout.addStretch()
        layout.addWidget(self.expression_label)
        layout.addWidget(self.result_label)
        layout.addStretch()

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)  # type: ignore[arg-type]
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


class HistoryItemDelegate(QStyledItemDelegate):
    """Item delegate that sizes rows to the item-widget's actual sizeHint."""

    def sizeHint(
        self,
        option: QStyleOptionViewItem,
        index: QModelIndex | QPersistentModelIndex,
    ) -> QSize:
        lw = cast(QListWidget, option.widget)
        widget = cast(Optional[QWidget], lw.itemWidget(lw.item(index.row())))

        if widget is None:
            return super().sizeHint(option, index)

        margin = int(style["item_margin"])
        wh = widget.sizeHint().height() + margin
        return QSize(lw.viewport().width(), max(wh, super().sizeHint(option, index).height()))
