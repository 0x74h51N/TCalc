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

    def to_double(self) -> float:
        return self.numerator / self.denominator


class FakeBigReal:
    def __str__(self):
        return "big real"


class FakeBigComplex:
    def __str__(self):
        return "big complex"


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
        param(FormatCase(1e11, False, "1.0000000000000000e+11"), id="large float"),
        param(FormatCase(2**-24, False, "5.9604644775390625e-08"), id="small float"),
        param(FormatCase(1.9999999999999991, False, "2"), id="float rounding noise"),
        param(FormatCase(5, False, "5"), id="int"),
        param(FormatCase(1000000, True, "1,000,000"), id="int grouped"),
        param(FormatCase(10**16 + 1, False, "1.0000000000000001e+16"), id="int past a double"),
        param(FormatCase(3 + 4j, False, "3+4i"), id="complex"),
        param(FormatCase(3 - 1j, False, "3-i"), id="complex unit imaginary"),
        param(FormatCase(2j, False, "2i"), id="imaginary"),
        param(FormatCase(1j, False, "i"), id="i"),
        param(FormatCase(-1j, False, "-i"), id="minus i"),
        param(FormatCase(3 + 0j, False, "3"), id="complex that is real"),
        param(
            FormatCase(FakeRational(10**16 + 1, 1), False, "1.0000000000000001e+16"),
            id="whole rational stays exact",
        ),
        param(FormatCase(FakeRational(1, 4), False, "0.25"), id="fraction"),
        param(FormatCase(FakeBigReal(), False, "big real"), id="big real"),
        param(FormatCase(FakeBigComplex(), False, "big complex"), id="big complex"),
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
        ),
    )
    assert format_result(case.value, group=case.group) == case.expected
