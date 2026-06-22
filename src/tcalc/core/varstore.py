#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from .constants import CONSTANTS
from .ops import get_symbols_with_aliases
from .utils import CalcValue

_reserved: frozenset[str] | None = None


def is_reserved(name: str) -> bool:
    """A name is reserved if it collides with a constant or an op symbol/alias."""
    global _reserved
    if _reserved is None:
        _reserved = frozenset(CONSTANTS) | frozenset(get_symbols_with_aliases())
    return name in _reserved


class VarStore:
    """Session variable bindings: single-letter name -> native CalcValue, stored
    as-is (a reference to the eval result; never a copy or display string)."""

    __slots__ = ("_vars",)

    def __init__(self) -> None:
        self._vars: dict[str, CalcValue] = {}

    def get(self, name: str) -> CalcValue | None:
        return self._vars.get(name)

    def set(self, name: str, value: CalcValue) -> None:
        self._vars[name] = value

    def clear(self) -> None:
        self._vars.clear()
