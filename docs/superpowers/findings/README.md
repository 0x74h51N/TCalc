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
- [generated-stubs.md](generated-stubs.md): how `patch_stub` was removed, why `CalcValue` drift needs no extra check, and why `ops.pyi` sits beside `ops.py` (#108).
- [native-warnings.md](native-warnings.md): what the native warning flags found, and the Int64 retry path behind `dispatch` (#108).
- [combinatorics.md](combinatorics.md): the nPr and nCr loops against a Gamma closed form, accuracy and time by size (#248).
- [imaginary-range.md](imaginary-range.md): an imaginary literal past double's range, and the Cx arm results no range promotion widens (#239).
- [native-abort.md](native-abort.md): what can end the process (a libstdc++ assertion), and the unchecked int64 conversions next to it, and the native and Python smoke runs (#246, #247, #248, #249).
- [rational-overflow.md](rational-overflow.md): an exact Rational result past int64 retried in double, in Add, Sub, Mul, Div and Pow (#245), and `intdiv` past int64 (#252).
