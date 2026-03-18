from PySide6.QtGui import QFontMetrics

from tcalc.core.ops import Operation

BREAK_SYMBOLS: frozenset[str] = frozenset(
    {
        Operation.ADD.symbol,
        Operation.SUB.symbol,
        Operation.MUL.symbol,
        Operation.DIV.symbol,
        Operation.EQUALS.symbol,
        Operation.CLOSE_PAREN.symbol,
        Operation.CLOSE_BRACE.symbol,
        Operation.CLOSE_BRACKET.symbol,
    }
)


def wrap_expression(expr: str, fm: QFontMetrics, max_width: int) -> str:
    if not expr:
        return ""

    lines: list[str] = []
    line_width = 0
    line_start = 0
    last_break = -1

    for i, ch in enumerate(expr):
        line_width += fm.horizontalAdvance(ch)

        if ch in BREAK_SYMBOLS:
            last_break = i + 1

        if line_width > max_width:
            cut = last_break if last_break > line_start else i
            lines.append(expr[line_start:cut])
            line_start = cut
            last_break = -1
            line_width = fm.horizontalAdvance(expr[line_start : i + 1])

    if line_start < len(expr):
        lines.append(expr[line_start:])

    return "\n".join(lines)
