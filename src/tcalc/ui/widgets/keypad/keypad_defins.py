from tcalc.core.ops import Operation
from tcalc.ui.widgets.keypad.utils import KeyDef, ShiftedDef

# Custom labels for buttons (where symbol differs from display)
NEGATE_LABEL = "+/-"
SQRT_LABEL = "√x"
RECIP_LABEL = "1/x"
FACT_LABEL = "x!"
SQR_LABEL = "x²"
POW_LABEL = "xʸ"
ROOT_LABEL = "x¹ᐟʸ"
INTDIV_LABEL = "intDiv"
POW10_LABEL = "10ˣ"
ENTER_LABEL = "↵"

SHIFTED_KEYS: dict[Operation, ShiftedDef] = {
    Operation.SIN: ShiftedDef(
        label=Operation.ASIN.symbol, operation=Operation.ASIN, tooltip="inverse sine"
    ),
    Operation.COS: ShiftedDef(
        label=Operation.ACOS.symbol, operation=Operation.ACOS, tooltip="inverse cosine"
    ),
    Operation.TAN: ShiftedDef(
        label=Operation.ATAN.symbol, operation=Operation.ATAN, tooltip="inverse tangent"
    ),
    Operation.LOG: ShiftedDef(label=POW10_LABEL, operation=Operation.POW10, tooltip="10 power"),
    Operation.LN: ShiftedDef(label="eˣ", operation=Operation.EXP, tooltip="exponential func"),
    Operation.SQR: ShiftedDef(label="x³", operation=Operation.CUBE, tooltip="cube"),
    Operation.POW: ShiftedDef(label=ROOT_LABEL, operation=Operation.ROOT, tooltip="root"),
    Operation.SQRT: ShiftedDef(label="³√x", operation=Operation.CBRT, tooltip="cube root"),
}


DIGIT_POSITIONS = {
    7: (1, 0),
    8: (1, 1),
    9: (1, 2),
    4: (2, 0),
    5: (2, 1),
    6: (2, 2),
    1: (3, 0),
    2: (3, 1),
    3: (3, 2),
    0: (4, 0),
}

NUMBER_KEYS: list[KeyDef] = []

for _d, (_row, _col) in DIGIT_POSITIONS.items():
    _key: KeyDef = KeyDef(label=str(_d), operation=str(_d), row=_row, col=_col)
    if _d == 0:
        _key.colspan = 2
    NUMBER_KEYS.append(_key)

NUMBER_KEYS.append(KeyDef(label=".", operation=Operation.DOT, row=4, col=2))

MATH_OPERATOR_KEYS: list[KeyDef] = [
    KeyDef(
        label=Operation.ADD.symbol, operation=Operation.ADD, row=1, col=3, rowspan=2, tooltip="add"
    ),
    KeyDef(label=Operation.SUB.symbol, operation=Operation.SUB, row=0, col=3, tooltip="subtract"),
    KeyDef(label=Operation.MUL.symbol, operation=Operation.MUL, row=0, col=2, tooltip="multiply"),
    KeyDef(label=Operation.DIV.symbol, operation=Operation.DIV, row=0, col=1, tooltip="divide"),
    KeyDef(
        label=Operation.PERCENT.symbol, operation=Operation.PERCENT, row=0, col=0, tooltip="percent"
    ),
    KeyDef(
        label=Operation.EQUALS.symbol,
        operation=Operation.EQUALS,
        row=3,
        col=3,
        rowspan=2,
        tooltip="equals",
    ),
]

PARANTHES_KEYS: list[KeyDef] = [
    KeyDef(
        label=Operation.OPEN_PAREN.symbol,
        operation=Operation.OPEN_PAREN,
        row=3,
        col=0,
        tooltip="open paren",
    ),
    KeyDef(
        label=Operation.CLOSE_PAREN.symbol,
        operation=Operation.CLOSE_PAREN,
        row=4,
        col=0,
        tooltip="close paren",
    ),
]

ACTION_KEYS: list[KeyDef] = [
    KeyDef(
        label=Operation.BACKSPACE.symbol,
        operation=Operation.BACKSPACE,
        row=0,
        col=0,
        tooltip="backspace",
    ),
    KeyDef(label=Operation.CLEAR.symbol, operation=Operation.CLEAR, row=1, col=0, tooltip="clear"),
    KeyDef(label=NEGATE_LABEL, operation=Operation.NEGATE, row=2, col=0, tooltip="negate"),
    KeyDef(label=ENTER_LABEL, operation=None, row=5, col=0, tooltip="enter"),
]


# Trig keys (with shift/hyp support)
TRIG_KEYS: list[KeyDef] = [
    KeyDef(
        label="Shift", operation="shift", checkable=True, row=0, col=0, tooltip="Second Functions"
    ),
    KeyDef(
        label=Operation.HYP.symbol.capitalize(),
        operation=Operation.HYP,
        checkable=True,
        row=0,
        col=1,
        tooltip="hyperbolic",
    ),
    KeyDef(
        label=Operation.SIN.symbol,
        operation=Operation.SIN,
        row=1,
        col=0,
        tooltip="sine",
        shifted=SHIFTED_KEYS[Operation.SIN],
    ),
    KeyDef(
        label=Operation.COS.symbol,
        operation=Operation.COS,
        row=2,
        col=0,
        tooltip="cosine",
        shifted=SHIFTED_KEYS[Operation.COS],
    ),
    KeyDef(
        label=Operation.TAN.symbol,
        operation=Operation.TAN,
        row=3,
        col=0,
        tooltip="tangent",
        shifted=SHIFTED_KEYS[Operation.TAN],
    ),
]

# Function keys (flat, no shift)
FUNCTION_KEYS: list[KeyDef] = [
    KeyDef(label=Operation.MOD.symbol, operation=Operation.MOD, row=0, col=0, tooltip="modulo"),
    KeyDef(
        label=INTDIV_LABEL, operation=Operation.INTDIV, row=0, col=1, tooltip="integer division"
    ),
    KeyDef(
        label=Operation.PERMUTE.symbol,
        operation=Operation.PERMUTE,
        row=1,
        col=0,
        tooltip="n permute r",
    ),
    KeyDef(
        label=Operation.CHOOSE.symbol,
        operation=Operation.CHOOSE,
        row=1,
        col=1,
        tooltip="n choose r",
    ),
    KeyDef(label=FACT_LABEL, operation=Operation.FACT, row=2, col=0, tooltip="factorial"),
    KeyDef(label=Operation.GAMMA.symbol, operation=Operation.GAMMA, row=2, col=1, tooltip="gamma"),
    KeyDef(
        label=Operation.LOG.symbol,
        operation=Operation.LOG,
        row=3,
        col=0,
        tooltip="logarithm base 10",
    ),
    KeyDef(label=POW10_LABEL, operation=Operation.POW10, row=3, col=1, tooltip="10 power"),
    KeyDef(label=Operation.LN.symbol, operation=Operation.LN, row=4, col=0, tooltip="natural log"),
    KeyDef(label="eˣ", operation=Operation.EXP, row=4, col=1, tooltip="exponential func"),
    KeyDef(label=RECIP_LABEL, operation=Operation.RECIP, row=5, col=0, tooltip="reciprocal"),
    KeyDef(
        label=Operation.TRUNC.symbol, operation=Operation.TRUNC, row=5, col=1, tooltip="truncate"
    ),
    KeyDef(label=Operation.FLOOR.symbol, operation=Operation.FLOOR, row=6, col=0, tooltip="floor"),
    KeyDef(label=Operation.CEIL.symbol, operation=Operation.CEIL, row=6, col=1, tooltip="ceiling"),
]

# Power keys (with shift support)
POWER_KEYS: list[KeyDef] = [
    KeyDef(
        label=SQR_LABEL,
        operation=Operation.SQR,
        row=3,
        col=1,
        tooltip="square",
        shifted=SHIFTED_KEYS[Operation.SQR],
    ),
    KeyDef(
        label=SQRT_LABEL,
        operation=Operation.SQRT,
        row=4,
        col=1,
        tooltip="square root",
        shifted=SHIFTED_KEYS[Operation.SQRT],
    ),
    KeyDef(
        label=POW_LABEL,
        operation=Operation.POW,
        row=5,
        col=1,
        tooltip="power",
        shifted=SHIFTED_KEYS[Operation.POW],
    ),
    KeyDef(
        label=Operation.IMAG.symbol, operation=Operation.IMAG, row=5, col=0, tooltip="imaginary"
    ),
    KeyDef(
        label=Operation.POLAR.symbol,
        operation=Operation.POLAR,
        row=4,
        col=0,
        tooltip="polar complex",
    ),
    KeyDef(label="π", operation="π", row=1, col=1, tooltip="pi"),
    KeyDef(label="e", operation="e", row=2, col=1, tooltip="Euler's number"),
]

FUNCTION_GROUP: dict[str, list[KeyDef]] = {"function": FUNCTION_KEYS}

TRIG_POWER_GROUP: dict[str, list[KeyDef]] = {"trig": TRIG_KEYS, "power": POWER_KEYS}

# Key Groups

NORMAL_MODE_KEYS: dict[str, list[KeyDef]] = {
    "digit": NUMBER_KEYS,
    "operator": MATH_OPERATOR_KEYS,
}

SIDEBAR_KEYS: dict[str, list[KeyDef]] = {"operator": PARANTHES_KEYS, "action": ACTION_KEYS}
