#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from dataclasses import dataclass

import pytest
from pytest import param

from tcalc.core.utils import fraction_text


@dataclass(frozen=True, slots=True)
class FakeRational:
    numerator: int
    denominator: int


# (numerator, denominator, expected)
@pytest.mark.parametrize(
    "num,den,expected",
    [
        param(1, 3, r"\frac{1}{3}", id="positive"),
        param(-2, 7, r"-\frac{2}{7}", id="negative"),
    ],
)
def test_fraction_text(num, den, expected):
    assert fraction_text(FakeRational(num, den)) == expected
