#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

import pytest
from pytest import param

from tcalc.core.utils import collection_text


class FakeCollection:
    def __init__(self, items: list[int], cap: tuple[int, int] | None) -> None:
        self.items = items
        self.cap = cap

    def preview(self) -> tuple[str, str, tuple[int, int] | None]:
        return "[", "]", self.cap

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, index: int) -> int:
        return self.items[index]


# items, cap, expected
@pytest.mark.parametrize(
    "items,cap,expected",
    [
        param([1, 2], None, "[<1>, <2>]", id="every item"),
        param([1, 2, 3, 4, 5], (1, 2), "[<1>, ..., <4>, <5>]", id="capped"),
    ],
)
def test_collection_text(items: list[int], cap: tuple[int, int] | None, expected: str) -> None:
    assert collection_text(FakeCollection(items, cap), lambda item: f"<{item}>") == expected
