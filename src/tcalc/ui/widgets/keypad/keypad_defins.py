from tcalc.core.ops import Operation

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

SHIFTED_KEYS = {
    Operation.SIN: {
        "label": Operation.ASIN.symbol,
        "operation": Operation.ASIN,
        "tooltip": "inverse sine",
    },
    Operation.COS: {
        "label": Operation.ACOS.symbol,
        "operation": Operation.ACOS,
        "tooltip": "inverse cosine",
    },
    Operation.TAN: {
        "label": Operation.ATAN.symbol,
        "operation": Operation.ATAN,
        "tooltip": "inverse tangent",
    },
    Operation.LOG: {"label": POW10_LABEL, "operation": Operation.POW10, "tooltip": "10 power"},
    Operation.LN: {"label": "eˣ", "operation": Operation.EXP, "tooltip": "exponential func"},
    Operation.MOD: {
        "label": INTDIV_LABEL,
        "operation": Operation.INTDIV,
        "tooltip": "integer division",
    },
    Operation.PERMUTE: {
        "label": Operation.CHOOSE.symbol,
        "operation": Operation.CHOOSE,
        "tooltip": "n choose m",
    },
    Operation.FACT: {
        "label": Operation.GAMMA.symbol,
        "operation": Operation.GAMMA,
        "tooltip": "gamma",
    },
    Operation.SQR: {"label": "x³", "operation": Operation.CUBE, "tooltip": "cube"},
    Operation.POW: {"label": ROOT_LABEL, "operation": Operation.ROOT, "tooltip": "root"},
    Operation.IMAG: {
        "label": Operation.POLAR.symbol,
        "operation": Operation.POLAR,
        "tooltip": "polar complex",
    },
    Operation.SQRT: {"label": "³√x", "operation": Operation.CBRT, "tooltip": "cube root"},
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
    {
        "label": Operation.ADD.symbol,
        "operation": Operation.ADD,
        "row": 1,
        "col": 3,
        "rowspan": 2,
        "tooltip": "add",
    },
    {
        "label": Operation.SUB.symbol,
        "operation": Operation.SUB,
        "row": 0,
        "col": 3,
        "tooltip": "subtract",
    },
    {
        "label": Operation.MUL.symbol,
        "operation": Operation.MUL,
        "row": 0,
        "col": 2,
        "tooltip": "multiply",
    },
    {
        "label": Operation.DIV.symbol,
        "operation": Operation.DIV,
        "row": 0,
        "col": 1,
        "tooltip": "divide",
    },
    {
        "label": Operation.PERCENT.symbol,
        "operation": Operation.PERCENT,
        "row": 0,
        "col": 0,
        "tooltip": "percent",
    },
    {
        "label": Operation.EQUALS.symbol,
        "operation": Operation.EQUALS,
        "row": 3,
        "col": 3,
        "rowspan": 2,
        "tooltip": "equals",
    },
]

PARANTHES_KEYS = [
    {
        "label": Operation.OPEN_PAREN.symbol,
        "operation": Operation.OPEN_PAREN,
        "row": 3,
        "col": 0,
        "tooltip": "open paren",
    },
    {
        "label": Operation.CLOSE_PAREN.symbol,
        "operation": Operation.CLOSE_PAREN,
        "row": 4,
        "col": 0,
        "tooltip": "close paren",
    },
]

ACTION_KEYS = [
    {
        "label": "Shift",
        "operation": "shift",
        "checkable": True,
        "row": 0,
        "col": 0,
        "tooltip": "Second Functions",
    },
    {
        "label": Operation.BACKSPACE.symbol,
        "operation": Operation.BACKSPACE,
        "row": 1,
        "col": 0,
        "tooltip": "backspace",
    },
    {
        "label": Operation.CLEAR.symbol,
        "operation": Operation.CLEAR,
        "row": 2,
        "col": 0,
        "tooltip": "clear",
    },
    {"label": NEGATE_LABEL, "operation": Operation.NEGATE, "row": 5, "col": 0, "tooltip": "negate"},
    {"label": "π", "operation": "π", "row": 6, "col": 0, "tooltip": "pi"},
    {"label": "e", "operation": "e", "row": 7, "col": 0, "tooltip": "Euler's number"},
]


# Science mode keys (left panel, 2 columns x 7 rows) - grouped by role
TRIG_KEYS = [
    {
        "label": Operation.HYP.symbol.capitalize(),
        "operation": Operation.HYP,
        "checkable": True,
        "row": 0,
        "col": 0,
        "tooltip": "hyperbolic",
    },
    {
        "label": Operation.SIN.symbol,
        "operation": Operation.SIN,
        "row": 1,
        "col": 0,
        "tooltip": "sine",
        "shifted": SHIFTED_KEYS[Operation.SIN],
    },
    {
        "label": Operation.COS.symbol,
        "operation": Operation.COS,
        "row": 2,
        "col": 0,
        "tooltip": "cosine",
        "shifted": SHIFTED_KEYS[Operation.COS],
    },
    {
        "label": Operation.TAN.symbol,
        "operation": Operation.TAN,
        "row": 3,
        "col": 0,
        "tooltip": "tangent",
        "shifted": SHIFTED_KEYS[Operation.TAN],
    },
]

FUNCTION_KEYS = [
    {
        "label": Operation.MOD.symbol,
        "operation": Operation.MOD,
        "row": 0,
        "col": 1,
        "tooltip": "modulo",
        "shifted": SHIFTED_KEYS[Operation.MOD],
    },
    {
        "label": Operation.PERMUTE.symbol,
        "operation": Operation.PERMUTE,
        "row": 1,
        "col": 1,
        "tooltip": "n permute m",
        "shifted": SHIFTED_KEYS[Operation.PERMUTE],
    },
    {
        "label": FACT_LABEL,
        "operation": Operation.FACT,
        "row": 2,
        "col": 1,
        "tooltip": "factorial",
        "shifted": SHIFTED_KEYS[Operation.FACT],
    },
    {
        "label": Operation.LOG.symbol,
        "operation": Operation.LOG,
        "row": 4,
        "col": 0,
        "tooltip": "logarithm to base 10",
        "shifted": SHIFTED_KEYS[Operation.LOG],
    },
    {
        "label": Operation.LN.symbol,
        "operation": Operation.LN,
        "row": 5,
        "col": 0,
        "tooltip": "natural log",
        "shifted": SHIFTED_KEYS[Operation.LN],
    },
    {
        "label": RECIP_LABEL,
        "operation": Operation.RECIP,
        "row": 3,
        "col": 1,
        "tooltip": "reciprocal",
    },
]

POWER_KEYS = [
    {
        "label": SQR_LABEL,
        "operation": Operation.SQR,
        "row": 4,
        "col": 1,
        "tooltip": "square",
        "shifted": SHIFTED_KEYS[Operation.SQR],
    },
    {
        "label": SQRT_LABEL,
        "operation": Operation.SQRT,
        "row": 5,
        "col": 1,
        "tooltip": "square root",
        "shifted": SHIFTED_KEYS[Operation.SQRT],
    },
    {
        "label": POW_LABEL,
        "operation": Operation.POW,
        "row": 6,
        "col": 1,
        "tooltip": "power",
        "shifted": SHIFTED_KEYS[Operation.POW],
    },
    {
        "label": Operation.IMAG.symbol,
        "operation": Operation.IMAG,
        "row": 6,
        "col": 0,
        "tooltip": "imaginary",
        "shifted": SHIFTED_KEYS[Operation.IMAG],
    },
]

# Key Groups

NORMAL_MODE_KEYS = {
    "digit": NUMBER_KEYS,
    "operator": MATH_OPERATOR_KEYS,
}

SIDEBAR_KEYS = {"operator": PARANTHES_KEYS, "action": ACTION_KEYS}

SCIENCE_MODE_KEYS = {
    "trig": TRIG_KEYS,
    "function": FUNCTION_KEYS,
    "power": POWER_KEYS,
}
