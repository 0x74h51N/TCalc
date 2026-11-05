from __future__ import annotations

from enum import Enum
from typing import Callable, Iterable

from PySide6.QtCore import QChildEvent, QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
)

from tcalc.theme import get_theme
from tcalc.ui.props import Prop

from ..config import CONFIG

# Widget size range for font interpolation
MIN_DIM = 100
MAX_DIM = 500


def apply_scaled_fonts(
    sample: QWidget,
    targets: Iterable[QWidget] | QWidget,
    min_pt: int,
    max_pt: int,
) -> None:
    """Scale font size of targets between min_pt and max_pt based on sample widget size."""
    # A theme that sets only min_pt can land above the default max_pt: that size, not a shrink
    max_pt = max(min_pt, max_pt)
    size = sample.size()
    if not size.isValid():
        size = sample.sizeHint()
    dim = min(size.width(), size.height())

    if dim <= MIN_DIM:
        point_size = min_pt
    elif dim >= MAX_DIM:
        point_size = max_pt
    else:
        # Linear interpolation between min and max
        ratio = (dim - MIN_DIM) / (MAX_DIM - MIN_DIM)
        point_size = int(min_pt + ratio * (max_pt - min_pt))

    if isinstance(targets, Iterable):
        for widget in targets:
            font = widget.font()
            font.setPointSize(point_size)
            widget.setFont(font)
    else:
        font = targets.font()
        font.setPointSize(point_size)
        targets.setFont(font)


def round_tooltip(event: QChildEvent) -> None:
    """Qt rounds only the tooltip's border; its window corners stay filled unless see-through."""
    # Called from each class that has a tooltip, not from an application eventFilter: a pad can
    # hold hundreds of keys, and a filter would run in Python for every event of every widget
    child = event.child()
    if (
        event.type() == QEvent.Type.ChildPolished
        and isinstance(child, QWidget)
        and child.windowType() == Qt.WindowType.ToolTip
    ):
        child.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


def set_raised(container: QWidget, raised: bool) -> None:
    """Turns on the edge rules under *container*; a property on an ancestor needs a re-polish."""
    if bool(container.property(Prop.RAISED)) == raised:
        return
    container.setProperty(Prop.RAISED, raised)
    for widget in (container, *container.findChildren(QWidget)):
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def shortest_side(widgets: Iterable[QWidget]) -> int | None:
    sides = [min(w.width(), w.height()) for w in widgets if not w.isHidden()]
    return min(sides) if sides else None  # None: a custom grid with no keys yet


def fit_radius(
    container: QWidget, selector: str, radius: int, side: int, applied: int | None
) -> int:
    """The radius set on *selector*, capped at half *side* since Qt squares a larger one."""
    fitted = min(radius, side // 2)
    if fitted != applied:
        container.setStyleSheet(f"{selector} {{ border-radius: {fitted}px; }}")
    return fitted


KEY_SELECTOR = f"QPushButton[{Prop.KEYPAD_ROLE}]"


def apply_key_radius(
    container: QWidget, keys: Iterable[QWidget], applied: int | None
) -> int | None:
    """The radius the keys have after fitting it; *applied* is the one they had."""
    side = shortest_side(keys)
    if side is None:
        return applied
    return fit_radius(container, KEY_SELECTOR, get_theme().look.keypad.button.radius, side, applied)


def key_fit_timer(container: QWidget, fit: Callable[[], None]) -> QTimer:
    """Keys reach their size after the layout runs, and a drag resizes many times."""
    timer = QTimer(container)
    timer.setSingleShot(True)
    timer.setInterval(CONFIG.keypad.resize_debounce_ms)
    timer.timeout.connect(fit)
    return timer


def shrink_key_radius(
    container: QWidget, keys: Iterable[QWidget], applied: int | None
) -> int | None:
    """Refits at once only a radius the keys shrank below, which Qt squares until the next fit."""
    side = shortest_side(keys)
    radius = get_theme().look.keypad.button.radius
    if (
        side is None or applied is None or min(radius, side // 2) >= applied
    ):  # None before launch fit
        return applied
    return fit_radius(container, KEY_SELECTOR, radius, side, applied)


class InputAlign(Enum):
    """Predefined alignment flags for expression inputs (text alignment)."""

    LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    CENTER = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
    RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    RIGHTB = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
    LEFTB = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
    RIGHTT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop
    LEFTT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
    BOTTOM = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom
    TOP = Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop
