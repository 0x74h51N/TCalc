#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QBrush, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QLineEdit, QListView, QVBoxLayout, QWidget

_MISSING = object()  # sentinel for "no data at this row"


class SearchablePicker(QWidget):
    """Frameless popup with a search field and a filterable item list."""

    item_selected = Signal(object)  # emits the *user_data* of the chosen item

    def __init__(
        self,
        items: list[tuple[Any, ...]],  # (text, data) or (text, data, swatch QColor)
        separator_after: int | None = None,
        min_width: int = 200,
        margin: int = 4,
        spacing: int = 2,
        list_height: int = 240,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setMinimumWidth(min_width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search...")
        self._search.setClearButtonEnabled(True)
        layout.addWidget(self._search)

        self._model = QStandardItemModel(self)
        self._data_by_row: dict[int, Any] = {}
        row = 0
        for i, (text, data, *swatch) in enumerate(items):
            item = QStandardItem(text)
            item.setEditable(False)
            if swatch:
                item.setBackground(QBrush(swatch[0]))
            self._model.appendRow(item)
            self._data_by_row[row] = data
            row += 1

            if separator_after is not None and i == separator_after:
                sep = QStandardItem()
                sep.setEnabled(False)
                sep.setSelectable(False)
                sep.setEditable(False)
                sep.setSizeHint(item.sizeHint())
                self._model.appendRow(sep)
                self._data_by_row[row] = _MISSING
                row += 1

        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self._list = QListView()
        self._list.setModel(self._proxy)
        self._list.setSelectionMode(QListView.SelectionMode.NoSelection)
        self._list.setFixedHeight(list_height)
        layout.addWidget(self._list)

        self._search.textChanged.connect(self._proxy.setFilterFixedString)
        self._list.clicked.connect(self._on_clicked)

    def _on_clicked(self, index) -> None:
        source_row = self._proxy.mapToSource(index).row()
        data = self._data_by_row.get(source_row, _MISSING)
        if data is not _MISSING:
            self.item_selected.emit(data)
            self.hide()

    def popup(self, global_pos) -> None:
        self._search.clear()
        self._list.scrollToTop()
        self.move(global_pos)
        self.show()
        self._search.setFocus()
