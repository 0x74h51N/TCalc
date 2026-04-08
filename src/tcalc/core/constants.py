from __future__ import annotations

import calc_native

E: float = float(str(calc_native.e))
PI: float = float(str(calc_native.pi))
I_UNIT: complex = calc_native.i

I_UNIT_CHARS = frozenset({"i", "I", "j", "J"})
I_UNIT_ALIASES: dict[str, complex] = {ch: I_UNIT for ch in I_UNIT_CHARS}

CONSTANTS: dict[str, float | complex] = {
    "e": E,
    "pi": PI,
    "π": PI,
    **I_UNIT_ALIASES,
}
