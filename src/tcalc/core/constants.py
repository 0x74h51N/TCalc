from __future__ import annotations

import re

import calc_native


def strip_subscript(symbol: str) -> str:
    return symbol.replace("{", "").replace("}", "")


def _spaced_name(camel: str) -> str:
    words = re.findall(r"[A-Z][a-z0-9]*", camel)
    return " ".join(words) if words else camel


CONST_BY_ID: dict[calc_native.ConstId, calc_native.ConstSpec] = {
    _spec.id: _spec for _spec in calc_native.const_table()
}

# id -> spaced display name ("SpeedOfLight" -> "Speed Of Light"), shared by the menu
# and the result status line.
CONST_NAMES: dict[calc_native.ConstId, str] = {
    _spec.id: _spaced_name(_spec.id.name) for _spec in calc_native.const_table()
}

# subscript key ("σ_SB") -> display name, for the status line on a subscript constant.
SUBSCRIPT_CONST_NAMES: dict[str, str] = {
    strip_subscript(_spec.symbol): CONST_NAMES[_spec.id]
    for _spec in calc_native.const_table()
    if "_{" in _spec.symbol
}

_imag = CONST_BY_ID[calc_native.ConstId.Imaginary]
I_UNIT_CHARS: frozenset[str] = frozenset({_imag.symbol, *_imag.aliases})
