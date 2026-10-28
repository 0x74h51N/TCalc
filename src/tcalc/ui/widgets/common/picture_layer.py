#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from functools import cache
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QImageReader, QMoveEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QStyle, QWidget

from tcalc.theme import PictureTarget, ThemePicture, get_theme

# Pause in resizing after which pictures are rendered again at the new size
SETTLE_MS = 150


def picture_rects(picture: ThemePicture, area: QRect, natural: QSize) -> tuple[QRect, QRect]:
    """The box *picture* takes in *area*, and where its image of *natural* size is drawn
    (larger than the box when it covers it)."""
    inner = area.adjusted(picture.margin, picture.margin, -picture.margin, -picture.margin)
    # A component smaller than its margins gets an empty box, never a negative one
    box_size = QSize(
        max(0, int(inner.width() * picture.size)), max(0, int(inner.height() * picture.size))
    )
    align = picture.position.alignment
    box = QStyle.alignedRect(Qt.LayoutDirection.LeftToRight, align, box_size, inner)
    image_size = natural.scaled(box_size, picture.fit.aspect_mode)
    return box, QStyle.alignedRect(Qt.LayoutDirection.LeftToRight, align, image_size, box)


@cache
def _natural_size(file: Path) -> QSize:
    """The picture file's own size (invalid when it is missing or unreadable)."""
    return QImageReader(str(file)).size()


def _render(picture: ThemePicture, size: QSize) -> QImage:
    reader = QImageReader(str(picture.file))
    reader.setScaledSize(size)
    image = reader.read()
    if picture.tint:
        # Keep the picture's shape, take the theme color
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), QColor(get_theme().colors[picture.tint]))
        painter.end()
    return image


class PicturePainter:
    """Paints the active theme's pictures for *target* on *widget*, from its paint event."""

    def __init__(self, widget: QWidget, target: PictureTarget) -> None:
        self._widget = widget
        self._target = target
        self._cache: dict[ThemePicture, QImage] = {}
        # Rendering an SVG is slow; while resizing, the last image is stretched instead
        self._settle = QTimer(widget)
        self._settle.setSingleShot(True)
        self._settle.setInterval(SETTLE_MS)
        self._settle.timeout.connect(widget.update)

    def resized(self) -> None:
        self._settle.start()

    def paint(self) -> None:
        pictures = [p for p in get_theme().pictures if p.target is self._target]
        if not pictures:
            self._cache.clear()
            return
        painter = QPainter(self._widget)
        images: dict[ThemePicture, QImage] = {}
        for picture in pictures:
            natural = _natural_size(picture.file)
            if not natural.isValid():
                continue
            box, rect = picture_rects(picture, self._widget.rect(), natural)
            # The reader ignores an empty scaled size and renders the file's own (huge) size
            if rect.isEmpty():
                continue
            image = self._cache.get(picture)
            if image is None or (image.size() != rect.size() and not self._settle.isActive()):
                image = _render(picture, rect.size())
            images[picture] = image
            painter.save()
            painter.setClipRect(box)
            painter.setOpacity(picture.opacity)
            painter.drawImage(rect, image)
            painter.restore()
        # Only the images in use stay cached
        self._cache = images


class PictureLayer(QWidget):
    """Paints the active theme's pictures for *target* behind *parent*'s other children.

    One line in a component adds it; the theme's ``[[pictures]]`` decide what it shows. A
    theme switch re-polishes every widget, which repaints the layer with the new theme.
    Not for a QMainWindow: its dock layout lowers docks below the layer.
    """

    def __init__(self, parent: QWidget, target: PictureTarget) -> None:
        super().__init__(parent)
        self._owner = parent
        self._pictures = PicturePainter(self, target)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(parent.rect())
        self.lower()
        parent.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._owner and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._owner.rect())
            self._pictures.resized()
        return False

    def moveEvent(self, event: QMoveEvent) -> None:
        # A scrolling owner (a list's viewport) moves its children; the pictures stay put
        if self.pos() != QPoint(0, 0):
            self.move(0, 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._pictures.paint()
