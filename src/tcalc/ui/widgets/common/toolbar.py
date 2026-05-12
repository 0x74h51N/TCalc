#
#
#
# TCalc - Copyright (C) 2025 Tahsin Onemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSize,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QIcon, QPixmap, QResizeEvent, QTransform
from PySide6.QtWidgets import QGraphicsOpacityEffect, QSizePolicy, QVBoxLayout, QWidget

from .button import IconButton
from .flow_layout import FlowLayout


class Toolbar(QWidget):
    """Toolbar widget with optional collapse/expand animation via toggle button."""

    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = 0,
        spacing: int = 0,
        collapsible: bool = False,
        toggle_icon: str = "arrow-down-double",
        toggle_tooltip: str = "Toggle toolbar",
        toggle_height: int = 14,
        toggle_anim_duration: int = 300,
    ) -> None:
        super().__init__(parent)

        self._toggle_btn: IconButton | None = None
        self._content: QWidget
        self._opacity: QGraphicsOpacityEffect | None = None
        self._anim_group: QParallelAnimationGroup | None = None
        self._height_anim: QVariantAnimation | None = None
        self._fade_anim: QPropertyAnimation | None = None
        self._rot_anim: QVariantAnimation | None = None
        self._base_pixmap: QPixmap | None = None
        self._current_angle = 0.0
        self._toggle_btn_height = toggle_height
        self._expanded = False

        if collapsible:
            outer = QVBoxLayout(self)
            outer.setContentsMargins(margin, margin, margin, margin)
            outer.setSpacing(0)

            self._content = QWidget(self)
            self._layout = FlowLayout(self._content, margin=margin, spacing=spacing)
            self._content.setGeometry(0, 0, 0, 0)
            self._content.show()
            outer.addStretch()

            icon_size = QSize(toggle_height, toggle_height)
            self._toggle_btn = IconButton(toggle_icon, toggle_tooltip, "", None, self)
            self._toggle_btn.setFixedHeight(toggle_height)
            self._toggle_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._toggle_btn.setIconSize(icon_size)
            self._toggle_btn.setProperty("uiRole", "toolbarToggle")
            self._toggle_btn.clicked.connect(self._toggle_btn_content)
            outer.addWidget(self._toggle_btn)

            self._base_pixmap = self._toggle_btn.icon().pixmap(icon_size)

            self._opacity = QGraphicsOpacityEffect(self._content)
            self._opacity.setOpacity(0.0)
            self._content.setGraphicsEffect(self._opacity)

            self.setFixedHeight(toggle_height)

            easing = QEasingCurve(QEasingCurve.Type.InOutCubic)

            self._height_anim = QVariantAnimation(self)
            self._height_anim.setDuration(toggle_anim_duration)
            self._height_anim.setEasingCurve(easing)
            self._height_anim.valueChanged.connect(self._apply_height)

            self._fade_anim = QPropertyAnimation(self._opacity, b"opacity", self)
            self._fade_anim.setDuration(toggle_anim_duration)
            self._fade_anim.setEasingCurve(easing)

            self._rot_anim = QVariantAnimation(self)
            self._rot_anim.setDuration(toggle_anim_duration)
            self._rot_anim.setEasingCurve(easing)
            self._rot_anim.valueChanged.connect(self._apply_toggle_btn_rotation)

            self._anim_group = QParallelAnimationGroup(self)
            self._anim_group.addAnimation(self._height_anim)
            self._anim_group.addAnimation(self._fade_anim)
            self._anim_group.addAnimation(self._rot_anim)

        else:
            sp = self.sizePolicy()
            sp.setHeightForWidth(True)
            self.setSizePolicy(sp)
            self._content = self
            self._layout = FlowLayout(self, margin=margin, spacing=spacing)

    def _apply_height(self, value: int) -> None:
        self.setFixedHeight(value)
        if self._content is not self:
            self._content.setGeometry(0, 0, self.width(), max(0, value - self._toggle_btn_height))

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._content is self:
            return
        self._content.setGeometry(0, 0, self.width(), self._content.height())
        if not self._expanded:
            return
        if (
            self._height_anim is not None
            and self._height_anim.state() == QAbstractAnimation.State.Running
        ):
            return
        if event.size().width() == event.oldSize().width():
            return
        new_h = self._expanded_height()
        if new_h != self.height():
            self.setFixedHeight(new_h)
            self._content.setGeometry(0, 0, self.width(), new_h - self._toggle_btn_height)

    def _apply_toggle_btn_rotation(self, value: float) -> None:
        if self._toggle_btn is None or self._base_pixmap is None:
            return
        self._current_angle = value
        rotated = self._base_pixmap.transformed(
            QTransform().rotate(value),
            Qt.TransformationMode.SmoothTransformation,
        )
        self._toggle_btn.setIcon(QIcon(rotated))

    def _expanded_height(self) -> int:
        lay = self._content.layout()
        w = self.width()
        if lay is not None and lay.hasHeightForWidth() and w > 0:
            content_h = max(0, lay.heightForWidth(w))
        else:
            content_h = self._content.sizeHint().height()
        return self._toggle_btn_height + content_h

    def _toggle_btn_content(self) -> None:
        if (
            self._content is self
            or self._anim_group is None
            or self._height_anim is None
            or self._fade_anim is None
            or self._rot_anim is None
            or self._opacity is None
        ):
            return

        expanding = not self._expanded
        self._expanded = expanding
        self._anim_group.stop()

        current = self.height()
        if expanding:
            target = self._expanded_height()
            self._height_anim.setStartValue(current)
            self._height_anim.setEndValue(target)
            self._fade_anim.setStartValue(self._opacity.opacity())
            self._fade_anim.setEndValue(1.0)
        else:
            self._height_anim.setStartValue(current)
            self._height_anim.setEndValue(self._toggle_btn_height)
            self._fade_anim.setStartValue(self._opacity.opacity())
            self._fade_anim.setEndValue(0.0)

        self._rot_anim.setStartValue(self._current_angle)
        self._rot_anim.setEndValue(180.0 if expanding else 0.0)

        self._anim_group.start()

    @property
    def is_expanded(self) -> bool:
        return self._content is self or self._expanded

    def set_expanded(self, expanded: bool) -> None:
        if self._content is self or self._expanded == expanded:
            return
        self._toggle_btn_content()

    def addWidget(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)
