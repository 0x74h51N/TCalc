import tomllib
from pathlib import Path


def _load_config():
    config_path = Path(__file__).parent / "config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


config = _load_config()
display_config = config["display"]
keypad_config = config["keypad"]
