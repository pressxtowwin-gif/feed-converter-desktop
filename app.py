#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py
Версия: 0.9.3-gui-foundation

Первый графический интерфейс Feed Converter Desktop на PySide6.

Цель версии:
- открыть главное окно;
- показать проекты из portable workspace data/projects;
- выбрать ЖК в списке;
- показать базовую карточку проекта;
- не переносить бизнес-логику в GUI.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    from PySide6.QtCore import Qt, QSize, QUrl
    from PySide6.QtGui import QAction, QDesktopServices, QFont
    from PySide6.QtWidgets import (
        QApplication,
        QFrame,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpacerItem,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - нужен понятный вывод пользователю
    print("PySide6 не установлен.")
    print("Установите его командой:")
    print("python3 -m pip install PySide6")
    raise SystemExit(1) from exc

from core.paths import APP_ROOT, PROJECTS_DIR, ensure_workspace
from core.project_service import list_projects, project_statistics, project_config_status

APP_VERSION = "0.9.3-gui-foundation"


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


class ProjectCard(QFrame):
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


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Feed Converter Desktop — {APP_VERSION}")
        self.setMinimumSize(QSize(1180, 760))
        self.projects: list[dict[str, Any]] = []

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(310)
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(22, 22, 22, 22)
        side_layout.setSpacing(14)

        app_title = QLabel("Feed Converter")
        app_title.setObjectName("AppTitle")
        side_layout.addWidget(app_title)

        version = QLabel(APP_VERSION)
        version.setObjectName("VersionText")
        side_layout.addWidget(version)

        self.new_project_btn = QPushButton("+ Новый ЖК")
        self.new_project_btn.setObjectName("PrimaryButton")
        self.new_project_btn.clicked.connect(self.show_new_project_placeholder)
        side_layout.addWidget(self.new_project_btn)

        label = QLabel("Жилые комплексы")
        label.setObjectName("SectionLabel")
        side_layout.addWidget(label)

        self.project_list = QListWidget()
        self.project_list.setObjectName("ProjectList")
        self.project_list.currentRowChanged.connect(self.on_project_selected)
        side_layout.addWidget(self.project_list, 1)

        self.refresh_btn = QPushButton("Обновить список")
        self.refresh_btn.setObjectName("SecondaryButton")
        self.refresh_btn.clicked.connect(self.load_projects)
        side_layout.addWidget(self.refresh_btn)

        main_layout.addWidget(self.sidebar)

        content = QFrame()
        content.setObjectName("Content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 26, 30, 26)
        content_layout.setSpacing(20)

        header = QFrame()
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_title = QLabel("Рабочий стол ЖК")
        header_title.setObjectName("PageTitle")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        workspace = QLabel(f"Workspace: {APP_ROOT}")
        workspace.setObjectName("MutedText")
        header_layout.addWidget(workspace)
        content_layout.addWidget(header)

        self.card = ProjectCard()
        self.card.refresh_hint_btn.clicked.connect(self.load_projects)
        content_layout.addWidget(self.card, 1)

        main_layout.addWidget(content, 1)

        self._build_menu()
        self.apply_styles()
        self.load_projects()

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Файл")
        refresh = QAction("Обновить список проектов", self)
        refresh.triggered.connect(self.load_projects)
        menu.addAction(refresh)
        menu.addSeparator()
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

    def load_projects(self) -> None:
        ensure_workspace()
        self.projects = list_projects(PROJECTS_DIR)
        self.project_list.clear()
        if not self.projects:
            item = QListWidgetItem("Проектов пока нет")
            item.setFlags(Qt.NoItemFlags)
            self.project_list.addItem(item)
            self.card.set_project(None)
            return

        for project in self.projects:
            name = project.get("name") or project.get("code")
            last_update = project.get("last_update") or "нет обновлений"
            item = QListWidgetItem(f"{name}\n{last_update}")
            item.setData(Qt.UserRole, project.get("code"))
            item.setSizeHint(QSize(260, 58))
            self.project_list.addItem(item)
        self.project_list.setCurrentRow(0)

    def on_project_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.projects):
            self.card.set_project(None)
            return
        self.card.set_project(self.projects[row])

    def show_new_project_placeholder(self) -> None:
        QMessageBox.information(
            self,
            "Новый ЖК",
            "Мастер создания нового ЖК появится в следующей GUI-версии.\n\n"
            "Пока новый проект можно создать через команду:\n"
            "python3 project_manager.py create",
        )

    def apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget#Root { background: #F5F7FB; color: #172033; }
            QFrame#Sidebar { background: #FFFFFF; border-right: 1px solid #E6EAF2; }
            QFrame#Content { background: #F5F7FB; }
            QLabel#AppTitle { font-size: 24px; font-weight: 800; color: #111827; }
            QLabel#VersionText { font-size: 12px; color: #8390A3; }
            QLabel#SectionLabel { font-size: 12px; font-weight: 700; color: #6B7280; text-transform: uppercase; margin-top: 10px; }
            QLabel#PageTitle { font-size: 28px; font-weight: 800; color: #111827; }
            QLabel#CardTitle { font-size: 30px; font-weight: 800; color: #111827; }
            QLabel#MutedText { font-size: 13px; color: #6B7280; }
            QLabel#InfoText { font-size: 14px; color: #374151; line-height: 1.4; }
            QFrame#ProjectCard { background: #FFFFFF; border: 1px solid #E6EAF2; border-radius: 22px; }
            QFrame#MetricsBox { background: #F8FAFD; border: 1px solid #E8EDF5; border-radius: 18px; }
            QFrame#MetricCard { background: #FFFFFF; border: 1px solid #E9EEF6; border-radius: 14px; }
            QLabel#MetricValue { font-size: 22px; font-weight: 800; color: #0F172A; }
            QLabel#MetricLabel { font-size: 12px; color: #6B7280; }
            QPushButton { border: none; border-radius: 12px; padding: 11px 16px; font-weight: 700; }
            QPushButton#PrimaryButton { background: #2563EB; color: white; }
            QPushButton#PrimaryButton:hover { background: #1D4ED8; }
            QPushButton#SecondaryButton { background: #EEF2FF; color: #1E3A8A; }
            QPushButton#SecondaryButton:hover { background: #E0E7FF; }
            QListWidget#ProjectList { background: #F8FAFD; border: 1px solid #E6EAF2; border-radius: 16px; padding: 8px; outline: none; }
            QListWidget#ProjectList::item { padding: 10px; border-radius: 12px; color: #1F2937; }
            QListWidget#ProjectList::item:selected { background: #E0ECFF; color: #0F172A; }
            QMenuBar { background: #FFFFFF; border-bottom: 1px solid #E6EAF2; }
            QMenuBar::item { padding: 6px 10px; }
            QMenu { background: #FFFFFF; border: 1px solid #E6EAF2; }
            QMenu::item { padding: 8px 22px; }
            """
        )


def main() -> None:
    ensure_workspace()
    app = QApplication(sys.argv)
    app.setApplicationName("Feed Converter Desktop")
    app.setApplicationVersion(APP_VERSION)
    font = QFont()
    font.setPointSize(13)
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
