#
# TCalc - Copyright (C) 2025 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""probe grade FILE [FILE]: grade a probe table, or compare two runs of the same cases."""

from __future__ import annotations

import sys
from pathlib import Path

from probes.grade import compare, grade
from probes.options import STDIN, Options
from probes.rows import ProbeError, format_rows, parse_rows

MAX_FILES = 2


def _table(source: str) -> str:
    return sys.stdin.read() if source == STDIN else Path(source).read_text()


def run(options: Options) -> int:
    if not 1 <= len(options.inputs) <= MAX_FILES:
        raise ProbeError(
            f"grade takes one table to grade or two to compare, got {len(options.inputs)}"
        )
    tables = [parse_rows(_table(source)) for source in options.inputs]
    if len(tables) == 1:
        print(format_rows([grade(row) for row in tables[0]]), end="")
    else:
        print(compare(tables[0], tables[1]))
    return 0
