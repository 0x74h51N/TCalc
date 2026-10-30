# Theme switching: status

Where the `feat/theme-switching` work stands: what is done and what is left.
The design is in [2026-10-27-theme-switching-design.md](2026-10-27-theme-switching-design.md),
and the original plan is in [../plans/2026-10-27-theme-switching.md](../plans/2026-10-27-theme-switching.md).

## Done

### Light, Dark, System Default
- View > Theme menu: Light, Dark, System Default, then the custom themes, then "Add Custom Theme..." (a disabled stub).
- Light and dark color sets. Qt holds the color scheme (`QStyleHints.setColorScheme`). System Default follows the OS scheme at startup and whenever it changes.
- The choice persists in `QSettings` (`theme`, `custom_theme`). A bad value or a missing custom theme falls back to System Default.
- One application stylesheet. Widgets follow the palette. A switch only re-polishes; nothing is rebuilt.
- Icons draw for the active theme:
  - Single-color icons are tinted.
  - Multi-color icons use light/dark variant files.
  - Red or colored icons are never tinted.

### Theme files
- Every theme is a TOML file:
  - Light and Dark ship in the package as `src/tcalc/themes/<variant>.toml`.
  - The example custom themes ship in the package too, one folder each: `src/tcalc/themes/<name>/theme.toml` with their own assets.
  - The user's own themes live in TCalc's data folder, `QStandardPaths.AppDataLocation/themes/<name>/` (Linux `~/.local/share/TCalc/themes/`), next to the history. A user theme with a bundled theme's name replaces it.
  - The custom themes in View > Theme are listed each time the menu opens, like the custom pads and presets, so a new theme folder shows up without a restart (its fonts load at startup).
- A custom theme names a `base` and overrides only what differs.
- `src/tcalc/themes/theme-template.toml` documents every key and where a user theme goes.
- `[fonts]` sets:
  - the app font;
  - the keypad key range (`keypad_min_pt`, `keypad_max_pt`);
  - menu items (`menu_size`, px);
  - the searchable picker (`picker_size`, pt).
- `[spacing]` overrides any number from `config.toml`'s style tables by name, for example `btn_radius`.
- `[color_usage]`:
  - `config.toml` names the theme color that every colored place uses: palette roles, icons, display, keys, custom pad, menus, history, tooltips, toasts.
  - A theme can point any place at another of its own colors without adding new colors. Example: `picker_text_color = "text_primary"`.
  - No color is hardcoded outside the theme files. The √ sign used to be hardcoded white; it now uses `radical_symbol_color`.
- Pictures:
  - A theme can put pictures behind the window, display, history, each keypad and custom pads.
  - Each picture is set by its target, position, fit and opacity.
  - While the window is resized, the last image is stretched. It is rendered again once resizing settles (150 ms single-shot `QTimer`).
- Theme fonts in the theme folders are registered with `QFontDatabase` at startup.

### Bundled themes
- **Kitty** (light):
  - Miniver font.
  - Translucent keys.
  - Line-art cats in the display and the history.
- **Retro** (dark): green phosphor CRT, VT323 font, square corners.
- **Sponge** (light):
  - Sponge-yellow display with holes.
  - Sea floor behind the whole window, with the white sky layer removed.
  - Some Time Later font.
- Ocean was dropped.
- Assets are Openclipart (CC0) or OFL fonts, credited in each theme's `CREDITS.txt`.

### Fixes along the way
- Custom pad picker items had the control color (light blue). The keypad rule `QWidget[uiRole="keypad"] QFrame` reached into the picker popup. The rule now targets `QFrame#toolbarSeparator`.
- Dock titles kept the old theme's font after a switch:
  - The cause: QDockWidget saves `QApplication::font("QDockWidgetTitle")` once and paints its native title with it.
  - The fix: every dock gets a `DockTitleBar` (a QLabel with Qt's own float/close buttons).
- The window picture was drawn over the keys after a dock tab switch or a re-dock (Sponge's sea floor):
  - The cause: the picture was a child widget lowered once at startup, and QMainWindow's dock layout lowers a dock below it.
  - The fix: `MainWindow` paints its pictures in its own `paintEvent` through `PicturePainter` (the cache, settle timer and drawing moved out of `PictureLayer`).
- The history picture scrolled with the items and only came back on a resize:
  - The cause: the list scrolls its viewport by moving the viewport's children, the picture layer included.
  - The fix: `PictureLayer` moves itself back to (0, 0) when it is moved. Display, keypads and custom pads never move it, so they pay nothing.
  - Measured on 150 MATH items: a scroll step costs the same as before (3.46 ms against 3.50 ms); Qt already repaints every visible item on each step.
- Docks could not be dragged, and 5 theme tests failed with "Internal C++ object (QMenu) already deleted": both came from PySide6 6.10.2 and are gone on 6.12, now pinned (see [2026-10-28-dependency-pins.md](2026-10-28-dependency-pins.md)). Dock dragging was checked on Fedora; WSL is not retested.
- CI used an unpinned ruff: fixed on `master` (ruff pinned in CI, then every dependency pinned) and merged into this branch.
- The history items and the Clear History button showed the app font size after a switch (and on the first open), until the next resize:
  - The cause: the app stylesheet's re-polish drops every font a widget got from `setFont`, so the side panel's scaled fonts went back to the app font.
  - The fix: `apply_theme` emits `theme_events.applied` right after `setStyleSheet`, inside the same call; `SidePanel` rescales its targets on it, before anything repaints.
- A menu switch applied the theme twice, the first time the wrong one:
  - The cause: right after `setColorScheme`, Qt still reports the old scheme (the change arrives later), and Light and Dark asked the scheme for their variant.
  - The fix: Light and Dark name their own variant; only System Default follows the scheme. Qt's late signal for a theme that is already on changes nothing.

### Performance
- `tests/benchmark/perf/test_theme_switch.py` measures one switch on a full window with 5, 50 and 150 history items. It has no threshold for now.
- Measured on 150 items: about 400 ms, almost all of it the stylesheet re-polish. Any app stylesheet change re-polishes every widget, and 92% of the 2111 widgets are history rows (13 per row). A one-rule stylesheet still costs 264 ms, so the stylesheet's content is not the lever; moving colors to the palette would not help either (91 colors in the qss against about 20 palette roles).
- The way under 100 ms is a history without row widgets (a delegate that measures and paints from the data). It goes on its own branch, and the threshold comes back with it.

## Left

1. "Add Custom Theme..." is still a disabled stub and needs its own spec.
2. Retro: the animated screen-effect idea is not started.
3. The window minimum size bug belongs on a separate branch.
4. Decide whether to drop the `src/tcalc/themes/*/*.png` line from `.gitignore`.
5. Some Time Later font: the ÷ − · glyphs are small.
6. `radius_medium` and `radius_large` are unused.
7. Display, keypads and custom pads still use the `PictureLayer` child widget; it is fine while nothing reorders or scrolls their children.
8. History delegate (own branch): rows painted from the data, no row widgets; brings the theme switch and the history load under 100 ms.
9. Final whole-branch review before merge.
10. Distribution (when packaging starts, not on this branch): a wheel built from `pyproject.toml` does not ship the themes, the template or the icons (measured 2026-10-30: 0 files under `tcalc/themes/` and `tcalc/assets/`, no `calc_native` either), because setuptools has no `package-data` entry, no `MANIFEST.in` and no native build step. A Fedora package or an installer also has to decide where the bundled themes and the template land and that user themes stay in `~/.local/share/TCalc/themes/`.
