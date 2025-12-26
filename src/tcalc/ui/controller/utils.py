from __future__ import annotations


def format_result(value) -> str:
    """Format a numeric result (float or complex) for display."""

    try:
        import calc_native  # type: ignore
    except ModuleNotFoundError:  # pragma: no cover
        calc_native = None

    if calc_native is not None and isinstance(value, getattr(calc_native, "BigReal", ())):
        return str(value)

    if calc_native is not None and isinstance(value, getattr(calc_native, "BigComplex", ())):
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

    # Float/int handling (legacy behavior)
    if isinstance(value, int):
        return f"{value:,}"

    return fmt_real(float(value))


def clean_for_expression(formatted: str) -> str:
    """Remove formatting (commas) from a display string for expression use."""
    return formatted.replace(",", "")
