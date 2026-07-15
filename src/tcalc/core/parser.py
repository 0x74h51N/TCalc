#
#
#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#

from __future__ import annotations

from typing import List

import calc_native


def tokenize_string(expression: str) -> List[calc_native.Token]:
    """Tokenize expression and return token list."""
    return calc_native.tokenize_string(expression).tokens


def tokenize(expression: str) -> calc_native.TokensBranch:
    """Tokenize expression and return full result with metadata."""
    return calc_native.tokenize_string(expression)
