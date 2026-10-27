#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from functools import cache
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QPaintEvent
from PySide6.QtWidgets import QStyle, QWidget

from tcalc.theme import PictureTarget, ThemePicture, get_theme


def picture_rects(picture: ThemePicture, area: QRect, natural: QSize) -> tuple[QRect, QRect]:
    """The box *picture* takes in *area*, and where its image of *natural* size is drawn
    (larger than the box when it covers it)."""
    inner = area.adjusted(picture.margin, picture.margin, -picture.margin, -picture.margin)
    box_size = QSize(int(inner.width() * picture.size), int(inner.height() * picture.size))
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


class PictureLayer(QWidget):
    """Paints the active theme's pictures for *target* behind *parent*'s other children.

    One line in a component adds it; the theme's ``[[pictures]]`` decide what it shows. A
    theme switch re-polishes every widget, which repaints the layer with the new theme.
    """

    def __init__(self, parent: QWidget, target: PictureTarget) -> None:
        super().__init__(parent)
        self._target = target
        self._owner = parent
        self._cache: dict[tuple[ThemePicture, int, int], QImage] = {}
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(parent.rect())
        self.lower()
        parent.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._owner and event.type() == QEvent.Type.Resize:
            self.setGeometry(self._owner.rect())
        return False

    def paintEvent(self, event: QPaintEvent) -> None:
        pictures = [p for p in get_theme().pictures if p.target is self._target]
        if not pictures:
            self._cache.clear()
            return
        painter = QPainter(self)
        images: dict[tuple[ThemePicture, int, int], QImage] = {}
        for picture in pictures:
            natural = _natural_size(picture.file)
            if not natural.isValid():
                continue
            box, rect = picture_rects(picture, self.rect(), natural)
            key = (picture, rect.width(), rect.height())
            images[key] = self._cache.get(key) or _render(picture, rect.size())
            painter.save()
            painter.setClipRect(box)
            painter.setOpacity(picture.opacity)
            painter.drawImage(rect, images[key])
            painter.restore()
        # Only the images in use stay cached
        self._cache = images
