# History item scrollbar groove (issue #97)

## 2026-11-02, cause and fix (PR #179)

The `background: transparent` rule on `QScrollArea#historyExprScroll` blacked the groove of a history item's horizontal scrollbar (Math mode). Besides making the viewport transparent, the rule writes a black palette onto the scroll area itself (Base `#ff000000`, Window and Button `#00000000`). Removing it fixes the groove, but then the viewport and the paint canvas fill with Base (`QScrollArea::setWidget` turns the canvas's autofill on) and hide the row color and the theme picture. The fix turns both autofills off after `setWidget`, as `result.py` does.

A QSS `background: transparent` on the viewport alone (`QScrollArea#historyExprScroll QWidget#qt_scrollarea_viewport`, with or without `>`) does not turn its autofill off; only the rule on the scroll area does.

The black groove shows only on screen (seen on KDE Wayland); offscreen runs, `grab()` and the backing store all give the right color, so they are no check for it. `QImage.pixelColor` returns black for an out of range coordinate: check its warning before trusting a black pixel.

The display's `QScrollArea#displayExpression` rule blackens that scroll area's palette the same way, but its scrollbar is right on screen, so it is left as is.
