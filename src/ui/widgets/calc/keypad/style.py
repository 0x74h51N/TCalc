from __future__ import annotations

from PySide6.QtWidgets import QPushButton


def apply_button_style(button: QPushButton, role: str) -> None:
    button.setObjectName("keypadButton")
    button.setProperty("keypadRole", role)
    
    button.style().unpolish(button)
    button.style().polish(button)
