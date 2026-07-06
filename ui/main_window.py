"""Main application window for Feed Converter Desktop."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QApplication,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QDialog,
)

from core.paths import APP_ROOT, PROJECTS_DIR, ensure_workspace
from core.project_service import list_projects
from ui.dialogs.new_project_dialog import NewProjectDialog
from ui.styles import APP_STYLESHEET
from ui.widgets.project_dashboard import ProjectDashboard

APP_VERSION = "0.9.3-gui-foundation"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        self._configure_application()
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
        self.new_project_btn.clicked.connect(self.open_new_project_dialog)
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

        self.card = ProjectDashboard()
        self.card.refresh_hint_btn.clicked.connect(self.load_projects)
        self.card.project_updated.connect(lambda code: self.load_projects(select_code=code))
        content_layout.addWidget(self.card, 1)

        main_layout.addWidget(content, 1)

        self._build_menu()
        self.apply_styles()
        self.load_projects()

    def _configure_application(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setApplicationName("Feed Converter Desktop")
        app.setApplicationVersion(APP_VERSION)
        font = QFont()
        font.setPointSize(13)
        app.setFont(font)

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Файл")
        refresh = QAction("Обновить список проектов", self)
        refresh.triggered.connect(self.load_projects)
        menu.addAction(refresh)
        menu.addSeparator()
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(quit_action)

    def on_project_selected(self, row: int) -> None:
        if row < 0 or row >= len(self.projects):
            self.card.set_project(None)
            return
        self.card.set_project(self.projects[row])

    def load_projects(self, _checked: bool = False, *, select_code: str | None = None) -> None:
        ensure_workspace()
        if select_code is None:
            current_item = self.project_list.currentItem()
            if current_item is not None:
                current_code = current_item.data(Qt.UserRole)
                if current_code:
                    select_code = str(current_code)
        self.projects = list_projects(PROJECTS_DIR)
        self.project_list.clear()
        if not self.projects:
            item = QListWidgetItem("Проектов пока нет")
            item.setFlags(Qt.NoItemFlags)
            self.project_list.addItem(item)
            self.card.set_project(None)
            return

        selected_row = 0
        for row, project in enumerate(self.projects):
            name = project.get("name") or project.get("code")
            last_update = project.get("last_update") or "нет обновлений"
            item = QListWidgetItem(f"{name}\n{last_update}")
            item.setData(Qt.UserRole, project.get("code"))
            item.setSizeHint(QSize(260, 58))
            self.project_list.addItem(item)
            if select_code and project.get("code") == select_code:
                selected_row = row
        self.project_list.setCurrentRow(selected_row)

    def open_new_project_dialog(self) -> None:
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.Accepted or not dialog.created_project:
            return

        result = dialog.created_project
        project_code = str(result.get("project_code", ""))
        self.load_projects(select_code=project_code)
        QMessageBox.information(
            self,
            "Проект создан",
            "Проект успешно создан.\n"
            f"ЖК: {result.get('project_name', '—')}\n"
            f"Формат фида: {result.get('feed_format', result.get('checked_feed_format', '—'))}\n"
            f"Квартир: {result.get('rows', result.get('checked_apartment_count', '—'))}\n"
            f"Excel: {result.get('excel_path', '—')}",
        )

    def apply_styles(self) -> None:
        self.setStyleSheet(APP_STYLESHEET)
