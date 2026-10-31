# Changelog

All notable changes to TCalc are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow the scheme in [docs/release.md](docs/release.md).

## [0.13.2](https://github.com/0x74h51N/TCalc/compare/v0.13.1...v0.13.2) - 2026-10-29

Colors and icons no longer depend on the desktop TCalc runs on, and the install script works on Ubuntu and macOS. TCalc now needs Python 3.14.

### Changed

- TCalc needs Python 3.14 and PySide6 6.12, and every dependency is pinned to a tested minor version (#93)

### Fixed

- Parts of the dark UI no longer take light colors from the operating system's color scheme (#89)
- The dependency install script works on Ubuntu and macOS: it installs the missing packages (ninja, venv, the xcb cursor library Qt needs), checks the Python version and no longer reinstalls Boost on every run (#88)
- Menu and button icons are no longer blank outside KDE (GNOME, WSLg, macOS, Windows), since every icon now ships with the app (#90)
- Docks can be dragged again; a fresh install could pick PySide6 6.10.2, which broke dragging (#93)

## [0.13.1](https://github.com/0x74h51N/TCalc/compare/v0.13.0...v0.13.1) - 2026-09-07

A fix for how the Flat history view writes scripts.

### Fixed

- The Flat history view keeps a script's braces, so `2^{n+1}5` and `log_{2}4` no longer read as `2^n + 15` and `log_24` (#87)

## [0.13.0](https://github.com/0x74h51N/TCalc/compare/v0.12.2...v0.13.0) - 2026-09-05

Logarithms take any base.

### Added

- Logarithms in any base, written `log_{2} 8`, exact where an exact answer exists (`log_{2}8` is 3) (#86)

### Removed

- The `\log{b}{x}` form, which ignored its base, is gone; write `log_{b} x` (#86)

## [0.12.2](https://github.com/0x74h51N/TCalc/compare/v0.12.1...v0.12.2) - 2026-08-28

`exp` and the inverses of logarithms give exact answers.

### Fixed

- `exp(ln 2)` is exactly 2, and `exp` of a BigReal keeps its full precision (#84)
- `e^{ln(56)}`, `10^{log n}` and `exp(ln(5))` give back their argument exactly instead of values such as `56.00000000000001` (#85)

## [0.12.1](https://github.com/0x74h51N/TCalc/compare/v0.12.0...v0.12.1) - 2026-08-25

Fixes for BigReal values that should be whole numbers, and for how lists and points are shown.

### Changed

- `mod` in a sum is up to 2.5 times faster when it divides exactly (`Σ mod(n, 1)` to $10^5$: 651 ms instead of 1613 ms) (#82)

### Fixed

- `mod` and `intdiv` are right when a division comes out exact (`mod(93, 3)` is 0, not 3), and `trunc`, `floor`, `ceil`, `root` and `gamma` no longer miss by one on such values (#82)
- Lists and points show their items as plain numbers (`[2, 9e+400]`, `[i, 2]`) instead of debug text such as `BigReal("2")` (#83)

## [0.12.0](https://github.com/0x74h51N/TCalc/compare/v0.11.0...v0.12.0) - 2026-08-20

Sums and products (Σ, Π), many of them answered in closed form instead of term by term. Evaluation moves entirely into the native core and gets several times faster, and trigonometric functions give exact answers at exact angles.

### Added

- Sums (Σ) and products (Π) over a variable and a range: a polynomial sum to a million is answered in under a millisecond, and a heavy body stops after half a second instead of freezing the app (#75)
- Geometric sums and products, sums of a single sin or cos term, and bodies that divide exactly (`n^2/n`) are answered directly instead of term by term (#76)
- Sums and products whose bodies hold constants such as π (`π n^2`, `π^n`) are answered directly, and bodies whose constants cancel stay exact (#78)
- Periodic trigonometric sums of any degree are exact and fast (`Σ sin(π n^2)` to a million: 0.14 ms instead of 38 s) (#80)

### Changed

- Evaluation runs entirely in the native core and is 5 to 15 times faster (#71)
- A variable assigned in one row stays defined for later rows (`A = 10`, then `A * 2`) (#71)
- A script of a script sits above its base, and each script level uses a smaller font, at any font size (#73)
- Building from source checks for Boost 1.83 or newer (#81)

### Fixed

- Multiplying very small exact decimals (`0.0000000001 * 0.0000000001`) no longer returns a wrong fraction (#71)
- `ln(-1)`, `log(-1)`, `acosh(0.5)` and `atanh(1.5)` give their complex results instead of wrong values (#71)
- Products, quotients and powers too small for a double switch to BigReal instead of collapsing to 0 (#71)
- Exponents and subscripts no longer vanish when a long expression scrolls sideways (#73)
- Exact results past $2^{53}$ keep all their digits on screen (`10^{16}+1` no longer shows as `10^{16}`) (#74)
- Trigonometric functions at exact angles give exact answers: `sin(π)` is 0, `sin(30°)` is 1/2, and `tan(90°)` is undefined instead of a huge number (#79)

## [0.11.0](https://github.com/0x74h51N/TCalc/compare/v0.10.1...v0.11.0) - 2026-07-11

Variables, named constants with a Constants menu, subscripts, and a View menu where Simple and Science become keypad presets. One history is shared by all presets.

### Added

- An expression can assign a value to a single-letter variable (`a = 5`), and letters side by side multiply (`ab` is `a·b`); the `=` key still evaluates the row (#60)
- Named mathematical, physical and chemical constants (CODATA 2022), typed by name or picked from a new Constants menu grouped by category (#61)
- A custom pad key can hold a constant (#61)
- A View menu holds the keypad, dock, history and layout controls, and Simple and Science are keypad presets instead of modes (#64)
- Keypad presets arrange the docks, and the current layout can be saved as a custom preset to apply, rename, update or delete (#65)
- The angle unit row can be shown or hidden from the View menu (Ctrl+O) (#65)
- A subscripted name such as `n_{2}` is a variable that can be assigned (#66)
- Subscripts render in the editor and history, and exponents keep a fixed offset from tall bases such as fractions and parentheses (#68)
- Constants with subscripted symbols (σ_SB, b_W, R_K, K_J, μ_B, μ_N) render as real subscripts in the editor, history, keys and Constants menu, and Rydberg is written R_∞ (#70)
- A constant typed alone is named in the status line (#70)

### Changed

- **Breaking:** One history is shared instead of one per mode, so the per-mode history saved by earlier versions is no longer shown (#64)
- A power is written `a^{b}`, and pressing `^` or pasting `3^4` builds one (#66)

### Fixed

- A result with thousands separators no longer turns into a list when it is reused with Enter or recalled from memory (#62)
- Storing a list or point in memory no longer nearly crashes the app; memory says it holds numbers only (#63)
- An unclosed brace such as `\frac{1` no longer drops what was typed inside it (#67)

## [0.10.1](https://github.com/0x74h51N/TCalc/compare/v0.10.0...v0.10.1) - 2026-06-19

A fix for a freeze when a result is edited again.

### Fixed

- The app no longer freezes when a huge exponent result is edited again (#59)

## [0.10.0](https://github.com/0x74h51N/TCalc/compare/v0.9.1...v0.10.0) - 2026-06-19

Lists and points, statistics over a list, and functions that take several arguments.

### Added

- Lists in square brackets `[1, 2, 3]` and points in parentheses `(1, 2)` are evaluated as collections (#50)
- A comma key enters collection elements, a collection result shows in the result line, and a status line shows a live `N element list` hint or a short error (#54)
- Statistics over a list: mean, median, min, max, sum, and sample and population variance and standard deviation (`mean[1, 2, 3]`) (#55)
- Functions take several arguments in their parentheses (`gcd(12, 18)`, `mean(1, 2, 3)`) (#56)

### Changed

- A Math Error or Invalid result shows its reason in the status line (#56)

### Removed

- `mod`, `intdiv`, `nCr` and `nPr` are no longer infix operators; write `mod(a, b)`, `intdiv(a, b)`, `nCr(n, r)` and `nPr(n, r)` (#56)

## [0.9.1](https://github.com/0x74h51N/TCalc/compare/v0.9.0...v0.9.1) - 2026-05-20

Two fixes in the expression editor.

### Fixed

- Parentheses around tall math no longer touch what is above and below them (#48)
- Pressing Delete in the editor no longer crashes the app, and the editor keeps its scroll position after an expression is restored (#49)

## [0.9.0](https://github.com/0x74h51N/TCalc/compare/v0.8.0...v0.9.0) - 2026-05-12

History opens many times faster, because its items are painted instead of built from widgets. Custom pad toolbars collapse.

### Added

- Custom pad toolbars collapse to save space, and a custom pad has a Save button (#47)

### Changed

- History with 150 items shows in 61 ms instead of 1.9 s (math view: 81 ms instead of 2.3 s), because items are painted and the newest load first (#40, #41)
- History in math view shows a third faster (150 items: 45 ms instead of 69 ms to first paint) (#42)

### Fixed

- A dock that is tabbed with another dock no longer gets its menu check and its visibility out of sync (#46)

## [0.8.0](https://github.com/0x74h51N/TCalc/compare/v0.7.2...v0.8.0) - 2026-04-10

Exact arithmetic: integers, decimals and fractions stay exact rational numbers as long as the answer is exact.

### Added

- Exact fractions: integers and decimals stay exact rational numbers, and a button switches a result between fraction and decimal view, its icon showing the view it switches to (#34, #36)
- The gcd and lcm functions (#34)
- Powers and roots of fractions stay exact when the answer is exact, and fall back to high precision when it is not (#35)

### Changed

- Adding a calculation to a long history no longer lags, and resizing the side panel no longer flickers (#37)

## [0.7.2](https://github.com/0x74h51N/TCalc/compare/v0.7.1...v0.7.2) - 2026-04-03

Math in the editor lines up with the text around it and keeps the cursor steady.

### Changed

- The editor scrolls smoothly to follow the cursor (#33)

### Fixed

- Powers and roots line up with the text around them (#32)
- Up and down move into nested fractions and powers (#33)
- Math no longer flickers while it realigns (#33)
- A restored expression puts the cursor at its end (#33)

## [0.7.1](https://github.com/0x74h51N/TCalc/compare/v0.7.0...v0.7.1) - 2026-03-31

Moving and editing inside a math expression lands where it should.

### Fixed

- Moving the cursor left, right, up and down through fractions, powers and roots lands where expected, and backspace before an operator removes its spaces (#31)
- Exponents and root degrees sit in the right place, and removing a math node no longer leaves wrong margins behind (#31)

## [0.7.0](https://github.com/0x74h51N/TCalc/compare/v0.6.3...v0.7.0) - 2026-03-30

A new history panel that can show rendered math, a dock layout, a keypad split into panels, and custom pads of your own.

### Added

- History items show the expression and the result on separate lines, with copy and remove buttons, striped rows and a Math, Flat and Raw view (#21)
- History can show its items as rendered math, laid out like the editor, with long expressions wrapped (#23)
- A root with no degree is a square root (#24)
- The keypad and the history are docks that can be moved, floated and toggled from the menu or with a shortcut (#26)
- The keypad is split into number, function and trig and power pads, each a dock of its own that can be shown or hidden (#29)
- Custom pads: make as many keypads of your own as you like, put operations on their keys, arrange them on a grid, and rename, recolor or remove them (#29)

### Changed

- **Breaking:** History is stored in a new binary file, so the history saved by earlier versions is no longer shown (#21)

### Fixed

- A BigReal value that turns complex keeps its full precision instead of being rounded to a double first (#20)
- Undo and redo no longer step past the first or the last history entry (#21)
- A long expression no longer overflows its history row (#21)
- A root shows its radicand and degree in the right order in the Flat history view (#24)
- Inserting a fraction after a number puts the cursor in the denominator instead of the numerator (#25)
- The part after a function in parentheses, as in `\frac{1}{2}+sin(69)`, no longer disappears from the editor (#28)

## [0.6.3](https://github.com/0x74h51N/TCalc/compare/v0.6.2...v0.6.3) - 2026-03-06

Fixes for deleting parentheses and math in the editor.

### Fixed

- Deleting an unclosed parenthesis keeps the text after it and the cursor in place, and backspace removes the whole space around an operator (#16)
- Deleting a fraction, power or root inside parentheses keeps its content and leaves the cursor where it was (#17)

## [0.6.2](https://github.com/0x74h51N/TCalc/compare/v0.6.1...v0.6.2) - 2026-03-02

Fixes for parentheses around rendered math.

### Fixed

- An opening parenthesis typed in the middle of a line wraps the fraction or power after it, and a closing parenthesis before one splits the text correctly (#12)
- Opening, closing and deleting parentheses around rendered math no longer misplaces the text or the cursor (#13)
- Nested parentheses around math render in the right order (#14)

## [0.6.1](https://github.com/0x74h51N/TCalc/compare/v0.6.0...v0.6.1) - 2026-02-27

Faster expression editing, fixes for spaces and parentheses, and a license change to the GNU GPL 3.0.

### Changed

- Rendering and editing long expressions is about twice as fast (a heavy expression renders in 39 ms instead of 89 ms) (#8)
- TCalc is licensed under the GNU GPL 3.0 instead of MIT (#10)
- Error logs are written only in debug mode (#11)

### Fixed

- Spaces around operators no longer disappear after a backspace or after a parenthesis closes, and a closing parenthesis can be typed anywhere inside its group (#7)
- A `+` typed right before or after a fraction or power no longer turns into a unary plus (#7)

## [0.6.0](https://github.com/0x74h51N/TCalc/compare/v0.5.9...v0.6.0) - 2026-02-21

The expression editor lays out fractions, powers and roots as math, and the rounding functions arrive.

### Added

- Factorial accepts fractional and negative non-integer values through the gamma function (`0.25!`) (142bc79)
- The rounding functions trunc (`int`), floor and ceil, and text names for operators such as `mul`, `div`, `pow`, `root` and `choose` (#6)
- The expression editor lays out fractions, powers and roots as math, LaTeX style, with parentheses drawn around the parts they group (#5)
- Clicking a history item copies it and shows a toast (#5)

### Changed

- Result and keypad fonts use better fitting sizes (8e886a2)
- π, e and numbers in scientific notation stay ordinary double values and only switch to BigReal when they do not fit in one (1ced5f4, 8c161d9)

### Fixed

- Inverse trigonometric functions no longer report an argument error for a valid input (6a07c61)
- A unary plus sign (`+3`, `2*+3`) no longer breaks the expression (12bca0c)
- An operator that is missing its operand reports a malformed expression instead of leaving the display in a stale state (4a39804)

## [0.5.9](https://github.com/0x74h51N/TCalc/compare/v0.5.1...v0.5.9) - 2025-12-26

A native parser reads every expression, complex results keep 50-digit precision, and very large numbers no longer break the display.

### Added

- Complex results keep 50-digit precision with BigComplex numbers, trigonometric functions included (#1)

### Changed

- Expressions are read by a native parser, and parser and evaluation errors say more clearly what went wrong (#1)
- The Clear button also resets the undo position (#1)
- Factorial and gamma switch to BigReal for large results, and `fact` and `gamma` can be typed by name (a1c6c39)

### Fixed

- The negate key works on an empty line, and the live preview shows a result for an expression that ends in `i` (#1)
- A number in scientific notation with a huge exponent no longer crashes the app (4539996)
- A BigReal value far outside the double range no longer gets a complex result by mistake (2931f91)
- Spaces around binary operators in the display no longer disappear (5d98db2)

## [0.5.1](https://github.com/0x74h51N/TCalc/compare/v0.5.0...v0.5.1) - 2025-12-19

No user-visible change: this version adds type annotations and the lint and type check setup.

## [0.5.0](https://github.com/0x74h51N/TCalc/compare/v0.2.0...v0.5.0) - 2025-12-18

A fuller Science mode: inverse and hyperbolic trigonometry, logarithms, roots, factorial, combinatorics, the constants π and e, and 50-digit BigReal numbers for values a double cannot hold.

### Added

- A backspace key on the keypad (52d1496)
- Hyperbolic functions (sinh, cosh, tanh) behind a Hyp toggle, and a Shift toggle for secondary keys (eb133e4)
- A memory slot with its buttons in a top bar, shown in the history panel (eb133e4)
- Inverse and inverse hyperbolic trigonometric functions through Shift, log, ln, modulo and the reciprocal key (44eaa69)
- Numbers too large or too precise for a double are computed with 50-digit BigReal arithmetic instead of overflowing (06e15f8)
- The constants π and e and the imaginary unit i can be used in expressions (06e15f8)
- Cube root, nth root, integer division, factorial, gamma, permutations (nPr) and combinations (nCr) (06e15f8)

### Changed

- TCalc starts with `python -m tcalc` (97386aa)
- A function key opens its parenthesis by itself, and the live preview no longer shows an error for an expression that is still being typed (44eaa69)
- **Breaking:** Each mode keeps its own history, so the history saved by earlier versions is no longer shown (44eaa69)

### Removed

- The AC key is gone (eb133e4)

### Fixed

- The cut, copy and paste shortcuts (Ctrl+X, Ctrl+C, Ctrl+V) are fixed (12f0aca)
- Inverse trigonometric results follow the selected angle unit, and implicit multiplication is read correctly in more places (44eaa69)

## [0.2.0](https://github.com/0x74h51N/TCalc/compare/v0.1.0...v0.2.0) - 2025-12-12

Expressions typed as a whole line, a history panel, an Edit menu and a first Science mode.

### Added

- An expression is typed as a whole line from the keyboard or the keypad and evaluated at once, with scientific notation, powers and square roots (3529d20)
- A history panel lists past calculations, and the Edit menu offers undo, redo, cut, copy and paste (b0d3af9)
- Keyboard shortcuts, menu icons and a backspace action (99b2cd1)
- A first Science mode with sin, cos and tan, complex results and Deg, Rad and Grad angle units (a7f015b)
- History is saved between sessions and can be cleared (a7f015b)
- Keypad keys show a tooltip (a7f015b)

## [0.1.0](https://github.com/0x74h51N/TCalc/tree/v0.1.0) - 2025-12-09

The first version of TCalc.

### Added

- A desktop calculator with a PySide6 window and keypad, whose arithmetic runs in a native C++ core (106e83e)
