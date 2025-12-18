from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from tcalc.app_state import CalculatorMode
from tcalc.theme import get_theme

from ..utils import apply_scaled_fonts
from .config import font_scale, layout_config, style
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

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(
            layout_config["margin"],
            layout_config["margin"],
            layout_config["margin"],
            layout_config["margin"],
        )
        self.main_layout.setSpacing(layout_config["spacing"])

        theme = get_theme()
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor(theme.colors["background_dark"]))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

        self._memory_bar = QWidget(self)
        memory_layout = QHBoxLayout(self._memory_bar)
        memory_layout.setContentsMargins(0, 0, 0, 0)
        memory_layout.setSpacing(layout_config["spacing"])

        self._memory_label = QLabel("Mem:", self._memory_bar)
        self._memory_value = QLabel("", self._memory_bar)
        self._memory_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        memory_layout.addWidget(self._memory_label, 0)
        memory_layout.addWidget(self._memory_value, 1)

        self._memory_divider = QFrame(self)
        self._memory_divider.setFrameShape(QFrame.Shape.HLine)
        self._memory_divider.setFrameShadow(QFrame.Shadow.Sunken)

        self._memory_bar.setVisible(False)
        self._memory_divider.setVisible(False)

        self.main_layout.addWidget(self._memory_bar)
        self.main_layout.addWidget(self._memory_divider)

        self.list = QListWidget()
        apply_history_style(self.list)
        self.main_layout.addWidget(self.list)

        self.divider = QFrame(self)
        self.divider.setFrameShape(QFrame.Shape.HLine)
        self.divider.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(self.divider)

        button_container = QHBoxLayout()
        button_container.addStretch(int(layout_config["button_spacer_stretch"]))

        self.clear_button = QPushButton("Clear History", self)
        self.clear_button.setIcon(QIcon.fromTheme("edit-clear-history"))
        self.clear_button.setToolTip("Clears all history permanently from local storage")
        self.clear_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.clear_button.clicked.connect(self.clear_history)
        button_container.addWidget(self.clear_button, int(layout_config["clear_button_stretch"]))

        self.main_layout.addLayout(button_container)

        self.reload_from_storage(mode)

        self._update_fonts()
        QTimer.singleShot(0, self._update_fonts)

    def set_memory(self, text: str) -> None:
        if text:
            self._memory_value.setText(text)
            self._memory_bar.setVisible(True)
            self._memory_divider.setVisible(True)
        else:
            self._memory_bar.setVisible(False)
            self._memory_divider.setVisible(False)

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
        list_scale = font_scale["list"]
        clear_scale = font_scale["clear_button"]
        apply_scaled_fonts(
            [
                (
                    self.list.viewport(),
                    (self.list,),
                    style["font_size"],
                    int(list_scale["max_pt"]),
                    int(list_scale["divisor"]),
                ),
                (
                    self,
                    (self._memory_label, self._memory_value),
                    style["font_size"],
                    int(list_scale["max_pt"]),
                    int(list_scale["divisor"]),
                ),
                (
                    self,
                    (self.clear_button,),
                    int(clear_scale["min_pt"]),
                    int(clear_scale["max_pt"]),
                    int(clear_scale["divisor"]),
                ),
            ]
        )

        self.list.clear()
        for item in self._history_items:
            self._add_item_to_list(item)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_fonts()
