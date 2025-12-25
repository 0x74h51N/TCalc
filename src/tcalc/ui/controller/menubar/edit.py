from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from PySide6.QtWidgets import QApplication

from tcalc.app_state import get_app_state

from ..utils import clean_for_expression

if TYPE_CHECKING:
    from ...window import MainWindow


class EditOperations:
    def __init__(self, window: MainWindow):
        self.window = window
        self.clipboard = QApplication.clipboard()
        self.app_state = get_app_state()

    @property
    def _display(self):
        return self.window.calc_widget.display

    @property
    def _history_list(self):
        return self.window.history.list

    def _get_history_expression(self, index: int) -> Optional[str]:
        item = self._history_list.item(index)
        return item.text().split("=")[0].strip() if item else None

    def _set_expression(self, expression: str) -> None:
        self._display.update_expr(expression)

    def copy(self) -> None:
        expr = self._display.expression_label

        if expr.hasFocus() and expr.hasSelectedText():
            expr.copy()
            return
        cleaned = clean_for_expression(self._display.result_label.text())
        self.clipboard.setText(cleaned)

    def cut(self) -> None:
        expr = self._display.expression_label

        if expr.hasFocus() and expr.hasSelectedText():
            expr.cut()
            return
        self.copy()
        self._display.update_res("")

    def paste(self) -> None:
        cleaned = clean_for_expression(self.clipboard.text())
        self._display.expression_label.insert(cleaned)
        self._display.expression_label.setFocus()

    def undo(self) -> None:
        history_count = self._history_list.count()
        if history_count == 0:
            return

        if self.app_state.history_index == -1:
            self.app_state.redo_cached_exprs = self._display.expression_label.text()
            self.app_state.history_index = history_count - 1
        else:
            self.app_state.history_index -= 1
            if self.app_state.history_index < 0:
                self.app_state.history_index = 0
                return

        expression = self._get_history_expression(self.app_state.history_index)
        if expression:
            self._set_expression(expression)

    def redo(self) -> None:
        if self.app_state.history_index == -1:
            return

        self.app_state.history_index += 1

        if self.app_state.history_index >= self._history_list.count():
            self._set_expression(self.app_state.redo_cached_exprs)
            self.reset_navigation()
        else:
            expression = self._get_history_expression(self.app_state.history_index)
            if expression:
                self._set_expression(expression)

    def reset_navigation(self) -> None:
        """Reset undo/redo navigation"""
        self.app_state.history_index = -1
        self.app_state.redo_cached_exprs = ""
