# Flatpak

## 2026-10-31: runtimes, Python versions and sizes (read only, nothing built)

- Flathub has `org.kde.Platform` 6.10 and 6.11 and `org.freedesktop.Platform` 25.08 and 26.08 (`flatpak remote-ls flathub --runtime --columns=application,branch`).
- `org.kde.Platform//6.11` is built on `org.freedesktop.Platform` 25.08 (`runtime-version` in `org.kde.Sdk.json.in` of `invent.kde.org/packaging/flatpak-kde-runtime`, branch `qt6.11`). Freedesktop 25.08 ships Python 3.13 (`v3.13.18` in `elements/include/python3.yml`, branch `release/25.08`); freedesktop 26.08 ships Python 3.14 (`v3.14.9`). TCalc requires Python >= 3.14, so the KDE 6.11 runtime's Python is too old.
- `io.qt.PySide.BaseApp` 6.11 builds PySide6 6.11.2 from source against the runtime's Qt and the runtime's `python3` (manifest `io.qt.PySide.BaseApp.yaml`, branch `branch/6.11`), so it carries Python 3.13 too. It is based on `io.qt.qtwebengine.BaseApp`; its download is 346.5 MB (`flatpak remote-ls flathub --all --columns=application,branch,download-size`). Its `cleanup.sh` removes WebEngine when `BASEAPP_REMOVE_WEBENGINE` is set.
- Runtime downloads: `org.kde.Platform//6.11` 414.5 MB (1.1 GB installed), `org.freedesktop.Platform//26.08` 282.7 MB (724.2 MB installed); shared between apps.

## 2026-10-31: Python 3.13 compatibility (scan only, not run)

- `requires-python = ">=3.14,<3.15"` came from pinning the minor; 3.13 was never tried. No Python 3.13 on the development machine (`/usr/bin` has 3.12 and 3.14).
- `grep -rnE --include='*.py' 'annotationlib|string\.templatelib|compression\.zstd|concurrent\.interpreters|^\s*except [A-Za-z_.]+, [A-Za-z_.]+:' src tests scripts` finds one 3.14-only construct: `src/tcalc/ui/widgets/keypad/custom_pad.py:855`, `except json.JSONDecodeError, TypeError:` (PEP 758), a `SyntaxError` on 3.13.
- 72 of the 88 files under `src/` have `from __future__ import annotations`; in the other 16 a forward reference in an annotation would raise at import on 3.13 (PEP 649 defers them only from 3.14). Only a run on 3.13 shows whether any does.
