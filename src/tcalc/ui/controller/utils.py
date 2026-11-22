from __future__ import annotations

import math
import re

import calc_native

from tcalc.core.ops import Operation
from tcalc.core.utils import CalcValue


def _build_hyp_map() -> dict[Operation, Operation]:
    pairs: tuple[tuple[str, str], ...] = (
        ("SIN", "SINH"),
        ("COS", "COSH"),
        ("TAN", "TANH"),
        ("ASIN", "ASINH"),
        ("ACOS", "ACOSH"),
        ("ATAN", "ATANH"),
    )

    m: dict[Operation, Operation] = {}
    for src_name, dst_name in pairs:
        src = getattr(Operation, src_name, None)
        dst = getattr(Operation, dst_name, None)
        if src is None or dst is None:
            continue
        m[src] = dst
    return m


HYP_MAP: dict[Operation, Operation] = _build_hyp_map()


def apply_hyp_variant(op: Operation, hyp_enabled: bool) -> Operation:
    if not hyp_enabled:
        return op
    return HYP_MAP.get(op, op)


# Significant digits of an exact value on the result line; #128 makes it a setting.
RESULT_DIGITS = 20

# An integer digit run: not after a point or a digit, and not an exponent.
_INT_RUN = re.compile(r"(?<![\d.])(?<!e[+-])\d{4,}")


def _group_digits(text: str) -> str:
    """Thousands separators into every integer digit run, both parts of a complex too."""
    return _INT_RUN.sub(lambda m: f"{int(m.group()):,}", text)


def format_result(value: CalcValue, *, group: bool = False) -> str:
    """Format a numeric result (float, complex, Rational, Collection, etc.).

    Default output is tokenizer-safe (no thousands separators) so it can be fed
    back into the editor. Pass group=True only for display widgets (result
    screen, memory bar, history), where the comma is a visual separator."""

    if isinstance(value, calc_native.Collection):
        # Native owns the glyphs and the cap, so a bulk collection formats at most
        # head+tail items. Items never group: "1,000,000" would not tokenize back.
        opener, closer, cap = value.preview()
        if cap is None:
            parts = [format_result(item) for item in value]
        else:
            head, tail = cap
            n = len(value)
            parts = [format_result(value[i]) for i in range(head)]
            parts.append("...")
            parts += [format_result(value[i]) for i in range(n - tail, n)]
        return opener + ", ".join(parts) + closer

    if isinstance(value, int | calc_native.Rational | calc_native.BigReal | calc_native.BigComplex):
        if group:
            return _group_digits(calc_native.decimal_text(value, RESULT_DIGITS))
        # Written into the expression, so it must read back as the same value.
        if isinstance(value, int):
            return str(value)
        if isinstance(value, calc_native.Rational):
            return str(value.numerator) if value.denominator == 1 else f"({value})"
        return calc_native.decimal_text(value, RESULT_DIGITS)

    def fmt_real(x: float) -> str:
        abs_val = abs(x)
        # cosh(1000) is inf, which has no exponent to split.
        if not math.isfinite(x):
            return str(x)
        if abs_val >= 1e10 or (0 < abs_val < 1e-6):
            mantissa, exponent = f"{x:.15e}".split("e")
            return f"{mantissa.rstrip('0').rstrip('.')}e{exponent}"

        if x.is_integer():
            return f"{int(x):,}" if group else str(int(x))

        result = f"{x:.16g}"
        if "999999999999" in result:
            result = f"{x:.15g}"

        return _group_digits(result) if group else result

    # Complex handling
    if isinstance(value, complex):
        re = float(value.real)
        im = float(value.imag)

        eps = 1e-12
        if abs(re) < eps:
            re = 0.0
        if abs(im) < eps:
            im = 0.0

        # Pure real -> format like float
        if im == 0.0:
            return fmt_real(re)

        # Pure imaginary
        if re == 0.0:
            if im == 1.0:
                return "i"
            if im == -1.0:
                return "-i"
            return f"{fmt_real(im)}i"

        # a +/- bi
        sign = "+" if im > 0 else "-"
        mag = abs(im)

        if mag == 1.0:
            imag_part = "i"
        else:
            imag_part = f"{fmt_real(mag)}i"

        return f"{fmt_real(re)}{sign}{imag_part}"

    return fmt_real(float(value))
