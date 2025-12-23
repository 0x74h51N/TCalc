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


_PROMO_RULES: dict[str, Callable[..., bool]] = {
    "sqrt": _cx_sqrt,
    "asin_acos": _cx_asin_acos,
    "acosh": _cx_acosh,
    "atanh": _cx_atanh,
    "log_ln": _cx_log_ln,
    "root": _cx_root,
}


@dataclass(frozen=True, slots=True)
class OpSpec:
    sym: str
    arity: Arity | None = None
    als: tuple[str, ...] = ()
    method: str = ""
    needs_unit: bool = False
    big: bool = False
    cx: Callable[..., bool] | None = None


OP_BY_ID: dict[object, OpSpec] = {}
OP_BY_SYMBOL: dict[str, OpSpec] = {}


_UI_SPECS: dict[str, OpSpec] = {
    "DIGIT": OpSpec(sym="digit"),
    "DOT": OpSpec(sym="."),
    "OPEN_PAREN": OpSpec(sym="("),
    "CLOSE_PAREN": OpSpec(sym=")"),
    "EQUALS": OpSpec(sym="="),
    "CLEAR": OpSpec(sym="C"),
    "BACKSPACE": OpSpec(sym="⌫"),
    "HYP": OpSpec(sym="hyp"),
    "IMAG": OpSpec(sym="i"),
}


_operation_values: dict[str, str] = {}
_op_specs_by_name: dict[str, OpSpec] = {}

for entry in calc_native.op_table():
    (op_id, symbol, _precedence, _associativity, arity, aliases,
     method, needs_unit, big_supported, promo_rule) = entry
    spec = OpSpec(
        sym=symbol,
        arity=arity.name.lower(),
        als=tuple(aliases),
        method=method,
        needs_unit=bool(needs_unit),
        big=bool(big_supported),
        cx=_PROMO_RULES.get(promo_rule) if promo_rule else None,
    )
    OP_BY_ID[op_id] = spec
    if symbol:
        OP_BY_SYMBOL[symbol] = spec
        for alias in spec.als:
            OP_BY_SYMBOL[alias] = spec
    name = op_id.name.upper()
    _operation_values[name] = method or op_id.name.lower()
    _op_specs_by_name[name] = spec

for name, spec in _UI_SPECS.items():
    _operation_values[name] = name.lower()
    _op_specs_by_name[name] = spec

Operation = Enum("Operation", _operation_values, type=str)


def _spec(self) -> OpSpec:
    return _op_specs_by_name[self.name]


def _symbol(self) -> str:
    return self.spec.sym


def _arity(self) -> Arity | None:
    return self.spec.arity


def _aliases(self) -> tuple[str, ...]:
    return self.spec.als


def _big_supported(self) -> bool:
    return self.spec.big


Operation.spec = property(_spec)
Operation.symbol = property(_symbol)
Operation.arity = property(_arity)
Operation.aliases = property(_aliases)
Operation.big_supported = property(_big_supported)


def get_symbols_with_aliases(filter_fn: Callable[[OpSpec], bool] | None = None) -> set[str]:
    symbols: set[str] = set()
    for op in _op_specs_by_name.values():
        if filter_fn and not filter_fn(op):
            continue
        if op.sym:
            symbols.add(op.sym)
            symbols.update(op.als)
    return symbols

