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
- **Light changes every color**, the keypad button families (`primary*`,
  `secondary*`, `accent*`, `action*`) included. *(First the user kept the
  keypad families dark; after seeing them on Light they asked for light
  versions, 2026-10-27.)*
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
- **Alpha colors are fixed values per theme (user decision).** Colors that are
  today computed in Python from a `[base, alpha]` pair (`rgba()` in
  `ui/utils.py`, the loops in the `style.py` modules, the toast's
  `_TOAST_ALPHA`) become plain entries in each color set, written as QSS
  `rgba(r, g, b, a%)` (the QSS reference documents `#rrggbb` and `rgba()`, not
  `#AARRGGBB`). Dark values equal what the pairs produce today; Light values
  are written by hand. The `[base, alpha]` tables and the alpha helpers are
  deleted. QSS templates name theme keys directly; the indirection tables in
  `ui/config.toml` that only map a style key to a theme key are removed too.
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
  project's own icons, Material `calculate`) are tinted with the theme's `icon`
  color, using the existing Qt-based `_apply_tint` (QPainter
  `CompositionMode_SourceIn`).
- **Icons are drawn for the active theme at paint time.** `get_icon` returns a
  `QIcon` backed by a `QIconEngine` (Qt's extension point for icon rendering)
  that builds the icon from the active theme (file variant + tint) and rebuilds
  it only when the theme changed since its last paint. Widgets repaint after
  the palette change, so every icon already shown follows a switch with no
  refresh code in widgets.
- **Multi-color icons** get separate light and dark files. Today that is only
  `snap-angle-symbolic` (Angle Buttons). Light files come from Breeze's
  `breeze` (light) theme, never drawn by hand.
  - `snap-angle-symbolic` light version (user approved): take Breeze light's
    `snap-angle-symbolic.svg` and apply the same style-only tweak as the dark
    one: 1px stroke added, accent recolored to a grey that fits Light (use the
    Light set's secondary text value). Path data untouched; diff the paths
    against the original and mark it "modified" in `assets/icons/README.md`.
- **Red icons** (`edit-delete`, `edit-delete-shred`, `application-exit`) stay
  as they are in both themes: one file, not tinted (user decision).
- The window icon (`accessories-calculator`, multi-color app icon) is not
  tinted and stays the same in both themes.
- Icons already shown (menu actions, toolbar and keypad `IconButton`s, the
  result area's fraction icon, constant-menu symbols, math-rendered keypad
  labels such as x² in `secondary_text`) must follow a switch;
  the icon engine above covers them.
- Explicitly rejected by the user: recoloring icons by rewriting SVG text at
  load time.

## Where styles are applied today

Styles are applied once, when each widget is built. These are the places that
read theme colors and therefore need to re-apply on a switch:

| Place | What it sets |
|---|---|
| `ui/styles.py` `init_styles` (once, from `ui/app.py`); `apply_color_scheme` (each switch) | Fusion style and fixed app font once; each switch only sets the app `QPalette` and app stylesheet (replacing the style would reload the platform theme fonts) |
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

Qt's own API first (user requirement); no custom theming framework.
- **State is held by Qt:** Light -> `QStyleHints.setColorScheme(Qt.ColorScheme.Light)`,
  Dark -> `Qt.ColorScheme.Dark`, System Default -> `Qt.ColorScheme.Unknown`
  (Qt's "follow the system").
- **One trigger:** `QStyleHints.colorSchemeChanged` fires both for the user's
  choice and for OS changes under System Default. Its handler reads
  `QStyleHints.colorScheme()` (Light -> Light set, anything else -> Dark set),
  loads that color set and applies it.
- **Persistence only in `AppState`:** the user's choice is saved in QSettings
  and re-requested from Qt at startup; Qt does not persist it.
- **WSLg (resolved):** without a desktop, Qt falls back to the generic platform
  theme, which ignores `setColorScheme`. With the bundled `gtk3` platform
  theme (`QT_QPA_PLATFORMTHEME=gtk3`) the request works and the signal fires
  (verified, Qt 6.12). Set it in `scripts/dev` only when running under WSL;
  never in app code, where it would override real desktops' platform themes.
- **App font is fixed (user decision).** The gtk3 platform theme also hands
  the GTK font to Qt (Adwaita Sans 11 instead of the generic Sans Serif 9),
  which enlarged every text without an explicit size and changed the family
  of the ones with one. `[theme.fonts]` `family_default` / `size_default`
  (Sans Serif, 9) are set with `QApplication.setFont`, so desktop font
  settings don't resize the layout.
- **Applying a set uses Qt's propagation only; widgets hold no theme code.**
  - The app palette (`QApplication.setPalette`) carries the theme to every
    widget (Qt docs: the application palette is the default for all widgets).
    Widgets that today copy a theme color into their own palette (side panel,
    display, result: all `background_dark`) instead use
    `setBackgroundRole(QPalette.ColorRole.Base)` with `Base` = `background_dark`
    in the app palette, so propagation reaches them.
  - All QSS is one **application** stylesheet: `common.qss` plus every
    component `.qss`, substituted from the active color set and set with
    `QApplication.setStyleSheet` at startup and on a switch. Qt re-polishes
    every widget, hidden ones included. No widget sets a color stylesheet of
    its own; the component `style.py` modules keep only non-color widget setup
    (fonts, selection modes) or go away.
  - Qt's styling docs advise against switching themes with style sheets
    because each change re-polishes all widgets. Accepted here (user
    decision): a switch is rare and user-initiated, and the app is already
    styled with QSS throughout.
  - Selectors that today rely on being set on one widget must be scoped so
    they don't leak app-wide (`keypad/style.qss`: bare `QSpinBox`, `QFrame`,
    and `QPushButton[keypadRole]` rules that would also hit the top bar's
    memory buttons). Rules duplicated across files (e.g. `#radicandSlot`)
    are kept once.
  - Icons follow through the icon engine (see Icons).
  - Toasts use `toaster.qss` (today unused; the toast builds an inline sheet
    with Python-computed alpha) through the application stylesheet.

Further constraints:
- No widget is rebuilt or recreated just to restyle it, and app state
  (expression, history, layout, docks) is untouched by a switch.
- Code style follows the repo: small, DRY, no special cases per icon name in
  `get_icon` beyond the tint/no-tint rule above. No `Any` in type hints.
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
- Restyling happens only on a switch: one app palette and one app
  stylesheet. Each icon is rebuilt at most once per switch, on its next paint.
- Between switches there is no extra work: no polling, no per-paint color
  lookups beyond today's. System Default reacts only to
  `QStyleHints.colorSchemeChanged`.

## Goals
- Light, Dark and System Default all work and switch live.
- System Default follows OS changes while running, event driven.
- Choice persists.

## Non-goals
- Custom themes (only the disabled menu entry exists).
- Changing fonts or spacing per theme.

## Anti-goals (would count as failure even if it "works")
- Needing a restart to see the new theme.
- Polling the OS theme.
- Hand-drawn or path-edited SVGs, or SVG text rewriting to recolor icons.
- Half-switched UI: any visible part still in the old theme after a switch.
- Losing user state (expression, history, layout) on a switch.

## Testing
- Unit tests in the style of `tests/py/unit/ui/` (pytest-qt, offscreen):
  switching sets the app palette and QSS from the new set, open and hidden
  widgets show the new colors without setting stylesheets of their own,
  shown icons draw in the new tint after a switch, the setting persists, System Default maps OS Light/Dark/Unknown correctly and reacts to
  `colorSchemeChanged`, single-color icons get the theme tint, red and window
  icons do not, `snap-angle-symbolic` uses the right file per theme.
- Manual check by the user on WSLg with `make dev`.

## Left to the builder
- The concrete Light values (within the rules above), and the icon color key.
- How the active set is stored in `config.toml` (e.g. `[theme.dark.colors]` /
  `[theme.light.colors]`) and how `Theme` / `get_theme()` expose it.
- The exact table entries and how menu action icons are found for refresh.
- File naming for the light/dark variants of multi-color icons.

## Experimental: Hello Kitty theme

- `ThemeMode.KITTY` ("Hello Kitty (Experimental)" in View > Theme) loads the `[theme.kitty]` variant; Qt's scheme is Light (`base = "light"`, so variant icon files come from `assets/icons/light/`).
- `apply_theme(app, variant)` replaces the scheme-only switch: Qt's `colorSchemeChanged` maps the scheme to a variant through `ThemeMode.variant(scheme)`, and `set_theme` restyles itself when the scheme does not change (Light <-> Hello Kitty).
- `keypad_image` puts a picture behind the main keypad (`MainKeypad` QSS `background-image`, `WA_StyledBackground`); keypad key colors are translucent so it shows through. The picture is user-supplied at `assets/themes/kitty/keypad.png` (git-ignored, third-party artwork); without it there is no picture.
