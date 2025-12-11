from PySide6.QtGui import QFontMetrics

from ....core import get_symbols_with_aliases, Operation

BREAK_SYMBOLS: set[str] = get_symbols_with_aliases(
    lambda op: op in {Operation.ADD, Operation.SUB, Operation.MUL, Operation.DIV, Operation.POW, Operation.EQUALS}
)


def wrap_expression(expr: str, fm: QFontMetrics, max_width: int) -> str:
    if not expr:
        return ""

    lines: list[str] = []
    line_start = 0
    i = 0
    n = len(expr)

    while i < n:
        current = expr[line_start:i + 1]
        width = fm.horizontalAdvance(current)

        if width > max_width:
            break_pos = -1
            for j in range(i, line_start, -1):
                if expr[j] in BREAK_SYMBOLS:
                    break_pos = j + 1 
                    break

            if break_pos == -1:
                break_pos = i

            lines.append(expr[line_start:break_pos])
            line_start = break_pos
            i = break_pos
        else:
            i += 1

    if line_start < n:
        lines.append(expr[line_start:])

    return "\n".join(lines)
