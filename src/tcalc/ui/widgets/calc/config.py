import tomllib
from pathlib import Path


def _load_config():
    config_path = Path(__file__).parent / "config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


config = _load_config()
display_config = config["display"]
keypad_config = config["keypad"]
layout_config = config["layout"]
style_config = config["style"]
topbar_config = config["topbar"]
font_scale_config = config["font_scale"]
