from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ....theme import get_theme
from .style import apply_history_style
from .config import layout_config
from .utils import wrap_expression
from .config import style

class History(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("historyWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            layout_config["margin"],
            layout_config["margin"],
            layout_config["margin"],
            layout_config["margin"],
        )
        layout.setSpacing(layout_config["spacing"])

        theme = get_theme()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(theme.colors["background_dark"]))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        self.list = QListWidget()
        apply_history_style(self.list)
        layout.addWidget(self.list)



    def update_history(self, expression: str) -> None:
        fm = self.list.fontMetrics()

        max_width = self.list.viewport().width() - 3 * style["item_padding"]

        wrapped = wrap_expression(expression, fm, max_width)

        self.list.addItem(wrapped)
        last_item = self.list.item(self.list.count() - 1)
        if last_item:
            last_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.list.scrollToBottom()

    
    def clear_history(self) -> None:
        self.list.clear()

   