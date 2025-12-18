from __future__ import annotations


from dataclasses import dataclass
from typing import Callable, Literal
from enum import Enum

from .utils import is_int_like

Arity = Literal["binary", "unary", "postfix"]
Assoc = Literal["left", "right"]


def _cx_sqrt(x: float) -> bool:
    return x < 0.0


def _cx_asin_acos(x: float) -> bool:
    return abs(x) > 1.0


def _cx_acosh(x: float) -> bool:
    return x < 1.0


def _cx_atanh(x: float) -> bool:
    return abs(x) >= 1.0


def _cx_log_ln(x: float) -> bool:
    return x <= 0.0


def _cx_root(x: float, y: float) -> bool:
    return x < 0.0 and ((not is_int_like(y)) or (int(round(y)) % 2 == 0))



PromoArity = Literal[1, 2]

@dataclass(frozen=True, slots=True)
class OpSpec:
    sym: str
    prec: int | None = None
    assoc: Assoc | None = None
    arity: Arity | None = None
    als: tuple[str, ...] = ()
    big: bool = False
    cx: Callable[..., bool] | None = None
    cx_arity: PromoArity | None = None



class Operation(str, Enum):
    """
    Operation identifiers.
    """

    DIGIT = "digit"

    # binary operators
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    DIV = "div"
    POW = "pow"

    # postfix percent
    PERCENT = "percent"

    DOT = "dot"
    OPEN_PAREN = "open_paren"
    CLOSE_PAREN = "close_paren"

    EQUALS = "equals"
    CLEAR = "clear"
    BACKSPACE = "backspace"
    NEGATE = "negate"
    SQRT = "sqrt"

    # Trigonometric functions (unary)
    SIN = "sin"
    COS = "cos"
    TAN = "tan"
    HYP = "hyp"
    SINH = "sinh"
    COSH = "cosh"
    TANH = "tanh"
    ASIN = "asin"
    ACOS = "acos"
    ATAN = "atan"
    ASINH = "asinh"
    ACOSH = "acosh"
    ATANH = "atanh"

    # Function operations
    RECIP = "recip"
    FACT = "fact"
    LOG = "log"
    LN = "ln"
    MOD = "mod"
    POW10 = "pow10"
    EXP = "exp"
    INTDIV = "intdiv"
    PERMUTE = "permute"
    CHOOSE = "choose"
    GAMMA = "gamma"
    CBRT = "cbrt"

    # Power operations
    SQR = "sqr"
    CUBE = "cube"
    EXP10 = "exp10"
    ROOT = "root"
    IMAG = "imag"
    POLAR = "polar"

    @property
    def spec(self) -> OpSpec:
        return OP_SPECS[self]

    @property
    def symbol(self) -> str:
        return self.spec.sym

    @property
    def precedence(self) -> int | None:
        return self.spec.prec

    @property
    def associativity(self) -> Assoc | None:
        return self.spec.assoc

    @property
    def arity(self) -> Arity | None:
        return self.spec.arity

    @property
    def aliases(self) -> tuple[str, ...]:
        return self.spec.als

    @property
    def big_supported(self) -> bool:
        return self.spec.big


OP_SPECS: dict[Operation, OpSpec] = {
    Operation.DIGIT: OpSpec(sym="digit"),

    Operation.ADD: OpSpec(sym="+", prec=1, assoc="left", arity="binary", big=True),
    Operation.SUB: OpSpec(sym="-", prec=1, assoc="left", arity="binary", big=True),
    Operation.MUL: OpSpec(sym="x", prec=2, assoc="left", arity="binary", als=("*",), big=True),
    Operation.DIV: OpSpec(sym="÷", prec=2, assoc="left", arity="binary", als=("/",), big=True),
    Operation.POW: OpSpec(sym="^", prec=3, assoc="right", arity="binary", big=True),

    Operation.PERCENT: OpSpec(sym="%", prec=4, assoc="left", arity="postfix"),

    Operation.DOT: OpSpec(sym="."),
    Operation.OPEN_PAREN: OpSpec(sym="("),
    Operation.CLOSE_PAREN: OpSpec(sym=")"),

    Operation.EQUALS: OpSpec(sym="="),
    Operation.CLEAR: OpSpec(sym="C"),
    Operation.BACKSPACE: OpSpec(sym="⌫"),

    Operation.NEGATE: OpSpec(sym="u-", prec=3, assoc="right", arity="unary"),
    Operation.SQRT: OpSpec(sym="√", prec=4, assoc="right", arity="unary", als=("sqrt",), big=True, cx=_cx_sqrt),

    Operation.SIN: OpSpec(sym="sin", prec=4, assoc="right", arity="unary"),
    Operation.COS: OpSpec(sym="cos", prec=4, assoc="right", arity="unary"),
    Operation.TAN: OpSpec(sym="tan", prec=4, assoc="right", arity="unary"),
    Operation.HYP: OpSpec(sym="hyp"),
    Operation.SINH: OpSpec(sym="sinh", prec=4, assoc="right", arity="unary"),
    Operation.COSH: OpSpec(sym="cosh", prec=4, assoc="right", arity="unary"),
    Operation.TANH: OpSpec(sym="tanh", prec=4, assoc="right", arity="unary"),
    Operation.ASIN: OpSpec(sym="asin", prec=4, assoc="right", arity="unary", cx=_cx_asin_acos),
    Operation.ACOS: OpSpec(sym="acos", prec=4, assoc="right", arity="unary", cx=_cx_asin_acos),
    Operation.ATAN: OpSpec(sym="atan", prec=4, assoc="right", arity="unary"),
    Operation.ASINH: OpSpec(sym="asinh", prec=4, assoc="right", arity="unary"),
    Operation.ACOSH: OpSpec(sym="acosh", prec=4, assoc="right", arity="unary", cx=_cx_acosh),
    Operation.ATANH: OpSpec(sym="atanh", prec=4, assoc="right", arity="unary", cx=_cx_atanh),

    Operation.RECIP: OpSpec(sym="⁻¹", prec=4, assoc="left", arity="postfix"),
    Operation.FACT: OpSpec(sym="!", prec=4, assoc="left", arity="postfix", als=("factorial",)),
    Operation.LOG: OpSpec(sym="log", prec=4, assoc="right", arity="unary", als=("log10",), big=True, cx=_cx_log_ln),
    Operation.LN: OpSpec(sym="ln", prec=4, assoc="right", arity="unary", big=True, cx=_cx_log_ln),
    Operation.MOD: OpSpec(sym="mod", prec=2, assoc="left", arity="binary", big=True),
    Operation.POW10: OpSpec(sym="⏨", prec=4, assoc="right", arity="unary"),
    Operation.EXP: OpSpec(sym="exp", prec=4, assoc="right", arity="unary", big=True),
    Operation.INTDIV: OpSpec(sym="div", prec=2, assoc="left", arity="binary", als=("//",), big=True),
    Operation.CHOOSE: OpSpec(sym="nCm", prec=4, assoc="right", arity="binary"),
    Operation.PERMUTE: OpSpec(sym="nPm", prec=4, assoc="right",arity="binary"),
    Operation.GAMMA: OpSpec(sym="Γ", prec=4, assoc="right", arity="unary"),
    Operation.CBRT: OpSpec(sym="³√", prec=4, assoc="right", arity="unary"),

    Operation.SQR: OpSpec(sym="²", prec=4, assoc="left", arity="postfix"),
    Operation.CUBE: OpSpec(sym="³", prec=4, assoc="left", arity="postfix"),
    Operation.EXP10: OpSpec(sym="⏨", prec=3, assoc="right", arity="binary"),
    Operation.ROOT: OpSpec(sym="⌄", prec=3, assoc="right", arity="binary", big=True, cx=_cx_root),
    Operation.IMAG: OpSpec(sym="i"),
    Operation.POLAR: OpSpec(sym="∠", prec=4, assoc="right", arity="unary", als=("polar",)),
}
def get_symbols_with_aliases(filter_fn=None) -> set[str]:
    symbols: set[str] = set()
    for op in Operation:
        if filter_fn and not filter_fn(op):
            continue
        if op.symbol:
            symbols.add(op.symbol)
            symbols.update(op.aliases)
    return symbols


def build_operator_table(filter_fn=None) -> dict[str, tuple[int, str]]:
    table: dict[str, tuple[int, str]] = {}
    for op in Operation:
        if filter_fn and not filter_fn(op):
            continue
        if op.symbol and op.precedence is not None:
            table[op.symbol] = (op.precedence, op.associativity or "left")
            for alias in op.aliases:
                table[alias] = (op.precedence, op.associativity or "left")
    return table


def build_operation_map(filter_fn=None) -> dict[str, Operation]:
    op_map: dict[str, Operation] = {}
    for op in Operation:
        if filter_fn and not filter_fn(op):
            continue
        if op.symbol:
            op_map[op.symbol] = op
            for alias in op.aliases:
                op_map[alias] = op
    return op_map
