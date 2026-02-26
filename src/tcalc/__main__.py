from __future__ import annotations

import sys
from typing import Optional, Sequence

from tcalc.ui.app import run_app


def main(argv: Optional[Sequence[str]] = None) -> int:
    if argv is None:
        argv = sys.argv
    args = list(argv)
    debug = "--debug" in args
    if debug:
        args.remove("--debug")
    return run_app(args, debug=debug)


if __name__ == "__main__":
    raise SystemExit(main())
