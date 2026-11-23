#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest
from pytest import param

from tcalc.ui.controller.utils import format_result


class FakeCollection:
    def __init__(self, items, cap=None):
        self._items, self._cap = items, cap

    def preview(self):
        return "[", "]", self._cap

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, i):
        return self._items[i]


@dataclass
class FakeRational:
    numerator: int
    denominator: int

    def __str__(self):
        return f"{self.numerator}/{self.denominator}"


@dataclass
class FakeBigReal:
    text: str

    def __str__(self):
        return self.text


@dataclass
class FakeBigComplex:
    text: str

    def __str__(self):
        return self.text


def fake_decimal_text(value, digits):
    return str(value)


@dataclass(frozen=True, slots=True)
class FormatCase:
    value: object
    group: bool
    expected: str


@pytest.mark.parametrize(
    "case",
    [
        param(FormatCase(1234567.89, False, "1234567.89"), id="float"),
        param(FormatCase(1234567.89, True, "1,234,567.89"), id="float grouped"),
        param(FormatCase(1234567.0, False, "1234567"), id="whole float"),
        param(FormatCase(1234567.0, True, "1,234,567"), id="whole float grouped"),
        param(FormatCase(1e11, False, "1e+11"), id="large float"),
        param(FormatCase(2**-24, False, "5.960464477539062e-08"), id="small float"),
        param(FormatCase(1.9999999999999991, False, "2"), id="float rounding noise"),
        param(FormatCase(float("inf"), False, "inf"), id="infinite float"),
        param(FormatCase(5, False, "5"), id="int"),
        param(FormatCase(1000000, True, "1,000,000"), id="int grouped"),
        param(FormatCase(10**16 + 1, False, "10000000000000001"), id="int past a double"),
        param(
            FormatCase(10**16 + 1, True, "10,000,000,000,000,001"), id="int display is native text"
        ),
        param(FormatCase(3 + 4j, False, "3+4i"), id="complex"),
        param(FormatCase(3 - 1j, False, "3-i"), id="complex unit imaginary"),
        param(FormatCase(2j, False, "2i"), id="imaginary"),
        param(FormatCase(1j, False, "i"), id="i"),
        param(FormatCase(-1j, False, "-i"), id="minus i"),
        param(FormatCase(3 + 0j, False, "3"), id="complex that is real"),
        param(
            FormatCase(FakeRational(10**16 + 1, 1), False, "10000000000000001"),
            id="whole rational stays exact",
        ),
        param(FormatCase(FakeRational(1, 4), False, "1/4"), id="fraction is decimal text"),
        param(
            FormatCase(FakeRational(2469135, 2), True, "2,469,135/2"),
            id="fraction display is native text",
        ),
        param(FormatCase(FakeBigReal("1234.5"), False, "1234.5"), id="big real"),
        param(FormatCase(FakeBigReal("1234.5"), True, "1,234.5"), id="big real grouped"),
        param(
            FormatCase(FakeBigComplex("1234+5678.5e+12i"), True, "1,234+5,678.5e+12i"),
            id="big complex grouped",
        ),
        param(
            FormatCase(FakeBigComplex("1e+1234i"), True, "1e+1234i"),
            id="big complex exponent not grouped",
        ),
        param(FormatCase(FakeCollection([1, 1000000]), True, "[1, 1000000]"), id="collection"),
        param(
            FormatCase(FakeCollection([1, 2, 3, 4], (1, 1)), False, "[1, ..., 4]"),
            id="collection past its cap",
        ),
    ],
)
def test_format_result(monkeypatch, case):
    monkeypatch.setattr(
        "tcalc.ui.controller.utils.calc_native",
        SimpleNamespace(
            Collection=FakeCollection,
            Rational=FakeRational,
            BigReal=FakeBigReal,
            BigComplex=FakeBigComplex,
            decimal_text=fake_decimal_text,
        ),
    )
    assert format_result(case.value, group=case.group) == case.expected
