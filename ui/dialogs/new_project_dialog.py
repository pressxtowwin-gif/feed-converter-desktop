"""New project creation wizard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.downloader import download_url_to_file
from core.feed_parser import load_xml, parse_universal
from core.paths import CACHE_DIR, PROJECTS_DIR, ensure_workspace
from core.project_service import create_project, safe_project_code
from core.settings import read_settings, write_settings


@dataclass(frozen=True)
class FeedCheckResult:
    """Validated XML feed metadata from the wizard check step."""

    url: str
    feed_format: str
    apartment_count: int
    xml_size: int
    cache_path: Path


class NewProjectDialog(QDialog):
    """Wizard for checking a feed URL and creating a new project."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новый ЖК")
        self.setMinimumSize(720, 620)
        self.created_project: dict[str, Any] | None = None
        self._feed_check: FeedCheckResult | None = None
        self._is_busy = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Создание нового ЖК")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        description = QLabel(
            "Введите данные проекта, проверьте XML-фид, затем создайте проект. "
            "Проект создаётся только после успешной проверки текущей XML-ссылки."
        )
        description.setObjectName("MutedText")
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)

        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Например: ЖК Солнечный")
        form.addRow("Название ЖК *", self.project_name_input)

        self.developer_name_input = QLineEdit()
        self.developer_name_input.setPlaceholderText("Необязательно")
        form.addRow("Застройщик", self.developer_name_input)

        self.feed_url_input = QLineEdit()
        self.feed_url_input.setPlaceholderText("https://example.com/feed.xml")
        form.addRow("XML-фид *", self.feed_url_input)
        layout.addLayout(form)

        self.status_area = QTextEdit()
        self.status_area.setReadOnly(True)
        self.status_area.setMinimumHeight(220)
        self.status_area.setPlaceholderText("Результат проверки XML появится здесь.")
        layout.addWidget(self.status_area, 1)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        self.check_xml_btn = QPushButton("Проверить XML")
        self.check_xml_btn.clicked.connect(self.check_xml)
        self.create_project_btn = QPushButton("Создать проект")
        self.create_project_btn.setObjectName("PrimaryButton")
        self.create_project_btn.setEnabled(False)
        self.create_project_btn.clicked.connect(self.create_checked_project)
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(self.check_xml_btn)
        buttons.addStretch()
        buttons.addWidget(self.create_project_btn)
        buttons.addWidget(self.cancel_btn)
        layout.addLayout(buttons)

        self.project_name_input.textChanged.connect(self.invalidate_check)
        self.feed_url_input.textChanged.connect(self.invalidate_check)

    def invalidate_check(self) -> None:
        if self._is_busy:
            return
        if self._feed_check is not None:
            self._feed_check = None
            self.create_project_btn.setEnabled(False)
            self._set_status("Проверка XML сброшена: изменились название проекта или XML-ссылка.")

    def _set_busy(self, busy: bool, *, allow_create: bool = False) -> None:
        self._is_busy = busy
        self.project_name_input.setEnabled(not busy)
        self.developer_name_input.setEnabled(not busy)
        self.feed_url_input.setEnabled(not busy)
        self.check_xml_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)
        self.create_project_btn.setEnabled((not busy) and allow_create)

    def _set_status(self, text: str) -> None:
        self.status_area.setPlainText(text)

    def _current_url(self) -> str:
        return self.feed_url_input.text().strip()

    def _validate_url(self) -> str:
        url = self._current_url()
        if not url.startswith(("http://", "https://")):
            raise ValueError("XML-ссылка должна начинаться с http:// или https://")
        return url

    def check_xml(self) -> None:
        self._feed_check = None
        self.create_project_btn.setEnabled(False)
        try:
            url = self._validate_url()
        except Exception as exc:
            self._set_status(f"Ошибка: {exc}")
            return

        self._set_busy(True)
        self._set_status("Проверяем XML: скачивание и разбор фида...")
        try:
            ensure_workspace()
            cache_path = CACHE_DIR / "last_gui_feed_check.xml"
            xml_size = download_url_to_file(url, cache_path)
            xml_bytes = load_xml(str(cache_path))
            rows, _columns, feed_format = parse_universal(xml_bytes)
            self._feed_check = FeedCheckResult(
                url=url,
                feed_format=feed_format,
                apartment_count=len(rows),
                xml_size=xml_size,
                cache_path=cache_path,
            )
            self._set_status(
                "Статус: XML успешно проверен\n"
                f"Формат фида: {feed_format}\n"
                f"Квартир: {len(rows)}\n"
                f"Размер XML: {xml_size} байт\n"
                f"Файл проверки: {cache_path}"
            )
            self._set_busy(False, allow_create=True)
        except Exception as exc:
            self._set_status(f"Ошибка проверки XML: {exc}")
            self._set_busy(False, allow_create=False)

    def _generate_unique_project_code(self, project_name: str) -> str:
        base_code = safe_project_code(project_name)
        project_code = base_code
        suffix = 2
        while (PROJECTS_DIR / project_code).exists():
            project_code = f"{base_code}_{suffix}"
            suffix += 1
        return project_code

    def create_checked_project(self) -> None:
        project_name = self.project_name_input.text().strip()
        if not project_name:
            self._set_status("Ошибка: укажите название ЖК.")
            return
        current_url = self._current_url()
        if self._feed_check is None or self._feed_check.url != current_url:
            self._feed_check = None
            self._set_status("Ошибка: сначала проверьте текущую XML-ссылку.")
            self.create_project_btn.setEnabled(False)
            return

        self._set_busy(True)
        self._set_status("Создаём проект...")
        try:
            ensure_workspace()
            project_code = self._generate_unique_project_code(project_name)
            result = create_project(
                PROJECTS_DIR,
                project_name,
                source=current_url,
                excel_name="lots.xlsx",
                project_code=project_code,
            )
            developer_name = self.developer_name_input.text().strip()
            if developer_name:
                project_dir = PROJECTS_DIR / project_code
                settings = read_settings(project_dir)
                settings["developer_name"] = developer_name
                write_settings(project_dir, settings)
            result["checked_feed_format"] = self._feed_check.feed_format
            result["checked_apartment_count"] = self._feed_check.apartment_count
            self.created_project = result
            self.accept()
        except Exception as exc:
            self._set_status(f"Ошибка создания проекта: {exc}")
            QMessageBox.critical(self, "Ошибка создания проекта", str(exc))
            self._set_busy(False, allow_create=True)
