from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QFrame,
    QPushButton,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon

from ....theme import get_theme
from .style import apply_history_style
from .config import layout_config
from .utils import wrap_expression
from .config import style
from .storage import load_history, save_history, clear_history_file

class History(QWidget):
    """History panel with persistent storage."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("historyWidget")
        self._history_items: list[str] = []

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(
            layout_config["margin"],
            layout_config["margin"],
            layout_config["margin"],
            layout_config["margin"],
        )
        self.layout.setSpacing(layout_config["spacing"])

        theme = get_theme()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(theme.colors["background_dark"]))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        self.list = QListWidget()
        apply_history_style(self.list)
        self.layout.addWidget(self.list)

        self.divider = QFrame(self)
        self.divider.setFrameShape(QFrame.HLine)
        self.divider.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(self.divider)

        button_container = QHBoxLayout()
        button_container.addStretch(1)
        
        self.clear_button = QPushButton("Clear History", self)
        self.clear_button.setIcon(QIcon.fromTheme("edit-clear-history"))
        self.clear_button.setToolTip("Clears all history permanently from local storage")
        self.clear_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.clear_button.clicked.connect(self.clear_history)
        button_container.addWidget(self.clear_button, 1) 
        
        self.layout.addLayout(button_container)
        
        # Load history from file
        self._load_from_storage()

    def _load_from_storage(self) -> None:
        """Load history from persistent storage."""
        self._history_items = load_history()

        for item in self._history_items:
            self._add_item_to_list(item)

    def _add_item_to_list(self, expression: str) -> None:
        """Add item to list widget with proper formatting."""
        fm = self.list.fontMetrics()
        max_width = self.list.viewport().width() - 3 * style["item_padding"]
        wrapped = wrap_expression(expression, fm, max_width)
        
        self.list.addItem(wrapped)
        last_item = self.list.item(self.list.count() - 1)
        if last_item:
            last_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    def update_history(self, expression: str) -> None:
        """Add expression to history and save to storage."""
        self._history_items.append(expression)
        self._add_item_to_list(expression)
        self.list.scrollToBottom()
        
        # Save to persistent storage
        save_history(self._history_items)

    def clear_history(self) -> None:
        """Clear history from UI and storage."""
        self.list.clear()
        self._history_items.clear()
        clear_history_file()

   