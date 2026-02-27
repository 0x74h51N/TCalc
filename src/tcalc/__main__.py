#
#
#
#
#   TCalc is a native-powered scientific desktop calculator designed
#   for high-performance, precision, and a superior user experience.
#   Copyright (C) <2025>  <Tahsin Önemli>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

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
