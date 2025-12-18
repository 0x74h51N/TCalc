from __future__ import annotations

import calc_native

E: object = calc_native.e
PI: object = calc_native.pi
I_UNIT: object = calc_native.i

CONSTANTS: dict[str, object] = {
    "e": E,
    "pi": PI,
    "π": PI,
    "i": I_UNIT,
}
