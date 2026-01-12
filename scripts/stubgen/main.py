from __future__ import annotations

import sys
from pathlib import Path
from runpy import run_path

STUBGEN_DIR = Path(__file__).resolve().parent
ROOT = STUBGEN_DIR.parents[1]


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(STUBGEN_DIR))

    for script in sorted(STUBGEN_DIR.glob("generate_*.py")):
        run_path(str(script), run_name="__main__")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
