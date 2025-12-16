from __future__ import annotations

from typing import Iterable, Sequence

from PySide6.QtWidgets import QWidget


FontScaleGroup = tuple[QWidget, Iterable[QWidget], int, int, int]


def _min_dim(widget: QWidget) -> int:
    size = widget.size()
    if not size.isValid():
        size = widget.sizeHint()
    return min(size.width(), size.height())


def apply_scaled_fonts(groups: Sequence[FontScaleGroup]) -> None:
    for sample, targets, min_pt, max_pt, divisor in groups:
        dim = _min_dim(sample)
        point_size = min_pt if dim <= 0 else max(min_pt, min(max_pt, dim // divisor))
        for widget in targets:
            font = widget.font()
            font.setPointSize(point_size)
            widget.setFont(font)
