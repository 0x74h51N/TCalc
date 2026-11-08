# Theme pictures without UI freezes

Issue #102, milestone First release (#22). Measurements: [picture-render.md](../findings/picture-render.md).

## Why

A theme picture is rasterized again on the UI thread every time its component settles at a new size (`PicturePainter.paint` calls `_render` once there has been no resize for `SETTLE_MS`). The cost is rasterizing, linear in the target's pixels: `undersea.svg` takes 170 ms at 1100x700 and about 1 s at 3440x1440. In the human agent's real app (Sponge, SIMPLE preset) a few seconds of dragging spent 4.3 s in 20 renders. The number of docks and keys is not the cause: with Dark, SIMPLE and SCIENCE differ by 3 ms per resize step.

## Goals

- No picture is rasterized from a file on the UI thread, at any window or screen size.
- A resize, a full screen switch or a dock change costs only a scale of a ready raster (1 to 2 ms per picture, measured), so the picture follows the window at once instead of stretching and then jumping.
- Starting the app and switching themes are not delayed by pictures: rendering runs in the background.
- An SVG picture shows within tens of milliseconds as a low resolution version, then the full resolution version replaces it. A raster picture is read once, at full size.
- Every `fit` (`contain`, `cover`, `stretch`) and every picture file type the theme can name works as today.

## Non-goals

- The history's `re_wrap` cost on resize (704 ms in the same profile); it is a separate subject.
- Device pixel ratio: pictures stay rendered in logical pixels, as today.
- Sharing renders between components that use the same file. No bundled theme puts a picture on a target that several components share (only `display`, `history` and `window` are used), so each painter keeps its own master.

## Anti-goals

- A final picture blurrier than today's settled render. The downscaled master measured as good as a direct render, edges included (see the findings).
- Rendering with `QSvgRenderer` in the worker: PySide6 keeps the GIL across `QSvgRenderer.render`, so it froze the main thread for the whole 1 s render; `QImageReader.read` releases it (0.3 ms longest main-thread gap).

## Design

All of it lives in `PicturePainter` (`src/tcalc/ui/widgets/common/picture_layer.py`), which `MainWindow` and every `PictureLayer` (display, history, keypads, custom pads) already use. No new file and no new layer. Two small classes are new, in the same file: the `QRunnable` that runs the job, and a `QObject` with the result signal, because Qt delivers a result from a pool thread to the UI thread only through a signal of an object that lives in the UI thread.

**One master per picture.** A picture is rendered once, at the largest size it can be drawn at on the human agent's screen: its natural size scaled with its own fit into the screen size times `picture.size`. The box is at most `picture.size` of a component that is at most the screen, and scaling with a fit grows with the box, so the drawn size is at most this master in both axes: the master is only ever scaled down. `cover` covers that box (`undersea.svg` on a 3440x1440 screen: 3440x1720, about 24 MB), `contain` fits inside it, `stretch` is the box itself. Scaling every fit to cover, as first planned, rendered Sponge's contained `holes.svg` at 2064x2064 where 864x864 is the most it is drawn at.

**Rendered in the background, in two passes for SVG.** The first paint that needs a master it does not have starts a job on `QThreadPool.globalInstance()` that runs the existing `_render` (`QImageReader` with `setScaledSize`). For an SVG it runs twice: first at an eighth of the master's width and height, then at the full master size. A raster file runs once, at the full size: its cost is the decode, the same at any target size (an 8919x6683 JPEG took 377 to 472 ms either way, see the findings), so a small pass would only delay the full one. Each result goes back to the UI thread through a queued signal; the painter keeps it and calls `update()` on its widget. Until the first result arrives the picture is not drawn. A job is started once per master; paints while it runs do not start another.

**Paint scales, it never renders.** For each picture, `paint` computes the box and image rect with `picture_rects` as today. With a full master, it draws a copy scaled to the rect size with `SmoothTransformation`; the existing `_cache` (one image per picture, the ones not in use dropped after each paint) holds that copy, and it is scaled again only when the rect size changes. With only the low resolution version, it draws that version through the existing `painter.drawImage(rect, image)`, which stretches it. Masters follow the same rule as `_cache`: a master no picture of the current paint uses is dropped. `SETTLE_MS`, the settle timer and `resized()` are removed; `PictureLayer.eventFilter` keeps only its geometry update, and `MainWindow.resizeEvent`, which exists only to call `resized()`, goes. `_render(picture, size)` keeps its signature, since the tests replace it.

**Which master is current.** A master is keyed by the `ThemePicture` and the master size. A theme switch brings new `ThemePicture` values, and a move to a screen of another size changes the master size; either way the next paint finds no master for the current key and starts a job. A result whose key is no longer the current one for its picture is dropped. A result that arrives after its widget is gone is dropped without an error.

**Tint.** `_render` tints with a `QPainter` after reading, and it stays there, in the worker: at 3440x2523 the tint held the main thread for 2.4 to 7.9 ms once per render (see the findings).

## Tests

Behavior, in `tests/py/unit/ui/test_picture_layer.py` (which uses the bundled themes; see the TODO in `tests/py/ui/conftest.py`):

- Resizing a component that has its master does not call `_render`, and the drawn image has the new rect size. This replaces `test_resizing_renders_the_picture_again_only_once_it_settles`.
- `_render` runs off the main thread, and the picture appears after the job finishes.
- The low resolution result of an SVG is drawn before the full one arrives; a raster picture is read once, at full size.
- A result for a picture of the previous theme is dropped after a theme switch.
- `test_empty_box_is_not_rendered` stays.

## Acceptance

The resize probe is kept in the findings as a script to copy and run, so the same measurement runs on master and on the branch (Sponge and Dark, SIMPLE and SCIENCE, 12 resize steps, offscreen and Wayland): busy time per step and `_render` calls on the main thread, plus the longest main-thread gap during startup and a theme switch. The existing `test_theme_switch` benchmark switches between Light and Dark, which have no pictures, and pytest-benchmark measures wall time, which cannot tell the settle wait from a freeze, so it does not cover this. The numbers go in the findings with the command.
