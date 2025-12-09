from __future__ import annotations

from PySide6.QtWidgets import QApplication

STYLE_SHEET = """
QLabel#displayExpression {
    color: #b6b8c9;
}
QLabel#displayResult {
    color: #f6f7fb;
}
QFrame#displayDivider {
    background-color: #2d2f3c;
    min-height: 1px;
    max-height: 1px;
}
QPushButton[keypadRole] {
    background-color: #2e313b;
    color: #f0f2ff;
    border: 1px solid #2f3138;
    border-radius: 12px;
    padding: 10px;
    font-size: 15px;
}
QPushButton[keypadRole]:pressed {
    background-color: #2a2c33;
}
QPushButton[keypadRole="operator"] {
    background-color: #343842;
    color: #f3d199;
    border-color: #444957;
}
QPushButton[keypadRole="operator"]:pressed {
    background-color: #3f4450;
}
QPushButton[keypadRole="action"] {
    background-color: #2f353d;
    color: #a6c7ff;
    border-color: #3a404b;
}
QPushButton[keypadRole="equals"] {
    background-color: #4a4f5a;
    color: #ffffff;
    border-color: #5a606d;
}
QPushButton[keypadRole="equals"]:pressed {
    background-color: #3e434d;
}
"""


def apply_styles(app: QApplication) -> None:
    """Apply the global stylesheet for the calculator UI."""
    base = app.styleSheet()
    sheet = STYLE_SHEET if not base else f"{base}\n{STYLE_SHEET}"
    app.setStyleSheet(sheet)
