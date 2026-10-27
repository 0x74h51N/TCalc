#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize

from tcalc.theme import PictureFit, PicturePosition, PictureTarget, ThemePicture
from tcalc.ui.widgets.common.picture_layer import picture_rects


def test_config_defaults():
    picture = ThemePicture.from_config(Path("t"), {"file": "a.svg", "target": "display"})
    assert picture == ThemePicture(Path("t/a.svg"), PictureTarget.DISPLAY)


def test_top_right_contain_sits_in_the_corner_inside_the_margin():
    picture = ThemePicture(
        Path("a.svg"), PictureTarget.DISPLAY, PicturePosition.TOP_RIGHT, size=0.5, margin=10
    )
    box, rect = picture_rects(picture, QRect(0, 0, 420, 220), QSize(100, 100))
    assert box == QRect(210, 10, 200, 100)
    assert rect == QRect(310, 10, 100, 100)  # square kept, pushed right


def test_cover_overflows_its_box():
    picture = ThemePicture(Path("a.svg"), PictureTarget.DISPLAY, fit=PictureFit.COVER)
    box, rect = picture_rects(picture, QRect(0, 0, 200, 100), QSize(100, 100))
    assert box == QRect(0, 0, 200, 100) and rect.size() == QSize(200, 200)
