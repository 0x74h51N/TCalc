from .....core import Operation


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
        "operation": Operation.DIGIT,
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
    {"label": Operation.ADD.symbol,  "operation": Operation.ADD, "row": 1, "col": 3, "rowspan": 2},
    {"label": Operation.SUB.symbol,  "operation": Operation.SUB, "row": 0, "col": 3},
    {"label": Operation.MUL.symbol,  "operation": Operation.MUL, "row": 0, "col": 2},
    {"label": Operation.DIV.symbol,  "operation": Operation.DIV, "row": 0, "col": 1},
    {"label": Operation.PERCENT.symbol,  "operation": Operation.PERCENT, "row": 0, "col": 0},
    {"label": Operation.OPEN_PAREN.symbol,  "operation": Operation.OPEN_PAREN, "row": 2, "col": 4},
    {"label": Operation.CLOSE_PAREN.symbol,  "operation": Operation.CLOSE_PAREN, "row": 3, "col": 4},
]

ACTION_KEYS = [
    {"label": Operation.CLEAR.symbol,   "operation": Operation.CLEAR, "row": 0, "col": 4},
    {"label": Operation.ALL_CLEAR.symbol,  "operation": Operation.ALL_CLEAR, "row": 1, "col": 4},
    {"label": "+/-", "operation": Operation.NEGATE, "row": 4, "col": 4},
    {"label": Operation.EQUALS.symbol,   "operation": Operation.EQUALS, "row": 3, "col": 3, "rowspan": 2},
]

NORMAL_MODE_KEYS = {
    "digit": NUMBER_KEYS,
    "operator": MATH_OPERATOR_KEYS,
    "action": ACTION_KEYS,
}
