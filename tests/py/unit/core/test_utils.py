#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest

from tcalc.core import utils as utils_mod

param = pytest.param


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        param(3.0, True, id="int"),
        param(2.0000000000001, True, id="epsilon-close"),
        param(2.1, False, id="fractional"),
    ],
)
def test_is_int_like(value, expected):
    assert utils_mod.is_int_like(value) is expected
