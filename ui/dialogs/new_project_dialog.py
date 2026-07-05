"""New project dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog


class NewProjectDialog(QDialog):
    """Empty dialog shell for future project creation workflow."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новый ЖК")
