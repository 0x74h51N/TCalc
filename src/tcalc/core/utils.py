import re
from typing import Any

_NUMBER_PATTERN = re.compile(r"(?:\d+\.\d*|\d+|\.\d+)(?:[eE][+-]?\d+)?")

def is_number_token(tok: Any) -> bool:
    if isinstance(tok, (int, float)):
        return True
    if isinstance(tok, str):
        return _NUMBER_PATTERN.fullmatch(tok) is not None
    return False

def parse_number_token(s: str) -> int | float:
    # int: "6"
    if "." not in s and "e" not in s.lower():
        return int(s)
    # float: "6.0", ".5", "1e3"
    return float(s)
