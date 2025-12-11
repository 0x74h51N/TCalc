from __future__ import annotations


def format_result(value: float) -> str:
    # sci notation for very large/small
    abs_val = abs(value)
    if abs_val >= 1e10 or (0 < abs_val < 1e-6):
        return f"{value:.6e}"
    
    # int handling
    if value.is_integer():
        return f"{int(value):,}"
    
    # decimal handling
    result = f"{value:.10g}"
    
    if '.' in result:
        int_part, dec_part = result.split('.', 1)
        if abs(float(int_part)) >= 1000:
            return f"{int(int_part):,}.{dec_part}"
    
    return result


def clean_for_expression(formatted: str) -> str:
    # remove all commas
    return formatted.replace(",", "")

