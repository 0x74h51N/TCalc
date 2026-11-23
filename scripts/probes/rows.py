#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""The value row every probe prints and the grader reads back."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Protocol

import calc_native

from tcalc.core.utils import CalcValue, collection_text


class ProbeError(Exception):
    """A failure the user of a probe can fix; printed as a message, not a trace."""


class Layer(StrEnum):
    """Where in TCalc a row's value was read, in the order a case passes through them."""

    EDITOR = "editor"
    TOKENS = "tokens"
    FLAT = "flat"
    RPN = "rpn"
    NODES = "nodes"
    SPLIT = "split"
    EVAL = "eval"
    BINDING = "binding"
    APPLY = "apply"
    DISPLAY = "display"
    WRITTEN = "written"
    ROUND_TRIP = "round trip"
    TREE = "tree"
    LOG = "log"
    PAINT = "paint"
    # an input the probe itself could not read, so the inputs after it still run
    PROBE = "probe"


class OperandKind(StrEnum):
    """native_probe's operand prefixes, so a row's input pastes back as its arguments."""

    INT = "int"
    DBL = "dbl"
    RAT = "rat"
    BIG = "big"
    CX = "cx"
    BIGCX = "bigcx"
    LIST = "list"


@dataclass(frozen=True)
class Row:
    input: str
    layer: Layer
    type: str
    value: str
    # by column name; open, since a test row's params become columns
    extra: tuple[tuple[str, str], ...] = ()


_FIELDS: tuple[str, ...] = tuple(f.name for f in fields(Row) if f.name != "extra")
TEXT_TYPE = "str"
UNIT_COLUMN = "unit"
PLAIN_COLUMN = "plain"


def type_name(value: object) -> str:
    return type(value).__name__


class Arm(Protocol):
    """One arm of a native value: its operand prefix, its exact text, its shown text."""

    @property
    def kind(self) -> OperandKind: ...

    def exact(self, value: CalcValue) -> str: ...

    def text(self, value: CalcValue) -> str: ...


@dataclass(frozen=True)
class _Arm[T]:
    cls: type[T]
    kind: OperandKind
    exact_of: Callable[[T], str]
    text_of: Callable[[T], str]

    def exact(self, value: CalcValue) -> str:
        # the table is looked up by type(value), so value is a T
        assert isinstance(value, self.cls)
        return self.exact_of(value)

    def text(self, value: CalcValue) -> str:
        assert isinstance(value, self.cls)
        return self.text_of(value)


def _float_hex(value: float) -> str:
    return value.hex()


def _complex_hex(value: complex) -> str:
    return f"{value.real.hex()},{value.imag.hex()}"


def _fraction(value: calc_native.Rational) -> str:
    return f"{value.numerator}/{value.denominator}"


def _held_digits(value: calc_native.BigReal | calc_native.BigComplex) -> str:
    # Boost's str(0): every digit the value holds
    return calc_native.decimal_text(value, 0)


def _collection_exact(value: calc_native.Collection) -> str:
    # no space, so the list stays one operand word
    return collection_text(value, exact_text, ",")


def _collection_shown(value: calc_native.Collection) -> str:
    return collection_text(value, value_text)


# keyed by the exact type: native classes have no subclasses, and a bool is no arm
_ARMS: dict[type, Arm] = {
    arm.cls: arm
    for arm in (
        _Arm(int, OperandKind.INT, str, str),
        _Arm(float, OperandKind.DBL, _float_hex, repr),
        _Arm(complex, OperandKind.CX, _complex_hex, repr),
        _Arm(calc_native.Rational, OperandKind.RAT, _fraction, _fraction),
        _Arm(calc_native.BigReal, OperandKind.BIG, _held_digits, _held_digits),
        _Arm(calc_native.BigComplex, OperandKind.BIGCX, _held_digits, _held_digits),
        _Arm(calc_native.Collection, OperandKind.LIST, _collection_exact, _collection_shown),
    )
}


def arm(value: CalcValue) -> Arm:
    return _ARMS[type(value)]


def exact_text(value: CalcValue) -> str:
    """The value as it is held, so reading the text back gives the same value."""
    return arm(value).exact(value)


def value_text(value: CalcValue) -> str:
    return arm(value).text(value)


def angle_unit(name: str) -> calc_native.AngleUnit:
    units = calc_native.AngleUnit.__members__
    if name not in units:
        raise ProbeError(f"no angle unit {name!r}; the units are {', '.join(units)}")
    return units[name]


def value_row(text: str, layer: Layer, value: CalcValue, unit: calc_native.AngleUnit) -> Row:
    """A value as TCalc gave it, with the angle unit it was computed in."""
    return Row(text, layer, type_name(value), value_text(value), ((UNIT_COLUMN, unit.name),))


def error_row(text: str, layer: Layer, error: Exception, unit: calc_native.AngleUnit) -> Row:
    """An error in place of a value: its class, and its message as the value."""
    return Row(text, layer, type_name(error), str(error), ((UNIT_COLUMN, unit.name),))


def probe_error_row(text: str, error: ProbeError) -> Row:
    return Row(text, Layer.PROBE, type_name(error), str(error))


def text_row(text: str, layer: Layer, value: str) -> Row:
    return Row(text, layer, TEXT_TYPE, value)


def operand_input(op_symbol: str, operands: Sequence[CalcValue]) -> str:
    """The op and its operands in native_probe's operand form, pasteable as its arguments."""
    return " ".join([op_symbol, *(f"{arm(value).kind}:{exact_text(value)}" for value in operands)])


def _header(rows: Sequence[Row]) -> list[str]:
    """The row fields, then each extra column in the order it first appears."""
    extras = dict.fromkeys(name for row in rows for name, _ in row.extra)
    return [*_FIELDS, *(name for name in extras if name not in _FIELDS)]


def _cells(row: Row, header: Sequence[str]) -> list[str]:
    extra = dict(row.extra)
    fixed = [row.input, str(row.layer), row.type, row.value]
    cells = fixed + [extra.get(name, "") for name in header[len(_FIELDS) :]]
    # a wrapped label's text holds a newline, which would split the row in two
    return [cell.replace("\n", "\\n") for cell in cells]


def format_rows(rows: Sequence[Row]) -> str:
    header = _header(rows)
    table = [header, *(_cells(row, header) for row in rows)]
    widths = [max(len(line[i]) for line in table) for i in range(len(header))]
    lines = ("  ".join(c.ljust(w) for c, w in zip(line, widths, strict=True)) for line in table)
    return "".join(line.rstrip() + "\n" for line in lines)


def _column_starts(header_line: str) -> list[int]:
    # format_rows puts at least two spaces between columns and none inside a header name
    return [
        i
        for i, char in enumerate(header_line)
        if char != " " and (i == 0 or header_line[i - 1] == " ")
    ]


def _row(line: str, bounds: Sequence[tuple[int, int | None]], header: Sequence[str]) -> Row:
    cells = [line[start:end].strip() for start, end in bounds]
    extra = tuple(zip(header[len(_FIELDS) :], cells[len(_FIELDS) :], strict=True))
    layers = {layer.value: layer for layer in Layer}
    if cells[1] not in layers:
        raise ProbeError(f"no layer {cells[1]!r} in {line!r}; is the table still aligned?")
    return Row(cells[0], layers[cells[1]], cells[2], cells[3], extra)


def parse_rows(text: str) -> list[Row]:
    nonblank = [line for line in text.splitlines() if line.strip()]
    if not nonblank:
        return []
    header_line, *lines = nonblank
    header = header_line.split()
    if tuple(header[: len(_FIELDS)]) != _FIELDS:
        raise ProbeError(f"not a probe table: {header_line!r}")
    starts = _column_starts(header_line)
    bounds = list(zip(starts, [*starts[1:], None], strict=True))
    return [_row(line, bounds, header) for line in lines]
