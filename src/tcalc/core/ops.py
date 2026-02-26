from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import calc_native


def is_int_like(v: float, eps: float = 1e-12) -> bool:
    return abs(v - round(v)) <= eps


def _cx_sqrt(x: float) -> bool:
    return x < 0.0


def _cx_asin_acos(x: float) -> bool:
    return abs(x) > 1.0


def _cx_acosh(x: float) -> bool:
    return x < 1.0


def _cx_atanh(x: float) -> bool:
    return abs(x) >= 1.0


def _cx_log_ln(x: float) -> bool:
    return x <= 0.0


def _cx_root(x: float, y: float) -> bool:
    return x < 0.0 and ((not is_int_like(y)) or (int(round(y)) % 2 == 0))


PROMO_RULES_BY_ID: dict[calc_native.OpId, Callable[..., bool]] = {
    calc_native.OpId.Sqrt: _cx_sqrt,
    calc_native.OpId.Asin: _cx_asin_acos,
    calc_native.OpId.Acos: _cx_asin_acos,
    calc_native.OpId.Acosh: _cx_acosh,
    calc_native.OpId.Atanh: _cx_atanh,
    calc_native.OpId.Log: _cx_log_ln,
    calc_native.OpId.Ln: _cx_log_ln,
    calc_native.OpId.Root: _cx_root,
}


@dataclass(frozen=True)
class _UIOpSpec:
    """Minimal OpSpec-compatible wrapper for UI-only operations."""

    symbol: str
    id: calc_native.OpId | None = None
    arity: None = None
    aliases: tuple[str, ...] = ()
    big_supported: bool = False
    big_complex_supported: bool = False
    angle_unit: bool = False
    method: str = ""


# Global registry mapping OpId to native OpSpec
OP_BY_ID: dict[calc_native.OpId, calc_native.OpSpec] = {}

# Build from native op_table
for native_spec in calc_native.op_table():
    OP_BY_ID[native_spec.id] = native_spec


# UI-only operations
_UI_SPECS = (
    ("DIGIT", "digit"),
    ("DOT", "."),
    ("OPEN_PAREN", "("),
    ("CLOSE_PAREN", ")"),
    ("EQUALS", "="),
    ("CLEAR", "C"),
    ("BACKSPACE", "⌫"),
    ("HYP", "hyp"),
    ("IMAG", "i"),
)

_specs_by_name: dict[str, calc_native.OpSpec | _UIOpSpec] = {}
_operation_values: dict[str, str] = {}

# Add native operations
for native_spec in calc_native.op_table():
    name = native_spec.id.name.upper()
    _specs_by_name[name] = native_spec
    _operation_values[name] = native_spec.method or native_spec.id.name.lower()

# Add UI operations as OpSpec-compatible wrappers
for name, symbol in _UI_SPECS:
    _specs_by_name[name] = _UIOpSpec(symbol=symbol)
    _operation_values[name] = name.lower()


class OperationBase(str, Enum):
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
    def big_supported(self) -> bool:
        """Whether BigReal is supported."""
        return self._spec.big_supported

    @property
    def bigcomplex_supported(self) -> bool:
        """Whether BigComplex is supported."""
        return self._spec.big_complex_supported

    @property
    def angle_unit(self) -> bool:
        """Whether operation needs angle unit setting."""
        return self._spec.angle_unit

    @property
    def cx(self) -> Callable[..., bool] | None:
        """Complex promotion rule for this operation."""
        op_id = self._spec.id
        if op_id is None:
            return None
        return PROMO_RULES_BY_ID.get(op_id)

    @property
    def method(self) -> str:
        """Method name for this operation."""
        return self._spec.method or self.name.lower()

    @property
    def token(self) -> str:
        """Token string for this operation."""
        return self.method


# Dynamically create the Operation enum
Operation: type[OperationBase] = Enum("Operation", _operation_values, type=OperationBase)  # type: ignore[assignment,misc]


def get_symbols_with_aliases(
    filter_fn: Callable[[calc_native.OpSpec | _UIOpSpec], bool] | None = None,
) -> set[str]:
    """Get all operation symbols including aliases."""
    symbols: set[str] = set()
    for op in Operation:
        spec = op._spec
        if filter_fn and not filter_fn(spec):
            continue
        symbols.add(op.symbol)
        symbols.update(op.aliases)
    return symbols


@dataclass(frozen=True)
class LatexExprSpec:
    """LaTeX expression specification."""

    symbol: str
    kind: calc_native.ExprKind
    opid: calc_native.OpId


class LatexExpr:
    """LaTeX expressions namespace with typed class attributes."""

    Frac: LatexExprSpec
    Pow: LatexExprSpec
    Root: LatexExprSpec
    Log: LatexExprSpec

    @classmethod
    def get(cls, kind: calc_native.ExprKind) -> LatexExprSpec:
        """Get spec by ExprKind."""
        return getattr(cls, kind.name)


for _entry in calc_native.latex_exprs():
    setattr(
        LatexExpr,
        _entry.kind.name,
        LatexExprSpec(symbol=_entry.symbol, kind=_entry.kind, opid=_entry.opid),
    )
