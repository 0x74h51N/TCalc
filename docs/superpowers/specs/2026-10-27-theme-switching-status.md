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
  - Built-ins live in `src/tcalc/themes/`.
  - Custom themes live in `themes/<name>/theme.toml` with their own assets.
- A custom theme names a `base` and overrides only what differs.
- `themes/theme-template.toml` documents every key.
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
  - Coral on the custom pads.
  - Sea floor behind the whole window, with the white sky layer removed.
  - Some Time Later font.
- Ocean was dropped.
- Assets are Openclipart (CC0) or OFL fonts, credited in each theme's `CREDITS.txt`.

### Fixes along the way
- Custom pad picker items had the control color (light blue). The keypad rule `QWidget[uiRole="keypad"] QFrame` reached into the picker popup. The rule now targets `QFrame#toolbarSeparator`.
- Dock titles kept the old theme's font after a switch:
  - The cause: QDockWidget saves `QApplication::font("QDockWidgetTitle")` once and paints its native title with it.
  - The fix: every dock gets a `DockTitleBar` (a QLabel with Qt's own float/close buttons).

## Left

1. **Docks cannot be dragged by the title bar.**
   - In the current WSL environment, a docked dock can't be dragged; with xcb, only the first drag works.
   - This also happens on `master` and on `fix/ubuntu-install-deps`, so the theme code is not proven to be the cause.
   - Plan: install the project fresh on Fedora, test `master` first and then this branch, and bisect if it still happens.
   - Check there whether `DockTitleBar` changes drag behavior. If it does, the alternatives for the dock title font are:
     - leave the native title (its font goes stale after a switch);
     - recreate the docks from `saveState`;
     - find another way to make Qt pick up the new title font.
2. **CI format check fails on this PR.**
   - CI installs ruff unpinned (`pip install ruff` in `.github/workflows/ci.yml`), while `pyproject.toml` pins `ruff==0.15.0`.
   - The newer ruff also formats Python blocks inside Markdown and flags `docs/superpowers/plans/2026-10-27-theme-switching.md`.
   - Local `make py-lint` doesn't show it.
   - To be fixed on its own branch so CI uses the pinned version, merged to `master`, then this branch is rebased.
3. "Add Custom Theme..." is still a disabled stub and needs its own spec.
4. Retro: the animated screen-effect idea is not started.
5. The window minimum size bug belongs on a separate branch.
6. Decide whether to drop the `themes/*/*.png` line from `.gitignore`.
7. Some Time Later font: the ÷ − · glyphs are small.
8. `radius_medium` and `radius_large` are unused.
9. Final whole-branch review before merge.
