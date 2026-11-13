#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#


from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import EnumType, StrEnum

import calc_native


@dataclass(frozen=True)
class _UIOpSpec:
    """Minimal OpSpec-compatible wrapper for UI-only operations."""

    symbol: str
    id: calc_native.OpId | None = None
    arity: None = None
    aliases: tuple[str, ...] = ()
    method: str = ""


# Paren UI specs — derived locally now that the native module no longer exposes
# a paren_table (the unified ParenToken model has no separate open/close enum).
_PAREN_SPECS = [
    ("OPEN_PAREN", "("),
    ("CLOSE_PAREN", ")"),
    ("OPEN_BRACKET", "["),
    ("CLOSE_BRACKET", "]"),
    ("OPEN_BRACE", "{"),
    ("CLOSE_BRACE", "}"),
]

# UI-only operations
_UI_SPECS = (
    ("DIGIT", "digit"),
    ("DOT", "."),
    ("COMMA", ","),
    *_PAREN_SPECS,
    ("EQUALS", "="),
    ("CLEAR", "C"),
    ("BACKSPACE", "⌫"),
    ("HYP", "hyp"),
)

# Global registry mapping OpId to native OpSpec
OP_BY_ID: dict[calc_native.OpId, calc_native.OpSpec] = {}

_specs_by_name: dict[str, calc_native.OpSpec | _UIOpSpec] = {}
_operation_values: dict[str, str] = {}

# Add native operations
for native_spec in calc_native.op_table():
    OP_BY_ID[native_spec.id] = native_spec  # Build from native op_table
    name = native_spec.id.name.upper()
    _specs_by_name[name] = native_spec
    _operation_values[name] = native_spec.method or native_spec.id.name.lower()

# Add UI operations as OpSpec-compatible wrappers
for name, symbol in _UI_SPECS:
    _specs_by_name[name] = _UIOpSpec(symbol=symbol)
    _operation_values[name] = name.lower()


class OperationBase(StrEnum):
    """Base class for Operation enum with runtime spec access."""

    @property
    def _spec(self) -> calc_native.OpSpec | _UIOpSpec:
        """Get the OpSpec or UI wrapper for this operation."""
        return _specs_by_name[self.name]

    @property
    def symbol(self) -> str:
        """Operation symbol."""
        return self._spec.symbol

    @property
    def arity(self) -> calc_native.OpArity | None:
        """Operation arity (unary/binary/postfix)."""
        return self._spec.arity

    @property
    def aliases(self) -> list[str] | tuple[str, ...]:
        """Alternative symbols for this operation."""
        return self._spec.aliases

    @property
    def method(self) -> str:
        """Method name for this operation."""
        return self._spec.method or self.name.lower()

    @property
    def token(self) -> str:
        """Token string for this operation."""
        return self.method


# Dynamically create the Operation enum
_operation_members = EnumType.__prepare__("Operation", (OperationBase,))
_operation_members["__module__"] = __name__
for name, value in _operation_values.items():
    _operation_members[name] = value
Operation = EnumType("Operation", (OperationBase,), _operation_members)


def get_symbols_with_aliases(
    filter_fn: Callable[[calc_native.OpSpec | _UIOpSpec], bool] | None = None,
) -> set[str]:
    """Get all operation symbols including aliases."""
    symbols: set[str] = set()
    for spec in _specs_by_name.values():
        if filter_fn and not filter_fn(spec):
            continue
        symbols.add(spec.symbol)
        symbols.update(spec.aliases)
    return symbols


@dataclass(frozen=True)
class LatexExprSpec:
    """LaTeX expression specification."""

    symbol: str
    kind: calc_native.LatexKind
    opid: calc_native.OpId


class LatexExpr:
    """LaTeX expressions namespace with typed class attributes."""

    Frac: LatexExprSpec
    Pow: LatexExprSpec
    Root: LatexExprSpec
    Log: LatexExprSpec
    Subscript: LatexExprSpec

    @classmethod
    def get(cls, kind: calc_native.LatexKind) -> LatexExprSpec:
        """Get spec by LatexKind."""
        return _LATEX_BY_KIND[kind]


_LATEX_BY_KIND: dict[calc_native.LatexKind, LatexExprSpec] = {}
for _entry in calc_native.latex_exprs():
    _LATEX_BY_KIND[_entry.kind] = LatexExprSpec(
        symbol=_entry.symbol, kind=_entry.kind, opid=_entry.opid
    )
    setattr(LatexExpr, _entry.kind.name, _LATEX_BY_KIND[_entry.kind])
