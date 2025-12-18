from __future__ import annotations

from pathlib import Path

import tomllib


def _load_config():
    config_path = Path(__file__).with_suffix(".toml")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


_config = _load_config()
style = _config["style"]
