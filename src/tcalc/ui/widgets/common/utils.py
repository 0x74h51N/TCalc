from __future__ import annotations

from enum import Enum, auto
from typing import Callable

from PySide6.QtCore import QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class Align(Enum):
    LEFT = auto()
    CENTER = auto()
    RIGHT = auto()
    TOP = auto()
    BOTTOM = auto()


_H_ALGN: dict[Align, Callable[[int, int, int], int]] = {
    Align.LEFT: lambda pw, ww, m: m,
    Align.CENTER: lambda pw, ww, m: (pw - ww) // 2,
    Align.RIGHT: lambda pw, ww, m: pw - ww - m,
}

_V_ALGN: dict[Align, Callable[[int, int, int], int]] = {
    Align.TOP: lambda ph, wh, m: m,
    Align.CENTER: lambda ph, wh, m: (ph - wh) // 2,
    Align.BOTTOM: lambda ph, wh, m: ph - wh - m,
}


def reposition(
    widget: QWidget,
    horizontal: Align = Align.CENTER,
    vertical: Align = Align.CENTER,
    margin: int = 6,
) -> None:
    """Position a widget relative to its parent based on alignment."""
    p = widget.parent()
    if not isinstance(p, QWidget):
        return

    x = _H_ALGN[horizontal](p.width(), widget.width(), margin)
    y = _V_ALGN[vertical](p.height(), widget.height(), margin)
    widget.move(x, y)


def setup_fade(
    target: QWidget, duration_ms: int = 400
) -> tuple[QGraphicsOpacityEffect, QPropertyAnimation]:
    """Attach an opacity effect and fade animation to a widget."""
    effect = QGraphicsOpacityEffect(target)
    effect.setOpacity(1.0)
    target.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity", target)
    anim.setDuration(duration_ms)
    return effect, anim


def start_fade_out(anim: QPropertyAnimation) -> None:
    """Trigger a 1.0 -> 0.0 fade-out on an already-configured animation."""
    anim.stop()
    anim.setStartValue(1.0)
    anim.setEndValue(0.0)
    anim.start()


def rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#RRGGBB`` + alpha to a CSS ``rgba(...)`` string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
