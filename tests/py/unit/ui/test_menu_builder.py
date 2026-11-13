#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest

from tcalc.ui.manubar.menu_builder import _narrow


class FakeContext:
    pass


class OtherContext:
    pass


def test_narrow_returns_the_context_of_the_asked_kind() -> None:
    ctx = FakeContext()
    assert _narrow(ctx, FakeContext) is ctx


def test_narrow_rejects_another_kind() -> None:
    with pytest.raises(TypeError, match="OtherContext expected, got FakeContext"):
        _narrow(FakeContext(), OtherContext)
