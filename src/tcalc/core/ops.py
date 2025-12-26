from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import calc_native

Arity = str


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


_PROMO_RULES_BY_ID: dict[object, Callable[..., bool]] = {
    calc_native.OpId.Sqrt: _cx_sqrt,
    calc_native.OpId.Asin: _cx_asin_acos,
    calc_native.OpId.Acos: _cx_asin_acos,
    calc_native.OpId.Acosh: _cx_acosh,
    calc_native.OpId.Atanh: _cx_atanh,
    calc_native.OpId.Log: _cx_log_ln,
    calc_native.OpId.Ln: _cx_log_ln,
    calc_native.OpId.Root: _cx_root,
}


@dataclass(frozen=True, slots=True)
class OpSpec:
    sym: str
    arity: Arity | None = None
    als: tuple[str, ...] = ()
    method: str = ""
    needs_unit: bool = False
    big: bool = False
    bigcx: bool = False
    cx: Callable[..., bool] | None = None


OP_BY_ID: dict[object, OpSpec] = {}


_UI_SPECS = (
    ("DIGIT", OpSpec(sym="digit")),
    ("DOT", OpSpec(sym=".")),
    ("OPEN_PAREN", OpSpec(sym="(")),
    ("CLOSE_PAREN", OpSpec(sym=")")),
    ("EQUALS", OpSpec(sym="=")),
    ("CLEAR", OpSpec(sym="C")),
    ("BACKSPACE", OpSpec(sym="⌫")),
    ("HYP", OpSpec(sym="hyp")),
    ("IMAG", OpSpec(sym="i")),
)


_specs_by_name: dict[str, OpSpec] = {}
_operation_values: dict[str, str] = {}

for entry in calc_native.op_table():
    (
        op_id,
        symbol,
        _precedence,
        _associativity,
        arity,
        aliases,
        method,
        needs_unit,
        big_supported,
        big_complex_supported,
    ) = entry

    spec = OpSpec(
        sym=symbol,
        arity=arity.name.lower(),
        als=tuple(aliases),
        method=method,
        needs_unit=bool(needs_unit),
        big=bool(big_supported),
        bigcx=bool(big_complex_supported),
        cx=_PROMO_RULES_BY_ID.get(op_id),
    )

    OP_BY_ID[op_id] = spec
    name = op_id.name.upper()
    _specs_by_name[name] = spec
    _operation_values[name] = method or op_id.name.lower()

for name, spec in _UI_SPECS:
    _specs_by_name[name] = spec
    _operation_values[name] = name.lower()


class Operation(str, Enum):
    _spec: OpSpec
    @property
    def spec(self) -> OpSpec:
        return self._spec

    @property
    def symbol(self) -> str:
        return self._spec.sym

    @property
    def arity(self) -> Arity | None:
        return self._spec.arity

    @property
    def aliases(self) -> tuple[str, ...]:
        return self._spec.als

    @property
    def big_supported(self) -> bool:
        return self._spec.big

    @property
    def bigcomplex_supported(self) -> bool:
        return self._spec.bigcx

    @property
    def token(self) -> str:
        return self._spec.method or self.name.lower()

Operation = Enum("Operation", _operation_values, type=Operation)
for op in Operation:
    op._spec = _specs_by_name[op.name]

del _operation_values
del _specs_by_name
del _UI_SPECS


def get_symbols_with_aliases(filter_fn: Callable[[OpSpec], bool] | None = None) -> set[str]:
    symbols: set[str] = set()
    for op in Operation:
        spec = op._spec
        if filter_fn and not filter_fn(spec):
            continue
        if spec.sym:
            symbols.add(spec.sym)
            symbols.update(spec.als)
    return symbols
