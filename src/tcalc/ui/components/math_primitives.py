from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QSizePolicy, QWidget


class MathPrimitive(QWidget):
    def __init__(self, parent=None):

        super().__init__(parent)
        self._color = Qt.GlobalColor.white
        self._pen_width = 2.0

    def setColor(self, color):
        self._color = color
        self.update()

    def setPenWidth(self, width: float):
        self._pen_width = width
        self.update()

    def build_path(self, w: float, h: float) -> QPainterPath:
        """Subclasses must implement this."""
        raise NotImplementedError

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._color)
        pen.setWidthF(self._pen_width)
        painter.setPen(pen)

        w = float(self.width())
        h = float(self.height())

        path = self.build_path(w, h)
        painter.drawPath(path)


class SqrtSymbol(MathPrimitive):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(25)
        self._pen_width = 2.0

    def build_path(self, w: float, h: float) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(0, h * 0.35)
        path.lineTo(w * 0.25, h * 0.35)
        path.lineTo(w * 0.45, h)
        path.lineTo(w, 0)
        return path


class CurlyBrace(MathPrimitive):
    WIDTH = 12
    WRAP_PADDING = 4

    def __init__(self, parent: QWidget, opening: bool) -> None:
        super().__init__(parent)
        self._opening = opening
        self._pen_width = 1.5
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def build_path(self, w: float, h: float) -> QPainterPath:
        inner_h = h + self.WRAP_PADDING
        mid_y = inner_h / 2
        r = min(w * 0.8, h * 0.15)

        path = QPainterPath()
        path.moveTo(w, 0)
        path.quadTo(w * 0.3, 0, w * 0.3, r)
        path.lineTo(w * 0.3, mid_y - r)
        path.quadTo(w * 0.3, mid_y, 0, mid_y)
        path.quadTo(w * 0.3, mid_y, w * 0.3, mid_y + r)
        path.lineTo(w * 0.3, h - r)
        path.quadTo(w * 0.3, h, w, h)

        if not self._opening:
            mirror = QTransform(-1, 0, 0, 1, w, 0)
            path = mirror.map(path)

        return path
