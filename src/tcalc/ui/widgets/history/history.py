#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.app_state import CalculatorMode
from tcalc.ui.config import history_style as style
from tcalc.ui.widgets.common.utils import Align
from tcalc.ui.widgets.utils import apply_scaled_fonts

from ..common import Toaster, ToastLevel
from .storage import clear_history_file, load_history, save_history
from .style import apply_history_style
from .utils import wrap_expression


class History(QWidget):
    """History panel with persistent storage."""

    def __init__(
        self, parent: Optional[QWidget] = None, mode: CalculatorMode = CalculatorMode.SIMPLE
    ):
        super().__init__(parent)
        self.setObjectName("historyWidget")
        self._history_items: list[str] = []
        self._mode = mode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.list = QListWidget()
        apply_history_style(self.list)

        self.list.itemClicked.connect(self._copy_item_to_clipboard)
        layout.addWidget(self.list, 1)

        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(divider)

        button_container = QHBoxLayout()
        button_container.addStretch(int(style["button_spacer_stretch"]))

        self.clear_button = QPushButton("Clear History", self)
        self.clear_button.setIcon(QIcon.fromTheme("edit-clear-history"))
        self.clear_button.setToolTip("Clears all history permanently from local storage")
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clear_button.clicked.connect(self.clear_history)
        button_container.addWidget(self.clear_button, int(style["clear_button_stretch"]))

        layout.addLayout(button_container)

        self._toaster = Toaster(self, horizontal=Align.LEFT)

        self.reload_from_storage(mode)

        QTimer.singleShot(0, self._update_fonts)

    def reload_from_storage(self, mode: CalculatorMode) -> None:
        self._mode = mode
        self._history_items = load_history(mode)
        self.list.clear()
        for item in self._history_items:
            self._add_item_to_list(item)

    def _add_item_to_list(self, expression: str) -> None:
        """Add item to list widget with proper formatting."""
        fm = self.list.fontMetrics()
        max_width = (
            self.list.viewport().width() - int(style["wrap_padding_factor"]) * style["item_padding"]
        )
        wrapped = wrap_expression(expression, fm, max_width)

        self.list.addItem(wrapped)
        last_item = self.list.item(self.list.count() - 1)
        if last_item:
            last_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            last_item.setData(Qt.ItemDataRole.UserRole, expression)

    def _copy_item_to_clipboard(self, item: QListWidgetItem) -> None:
        """Copy the original expression to clipboard when an item is clicked."""
        raw: str = item.data(Qt.ItemDataRole.UserRole)

        expression: str = raw.split("=")[0].replace("\n", "").replace("\r", "").strip()
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(expression)
            self._toaster.show_toast("Copied!", ToastLevel.INFO)

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

    def update_history(self, expression: str) -> None:
        """Add expression to history and save to storage."""
        self._history_items.append(expression)
        self._add_item_to_list(expression)
        self.list.scrollToBottom()

        # Save to persistent storage
        save_history(self._history_items, self._mode)

    def clear_history(self) -> None:
        """Clear history from UI and storage."""
        self.list.clear()
        self._history_items.clear()
        clear_history_file(self._mode)

    def _update_fonts(self) -> None:

        apply_scaled_fonts(
            self.list.viewport(), [self.list], style["font_size"], int(style["max_pt"])
        )

        apply_scaled_fonts(
            self, [self.clear_button], int(style["btn_min_pt"]), int(style["btn_max_pt"])
        )

        self.list.clear()
        for item in self._history_items:
            self._add_item_to_list(item)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fonts()
