from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

from ...app_state import get_app_state
from .utils import clean_for_expression

if TYPE_CHECKING:
    from ..window import MainWindow


class EditOperations:
    def __init__(self, window: MainWindow):
        self.window = window
        self.clipboard = QApplication.clipboard()
        self.app_state = get_app_state()

    def copy(self) -> None:
        if not hasattr(self.window, 'calc_widget'):
            return
        
        display = self.window.calc_widget.display
        result_text = display.result_label.text()

        cleaned_text = clean_for_expression(result_text) # clean the comas
        self.clipboard.setText(cleaned_text)

    def cut(self) -> None:
        if not hasattr(self.window, 'calc_widget'):
            return
        
        display = self.window.calc_widget.display
        result_text = display.result_label.text()

        cleaned_text = clean_for_expression(result_text) # clean the comas
        self.clipboard.setText(cleaned_text)
        display.update_res("")

    def paste(self) -> None:
        if not hasattr(self.window, 'calc_widget'):
            return
        
        display = self.window.calc_widget.display
        expression_input = display.expression_label
        
        clipboard_text = self.clipboard.text()

        cleaned_text = clean_for_expression(clipboard_text) # clean the comas again
        
        expression_input.insert(cleaned_text)
        
        expression_input.setFocus()

    def undo(self) -> None:
        #Navigate backwards in history and restore expression
        if not hasattr(self.window, 'calc_widget') or not hasattr(self.window, 'history'):
            return
        
        display = self.window.calc_widget.display
        history_list = self.window.history.list
        history_count = history_list.count()
        
        if history_count == 0:
            return
        
        if self.app_state.history_index == -1:
            self.app_state.redo_memory = display.expression_label.text()
            self.app_state.history_index = history_count - 1
        else:
            self.app_state.history_index -= 1
            if self.app_state.history_index < 0:
                self.app_state.history_index = 0
                return
        
        # Get history item adn extract expression
        history_item = history_list.item(self.app_state.history_index)
        if history_item:
            full_text = history_item.text()
            expression = full_text.split("=")[0].strip()
            display.update_expr(expression)
            display.expression_label.setFocus()

    def redo(self) -> None:
        if not hasattr(self.window, 'calc_widget') or not hasattr(self.window, 'history'):
            return
        
        display = self.window.calc_widget.display
        history_list = self.window.history.list
        history_count = history_list.count()
        
        if self.app_state.history_index == -1:
            return
        
        self.app_state.history_index += 1
        
        # No history then restore saved expression
        if self.app_state.history_index >= history_count:
            display.update_expr(self.app_state.redo_memory)
            self.app_state.history_index = -1
            self.app_state.redo_memory = ""
        else:
            # Get history item and extract expression
            history_item = history_list.item(self.app_state.history_index)
            if history_item:
                full_text = history_item.text()
                expression = full_text.split("=")[0].strip()
                display.update_expr(expression)
        
        display.expression_label.setFocus()
    
    def reset_navigation(self) -> None:
        self.app_state.history_index = -1
        self.app_state.redo_memory = ""
