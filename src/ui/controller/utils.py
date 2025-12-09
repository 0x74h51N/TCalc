from __future__ import annotations


def parse_entry(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        return 0.0


def format_result(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.10g}"

