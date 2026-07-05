"""Right-side project dashboard widget."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.paths import PROJECTS_DIR
from core.system.openers import BrowserOpenError, open_xml_in_browser
from core.excel_table import read_existing_rows_by_id
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
    """Правая панель с рабочей информацией о выбранном ЖК."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("ProjectCard")
        self.project: dict[str, Any] | None = None
        self.project_dir: Path | None = None
        self.main_excel_path: Path | None = None
        self.current_xml_path: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        self.empty_state = QLabel("Выберите ЖК слева или создайте новый проект")
        self.empty_state.setObjectName("EmptyState")
        self.empty_state.setWordWrap(True)
        self.empty_state.setAlignment(Qt.AlignCenter)
        root.addWidget(self.empty_state, 1)

        self.content = QWidget()
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)
        root.addWidget(self.content, 1)

        header = QFrame()
        header.setObjectName("DashboardSection")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 18, 20, 18)
        header_layout.setSpacing(8)

        self.title = QLabel("Выберите ЖК")
        self.title.setObjectName("CardTitle")
        self.title.setWordWrap(True)
        header_layout.addWidget(self.title)

        self.subtitle = QLabel("")
        self.subtitle.setObjectName("InfoText")
        self.subtitle.setWordWrap(True)
        header_layout.addWidget(self.subtitle)
        content_layout.addWidget(header)

        self.metrics = QFrame()
        self.metrics.setObjectName("MetricsBox")
        metrics_layout = QHBoxLayout(self.metrics)
        metrics_layout.setContentsMargins(18, 18, 18, 18)
        metrics_layout.setSpacing(16)
        self.metric_apartments = self._metric_widget("Квартир сейчас", "—")
        self.metric_updates = self._metric_widget("Всего обновлений", "—")
        self.metric_last = self._metric_widget("Последнее обновление", "—")
        self.metric_feed = self._metric_widget("Тип фида", "—")
        for metric in (self.metric_apartments, self.metric_updates, self.metric_last, self.metric_feed):
            metrics_layout.addWidget(metric)
        content_layout.addWidget(self.metrics)

        actions = QFrame()
        actions.setObjectName("DashboardSection")
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(20, 16, 20, 16)
        action_layout.setSpacing(12)
        self.open_excel_btn = self._action_button("Открыть Excel", self.open_excel)
        self.open_folder_btn = self._action_button("Открыть папку", self.open_project_folder)
        self.open_xml_btn = self._action_button("Открыть XML", self.open_xml)
        self.refresh_hint_btn = self._action_button("Обновить список", None)
        for button in (self.open_excel_btn, self.open_folder_btn, self.open_xml_btn, self.refresh_hint_btn):
            action_layout.addWidget(button)
        action_layout.addStretch()
        content_layout.addWidget(actions)

        feed_section = QFrame()
        feed_section.setObjectName("DashboardSection")
        feed_layout = QVBoxLayout(feed_section)
        feed_layout.setContentsMargins(20, 18, 20, 18)
        feed_layout.setSpacing(12)
        feed_title = QLabel("XML / фид")
        feed_title.setObjectName("SectionTitle")
        feed_layout.addWidget(feed_title)

        self.feed_grid = QGridLayout()
        self.feed_grid.setHorizontalSpacing(16)
        self.feed_grid.setVerticalSpacing(10)
        self.feed_type_value = self._add_info_row(0, "Тип фида в настройках")
        self.detected_format_value = self._add_info_row(1, "Последний формат")
        self.xml_path_value = self._add_info_row(2, "Текущий XML")
        self.excel_path_value = self._add_info_row(3, "Основной Excel")
        feed_layout.addLayout(self.feed_grid)

        self.feed_url_value = QTextEdit()
        self.feed_url_value.setObjectName("ReadOnlyField")
        self.feed_url_value.setReadOnly(True)
        self.feed_url_value.setFixedHeight(72)
        feed_layout.addWidget(QLabel("Feed URL"))
        feed_layout.addWidget(self.feed_url_value)
        content_layout.addWidget(feed_section)
        content_layout.addStretch()

        self.set_project(None)

    def _action_button(self, text: str, callback: Any | None) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("SecondaryButton")
        if callback is not None:
            button.clicked.connect(callback)
        return button

    def _add_info_row(self, row: int, label: str) -> QLabel:
        label_widget = QLabel(label)
        label_widget.setObjectName("MetricLabel")
        value_widget = QLabel("—")
        value_widget.setObjectName("InfoText")
        value_widget.setWordWrap(True)
        self.feed_grid.addWidget(label_widget, row, 0)
        self.feed_grid.addWidget(value_widget, row, 1)
        return value_widget

    def _metric_widget(self, label: str, value: str) -> QWidget:
        box = QFrame()
        box.setObjectName("MetricCard")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        value_label = QLabel(value)
        value_label.setObjectName("MetricValue")
        value_label.setWordWrap(True)
        label_label = QLabel(label)
        label_label.setObjectName("MetricLabel")
        label_label.setWordWrap(True)
        layout.addWidget(value_label)
        layout.addWidget(label_label)
        box.value_label = value_label  # type: ignore[attr-defined]
        return box

    def set_project(self, project: dict[str, Any] | None) -> None:
        self.project = project
        self.content.setVisible(bool(project))
        self.empty_state.setVisible(not bool(project))
        if not project:
            self.project_dir = None
            self.main_excel_path = None
            self.current_xml_path = None
            return

        code = str(project.get("code") or "")
        name = project.get("name") or code
        self.project_dir = PROJECTS_DIR / code
        self.current_xml_path = self.project_dir / "xml" / "current.xml"

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

        main_excel = config.get("main_excel") or project.get("main_excel") or "lots.xlsx"
        self.main_excel_path = self.project_dir / "tables" / str(main_excel)
        feed_type = config.get("feed_type") or "auto"
        detected_format = config.get("feed_format_last_detected") or project.get("feed_format_last_detected")
        last_update = stats.get("last_update") or config.get("last_update") or project.get("last_update")
        developer = config.get("developer_name") or config.get("developer")
        current_apartments = stats.get("current_apartments")
        if current_apartments is None and self.main_excel_path and self.main_excel_path.exists():
            try:
                _rows_by_id, _columns, current_apartments = read_existing_rows_by_id(self.main_excel_path)
            except Exception:
                current_apartments = None

        header_parts = [f"Код проекта: {code}"]
        if developer:
            header_parts.append(f"Застройщик: {developer}")
        header_parts.append(f"Формат фида: {_safe(detected_format or feed_type)}")
        header_parts.append(f"Последнее обновление: {_safe(last_update)}")

        self.title.setText(str(name))
        self.subtitle.setText(" · ".join(header_parts))
        self.metric_apartments.value_label.setText(_format_int(current_apartments or project.get("apartments_total")))  # type: ignore[attr-defined]
        self.metric_updates.value_label.setText(_format_int(stats.get("updates_total")))  # type: ignore[attr-defined]
        self.metric_last.value_label.setText(_safe(last_update))  # type: ignore[attr-defined]
        self.metric_feed.value_label.setText(_safe(detected_format or feed_type))  # type: ignore[attr-defined]
        self.feed_type_value.setText(_safe(feed_type))
        self.detected_format_value.setText(_safe(detected_format))
        self.xml_path_value.setText(str(self.current_xml_path))
        self.excel_path_value.setText(str(self.main_excel_path))
        self.feed_url_value.setPlainText(_safe(config.get("feed_url") or project.get("feed_url")))

    def _open_existing_file(self, path: Path | None, title: str, missing_message: str) -> None:
        if path is None:
            return
        if not path.exists():
            QMessageBox.warning(self, title, f"{missing_message}:\n{path}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def open_excel(self) -> None:
        self._open_existing_file(self.main_excel_path, "Excel не найден", "Основной Excel-файл не найден")

    def open_xml(self) -> None:
        if self.current_xml_path is None:
            return
        if not self.current_xml_path.exists():
            QMessageBox.warning(self, "XML не найден", f"Текущий XML-файл не найден:\n{self.current_xml_path}")
            return

        browser_options = {
            "Браузер по умолчанию": "default",
            "Google Chrome": "chrome",
            "Safari": "safari",
            "Firefox": "firefox",
            "Microsoft Edge": "edge",
        }
        browser_label, accepted = QInputDialog.getItem(
            self,
            "Открыть XML",
            "Выберите браузер:",
            list(browser_options.keys()),
            0,
            False,
        )
        if not accepted:
            return

        try:
            open_xml_in_browser(self.current_xml_path, browser_options[browser_label])
        except (BrowserOpenError, OSError) as exc:
            QMessageBox.warning(self, "Браузер недоступен", str(exc))

    def open_project_folder(self) -> None:
        self._open_existing_file(self.project_dir, "Папка не найдена", "Папка проекта не найдена")
