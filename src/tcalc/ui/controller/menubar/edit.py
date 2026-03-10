from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from PySide6.QtWidgets import QApplication

from tcalc.app_state import get_app_state

from ..utils import clean_for_expression

if TYPE_CHECKING:
    from ...window import MainWindow


class EditOperations:
    def _do_history_op(self, delta: int, reset_on_end: bool = False) -> None:
        count = len(self._history._history_items)
        if not count:
            return

        current_idx = self.app_state.history_index

        if current_idx in (-1, count):
            if delta >= 0:
                return
            self.app_state.redo_cached_exprs = self._display.expression.get_plain_text()
            next_idx = count - 1
        else:
            next_idx = max(0, min(current_idx + delta, count))

        if next_idx == current_idx:
            return

        self.app_state.history_index = next_idx

        if next_idx >= count:
            self._set_expression(self.app_state.redo_cached_exprs)
            if reset_on_end:
                self.reset_navigation()
            return

        self._history.highlight_item(next_idx)
        expr = self._get_history_expression(next_idx)
        if expr:
            self._set_expression(expr)

    def _do_clip(self, action: str, after: Optional[Callable[[], None]] = None) -> None:
        exprs = self._display.expression.expression_inputs()
        cleaned = clean_for_expression(self._display.result_label.text())
        for expr in exprs:
            if expr.hasSelectedText():
                getattr(expr, action)()
                return
        self.clipboard.setText(cleaned)
        if after:
            after()

    def __init__(self, window: MainWindow):
        self.window = window
        self.clipboard = QApplication.clipboard()
        self.app_state = get_app_state()

    @property
    def _display(self):
        return self.window.calc_widget.display

    @property
    def _history(self):
        return self.window.history

    def _get_history_expression(self, index: int) -> Optional[str]:
        item = self._history.get_history_item(index)
        if not item:
            return None

        return item

    def _set_expression(self, expression: str) -> None:
        self._display.expression.set_plain_text(expression)

    def copy(self) -> None:
        self._do_clip("copy")

    def cut(self) -> None:
        self._do_clip("cut", after=lambda: self._display.update_res(""))

    def paste(self) -> None:
        cleaned = clean_for_expression(self.clipboard.text())
        self._display.expression.set_plain_text(cleaned)

    def undo(self) -> None:
        self._do_history_op(-1)

    def redo(self) -> None:
        self._do_history_op(1, reset_on_end=True)

    def reset_navigation(self) -> None:
        """Reset undo/redo navigation"""
        self.app_state.history_index = -1
        self.app_state.redo_cached_exprs = ""
        self._history.clear_highlight()
