from pathlib import Path

import tomllib


def _load_config():
    config_path = Path(__file__).parent / "config.toml"
    with open(config_path, "rb") as f:
        return tomllib.load(f)


_config = _load_config()
window = _config["window"]
style = _config["style"]

# Side panel layout
side_panel_config = _config["side_panel"]

# History
_history = _config["history"]
history_config = _history
history_style = _history["style"]
history_math = _history["math"]

# Memory
_memory = _config.get("memory", {})
memory_style = _memory.get("style", {})


def get_history_width_from_total(total_width: int) -> int:
    # Calculate history width based on total width and ratio

    total_stretch = window["calc_stretch"] + window["history_stretch"]

    calculated = total_width * window["history_stretch"] // total_stretch

    return max(window["history_min_width"], calculated)
