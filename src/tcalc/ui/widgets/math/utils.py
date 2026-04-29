#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

import calc_native
from PySide6.QtWidgets import QLineEdit

ParenSplit = calc_native.ParenSplit
LatexSplit = calc_native.LatexSplit
StructuralSplit = ParenSplit | LatexSplit

structural_split = calc_native.structural_split
split_operand = calc_native.split_operand


def update_autowidth(le: QLineEdit) -> None:
    """Resize a QLineEdit to fit its current text length."""
    fm = le.fontMetrics()
    text_width = fm.horizontalAdvance(le.text())
    margins = le.textMargins()
    pad = margins.left() + margins.right() + fm.averageCharWidth()
    le.setFixedWidth(int(text_width + pad / 2))
