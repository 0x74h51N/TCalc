from __future__ import annotations


class FileOperations:
    def __init__(self, window) -> None:
        self._window = window

    def quit(self) -> None:
        self._window.close()

