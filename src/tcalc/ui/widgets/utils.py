from __future__ import annotations

from typing import Iterable

from PySide6.QtWidgets import QWidget

# Widget size range for font interpolation
MIN_DIM = 100
MAX_DIM = 500


def apply_scaled_fonts(
    sample: QWidget,
    targets: Iterable[QWidget],
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

    for widget in targets:
        font = widget.font()
        font.setPointSize(point_size)
        widget.setFont(font)
