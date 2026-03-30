from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QStyle, QWidget


class FlowLayout(QLayout):
    """Layout that arranges widgets in a horizontal flow, wrapping as needed."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = -1) -> None:
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._h_spacing = spacing
        self._v_spacing = spacing
        self._items: list[QLayoutItem] = []
        if parent is not None:
            parent.installEventFilter(self)

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Show and obj is self.parentWidget():
            self.invalidate()
            self.activate()
        return False

    # -- QLayout interface -------------------------------------------------

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientation:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), apply_geometry=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        h = self._do_layout(rect, apply_geometry=True)
        # Ensure the parent widget has the correct minimum height for wrap
        pw = self.parentWidget()
        if pw is not None:
            pw.setMinimumHeight(h)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    # -- spacing helpers ---------------------------------------------------

    def horizontalSpacing(self) -> int:
        if self._h_spacing >= 0:
            return self._h_spacing
        return self._smart_spacing(QStyle.PixelMetric.PM_LayoutHorizontalSpacing)

    def verticalSpacing(self) -> int:
        if self._v_spacing >= 0:
            return self._v_spacing
        return self._smart_spacing(QStyle.PixelMetric.PM_LayoutVerticalSpacing)

    def _smart_spacing(self, pm: QStyle.PixelMetric) -> int:
        parent = self.parent()
        if parent is None:
            return -1
        if isinstance(parent, QWidget):
            return parent.style().pixelMetric(pm, None, parent)
        if isinstance(parent, QLayout):
            return parent.spacing()
        return -1

    # -- core layout logic -------------------------------------------------

    def _do_layout(self, rect: QRect, *, apply_geometry: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        row_height = 0

        for item in self._items:
            wid = item.widget()
            if wid is not None and not wid.isVisible():
                continue

            h_space = self.horizontalSpacing()
            v_space = self.verticalSpacing()
            next_x = x + item.sizeHint().width() + h_space

            if next_x - h_space > effective.right() and row_height > 0:
                x = effective.x()
                y += row_height + v_space
                next_x = x + item.sizeHint().width() + h_space
                row_height = 0

            if apply_geometry:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = next_x
            row_height = max(row_height, item.sizeHint().height())

        return y + row_height - rect.y() + m.bottom()
