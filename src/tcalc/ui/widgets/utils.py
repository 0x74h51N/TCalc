from __future__ import annotations

from enum import Enum
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
)

from tcalc.theme import get_theme

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


def _fitted_key_radius(keys: Iterable[QWidget]) -> int | None:
    """Theme key radius, capped at half the shortest key side: Qt squares a larger one."""
    sides = [min(key.width(), key.height()) for key in keys if not key.isHidden()]
    if not sides:  # a custom grid with no keys yet
        return None
    return min(int(get_theme().spacing["radius_small"]), min(sides) // 2)


def _set_key_radius(container: QWidget, radius: int) -> None:
    container.setProperty("keyRadius", radius)
    container.setStyleSheet(f"QPushButton[keypadRole] {{ border-radius: {radius}px; }}")


def apply_key_radius(container: QWidget, keys: Iterable[QWidget]) -> None:
    radius = _fitted_key_radius(keys)
    if radius is not None and radius != container.property("keyRadius"):
        _set_key_radius(container, radius)


def shrink_key_radius(container: QWidget, keys: Iterable[QWidget]) -> None:
    """Refits at once only a radius the keys shrank below, which Qt squares until the next fit."""
    radius = _fitted_key_radius(keys)
    applied = container.property("keyRadius")
    if radius is not None and applied is not None and radius < applied:  # None before launch fit
        _set_key_radius(container, radius)


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
