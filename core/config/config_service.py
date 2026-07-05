#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration Engine проекта.

Единая точка чтения, нормализации, проверки и сохранения settings.json.
Остальной код не должен напрямую знать структуру JSON — он работает
через эти функции/сервис.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .schema import (
    CONFIG_ENGINE_VERSION,
    CONFIG_SCHEMA_VERSION,
    DEFAULT_SAFETY,
    DEFAULT_UPDATE_FIELDS,
    default_settings,
)


class ConfigError(Exception):
    """Ошибка настроек проекта."""


def settings_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / "settings.json"


def _deep_merge_defaults(value: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Добавить отсутствующие ключи из defaults, не затирая пользовательские значения."""
    result = dict(value)
    for key, default_value in defaults.items():
        if key not in result or result[key] is None:
            result[key] = deepcopy(default_value)
            continue
        if isinstance(default_value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_defaults(result[key], default_value)
    return result


def normalize_project_config(settings: dict[str, Any], project_code: str | None = None) -> dict[str, Any]:
    """Нормализовать настройки проекта.

    Функция не удаляет неизвестные ключи: это важно для будущей обратной
    совместимости и ручных служебных заметок.
    """
    normalized = _deep_merge_defaults(settings or {}, default_settings())

    # Специальная нормализация вложенных блоков, чтобы новые поля добавлялись
    # даже в старые проекты.
    normalized["update_fields"] = _deep_merge_defaults(
        normalized.get("update_fields") if isinstance(normalized.get("update_fields"), dict) else {},
        DEFAULT_UPDATE_FIELDS,
    )
    normalized["safety"] = _deep_merge_defaults(
        normalized.get("safety") if isinstance(normalized.get("safety"), dict) else {},
        DEFAULT_SAFETY,
    )

    if not isinstance(normalized.get("feed_history"), list):
        normalized["feed_history"] = []
    if not isinstance(normalized.get("reminders"), list):
        normalized["reminders"] = []

    if project_code and not normalized.get("project_code"):
        normalized["project_code"] = project_code

    # Старые проекты могли не иметь версии схемы.
    try:
        current_version = int(normalized.get("config_schema_version") or 0)
    except Exception:
        current_version = 0
    if current_version < CONFIG_SCHEMA_VERSION:
        normalized["config_schema_version"] = CONFIG_SCHEMA_VERSION

    return normalized


def validate_project_config(settings: dict[str, Any]) -> list[str]:
    """Вернуть список проблем в настройках. Пустой список = все хорошо."""
    errors: list[str] = []
    if not settings.get("project_name"):
        errors.append("Не указано project_name")
    if not settings.get("project_code"):
        errors.append("Не указано project_code")
    if not settings.get("main_excel"):
        errors.append("Не указано main_excel")
    if settings.get("feed_type") not in {"auto", "yandex", "domclick"}:
        errors.append("feed_type должен быть auto, yandex или domclick")
    if not isinstance(settings.get("update_fields"), dict):
        errors.append("update_fields должен быть объектом")
    if not isinstance(settings.get("safety"), dict):
        errors.append("safety должен быть объектом")
    return errors


def _infer_main_excel(project_dir: Path) -> str:
    """Попробовать определить основную таблицу для старого проекта без settings.json."""
    tables_dir = project_dir / "tables"
    if not tables_dir.exists():
        return "lots.xlsx"
    xlsx_files = sorted([p for p in tables_dir.glob("*.xlsx") if not p.name.startswith("~$")])
    if not xlsx_files:
        return "lots.xlsx"
    # Если есть таблица с updated в названии — часто это текущая рабочая версия.
    updated = [p for p in xlsx_files if "updated" in p.stem.lower()]
    return (updated[0] if updated else xlsx_files[0]).name


def _create_default_project_config(project_dir: Path) -> dict[str, Any]:
    project_code = project_dir.name
    settings = default_settings()
    settings["project_code"] = project_code
    settings["project_name"] = project_code
    settings["main_excel"] = _infer_main_excel(project_dir)
    return normalize_project_config(settings, project_code=project_code)


def read_project_config(project_dir: str | Path, auto_migrate: bool = True) -> dict[str, Any]:
    path = settings_path(project_dir)
    project_dir = Path(project_dir)
    project_code = project_dir.name

    if not path.exists():
        normalized = _create_default_project_config(project_dir)
        if auto_migrate:
            write_project_config(project_dir, normalized)
        return normalized

    raw = json.loads(path.read_text(encoding="utf-8"))
    normalized = normalize_project_config(raw, project_code=project_code)
    if auto_migrate and normalized != raw:
        write_project_config(project_dir, normalized)
    return normalized


def write_project_config(project_dir: str | Path, settings: dict[str, Any]) -> None:
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    normalized = normalize_project_config(settings, project_code=project_dir.name)
    path = settings_path(project_dir)
    path.write_text(json.dumps(normalized, ensure_ascii=False, indent=4), encoding="utf-8")


def ensure_project_config(project_dir: str | Path) -> dict[str, Any]:
    """Прочитать и автоматически привести settings.json к актуальной схеме."""
    return read_project_config(project_dir, auto_migrate=True)


def config_status(project_dir: str | Path) -> dict[str, Any]:
    settings = ensure_project_config(project_dir)
    errors = validate_project_config(settings)
    return {
        "config_engine_version": CONFIG_ENGINE_VERSION,
        "schema_version": settings.get("config_schema_version"),
        "settings_path": str(settings_path(project_dir)),
        "project_code": settings.get("project_code"),
        "project_name": settings.get("project_name"),
        "feed_url": settings.get("feed_url"),
        "feed_type": settings.get("feed_type"),
        "feed_format_last_detected": settings.get("feed_format_last_detected"),
        "last_update": settings.get("last_update"),
        "developer_name": settings.get("developer_name") or settings.get("developer"),
        "developer": settings.get("developer"),
        "main_excel": settings.get("main_excel"),
        "update_fields": settings.get("update_fields", {}),
        "safety": settings.get("safety", {}),
        "reminders_count": len(settings.get("reminders", [])),
        "errors": errors,
        "is_valid": len(errors) == 0,
    }
