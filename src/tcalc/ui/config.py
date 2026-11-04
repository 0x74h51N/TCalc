# The UI config: config.toml read once into typed tables
from __future__ import annotations

import tomllib
from collections.abc import Callable
from dataclasses import asdict, dataclass
from functools import reduce
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QEasingCurve

from tcalc.typed_tables import build

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

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
class ColorUsage:
    palette_window_color: str
    palette_window_text_color: str
    palette_base_color: str
    palette_text_color: str
    palette_button_color: str
    palette_button_text_color: str
    palette_highlight_color: str
    palette_highlighted_text_color: str
    icon_color: str
    fraction_icon_color: str
    key_symbol_color: str
    constants_menu_symbol_color: str
    display_background_color: str
    expression_text_color: str
    expression_selection_color: str
    expression_selection_text_color: str
    expression_slot_focus_color: str
    radical_line_color: str
    radical_symbol_color: str
    result_text_color: str
    status_text_color: str
    status_error_text_color: str
    fraction_button_color: str
    fraction_button_hover_color: str
    fraction_button_pressed_color: str
    memory_button_color: str
    memory_button_text_color: str
    memory_button_hover_color: str
    memory_button_pressed_color: str
    memory_button_disabled_color: str
    memory_button_disabled_text_color: str
    number_key_color: str
    number_key_text_color: str
    number_key_pressed_color: str
    operator_key_color: str
    operator_key_text_color: str
    operator_key_pressed_color: str
    action_key_color: str
    action_key_text_color: str
    action_key_pressed_color: str
    equals_key_color: str
    equals_key_text_color: str
    equals_key_pressed_color: str
    equals_key_border_color: str
    trig_key_color: str
    trig_key_text_color: str
    trig_key_pressed_color: str
    function_key_color: str
    function_key_text_color: str
    function_key_pressed_color: str
    power_key_color: str
    power_key_text_color: str
    power_key_pressed_color: str
    key_hover_border_color: str
    key_checked_color: str
    key_disabled_color: str
    key_disabled_text_color: str
    add_key_color: str
    add_key_hover_color: str
    spinbox_color: str
    spinbox_text_color: str
    spinbox_focus_border_color: str
    pad_toolbar_separator_color: str
    pad_menu_background_color: str
    pad_menu_text_color: str
    pad_menu_border_color: str
    pad_menu_selected_color: str
    pad_menu_separator_color: str
    picker_background_color: str
    picker_border_color: str
    picker_list_background_color: str
    picker_text_color: str
    picker_hover_color: str
    menu_background_color: str
    menu_text_color: str
    menu_border_color: str
    menu_selected_color: str
    menu_selected_text_color: str
    menu_selected_border_color: str
    menu_disabled_text_color: str
    menu_separator_color: str
    history_background_color: str
    history_text_color: str
    history_row_color: str
    history_alternate_row_color: str
    history_selected_color: str
    history_selected_text_color: str
    option_text_color: str
    option_hover_color: str
    option_checked_color: str
    option_checked_text_color: str
    icon_button_color: str
    icon_button_text_color: str
    icon_button_hover_color: str
    icon_button_pressed_color: str
    icon_button_light_color: str
    icon_button_shadow_color: str
    tooltip_background_color: str
    tooltip_border_color: str
    tooltip_text_color: str
    toast_text_color: str
    toast_info_color: str
    toast_warn_color: str
    toast_error_color: str


# Picks a place from [color_usage]; a caller that resolves its color on every theme switch keeps it
type ColorPlace = Callable[[ColorUsage], str]


@dataclass(frozen=True, slots=True)
class FontsConfig:
    family_default: str
    size_default: int
    family_monospace: str
    keypad_min_pt: int
    keypad_max_pt: int
    menu_size: int
    picker_size: int


@dataclass(frozen=True, slots=True)
class OptionGroupConfig:
    padding_y: int
    padding_x: int


@dataclass(frozen=True, slots=True)
class StyleConfig:
    tooltip_padding: int
    icon_padding: int
    button_padding: int
    key_radius: int
    icon_button_radius: int
    tooltip_radius: int
    option_radius: int
    option_group: OptionGroupConfig


@dataclass(frozen=True, slots=True)
class IconsConfig:
    untinted: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ToastConfig:
    pad_y: int
    pad_x: int
    border_radius: int
    font_size: int


@dataclass(frozen=True, slots=True)
class SidePanelConfig:
    margin: int
    spacing: int
    resize_debounce_ms: int


@dataclass(frozen=True, slots=True)
class HistoryStyleConfig:
    button_spacer_stretch: int
    clear_button_stretch: int
    item_padding: int
    item_min_height: int
    item_margin: int
    item_spacing: int
    action_btn_size: int
    font_size: int
    wrap_padding_factor: int
    max_pt: int
    expr_min_pt: int
    expr_max_pt: int
    result_min_pt: int
    result_max_pt: int
    btn_margin: int
    clr_btn_min_pt: int
    clr_btn_max_pt: int


@dataclass(frozen=True, slots=True)
class HistoryMathConfig:
    base_font: int
    scale_main: float
    scale_aux: float
    scale_script: float


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
class CalcStyleConfig:
    compact_pad_y: int
    compact_pad_x: int


@dataclass(frozen=True, slots=True)
class ResultConfig:
    height: int
    font_size: int
    max_pt: int
    font_norm: int
    resize_debounce_ms: int
    btn_size: int
    btn_padding: int
    frac_toggle_radius: int
    frac_icon: str
    decimal_icon: str


@dataclass(frozen=True, slots=True)
class DisplayConfig:
    margin: int
    spacing: int
    divider_height: int
    root_border_width: int
    expression_font_size: int
    expression_height_factor: float
    expression_min_height: int
    expr_max_pt: int
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
    memory_pad_y: int
    memory_pad_x: int


@dataclass(frozen=True, slots=True)
class CalcConfig:
    layout: CalcLayoutConfig
    style: CalcStyleConfig
    display: DisplayConfig
    topbar: TopbarConfig


@dataclass(frozen=True, slots=True)
class ManubarStyleConfig:
    item_padding_horizontal: int
    item_padding_vertical: int
    item_margin: int
    item_min_width: int
    item_border_radius: int
    icon_padding_left: int
    icon_padding_right: int
    separator_height: int
    separator_margin_vertical: int
    separator_margin_horizontal: int
    menu_padding: int


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
    style: ManubarStyleConfig
    preset: PresetConfig


@dataclass(frozen=True, slots=True)
class UiConfig:
    window: WindowConfig
    color_usage: ColorUsage
    fonts: FontsConfig
    style: StyleConfig
    icons: IconsConfig
    toast: ToastConfig
    side_panel: SidePanelConfig
    history: HistoryConfig
    memory: MemoryConfig
    keypad: KeypadConfig
    calc: CalcConfig
    manubar: ManubarConfig


@dataclass(frozen=True, slots=True)
class StyleTable:
    """A config table whose int values the stylesheet substitutes as $<prefix><field>."""

    path: tuple[str, ...]
    prefix: str

    def table(self, ui: UiConfig) -> DataclassInstance:
        return reduce(getattr, self.path, ui)


def int_fields(table: DataclassInstance) -> dict[str, int]:
    """The int values of *table* by field name: the numbers a stylesheet can use."""
    return {name: value for name, value in asdict(table).items() if type(value) is int}


# A theme's [spacing] overrides a value of these tables by its substitution name
STYLESHEET_TABLES = (
    StyleTable(("style",), ""),
    StyleTable(("style", "option_group"), "option_"),
    StyleTable(("manubar", "style"), ""),
    StyleTable(("calc", "style"), ""),
    StyleTable(("calc", "topbar"), ""),
    StyleTable(("calc", "display"), ""),
    StyleTable(("calc", "display", "result"), ""),
    StyleTable(("toast",), "toast_"),
)


with open(CONFIG_PATH, "rb") as _file:
    CONFIG: UiConfig = build(UiConfig, tomllib.load(_file), "config")
