# Theme picture rendering

## 2026-10-30: a resize that pauses re-renders the theme SVGs, about 120 ms to 340 ms each

`PicturePainter.paint` renders a picture again (`_render`, `QImageReader.read` of the SVG at the new size) once the owner has not been resized for `SETTLE_MS` (150 ms). A drag that pauses longer than that between moves pays a full render of every picture whose box changed. In Sponge the largest is `undersea.svg` (849 KB, target `window`); `holes.svg` covers the display and the history.

Real app, Sponge with `radius_small = 50`, window dragged for a few seconds (cProfile, branch `fix/keypad-key-radius` on 709667e with the key radius change uncommitted):

```
.venv/bin/python -m cProfile -o resize.prof -m tcalc
```

- `QImageReader.read`: 14 calls, 4.76 s, about 340 ms each, all from `picture_layer.py:71(paint)` through `_render`.
- `setStyleSheet` from `apply_key_radius`: 141 calls, 0.33 s. `apply_key_radius`: 0.38 s in all.
- `PictureLayer.eventFilter` shows 17.98 s own time with 0.07 s cumulative and recursion (5848/5820 calls); cProfile misattributes it, it is not a measurement.

Offscreen probe, `MainWindow` with a copy of Sponge and three key grids in docks, 12 resizes of 20x10 px with 200 ms of event processing after each (so the settle timer fires), `-p no:randomly`:

| tree | radius | `_render` calls | `_render` time | busy per step, mean / max |
|---|---|---|---|---|
| master 709667e | 5 | 18 | 2242 ms | 332 / 394 ms |
| master 709667e | 50 | 18 | 2191 ms | 327 / 371 ms |
| key radius fix | 5 | 21 | 2210 ms | 328 / 386 ms |
| key radius fix | 50 | 21 | 2171 ms | 326 / 376 ms |

The stall after a pause is the picture render, on master as well; the key radius fix adds 3 renders (its style change resizes the pads once more) and about 9 ms of `apply_key_radius` with 96 `StyleChange` events at radius 50.

## 2026-11-02: the cost is rasterizing, and it grows with the target's pixels

`undersea.svg` (natural 600x300), offscreen, best of 3, master e0310a8, 16 cores. Probe: a script timing `QImageReader.read` with `setScaledSize`, `QSvgRenderer` construction, `QSvgRenderer.render` into a fresh `QImage`, and `QImage.scaled(..., SmoothTransformation)` from a 3440x1440 render.

| target size | `QImageReader.read` | `QSvgRenderer.render` only | `QImage.scaled` smooth from 3440x1440 |
|---|---|---|---|
| 400x300 | 39 ms | 31 ms | 0.7 ms |
| 1100x700 | 178 ms | 170 ms | 1.1 ms |
| 1920x1080 | 452 ms | 446 ms | 1.8 ms |
| 2560x1440 | 762 ms | 752 ms | 1.7 ms |
| 3440x1440 | 1054 ms | 1030 ms | |

Parsing the file (`QSvgRenderer` construction) is 6 ms; the rest is rasterizing, about linear in the target's pixel count. The worst case is a `window` picture in a maximized window: about 1 s of UI thread per settle on a 3440x1440 screen. Scaling a ready raster to any of these sizes costs 1 to 2 ms.

## 2026-11-02: the SIMPLE preset freezes the same way; dock count is not the cause

Offscreen and on KDE Wayland, `MainWindow` with Sponge and with Dark, SIMPLE and SCIENCE presets, 12 resizes with 200 ms of event processing after each (busy is the time inside `processEvents`):

| platform, size | theme | preset | busy per step, mean / max | `_render` |
|---|---|---|---|---|
| offscreen, about 1200x770 | sponge | SIMPLE | 206 / 233 ms | 24x, 2369 ms |
| offscreen, about 1200x770 | sponge | SCIENCE | 207 / 236 ms | 24x, 2340 ms |
| offscreen, about 1200x770 | dark | SIMPLE | 6.6 / 7.6 ms | none |
| offscreen, about 1200x770 | dark | SCIENCE | 9.8 / 13.0 ms | none |
| wayland, up to 1880x1090 | sponge | SIMPLE | 390 / 477 ms | 24x, 4458 ms |
| wayland, up to 1880x1090 | sponge | SCIENCE | 398 / 477 ms | 24x, 4494 ms |
| wayland, up to 1880x1090 | dark | SIMPLE | 14.2 / 15.7 ms | none |
| wayland, up to 1880x1090 | dark | SCIENCE | 16.9 / 19.0 ms | none |

The owner's real app, Sponge, SIMPLE, history panel open, a few seconds of dragging, resizing and full screen (`PYTHONPATH=src .venv/bin/python -m cProfile -o run.prof -m tcalc`): `_render` 20 calls, 4342 ms, 217 ms per call on average; `paint` 4841 ms in all. Next is the history: `update_fonts` 1960 calls, 704 ms, nearly all of it `re_wrap` (1846 calls, 673 ms). Key radius, resize events and the picture layer's event filter are under 75 ms each.

## 2026-11-02: only `QImageReader.read` frees the main thread when run in a worker

`undersea.svg` at 3440x1440 in a `QRunnable` on `QThreadPool.globalInstance()`, offscreen, PySide6 6.10.2, while the main thread loops on `processEvents`:

| worker code | worker time | longest main-thread gap |
|---|---|---|
| `QImageReader` with `setScaledSize`, `read()` | 1037 ms | 0.3 ms |
| `QSvgRenderer(file).render(QPainter(image))` | 1044 ms | 1024 ms |

PySide6 releases the GIL in `QImageReader.read` but not across `QSvgRenderer.render`, so a background render must go through `QImageReader`; with `QSvgRenderer` the UI freezes for the whole render even off the main thread.

## 2026-11-02: a downscaled screen-size raster looks as good as a direct render

`undersea.svg`, a master read at the size that covers 3440x1440 (3440x1720), then `QImage.scaled(..., IgnoreAspectRatio, SmoothTransformation)` to the target, against `QImageReader.read` at the target size:

| case | target | mean abs diff | 99th percentile | max |
|---|---|---|---|---|
| cover | 160x80 | 2.91 / 255 | 52 | 255 |
| cover | 400x200 | 1.39 / 255 | 40 | 255 |
| cover | 1100x550 | 0.77 / 255 | 18 | 255 |
| stretch | 1000x200 | 1.11 / 255 | 34 | 255 |
| stretch | 300x700 | 1.02 / 255 | 34 | 255 |

The differences sit on shape edges. Side by side at 400x200, the direct render shows hairline seams where shapes meet (the water's edge); the downscaled master does not. A box of any fit is never larger than the cover size of the screen in either axis, so the master is only ever scaled down, `stretch` included.

## 2026-11-02: a tinted render in a worker holds the main thread for a few ms

Kitty's `kitty.svg` (`tint = "accent_text"`) through `_render` at the size that covers 3440x1440 (3440x2523), in a `QRunnable` on `QThreadPool.globalInstance()`, offscreen, three runs: worker 28, 22 and 19 ms, longest main-thread gap 7.9, 2.4 and 2.4 ms. The tint's `QPainter` step keeps the GIL briefly; once per master that is within a frame, so the tint can stay in `_render` in the worker.

## 2026-11-02: a large raster picture costs its decode, at any target size

A progressive JPEG of 8919x6683 (7.2 MB) as Sponge's `window` picture (`fit = "cover"`), offscreen, best of 3:

| target size | `QImageReader.read` | peak RSS of a lone read (app alone: 44 MB) |
|---|---|---|
| 400x300 | 377 ms | 221 MB |
| 1100x700 | 380 ms | |
| 1920x1080 | 398 ms | |
| 3440x1440 | 472 ms | 276 MB (at 3440x2578) |

Unlike an SVG, the cost is decoding the whole file (8919x6683x3 bytes is 179 MB), so it barely depends on the target size, and the low resolution pass is as slow as the full one: the full picture arrives after both, about 850 ms instead of about 470 ms. In a worker the read leaves the main thread free (longest gap 0.3 ms). Same probes as for `undersea.svg`, offscreen:

| | 7963c0d | branch `perf/theme-picture-render` |
|---|---|---|
| resize, busy per step mean / max (1240x806) | 399.1 / 424.9 ms, `_render` 24x 4686 ms | 7.3 / 10.0 ms, no `_render` on the main thread |
| startup longest gap / after a switch to Sponge (1000x650) | 382.8 / 367.7 ms | 15.0 / 3.9 ms |

## The resize probe

The busy time per resize step in the tables above, and the check for #102. Save it as `resize_probe.py` outside the tree and run it from the repository root, offscreen or on the real platform:

```
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python resize_probe.py sponge SIMPLE 1000
PYTHONPATH=src python resize_probe.py sponge SCIENCE 1400
```

On master 7963c0d, offscreen: `sponge SIMPLE` 234.1 ms mean, 283.2 ms max per step, `_render` 24x 2706 ms; `dark SCIENCE` 9.9 ms mean, 13.1 ms max, no `_render`.

<details><summary>resize_probe.py</summary>

```python
# Usage: PYTHONPATH=src python resize_probe.py <theme> <SIMPLE|SCIENCE> <start width>
import cProfile, os, pstats, sys, tempfile, time

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QDockWidget

theme, preset, width = sys.argv[1], sys.argv[2], int(sys.argv[3])
ini = os.path.join(tempfile.mkdtemp(), "probe.ini")
import tcalc.app_state as A
import tcalc.ui.layout_presets as LP
import tcalc.ui.widgets.history.history as H
import tcalc.ui.widgets.keypad.custom_pad as CP
import tcalc.ui.window as W
for mod in (A, W, LP, CP):
    mod.QSettings = lambda *a, **k: QSettings(ini, QSettings.Format.IniFormat)
H.load_history = lambda: []
H.save_history = lambda _i: None
from tcalc.ui.styles import init_styles

app = QApplication([])
init_styles(app, theme)
w = W.MainWindow()
height = width * 13 // 20
w.resize(width, height)
w.show()
w.apply_preset_layout(A.KeypadPreset[preset])
for d in w.findChildren(QDockWidget):
    if d.objectName() == "historyDock":
        d.show()
end = time.perf_counter() + 1.0
while time.perf_counter() < end:
    app.processEvents()

def busy_ms(seconds: float) -> float:
    busy, end = 0.0, time.perf_counter() + seconds
    while time.perf_counter() < end:
        t = time.perf_counter()
        app.processEvents()
        busy += time.perf_counter() - t
        time.sleep(0.001)
    return busy * 1000

prof, steps = cProfile.Profile(), []
prof.enable()
for i in range(1, 13):
    t = time.perf_counter()
    w.resize(width + 2 * i * width // 100, height + 2 * i * height // 100)
    steps.append((time.perf_counter() - t) * 1000 + busy_ms(0.2))
prof.disable()
render = [v for k, v in pstats.Stats(prof).stats.items() if k[2] == "_render"]
calls, render_ms = sum(v[1] for v in render), sum(v[3] for v in render) * 1000
print(f"{os.environ.get('QT_QPA_PLATFORM', 'default')} {w.width()}x{w.height()} {theme} {preset}: "
      f"busy/step mean {sum(steps) / len(steps):.1f} max {max(steps):.1f} ms, _render {calls}x {render_ms:.0f} ms")
sys.stdout.flush()
os._exit(0)
```

</details>

## 2026-11-02: with background masters, resizing costs what Dark costs

Branch `perf/theme-picture-render` (uncommitted change on 7963c0d) against 7963c0d itself, same probes, same commands. Resize probe (`resize_probe.py` below):

| platform, size | theme, preset | 7963c0d busy per step, mean / max | branch busy per step, mean / max | branch `_render` on the main thread |
|---|---|---|---|---|
| offscreen, 1240x806 | sponge SIMPLE | 234.1 / 283.2 ms | 8.2 / 9.5 ms | 0 |
| offscreen, 1240x806 | sponge SCIENCE | | 10.1 / 13.7 ms | 0 |
| offscreen, 1240x806 | dark SIMPLE | | 5.3 / 7.2 ms | 0 |
| offscreen, 1240x806 | dark SCIENCE | 9.9 / 13.1 ms | 6.7 / 9.5 ms | 0 |
| wayland, 1736x1128 | sponge SIMPLE | 433.1 / 519.4 ms | 17.9 / 21.0 ms | 0 |
| wayland, 1736x1128 | sponge SCIENCE | 424.6 / 516.1 ms | 20.6 / 22.8 ms | 0 |
| wayland, 1736x1128 | dark SIMPLE | | 11.4 / 12.9 ms | 0 |
| wayland, 1736x1128 | dark SCIENCE | | 12.8 / 14.4 ms | 0 |

Startup and theme switch (`gap_probe.py` below): the longest main-thread gap from `MainWindow()` through 3 s of events with Sponge, and through 3 s after `apply_theme(app, "sponge")` from Dark.

| platform, size | 7963c0d startup / after switch | branch startup / after switch |
|---|---|---|
| offscreen, 1000x650 | 203.0 / 164.1 ms | 20.7 / 3.5 ms |
| wayland, 1400x910 | 357.5 / 332.8 ms | 19.5 / 4.0 ms |

```
QT_QPA_PLATFORM=offscreen PYTHONPATH=src python gap_probe.py 1000
PYTHONPATH=src python gap_probe.py 1400
```

<details><summary>gap_probe.py</summary>

```python
# Usage: PYTHONPATH=src python gap_probe.py <width>
# Longest main-thread gap from MainWindow() until Sponge's pictures are drawn, and around a
# switch from Dark to Sponge. "Drawn" is 3 s of events: master renders synchronously in paint.
import os, sys, tempfile, time

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QDockWidget

width = int(sys.argv[1])
ini = os.path.join(tempfile.mkdtemp(), "probe.ini")
import tcalc.app_state as A
import tcalc.ui.layout_presets as LP
import tcalc.ui.widgets.history.history as H
import tcalc.ui.widgets.keypad.custom_pad as CP
import tcalc.ui.window as W
for mod in (A, W, LP, CP):
    mod.QSettings = lambda *a, **k: QSettings(ini, QSettings.Format.IniFormat)
H.load_history = lambda: []
H.save_history = lambda _i: None
from tcalc.ui.styles import apply_theme, init_styles

app = QApplication([])

def longest_gap(seconds: float, start: float) -> float:
    gap, last, end = 0.0, start, time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        now = time.perf_counter()
        gap, last = max(gap, now - last), now
    return gap * 1000

t = time.perf_counter()
init_styles(app, "sponge")
w = W.MainWindow()
w.resize(width, width * 13 // 20)
w.show()
for d in w.findChildren(QDockWidget):
    if d.objectName() == "historyDock":
        d.show()
build = (time.perf_counter() - t) * 1000
startup = longest_gap(3.0, time.perf_counter())
apply_theme(app, "dark")
longest_gap(1.0, time.perf_counter())
t = time.perf_counter()
apply_theme(app, "sponge")
switch_call = (time.perf_counter() - t) * 1000
switch = longest_gap(3.0, time.perf_counter())
print(f"{os.environ.get('QT_QPA_PLATFORM', 'default')} {w.width()}x{w.height()}: build {build:.0f} ms, "
      f"startup longest gap {startup:.1f} ms; switch call {switch_call:.0f} ms, after it longest gap {switch:.1f} ms")
sys.stdout.flush()
os._exit(0)
```

</details>
