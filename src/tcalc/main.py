from __future__ import annotations

import sys
from typing import Optional, Sequence

from tcalc.ui.app import run_app


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv
    return run_app(argv)
