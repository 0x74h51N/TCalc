from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QWidget

from .utils import Align, reposition, setup_fade, start_fade_out


class ToastLevel(Enum):
    INFO = auto()
    WARN = auto()
    ERROR = auto()


class Toaster(QLabel):
    """Lightweight toast notification that overlays on a parent widget."""

    def __init__(
        self,
        parent: QWidget,
        duration_ms: int = 1500,
        fade_ms: int = 400,
        horizontal: Align = Align.CENTER,
        vertical: Align = Align.BOTTOM,
        x_offset: int = 0,
        y_offset: int = 0,
    ) -> None:
        super().__init__(parent)
        self._duration_ms = duration_ms
        self._horizontal = horizontal
        self._vertical = vertical
        self._x_offset = x_offset
        self._y_offset = y_offset

        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(False)
        self.hide()

        self._opacity_effect, self._fade_anim = setup_fade(self, fade_ms)
        self._fade_anim.finished.connect(self._on_fade_done)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade)

    def show_toast(self, message: str, level: ToastLevel = ToastLevel.INFO) -> None:
        """Display a toast with the given message and level."""
        self._hide_timer.stop()
        self._fade_anim.stop()

        self.setText(message)
        # toaster.qss styles each level through this property
        self.setProperty("toastLevel", level.name.lower())
        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()
        reposition(self, self._horizontal, self._vertical)
        if self._x_offset or self._y_offset:
            self.move(self.x() + self._x_offset, self.y() + self._y_offset)
        self._opacity_effect.setOpacity(1.0)
        self.show()
        self.raise_()
        self._hide_timer.start(self._duration_ms)

    def _start_fade(self) -> None:
        start_fade_out(self._fade_anim)

    def _on_fade_done(self) -> None:
        self.hide()
        self._opacity_effect.setOpacity(1.0)
