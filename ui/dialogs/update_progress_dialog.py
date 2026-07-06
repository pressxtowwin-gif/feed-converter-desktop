"""Modal update progress dialog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout


class UpdateProgressDialog(QDialog):
    """Shows visible update stages while the backend worker runs."""

    def __init__(self, parent=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(parent)
        self.setWindowTitle("Обновление проекта")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self._labels: dict[str, QLabel] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)
        title = QLabel("Идёт обновление проекта")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        for stage in (
            "Получение XML...",
            "Проверка структуры...",
            "Safety-проверка...",
            "Резервная копия...",
            "Обновление Excel...",
            "История изменений...",
            "Готово.",
        ):
            label = QLabel(stage)
            label.setObjectName("InfoText")
            layout.addWidget(label)
            self._labels[stage] = label

    def set_stage(self, text: str, status: str) -> None:
        label = self._labels.get(text)
        if label is None:
            return
        prefix = {"running": "… ", "done": "✓ ", "blocked": "⚠ "}.get(status, "")
        label.setText(f"{prefix}{text}")
