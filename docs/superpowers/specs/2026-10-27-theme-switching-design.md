# Theme switching: Light, Dark, System Default

Date: 2026-10-27
Status: approved 2026-10-27

## Why

TCalc only has a dark color set. On a machine whose OS theme is light the app
still looks dark (the palette fix in PR #89 made sure the OS can't leak into
it), and the user has no way to pick a light look. This adds a user-chosen
theme that is independent of the OS, plus an option to follow the OS.

## What the user sees

- **View menu, at the very top:** a `Theme` submenu, then a separator, then the
  existing `Keypad Preset` submenu.
- **Inside `Theme`:**
  - `Light`
  - `Dark`
  - `System Default`
  - separator
  - `Add Custom Theme...`
- The three choices are checkable and exclusive; the active one shows a check
  mark, like the Keypad Preset entries.
- `Add Custom Theme...` is present but disabled, in the same way as
  `Statistic (Coming Soon)`. Its content and behavior are a separate spec.
  *(Showing it disabled is the writer's call; the user only said it must not
  work yet.)*
- **Picking a theme applies it immediately**, with no restart. Everything that
  is already open switches: main window, menu bar and menus, keypads (built-in
  and custom), display and result area, top bar, history panel, side panel,
  toasts, tooltips, constant menus, and icons.
- The choice is remembered across launches.

## Behavior

### System Default
- Follows the OS color scheme: OS light -> Light, OS dark -> Dark.
- If the OS reports no preference (e.g. WSLg, where Qt returns
  `Qt.ColorScheme.Unknown`), use Dark.
- While the app runs, if the OS theme changes, the app follows it. This must be
  event driven, reacting to `QStyleHints.colorSchemeChanged`; no polling or
  timers.
- When Light or Dark is chosen explicitly, OS changes are ignored.

### Persistence
- Stored in `QSettings("TCalc", "TCalc")` like the other app settings
  (see `AppState`), key e.g. `theme`, values `light` / `dark` / `system`.
- First launch default: `System Default`. *(Writer's call.)*
- An unknown stored value falls back to the default, the way `keypad_preset`
  does in `AppState.__init__`.

## Colors

### Color sets
- Today all colors live in `src/tcalc/config.toml` under `[theme.colors]`. That
  set becomes the **Dark** set unchanged.
- A **Light** set is added with exactly the same keys. The user wants the
  values written by hand, derived from the existing dark values (not taken from
  an external palette).
- **First iteration of Light changes only:** backgrounds, text, borders,
  selection, icon and status colors. The keypad button families (`primary*`,
  `secondary*`, `accent*`, `action*`) keep their dark values for now. If the
  colored buttons look bad on a light background, finding lighter values for
  them is a later step, not this spec.
- **Status colors** (`status_warn`, `status_error`, `status_info`,
  `status_success`) get Light values readable on a light background; the dark
  ones are pale tones picked for a dark background. *(Writer's call.)*
- **Button colors used outside keypads (user's decision: remap).** The button
  families are also referenced, through `src/tcalc/ui/config.toml`, by non-keypad
  UI: option-group checked/hover state (`[style.option_group]`), custom pad
  separators, toolbar separator, add-key button and spin box
  (`[keypad.custom.colors]`), the fraction toggle background and icon tint
  (`frac_*`), top bar memory buttons (`memory_*`), and the display's
  `disabled_text`. These must follow the theme: remap them to keys whose Light
  values change (background/border/text/selection family, or new keys) so
  Light shows no dark separators, dark highlights or pale-yellow icon. Keypad
  key colors themselves (`key_*`, `operator_*`, `action_*`, `equals_*`,
  `trig_*`, `function_*`, `power_*`, ...) stay on the button families. The
  builder decides the exact mapping per entry.
- `[theme.spacing]` and `[theme.fonts]` are shared by both themes.
- Colors the user picked for custom pad keys (stored as hex in QSettings) are
  never changed by a theme switch.

### Single source of truth
- Every place that currently reads `get_theme().colors` must read the active
  set, so that switching changes what all of them see. Nothing may cache a
  color across a theme switch.

## Icons

Agreed approach (see also the bundled icon notes in `assets/icons/README.md`):

- **Single-color icons** (Breeze icons that only use `ColorScheme-Text`, the
  project's own icons, Material `calculate`) are tinted at load time in
  `get_icon` (`src/tcalc/ui/utils.py`) with a theme color, using the existing
  Qt-based `_apply_tint` (QPainter `CompositionMode_SourceIn`). Which theme key
  is the icon color is left to the builder (a new key such as `icon` is fine).
- **Multi-color icons** get separate light and dark files. Today that is
  `snap-angle-symbolic` (Angle Buttons) and `application-exit` (red plus a
  `ColorScheme-Text` white part that would vanish on light; *writer's call*).
  Light files come from Breeze's `breeze` (light) theme, never drawn by hand.
  - `snap-angle-symbolic` light version (user approved): take Breeze light's
    `snap-angle-symbolic.svg` and apply the same style-only tweak as the dark
    one: 1px stroke added, accent recolored to a grey that fits Light (use the
    Light set's secondary text value). Path data untouched; diff the paths
    against the original and mark it "modified" in `assets/icons/README.md`.
  - `application-exit` light version: Breeze light's file, unmodified; its red
    part stays red.
- **Red icons** (`edit-delete`, `edit-delete-shred`) are single-color red, stay
  as they are in both themes and are not tinted.
- The window icon (`accessories-calculator`, multi-color app icon) is not
  tinted and stays the same in both themes.
- Icons already shown (menu actions, toolbar and keypad `IconButton`s, the
  result area's fraction icon) must refresh on a theme switch.
- Explicitly rejected by the user: recoloring icons by rewriting SVG text at
  load time.

## Where styles are applied today

Styles are applied once, when each widget is built. These are the places that
read theme colors and therefore need to re-apply on a switch:

| Place | What it sets |
|---|---|
| `ui/styles.py` `apply_styles` (from `ui/app.py`) | Fusion style, app `QPalette`, app-wide `common.qss` |
| `ui/manubar/style.py` `apply_menu_styles` | menu bar QSS |
| `ui/widgets/calc/topbar/style.py` `apply_topbar_style` | top bar QSS |
| `ui/widgets/calc/display/style.py` `apply_display_style` | display palette + QSS |
| `ui/widgets/calc/display/result/style.py` `apply_style` | result palette + QSS |
| `ui/widgets/calc/display/result/result.py` | fraction icon tint |
| `ui/widgets/history/style.py` `apply_history_style` | history palette/QSS |
| `ui/widgets/keypad/style.py` `apply_keypad_style` (keypad.py, custom_pad.py) | keypad QSS |
| `ui/widgets/side_panel/side_panel.py` | side panel palette |
| `ui/widgets/common/button.py` | a key's text color; `IconButton` icons |
| `ui/widgets/common/toaster.py` | toast colors (read when shown, likely fine) |
| `ui/widgets/common/constants_menu.py` | constant menu text color |
| `ui/widgets/keypad/custom_pad.py` | color picker list built from theme colors |

The builder may find more; the table is a starting point, not a contract.

## How the switch reaches widgets

Central management (user requirement): style modules gain no theme code.
- **State:** the user's choice (`light` / `dark` / `system`) lives in
  `AppState` (`app_state.py`), persisted in QSettings. Qt is not used to hold
  it: `QStyleHints.setColorScheme` is only a request to the platform theme and
  was verified to be ignored on WSLg (scheme stays `Unknown`, no signal), so it
  cannot be relied on. The OS scheme is read from
  `QStyleHints.colorScheme()` and followed via `colorSchemeChanged`.
- **One module owns switching** (e.g. `ui/theming.py`): resolve the variant,
  load that color set, set the app palette and app stylesheet, then walk
  `QApplication.allWidgets()` and re-run each widget's existing style function,
  looked up in one table in that module (widget class -> style function, e.g.
  `Keypad -> apply_keypad_style`). The existing `apply_*_style` functions are
  called as they are.
- **Inline colors:** where a widget computes a color inside its `__init__`
  (side panel palette, `IconButton` icon, math-rendered `KeyButton` icon,
  result fraction icon tint), that code is moved into a small function so the
  table can call it. Moving only; no theme logic is added there.
- `QAction` icons (menus) are not widgets; the module refreshes them too
  (e.g. by the icon name stored on the action).

Further constraints:
- No widget is rebuilt or recreated just to restyle it, and app state
  (expression, history, layout, docks) is untouched by a switch.
- Code style follows the repo: small, DRY, no special cases per icon name in
  `get_icon` beyond the tint/no-tint rule above.
- Prefer Qt's own APIs and recommended patterns over hand-rolled mechanisms;
  write no code Qt already provides (user requirement).

## Menu wiring

- Built from `VIEW_ACTIONS` in `ui/manubar/defins.py` with the existing
  `SubmenuItem` / `MenuActionItem` / `MenuSeparatorItem` types, the same way
  Keypad Preset is. Check-state syncing can mirror how `ViewMenu` syncs preset
  checks (`ui/manubar/menus/view.py`).
- Menu icons for the theme entries are optional; if used, they must come from
  an existing icon set, unmodified.

## Runtime cost (user requirement)

Theme colors must cost nothing at runtime beyond what the current build-time
styling costs:
- Only the **active** color set lives in memory. At startup only that set is
  read from `config.toml`; the other set is never loaded or kept alongside.
- On a switch, the new set is read then and replaces the old one (the old
  dict is dropped). No cache of both sets, no pre-rendered icons for the
  inactive theme.
- Restyling happens only on a switch, by re-running the same style functions
  that run at widget build time. Icons are re-tinted once per switch.
- Between switches there is no extra work: no polling, no per-paint color
  lookups beyond today's. System Default reacts only to
  `QStyleHints.colorSchemeChanged`.

## Goals
- Light, Dark and System Default all work and switch live.
- System Default follows OS changes while running, event driven.
- Choice persists.

## Non-goals
- Custom themes (only the disabled menu entry exists).
- Lighter colors for the colored keypad buttons (later, if needed).
- Changing fonts or spacing per theme.

## Anti-goals (would count as failure even if it "works")
- Needing a restart to see the new theme.
- Polling the OS theme.
- Hand-drawn or path-edited SVGs, or SVG text rewriting to recolor icons.
- Half-switched UI: any visible part still in the old theme after a switch.
- Losing user state (expression, history, layout) on a switch.

## Testing
- Unit tests in the style of `tests/py/unit/ui/` (pytest-qt, offscreen):
  switching sets the app palette and QSS from the new set, the setting
  persists, System Default maps OS Light/Dark/Unknown correctly and reacts to
  `colorSchemeChanged`, single-color icons get the theme tint, red and window
  icons do not, `snap-angle-symbolic` uses the right file per theme.
- Manual check by the user on WSLg with `make dev`.

## Left to the builder
- The concrete Light values (within the rules above), and the icon color key.
- How the active set is stored in `config.toml` (e.g. `[theme.dark.colors]` /
  `[theme.light.colors]`) and how `Theme` / `get_theme()` expose it.
- The exact table entries and how menu action icons are found for refresh.
- File naming for the light/dark variants of multi-color icons.
