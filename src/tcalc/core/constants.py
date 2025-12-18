from __future__ import annotations

import calc_native 

E: object = calc_native.e
PI: object = calc_native.pi
I: object = calc_native.i

MATH_CONSTANTS: dict[str, object] = {
    "e": E,
    "pi": PI,
    "π": PI,
    "i": I,
}

CONSTANTS= (MATH_CONSTANTS)