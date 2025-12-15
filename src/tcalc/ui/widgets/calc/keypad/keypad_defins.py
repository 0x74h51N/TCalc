from .....core import Operation


# Custom labels for buttons (where symbol differs from display)
NEGATE_LABEL = "+/-"
SQRT_LABEL = "√x"
INV_LABEL = "1/x"
FACT_LABEL = "x!"
SQR_LABEL = "x²"
POW_LABEL = "xʸ"
EXP10_LABEL = "x·10ʸ"


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

NUMBER_KEYS = []

for d, (row, col) in DIGIT_POSITIONS.items():
    key = {
        "label": str(d),
        "operation": str(d),
        "row": row,
        "col": col,
    }
    if d == 0:
        key["colspan"] = 2
    NUMBER_KEYS.append(key)

NUMBER_KEYS.append(
    {
        "label": ".",
        "operation": Operation.DOT,
        "row": 4,
        "col": 2,
    }
)

MATH_OPERATOR_KEYS = [
    {"label": Operation.ADD.symbol,  "operation": Operation.ADD, "row": 1, "col": 3, "rowspan": 2, "tooltip": "add"},
    {"label": Operation.SUB.symbol,  "operation": Operation.SUB, "row": 0, "col": 3, "tooltip": "subtract"},
    {"label": Operation.MUL.symbol,  "operation": Operation.MUL, "row": 0, "col": 2, "tooltip": "multiply"},
    {"label": Operation.DIV.symbol,  "operation": Operation.DIV, "row": 0, "col": 1, "tooltip": "divide"},
    {"label": Operation.PERCENT.symbol,  "operation": Operation.PERCENT, "row": 0, "col": 0, "tooltip": "percent"},
    {"label": Operation.OPEN_PAREN.symbol,  "operation": Operation.OPEN_PAREN, "row": 3, "col": 4, "tooltip": "open paren"},
    {"label": Operation.CLOSE_PAREN.symbol,  "operation": Operation.CLOSE_PAREN, "row": 4, "col": 4, "tooltip": "close paren"},
]

ACTION_KEYS = [
    {"label": Operation.BACKSPACE.symbol,   "operation": Operation.BACKSPACE, "row": 0, "col": 4, "tooltip": "backspace"},
    {"label": Operation.CLEAR.symbol,   "operation": Operation.CLEAR, "row": 1, "col": 4, "tooltip": "clear"},
    {"label": Operation.ALL_CLEAR.symbol,  "operation": Operation.ALL_CLEAR, "row": 2, "col": 4, "tooltip": "clear all"},
    {"label": NEGATE_LABEL, "operation": Operation.NEGATE, "row": 5, "col": 4, "tooltip": "negate"},
    {"label": Operation.EQUALS.symbol,   "operation": Operation.EQUALS, "row": 3, "col": 3, "rowspan": 2, "tooltip": "equals"},
]

# Science mode keys (left panel, 2 columns x 7 rows) - grouped by role
TRIG_KEYS = [
    {"label": Operation.HYP.symbol.capitalize(), "operation": Operation.HYP, "row": 0, "col": 0, "tooltip": "hyperbolic"},
    {"label": Operation.SIN.symbol, "operation": Operation.SIN, "row": 1, "col": 0, "tooltip": "sine"},
    {"label": Operation.COS.symbol, "operation": Operation.COS, "row": 2, "col": 0, "tooltip": "cosine"},
    {"label": Operation.TAN.symbol, "operation": Operation.TAN, "row": 3, "col": 0, "tooltip": "tangent"},
]

FUNCTION_KEYS = [
    {"label": Operation.MOD.symbol, "operation": Operation.MOD, "row": 0, "col": 1, "tooltip": "modulo"},
    {"label": INV_LABEL, "operation": Operation.INV, "row": 1, "col": 1, "tooltip": "inverse"},
    {"label": FACT_LABEL, "operation": Operation.FACT, "row": 2, "col": 1, "tooltip": "factorial"},
    {"label": Operation.LOG.symbol, "operation": Operation.LOG, "row": 4, "col": 0, "tooltip": "logarithm to base 10"},
    {"label": Operation.LN.symbol, "operation": Operation.LN, "row": 5, "col": 0, "tooltip": "natural log"},
]

POWER_KEYS = [
    {"label": SQR_LABEL, "operation": Operation.SQR, "row": 3, "col": 1, "tooltip": "square"},
    {"label": SQRT_LABEL, "operation": Operation.SQRT, "row": 4, "col": 1, "tooltip": "square root"},
    {"label": POW_LABEL, "operation": Operation.POW, "row": 5, "col": 1, "tooltip": "power"},
    {"label": Operation.IMAG.symbol, "operation": Operation.IMAG, "row": 6, "col": 0, "tooltip": "imaginary"},
    {"label": EXP10_LABEL, "operation": Operation.EXP10, "row": 6, "col": 1, "tooltip": "exp 10"},
]

SCIENCE_MODE_KEYS = {
    "trig": TRIG_KEYS,
    "function": FUNCTION_KEYS,
    "power": POWER_KEYS,
}


NORMAL_MODE_KEYS = {
    "digit": NUMBER_KEYS,
    "operator": MATH_OPERATOR_KEYS,
    "action": ACTION_KEYS,
}
