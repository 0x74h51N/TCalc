# The UI config: config.toml read once into typed tables
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QEasingCurve

from tcalc.typed_tables import build

CONFIG_PATH = Path(__file__).parent / "config.toml"


@dataclass(frozen=True, slots=True)
class WindowConfig:
    min_height: int
    calc_min_width: int
    history_min_width: int
    numpad_min_width: int
    funcpad_min_width: int
    trigpad_min_width: int
    layout_margins: int
    layout_spacing: int
    divider_line_width: int
    size_hint_width: int
    size_hint_height: int
    calc_stretch: int
    history_stretch: int


@dataclass(frozen=True, slots=True)
class IconsConfig:
    untinted: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SidePanelConfig:
    margin: int
    spacing: int
    resize_debounce_ms: int


@dataclass(frozen=True, slots=True)
class HistoryStyleConfig:
    button_spacer_stretch: int
    clear_button_stretch: int
    item_min_height: int
    item_margin: int
    item_spacing: int
    action_btn_size: int
    font_size: int
    max_pt: int
    expr_min_pt: int
    expr_max_pt: int
    btn_margin: int
    clr_btn_min_pt: int
    clr_btn_max_pt: int


@dataclass(frozen=True, slots=True)
class HistoryMathConfig:
    base_font: int


@dataclass(frozen=True, slots=True)
class HistoryConfig:
    max_items: int
    style: HistoryStyleConfig
    math: HistoryMathConfig


@dataclass(frozen=True, slots=True)
class MemoryStyleConfig:
    font_size: int
    max_pt: int
    divider_spacing: int


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    style: MemoryStyleConfig


@dataclass(frozen=True, slots=True)
class CustomPadConfig:
    default_cols: int
    default_rows: int
    default_max_rows: int
    min_cols: int
    max_cols: int
    min_grid_rows: int
    max_grid_rows: int
    min_rows: int
    max_rows: int
    toolbar_margin: int
    toolbar_spacing: int
    spin_width: int
    spin_font_size: int
    picker_min_width: int
    picker_margin: int
    picker_spacing: int
    picker_list_height: int
    picker_list_margin_left: int
    picker_list_margin_top: int
    picker_list_margin_right: int
    picker_list_margin_bottom: int


@dataclass(frozen=True, slots=True)
class KeypadConfig:
    top_margin: int
    side_margin: int
    bottom_margin: int
    grid_spacing: int
    hbox_spacing: int
    hbox_stretch: int
    normal_mode_keys_stretch: int
    right_side_grid_stretch: int
    science_grid_stretch: int
    column_split: int
    keypad_stretch: int
    resize_debounce_ms: int
    custom: CustomPadConfig


@dataclass(frozen=True, slots=True)
class CalcLayoutConfig:
    display_stretch: int
    divider_line_width: int


@dataclass(frozen=True, slots=True)
class ResultConfig:
    height: int
    font_norm: int
    resize_debounce_ms: int
    btn_size: int
    frac_icon: str
    decimal_icon: str


@dataclass(frozen=True, slots=True)
class DisplayConfig:
    margin: int
    spacing: int
    expression_height_factor: float
    expression_min_height: int
    scroll_anim_duration: int
    scroll_anim_curve: QEasingCurve.Type
    result: ResultConfig


@dataclass(frozen=True, slots=True)
class TopbarConfig:
    side_margin: int
    top_margin: int
    bottom_margin: int
    grid_spacing: int
    spacer_stretch: int


@dataclass(frozen=True, slots=True)
class CalcConfig:
    layout: CalcLayoutConfig
    display: DisplayConfig
    topbar: TopbarConfig


@dataclass(frozen=True, slots=True)
class PresetConfig:
    row_icon: str
    rename_icon: str
    update_icon: str
    delete_icon: str
    action_btn_size: int
    action_spacing: int
    bar_offset: int


@dataclass(frozen=True, slots=True)
class ManubarConfig:
    preset: PresetConfig


@dataclass(frozen=True, slots=True)
class UiConfig:
    window: WindowConfig
    icons: IconsConfig
    side_panel: SidePanelConfig
    history: HistoryConfig
    memory: MemoryConfig
    keypad: KeypadConfig
    calc: CalcConfig
    manubar: ManubarConfig


with open(CONFIG_PATH, "rb") as _file:
    CONFIG: UiConfig = build(UiConfig, tomllib.load(_file), "config")
