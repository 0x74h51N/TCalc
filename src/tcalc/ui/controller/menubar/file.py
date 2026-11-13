from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tcalc.ui.window import MainWindow


class FileOperations:
    def __init__(self, window: MainWindow) -> None:
        self._window = window

    def quit(self) -> None:
        self._window.close()
