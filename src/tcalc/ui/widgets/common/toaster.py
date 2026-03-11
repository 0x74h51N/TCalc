from __future__ import annotations

from enum import Enum, auto

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QWidget

from tcalc.theme import get_theme

from .utils import Align, reposition, setup_fade, start_fade_out


class ToastLevel(Enum):
    INFO = auto()
    WARN = auto()
    ERROR = auto()


_TOAST_ALPHA = 140


def _bg_for_level(level: ToastLevel) -> str:
    """Return an rgba() background string for the given toast level."""
    theme = get_theme()
    color_map: dict[ToastLevel, str] = {
        ToastLevel.INFO: theme.colors["background_light"],
        ToastLevel.WARN: theme.colors["status_warn"],
        ToastLevel.ERROR: theme.colors["status_error"],
    }
    hex_color = color_map[level]
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {_TOAST_ALPHA})"


class Toaster(QLabel):
    """Lightweight toast notification that overlays on a parent widget."""

    def __init__(
        self,
        parent: QWidget,
        duration_ms: int = 1500,
        fade_ms: int = 400,
        padding: str = "6px 10px",
        border_radius: int = 4,
        font_size: int = 13,
        horizontal: Align = Align.CENTER,
        vertical: Align = Align.BOTTOM,
        x_offset: int = 0,
        y_offset: int = 0,
    ) -> None:
        super().__init__(parent)
        self._duration_ms = duration_ms
        self._padding = padding
        self._border_radius = border_radius
        self._font_size = font_size
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

        theme = get_theme()
        bg = _bg_for_level(level)
        text_color = theme.colors["text_primary"]

        self.setText(message)
        self.setStyleSheet(
            f"background: {bg};"
            f"color: {text_color};"
            f"padding: {self._padding};"
            f"border-radius: {self._border_radius}px;"
            f"font-size: {self._font_size}px;"
        )
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
