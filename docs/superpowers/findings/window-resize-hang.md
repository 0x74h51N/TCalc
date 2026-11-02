# Window resize hang on two screens

## 2026-11-02, branch perf/theme-picture-render (uncommitted)

Setup: KDE Wayland, DP-1 3440x1440 at scale 1, HDMI-A-1 2195x1235 at scale 1.75. The saved geometry restores the window over the whole of DP-1 (3440x1412). Theme Sponge, preset SIMPLE, run through `make dev` (`python -m tcalc --debug` under `entr`).

Seen twice: dragging the window edge froze the app until KWin killed it (`kwin_killer_helper` at 12:51:53, an earlier run ended in SIGABRT at 12:46:39 with a core dump). The terminal printed nothing.

During the freeze (`eu-stack -p <pid>`), on both runs:

- The main thread loops inside the event loop's posted event dispatch: `sendPostedEvents` deletes a `QPropertyAnimation`, its `QObject::destroyed` calls into `libQt6Widgets` and does not return. The top frame is always `libQt6Widgets +0x24c894`; the caller below it varies (`+0x35b3b7`, `+0xf52f2b`). No Python frame is on the stack.
- RSS grows by about 6 MB/s (1.73 GB to 2.0 GB); the pool threads are idle, so no picture render is running.
- `py-spy` 0.4.1 cannot read Python 3.14 (`Failed to find python version from target process`); `eu-stack` works.

Not reproduced (same branch, a copy of the owner's settings, Sponge, history loaded):

- Programmatic `resize()` in 8 steps from 3440x1412 down to 800x600 and back, pumped with `processEvents()`: no hang, RSS 173 to 253 MB. The owner also dragged the window edge during this run without a freeze.
- The same under `app.exec()`, 24 steps driven by a QTimer, with a 100 ms heartbeat: no main-thread gap over 300 ms, RSS 173 to 277 MB.

Open: which animation it is, whether master hangs too, and what the `make dev` run had that the probe did not (`--debug`, a long-running process, interactive resize across both screens).
