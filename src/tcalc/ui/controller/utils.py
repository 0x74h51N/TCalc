from __future__ import annotations

from typing import Dict, Tuple

import calc_native

from tcalc.core.ops import Operation


def _build_hyp_map() -> Dict[Operation, Operation]:
    pairs: Tuple[Tuple[str, str], ...] = (
        ("SIN", "SINH"),
        ("COS", "COSH"),
        ("TAN", "TANH"),
        ("ASIN", "ASINH"),
        ("ACOS", "ACOSH"),
        ("ATAN", "ATANH"),
    )

    m: Dict[Operation, Operation] = {}
    for src_name, dst_name in pairs:
        src = getattr(Operation, src_name, None)
        dst = getattr(Operation, dst_name, None)
        if src is None or dst is None:
            continue
        m[src] = dst
    return m


HYP_MAP: Dict[Operation, Operation] = _build_hyp_map()


def apply_hyp_variant(op: Operation, hyp_enabled: bool) -> Operation:
    if not hyp_enabled:
        return op
    return HYP_MAP.get(op, op)


def format_result(value) -> str:
    """Format a numeric result (float, complex, Rational, Collection, etc.) for display."""

    if isinstance(value, calc_native.Collection):
        return repr(value)

    if isinstance(value, calc_native.Rational):
        # Display as decimal value for now; fraction widget will use .numerator/.denominator
        return format_result(value.to_double())

    if isinstance(value, calc_native.BigReal):
        return str(value)

    if isinstance(value, calc_native.BigComplex):
        return str(value)

    def fmt_real(x: float) -> str:
        abs_val = abs(x)
        if abs_val >= 1e10 or (0 < abs_val < 1e-6):
            return f"{x:.16e}"

        if x.is_integer():
            return f"{int(x):,}"

        result = f"{x:.16g}"
        if "999999999999" in result:
            result = f"{x:.15g}"

        if "." in result:
            int_part, dec_part = result.split(".", 1)
            if abs(float(int_part)) >= 1000:
                return f"{int(int_part):,}.{dec_part}"

        return result

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


# def clean_for_expression(formatted: str) -> str:
#     """Remove formatting (commas) from a display string for expression use."""
#     return formatted.replace(",", "")
