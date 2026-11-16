#
# TCalc - Copyright (C) 2026 Tahsin Önemli
# SPDX-License-Identifier: GPL-3.0-or-later
#
"""Runs the smoke cases it reads from stdin on the app's path, announcing each on stdout."""

from __future__ import annotations

import faulthandler
import json
import resource
import sys

import calc_native
from PySide6.QtWidgets import QApplication

from tcalc.core.native_eval import evaluate_branch
from tcalc.core.parser import tokenize
from tcalc.errors import CalculatorError
from tcalc.ui.app import EVAL_TIME_BUDGET_MS
from tcalc.ui.controller.utils import format_result
from tests.py.helpers import editor_canonical

# Well past the deadline: a case still running then is one the deadline did not stop.
FREEZE_LIMIT_S = 4 * EVAL_TIME_BUDGET_MS / 1000


def _say(line: dict[str, object]) -> None:
    print(json.dumps(line), flush=True)


def main() -> None:
    # Linux ignores a 0 core limit when core_pattern is a pipe; a dump would outlast the case.
    resource.setrlimit(resource.RLIMIT_CORE, (1, 1))
    app = QApplication.instance() or QApplication([])
    calc_native.set_eval_time_budget_ms(EVAL_TIME_BUDGET_MS)
    for i, expr in enumerate(json.load(sys.stdin)):
        _say({"start": i})
        # A C thread, so it fires even while a native call holds the GIL; it exits with 1.
        faulthandler.dump_traceback_later(FREEZE_LIMIT_S, exit=True)
        try:
            calc_native.clear_vars()
            branch = tokenize(editor_canonical(expr))
            value = evaluate_branch(branch, calc_native.Calculator(), calc_native.AngleUnit.RAD)
            format_result(value, group=True)
        except CalculatorError:
            pass
        except Exception as exc:
            _say({"error": i, "exc": repr(exc)})
        faulthandler.cancel_dump_traceback_later()
    app.quit()


if __name__ == "__main__":
    main()
