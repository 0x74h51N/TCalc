# Theme Pictures Without UI Freezes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Theme pictures are rasterized once per screen in the background, and a resize only scales a ready raster, so no picture ever freezes the UI (issue #102).

**Architecture:** `PicturePainter` keeps one master per picture, rendered by the existing `_render` in a `QRunnable` on `QThreadPool.globalInstance()`, first at an eighth of the size and then in full; the result comes back through a queued signal. `paint` scales the master to the rect with `SmoothTransformation` and caches the copy in the existing `_cache`; the settle timer goes.

**Tech Stack:** Python 3.14, PySide6 6.10 (`QThreadPool`, `QRunnable`, `QImageReader`), pytest with pytest-qt.

**Spec:** `docs/superpowers/specs/2026-11-02-theme-picture-render-design.md`. Measurements: `docs/superpowers/findings/picture-render.md`.

## Global Constraints

- The worker renders through `QImageReader` only (the existing `_render`); `QSvgRenderer` in a worker holds the GIL for the whole render.
- `_render(picture: ThemePicture, size: QSize) -> QImage` keeps its signature; the tests replace it.
- No new file and no new layer: everything is in `src/tcalc/ui/widgets/common/picture_layer.py`. The only new classes are the `QRunnable` and the `QObject` that carries its result signal.
- Master size: the picture's natural size scaled to cover the owner widget's screen size times `picture.size`, `KeepAspectRatioByExpanding`. Low resolution pass: an eighth of the master's width and height.
- No commit without the owner's approval of the diff; every commit step stops for it.
- No em dash anywhere; Markdown is not hard-wrapped.

## Review Focus

- The widget is closed while its render runs (a custom pad removed, the app closed during startup): the late result is dropped, nothing is raised. Test in Task 2.
- The theme is switched while a render of the old theme runs: the old result is never drawn. Test in Task 2.
- The window moves to a screen of another size: the next paint starts a render at the new master size and keeps drawing the old master until it arrives. Test in Task 2.
- A component is resized while only the low resolution version exists: it is drawn stretched into the new rect, no render starts. Test in Task 1 (`test_low_resolution_is_drawn_before_the_full_one`).
- A component smaller than its margins: no job starts. The existing `test_empty_box_is_not_rendered` stays and must pass unchanged.

### Task 1: Masters rendered in the background, paint only scales

**Files:**
- Modify: `src/tcalc/ui/widgets/common/picture_layer.py` (`SETTLE_MS`, `PicturePainter`, `PictureLayer.eventFilter`)
- Modify: `src/tcalc/ui/window.py:78-80` (remove `resizeEvent`, and the `QResizeEvent` import if it becomes unused)
- Test: `tests/py/unit/ui/test_picture_layer.py`

**Interfaces:**
- Produces: `master_size(picture: ThemePicture, screen: QSize) -> QSize` (module level, public, used by Task 2's tests); `LOW_RES_DIVISOR = 8`; `PicturePainter._masters: dict[ThemePicture, tuple[tuple[int, int], QImage]]` (picture to its master key and the latest image for it, low or full); `PicturePainter._pending: set[tuple[ThemePicture, tuple[int, int]]]`; `PicturePainter._on_ready(picture: ThemePicture, key: tuple[int, int], image: QImage) -> None`. `PicturePainter.resized()` is removed.

- [ ] **Step 1: Write the failing tests**

Delete `test_resizing_renders_the_picture_again_only_once_it_settles`. Add, next to the `sponge` fixture: `record_renders(monkeypatch) -> list[tuple[tuple[int, int], int]]`, which wraps `_render` and records `(size.toTuple(), threading.get_ident())` per call; `sponge_window_layer(qtbot, width, height) -> tuple[QWidget, PictureLayer]`, a shown `QWidget` of that size with a `PictureLayer(window, PictureTarget.WINDOW)`; and `window_picture() -> ThemePicture`, the loaded theme's `[p for p in get_theme().pictures if p.target is PictureTarget.WINDOW][0]` (the filter `paint` uses). Then these tests:

```python
@pytest.mark.usefixtures("sponge")
@pytest.mark.parametrize(
    "size, screen, expected",
    [
        param(1.0, QSize(3440, 1440), QSize(3440, 1720), id="full screen cover"),
        param(0.5, QSize(1000, 600), QSize(600, 300), id="half box"),
    ],
)
def test_master_size_covers_the_screen_times_the_picture_size(size, screen, expected):
    # Sponge's window picture is undersea.svg, natural size 600x300
    picture = dataclasses.replace(window_picture(), size=size)
    assert master_size(picture, screen) == expected

@pytest.mark.usefixtures("sponge")
def test_render_runs_off_the_main_thread_and_resizing_only_scales(qtbot, monkeypatch):
    calls = record_renders(monkeypatch)
    window, layer = sponge_window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: len(calls) == 2)  # low resolution, then full
    assert all(thread != threading.get_ident() for _, thread in calls)
    for width in (420, 440, 460):
        window.resize(width, 200)
        layer.grab()
    assert len(calls) == 2
    assert layer._pictures._cache[window_picture()].size() == layer_image_rect(layer).size()

@pytest.mark.usefixtures("sponge")
def test_low_resolution_is_drawn_before_the_full_one(qtbot, monkeypatch):
    full = threading.Event()
    calls = record_renders(monkeypatch, hold_full=full)
    window, layer = sponge_window_layer(qtbot, 400, 200)
    layer.grab()
    qtbot.waitUntil(lambda: window_picture() in layer._pictures._masters)
    key, image = layer._pictures._masters[window_picture()]
    assert image.size() == QSize(key[0] // LOW_RES_DIVISOR, key[1] // LOW_RES_DIVISOR)
    window.resize(460, 200)
    layer.grab()
    assert len(calls) == 2  # the low pass and the held full pass, no new job
    full.set()
    qtbot.waitUntil(lambda: layer._pictures._masters[window_picture()][1].size() == QSize(*key))
```

`record_renders` takes an optional `hold_full: threading.Event`; when given, a call whose size is not the low resolution size waits on it before rendering. `layer_image_rect(layer) -> QRect` is the second value of `picture_rects(window_picture(), layer.rect(), _natural_size(window_picture().file))`.

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=src python -m pytest tests/py/unit/ui/test_picture_layer.py -q`
Expected: the new tests fail (`master_size` is not defined, renders happen on the main thread); `test_empty_box_is_not_rendered`, the rect tests and the scroll test pass.

- [ ] **Step 3: Implement**

In `picture_layer.py`:
- `master_size`: `_natural_size(picture.file).scaled(QSize(int(screen.width() * picture.size), int(screen.height() * picture.size)), Qt.AspectRatioMode.KeepAspectRatioByExpanding)`.
- `_RenderResult(QObject)` with `ready = Signal(object, object, QImage)`, parented to the painter's widget, `ready` connected to `PicturePainter._on_ready`.
- `_RenderJob(QRunnable)` holding the picture, the key and the `_RenderResult`; `run()` emits `ready(picture, key, _render(picture, QSize(key[0] // LOW_RES_DIVISOR, key[1] // LOW_RES_DIVISOR)))`, then `ready(picture, key, _render(picture, QSize(*key)))`.
- `paint`: the key is `master_size(picture, self._widget.screen().size()).toTuple()`. When `_masters` has no entry for the picture or its key differs, start a job unless `(picture, key)` is in `_pending`, and draw what `_masters` holds for the picture, if anything. A full image (its size equals the key) is drawn through `_cache`, scaled again with `image.scaled(rect.size(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)` only when `_cache[picture].size() != rect.size()` (the rect already has the fit's aspect, so `stretch` needs nothing else); a low one through `painter.drawImage(rect, image)`. After the loop, `_cache`, `_masters` and `_pending` keep only the entries of this paint's pictures, so a result for a picture of the previous theme finds no pending entry and is dropped.
- `_on_ready`: drop the image unless `(picture, key)` is in `_pending`; store it in `_masters`; remove the key from `_pending` when the image is full; `self._widget.update()`.
- Remove `SETTLE_MS`, `_settle`, `resized()`; `PictureLayer.eventFilter` only sets the geometry. In `window.py`, remove `resizeEvent`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/py/unit/ui/test_picture_layer.py -q`
Expected: all pass.

- [ ] **Step 5: Check the rest and look at the app**

Run: `grep -rn "SETTLE_MS\|\.resized()" src tests`, expected: no picture-related hit (the keypad's own `KEY_SETTLE_MS` in `test_theme_switch.py` is unrelated). Run `make typecheck` and `make py-lint`, expected: clean. Run the app with Sponge and Kitty (`PYTHONPATH=src python -m tcalc`) and give it to the owner to look at a drag, a full screen switch and a theme switch.

- [ ] **Step 6: Commit (after the owner approves the diff)**

```bash
git add src/tcalc/ui/widgets/common/picture_layer.py src/tcalc/ui/window.py tests/py/unit/ui/test_picture_layer.py
git commit -m "perf/theme: render theme pictures once in the background and only scale them on resize"
```

### Task 2: Late, stale and screen-changed results

**Files:**
- Modify: `src/tcalc/ui/widgets/common/picture_layer.py` (`_RenderJob.run`, only if Step 2 shows the closed-widget test failing)
- Test: `tests/py/unit/ui/test_picture_layer.py`

**Interfaces:**
- Consumes: `master_size`, `PicturePainter._masters`, `_pending`, `_on_ready` from Task 1.

- [ ] **Step 1: Write the failing tests**

All three hold the full-size render on a `threading.Event`, like Task 1's low resolution test.

- `test_result_of_the_previous_theme_is_never_drawn`: Sponge, first grab, switch with `load_theme("kitty")`, grab again, release the event, wait for the pool (`QThreadPool.globalInstance().waitForDone()` then `qtbot.wait(50)`), grab; assert every key of `layer._pictures._masters` is a Kitty picture.
- `test_widget_closed_while_rendering_raises_nothing`: first grab, `window.close(); window.deleteLater(); qtbot.wait(10)`, release, wait for the pool; inside `with qtbot.captureExceptions() as exceptions:`, assert `not exceptions`.
- `test_screen_of_another_size_renders_a_new_master`: after the full master arrives, monkeypatch `picture_layer.master_size` to return a larger size, grab; assert a third and fourth `_render` call at the new key, and that the grab between them still drew the old master (`_masters[picture][0]` is the old key until the new low result arrives).

- [ ] **Step 2: Run them to verify which fail**

Run: `PYTHONPATH=src python -m pytest tests/py/unit/ui/test_picture_layer.py -q`
Expected: report each test's result. A test that passes on Task 1's code already proves the behavior; it stays and gets no code. The closed-widget one is expected to fail with `RuntimeError: Internal C++ object (_RenderResult) already deleted` raised from the worker's `emit`.

- [ ] **Step 3: Fix only what failed**

For the closed widget: in `_RenderJob.run`, the `emit` is wrapped in `except RuntimeError` with the comment `# The widget closed while its render ran (a removed pad, the app closed at startup)`, and the job returns. Nothing else is guarded.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=src python -m pytest tests/py/unit/ui/test_picture_layer.py -q`
Expected: all pass.

- [ ] **Step 5: Commit (after the owner approves the diff)**

```bash
git add src/tcalc/ui/widgets/common/picture_layer.py tests/py/unit/ui/test_picture_layer.py
git commit -m "perf/theme: drop picture renders that come back late or for an old theme"
```

### Task 3: Acceptance numbers

**Files:**
- Modify: `docs/superpowers/findings/picture-render.md`

- [ ] **Step 1: Run the resize probe on the branch**

The probe is in the findings (`resize_probe.py`). Run, from the repository root:

```bash
for t in sponge dark; do for p in SIMPLE SCIENCE; do QT_QPA_PLATFORM=offscreen PYTHONPATH=src python resize_probe.py $t $p 1000; done; done
for t in sponge dark; do for p in SIMPLE SCIENCE; do PYTHONPATH=src python resize_probe.py $t $p 1400; done; done
```

Expected: report the numbers as measured; `_render` calls on the main thread are 0 with the change (the profile only sees the main thread).

- [ ] **Step 2: Measure startup and theme switch**

Extend the probe in the findings with a loop that, from `MainWindow()` until both masters of every picture are in, and again around `apply_theme(app, "sponge")` from Dark, records the longest gap between `processEvents` returns. Report the two numbers for offscreen and Wayland.

- [ ] **Step 3: Record**

Add an entry with today's date, the branch and commit, the commands and the numbers to `docs/superpowers/findings/picture-render.md`, next to the master numbers already there.

- [ ] **Step 4: Run the whole suite**

Run: `make py-test`
Expected: every suite passes.

- [ ] **Step 5: Commit (after the owner approves the diff)**

```bash
git add docs/superpowers/findings/picture-render.md
git commit -m "docs/findings: picture render numbers with background masters"
```
