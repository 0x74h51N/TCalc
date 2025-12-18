from __future__ import annotations

import tomllib
from pathlib import Path


def _load_config():
    config_path = Path(__file__).with_suffix(".toml")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


_config = _load_config()
layout_config = _config["layout"]
style = _config["style"]
font_scale = _config["font_scale"]
storage_config = _config["storage"]
