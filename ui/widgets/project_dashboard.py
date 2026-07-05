"""Right-side project dashboard widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.paths import PROJECTS_DIR
from core.project_service import project_config_status, project_statistics


def _safe(value: Any, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _format_int(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{int(value):,}".replace(",", " ")
    except Exception:
        return str(value)


class ProjectDashboard(QFrame):
    """Правая панель с базовой информацией о выбранном ЖК."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ProjectCard")
        self.project: dict[str, Any] | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        self.title = QLabel("Выберите ЖК")
        self.title.setObjectName("CardTitle")
        layout.addWidget(self.title)

        self.subtitle = QLabel("Проекты отображаются из папки data/projects.")
        self.subtitle.setObjectName("MutedText")
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)

        self.metrics = QFrame()
        self.metrics.setObjectName("MetricsBox")
        metrics_layout = QHBoxLayout(self.metrics)
        metrics_layout.setContentsMargins(18, 18, 18, 18)
        metrics_layout.setSpacing(16)

        self.metric_apartments = self._metric_widget("Квартир", "—")
        self.metric_updates = self._metric_widget("Обновлений", "—")
        self.metric_last = self._metric_widget("Последнее обновление", "—")
        metrics_layout.addWidget(self.metric_apartments)
        metrics_layout.addWidget(self.metric_updates)
        metrics_layout.addWidget(self.metric_last)
        layout.addWidget(self.metrics)

        self.feed_info = QLabel("Фид: —")
        self.feed_info.setObjectName("InfoText")
        self.feed_info.setWordWrap(True)
        layout.addWidget(self.feed_info)

        self.path_info = QLabel("Папка: —")
        self.path_info.setObjectName("InfoText")
        self.path_info.setWordWrap(True)
        layout.addWidget(self.path_info)

        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        self.open_folder_btn = QPushButton("Открыть папку")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.clicked.connect(self.open_project_folder)
        self.refresh_hint_btn = QPushButton("Обновить список")
        self.refresh_hint_btn.setObjectName("SecondaryButton")
        action_row.addWidget(self.open_folder_btn)
        action_row.addWidget(self.refresh_hint_btn)
        action_row.addStretch()
        layout.addLayout(action_row)

        self.note = QLabel(
            "Это GUI Foundation: интерфейс пока только показывает проекты и базовую карточку. "
            "Кнопки обновления, создания ЖК и профили обновляемых полей будут добавлены в следующих версиях."
        )
        self.note.setObjectName("MutedText")
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        layout.addStretch()

    def _metric_widget(self, label: str, value: str) -> QWidget:
        box = QFrame()
        box.setObjectName("MetricCard")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        label_label = QLabel(label)
        label_label.setObjectName("MetricLabel")
        layout.addWidget(value_label)
        layout.addWidget(label_label)
        box.value_label = value_label  # type: ignore[attr-defined]
        return box

    def set_project(self, project: dict[str, Any] | None) -> None:
        self.project = project
        if not project:
            self.title.setText("Выберите ЖК")
            self.subtitle.setText("Проекты отображаются из папки data/projects.")
            self.metric_apartments.value_label.setText("—")  # type: ignore[attr-defined]
            self.metric_updates.value_label.setText("—")  # type: ignore[attr-defined]
            self.metric_last.value_label.setText("—")  # type: ignore[attr-defined]
            self.feed_info.setText("Фид: —")
            self.path_info.setText("Папка: —")
            self.open_folder_btn.setEnabled(False)
            return

        code = project.get("code", "")
        name = project.get("name") or code
        pdir = PROJECTS_DIR / code
        stats: dict[str, Any] = {}
        config: dict[str, Any] = {}
        try:
            stats = project_statistics(PROJECTS_DIR, code)
        except Exception:
            stats = {}
        try:
            config = project_config_status(PROJECTS_DIR, code)
        except Exception:
            config = {}

        current_apartments = stats.get("current_apartments") or project.get("apartments_total")
        updates_total = stats.get("updates_total")
        last_update = stats.get("last_update") or project.get("last_update")
        feed_type = config.get("feed_type") or project.get("feed_format_last_detected") or "auto"
        feed_url = config.get("feed_url") or project.get("feed_url") or "—"

        self.title.setText(str(name))
        self.subtitle.setText(f"Код проекта: {code}")
        self.metric_apartments.value_label.setText(_format_int(current_apartments))  # type: ignore[attr-defined]
        self.metric_updates.value_label.setText(_format_int(updates_total))  # type: ignore[attr-defined]
        self.metric_last.value_label.setText(_safe(last_update))  # type: ignore[attr-defined]
        self.feed_info.setText(f"Фид: {feed_type}\nСсылка: {feed_url}")
        self.path_info.setText(f"Папка проекта: {pdir}")
        self.open_folder_btn.setEnabled(True)

    def open_project_folder(self) -> None:
        if not self.project:
            return
        path = PROJECTS_DIR / str(self.project.get("code"))
        if not path.exists():
            QMessageBox.warning(self, "Папка не найдена", f"Папка проекта не найдена:\n{path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
