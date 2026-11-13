# Findings

One line per findings file: the file, then the subject in a few words. Read this index before analyzing a subject; add a line when a new findings file is created.

- [theme-radius.md](theme-radius.md): why theme corner radii turn square (Qt drops a radius above half the short side), the tooltip's square window and QSS borders that drop the button frame.
- [picture-render.md](picture-render.md): the cost of re-rendering theme pictures when a resize pauses.
- [custom-pad-toolbar.md](custom-pad-toolbar.md): custom pad toolbar spin boxes and theme fonts.
- [ci-runtime.md](ci-runtime.md): CI job durations and how path-based skipping meets the required checks.
- [versioning.md](versioning.md): the version strings setuptools-scm gives in a tagged, untagged, archived and shallow checkout.
- [history-scrollbar.md](history-scrollbar.md): the black groove of a history item's horizontal scrollbar (#97).
- [window-resize-hang.md](window-resize-hang.md): the main window freezing while resized on two screens.
- [typed-config.md](typed-config.md): how config.toml and theme overrides reach the stylesheet and the Python reads (#104).
- [ui-test-isolation.md](ui-test-isolation.md): UI tests that pass in `make py-test` but fail when their file runs alone.
- [python-test-layers.md](python-test-layers.md): which modules load the native module, what the fake `calc_native` is really used for, and the test and mypy baselines (#205).
- [editor-dissolve-cursor.md](editor-dissolve-cursor.md): where Left, Right and Backspace move the cursor through a Math Widget, where it lands after a dissolve, and a failed fix (#184, #219).
- [complex-root.md](complex-root.md): where the complex root noise comes from, and the exactness and cost of pow, Newton, half turns and wider types on the root rows (#223, #225).
- [bigreal-domain.md](bigreal-domain.md): a negative BigReal under sqrt, root, ln and log is a math error instead of a BigComplex, and what works next to it (#226).
- [generated-stubs.md](generated-stubs.md): what `patch_stub` still patches in the `pybind11-stubgen` output, and the `Collection.__hash__` it covers (#108).
