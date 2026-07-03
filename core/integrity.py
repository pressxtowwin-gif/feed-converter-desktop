#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project Integrity Engine.

v0.9.1: самовосстановление структуры проекта.

Задача модуля — гарантировать, что любой существующий проект можно открыть
после обновления программы без ручного редактирования папок, settings.json
или history.db.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ensure_project_config
from .config.config_service import settings_path
from .config.schema import CONFIG_SCHEMA_VERSION
from .data_engine import initialize_project_data_engine, DATABASE_SCHEMA_VERSION

INTEGRITY_ENGINE_VERSION = "0.9.1-project-integrity-engine"
PROJECT_MANIFEST_FILENAME = "project.manifest.json"
REQUIRED_DIRS = ("xml", "xml/archive", "tables", "backups", "history", "logs")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def manifest_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / PROJECT_MANIFEST_FILENAME


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")


def _ensure_required_dirs(project_dir: Path) -> list[str]:
    actions: list[str] = []
    project_dir.mkdir(parents=True, exist_ok=True)
    for rel in REQUIRED_DIRS:
        path = project_dir / rel
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            actions.append(f"created_dir:{rel}")
        elif not path.is_dir():
            raise NotADirectoryError(f"Ожидалась папка, но найден файл: {path}")
    return actions


def _ensure_manifest(project_dir: Path, settings: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    path = manifest_path(project_dir)
    actions: list[str] = []
    manifest = _read_json(path)
    created = not path.exists()

    defaults = {
        "project_version": INTEGRITY_ENGINE_VERSION,
        "project_code": settings.get("project_code") or project_dir.name,
        "project_name": settings.get("project_name") or project_dir.name,
        "created_at": settings.get("created_at") or _now(),
        "last_integrity_check": _now(),
        "config_schema_version": CONFIG_SCHEMA_VERSION,
        "database_schema_version": DATABASE_SCHEMA_VERSION,
    }

    changed = created
    for key, value in defaults.items():
        if key not in manifest or manifest.get(key) in (None, ""):
            manifest[key] = value
            changed = True

    # Эти поля обновляем при каждой успешной проверке структуры.
    manifest["project_version"] = INTEGRITY_ENGINE_VERSION
    manifest["last_integrity_check"] = _now()
    manifest["config_schema_version"] = CONFIG_SCHEMA_VERSION
    manifest["database_schema_version"] = DATABASE_SCHEMA_VERSION
    changed = True

    if changed:
        _write_json(path, manifest)
        actions.append("created_manifest" if created else "updated_manifest")
    return manifest, actions


def ensure_project_structure(project_dir: str | Path) -> dict[str, Any]:
    """Привести проект к актуальной структуре.

    Функция безопасна для повторного запуска: пользовательские настройки,
    таблицы, XML и история не перезаписываются.
    """
    project_dir = Path(project_dir)
    actions: list[str] = []

    actions.extend(_ensure_required_dirs(project_dir))

    settings_was_missing = not settings_path(project_dir).exists()
    settings = ensure_project_config(project_dir)
    if settings_was_missing:
        actions.append("created_settings")
    else:
        actions.append("checked_settings")

    db_path = project_dir / "history" / "history.db"
    db_was_missing = not db_path.exists()
    data_status = initialize_project_data_engine(project_dir)
    actions.append("created_history_db" if db_was_missing else "checked_history_db")

    manifest, manifest_actions = _ensure_manifest(project_dir, settings)
    actions.extend(manifest_actions)

    return {
        "integrity_engine_version": INTEGRITY_ENGINE_VERSION,
        "project_dir": str(project_dir),
        "project_code": project_dir.name,
        "settings_path": str(settings_path(project_dir)),
        "settings_created": settings_was_missing,
        "manifest_path": str(manifest_path(project_dir)),
        "history_db": data_status.get("db_path", str(db_path)),
        "manifest": manifest,
        "settings": settings,
        "actions": actions,
        "required_dirs": [str(project_dir / rel) for rel in REQUIRED_DIRS],
        "ok": True,
    }


def doctor_project(project_dir: str | Path) -> dict[str, Any]:
    """Публичная диагностическая проверка проекта."""
    return ensure_project_structure(project_dir)
