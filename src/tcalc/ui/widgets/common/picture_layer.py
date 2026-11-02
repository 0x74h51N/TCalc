#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from functools import cache
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRunnable, QSize, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage, QImageReader, QMoveEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QStyle, QWidget

from tcalc.theme import PictureTarget, ThemePicture, get_theme, qcolor

# A pass this much smaller shows the picture within tens of ms while the full one renders
LOW_RES_DIVISOR = 8


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


def master_size(picture: ThemePicture, screen: QSize) -> QSize:
    """The largest image *picture* can be drawn at on *screen*: its box is at most the screen's."""
    box = QSize(int(screen.width() * picture.size), int(screen.height() * picture.size))
    return _natural_size(picture.file).scaled(box, picture.fit.aspect_mode)


def _render(picture: ThemePicture, size: QSize) -> QImage:
    reader = QImageReader(str(picture.file))
    reader.setScaledSize(size)
    image = reader.read()
    if picture.tint:
        # Keep the picture's shape, take the theme color
        painter = QPainter(image)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(image.rect(), qcolor(get_theme().colors[picture.tint]))
        painter.end()
    return image


MasterKey = tuple[int, int]


class _RenderResult(QObject):
    # Lives in the UI thread, so a pool thread's result reaches the painter through the event loop
    ready = Signal(object, object, QImage)


class _RenderJob(QRunnable):
    def __init__(self, picture: ThemePicture, key: MasterKey, result: _RenderResult) -> None:
        super().__init__()
        self._picture = picture
        self._key = key
        self._result = result

    def run(self) -> None:
        width, height = self._key
        sizes = [QSize(*self._key)]
        # An SVG's cost grows with its pixels, so a small pass shows it sooner; a raster file
        # costs its whole decode at any size, so a small pass would only delay the full one
        if QImageReader(str(self._picture.file)).format() == b"svg":
            sizes.insert(0, QSize(width // LOW_RES_DIVISOR, height // LOW_RES_DIVISOR))
        for size in sizes:
            image = _render(self._picture, size)
            try:
                self._result.ready.emit(self._picture, self._key, image)
            except RuntimeError:
                # The widget closed while its render ran (a removed pad, the app closed at startup)
                return


class PicturePainter:
    """Paints the active theme's pictures for *target* on *widget*, from its paint event."""

    def __init__(self, widget: QWidget, target: PictureTarget) -> None:
        self._widget = widget
        self._target = target
        self._cache: dict[ThemePicture, QImage] = {}
        # Rasterizing on the UI thread froze resizes (issue #102), so masters render in the pool
        self._masters: dict[ThemePicture, tuple[MasterKey, QImage]] = {}
        self._pending: set[tuple[ThemePicture, MasterKey]] = set()
        self._result = _RenderResult(widget)
        self._result.ready.connect(self._on_ready)

    def paint(self) -> None:
        pictures = [p for p in get_theme().pictures if p.target is self._target]
        if not pictures:
            self._cache.clear()
            self._masters.clear()
            self._pending.clear()
            return
        painter = QPainter(self._widget)
        screen = self._widget.screen().size()
        drawn: set[ThemePicture] = set()
        for picture in pictures:
            natural = _natural_size(picture.file)
            if not natural.isValid():
                continue
            box, rect = picture_rects(picture, self._widget.rect(), natural)
            # The reader ignores an empty scaled size and renders the file's own (huge) size
            if rect.isEmpty():
                continue
            drawn.add(picture)
            key = master_size(picture, screen).toTuple()
            master = self._masters.get(picture)
            if (master is None or master[0] != key) and (picture, key) not in self._pending:
                self._pending.add((picture, key))
                QThreadPool.globalInstance().start(_RenderJob(picture, key, self._result))
            if master is None:
                continue
            image = master[1]
            if image.size() == QSize(*master[0]):
                scaled = self._cache.get(picture)
                if scaled is None or scaled.size() != rect.size():
                    scaled = image.scaled(
                        rect.size(),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self._cache[picture] = scaled
                image = scaled
            painter.save()
            painter.setClipRect(box)
            painter.setOpacity(picture.opacity)
            painter.drawImage(rect, image)
            painter.restore()
        # Only the pictures of this paint keep their images and their pending renders
        self._cache = {p: i for p, i in self._cache.items() if p in drawn}
        self._masters = {p: m for p, m in self._masters.items() if p in drawn}
        self._pending = {(p, k) for p, k in self._pending if p in drawn}

    def _on_ready(self, picture: ThemePicture, key: MasterKey, image: QImage) -> None:
        if (picture, key) not in self._pending:
            return
        full = image.size() == QSize(*key)
        current = self._masters.get(picture)
        # A new screen's low pass would blur a picture that is sharp until its full pass arrives
        if not full and current is not None and current[1].size() == QSize(*current[0]):
            return
        self._masters[picture] = (key, image)
        if full:
            self._pending.discard((picture, key))
            self._cache.pop(picture, None)
        self._widget.update()


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
        return False

    def moveEvent(self, event: QMoveEvent) -> None:
        # A scrolling owner (a list's viewport) moves its children; the pictures stay put
        if self.pos() != QPoint(0, 0):
            self.move(0, 0)

    def paintEvent(self, event: QPaintEvent) -> None:
        self._pictures.paint()
