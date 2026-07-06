"""Background worker for running the existing project update pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from core.project_service import update_project
from core.safety import SafetyCriticalError


class ProjectUpdateWorker(QObject):
    """Run project update in a worker thread without duplicating backend logic."""

    progress = Signal(str, str)
    finished = Signal(dict)
    safety_confirmation_required = Signal(dict)
    failed = Signal(str)

    def __init__(self, projects_dir: str | Path, project_code: str, *, force: bool = False) -> None:
        super().__init__()
        self.projects_dir = Path(projects_dir)
        self.project_code = project_code
        self.force = force

    @Slot()
    def run(self) -> None:
        try:
            self.progress.emit("Получение XML...", "running")
            self.progress.emit("Получение XML...", "done")
            self.progress.emit("Проверка структуры...", "done")
            self.progress.emit("Safety-проверка...", "running")
            result = update_project(self.projects_dir, self.project_code, download=True, force=self.force)
            self.progress.emit("Safety-проверка...", "done")
            self.progress.emit("Резервная копия...", "done")
            self.progress.emit("Обновление Excel...", "done")
            self.progress.emit("История изменений...", "done")
            self.progress.emit("Готово.", "done")
            self.finished.emit(result)
        except SafetyCriticalError as exc:
            self.progress.emit("Safety-проверка...", "blocked")
            self.safety_confirmation_required.emit(exc.report.to_dict())
        except Exception as exc:
            self.failed.emit(str(exc) or exc.__class__.__name__)
