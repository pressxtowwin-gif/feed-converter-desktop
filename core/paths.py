#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core.paths

v0.9.2 Portable Workspace.

Единая точка определения путей приложения. Программа не должна зависеть
от имени папки пользователя или абсолютного пути на macOS/Windows/Linux.
Все пользовательские данные хранятся внутри папки приложения в каталоге data/.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

PATHS_VERSION = "0.9.2-portable-workspace"


def get_app_root() -> Path:
    """Вернуть корневую папку приложения.

    В режиме разработки это папка, где лежит project_manager.py и core/.
    В собранном приложении PyInstaller это папка рядом с исполняемым файлом.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


APP_ROOT = get_app_root()
DATA_DIR = APP_ROOT / "data"
PROJECTS_DIR = DATA_DIR / "projects"
APP_LOGS_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
SETTINGS_DIR = DATA_DIR / "settings"
TEMPLATES_DIR = DATA_DIR / "templates"

# Старые папки до v0.9.2. Нужны только для автоматической миграции.
LEGACY_PROJECTS_DIR = APP_ROOT / "projects"
LEGACY_LOGS_DIR = APP_ROOT / "logs"


def _is_effectively_empty(path: Path) -> bool:
    if not path.exists():
        return True
    if not path.is_dir():
        return False
    try:
        return next(path.iterdir(), None) is None
    except StopIteration:
        return True


def _merge_dir_contents(src: Path, dst: Path) -> list[str]:
    actions: list[str] = []
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        target = dst / child.name
        if target.exists():
            actions.append(f"skip_existing:{child} -> {target}")
            continue
        shutil.move(str(child), str(target))
        actions.append(f"moved:{child} -> {target}")
    try:
        if _is_effectively_empty(src):
            src.rmdir()
            actions.append(f"removed_empty_legacy_dir:{src}")
    except Exception:
        pass
    return actions


def _migrate_legacy_dir(src: Path, dst: Path) -> list[str]:
    actions: list[str] = []
    if not src.exists():
        return actions
    if src.resolve() == dst.resolve():
        return actions
    if not src.is_dir():
        actions.append(f"legacy_path_is_not_dir:{src}")
        return actions

    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        actions.append(f"moved_legacy_dir:{src} -> {dst}")
        return actions

    actions.extend(_merge_dir_contents(src, dst))
    return actions


def ensure_workspace(*, migrate_legacy: bool = True) -> dict[str, Any]:
    """Создать/проверить portable workspace.

    Все runtime-данные живут внутри data/:
      data/projects
      data/logs
      data/cache
      data/settings
      data/templates

    Если обнаружены старые папки projects/ или logs/ в корне приложения,
    они аккуратно переносятся в data/.
    """
    actions: list[str] = []
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if migrate_legacy:
        actions.extend(_migrate_legacy_dir(LEGACY_PROJECTS_DIR, PROJECTS_DIR))
        actions.extend(_migrate_legacy_dir(LEGACY_LOGS_DIR, APP_LOGS_DIR))

    for path in (PROJECTS_DIR, APP_LOGS_DIR, CACHE_DIR, SETTINGS_DIR, TEMPLATES_DIR):
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            actions.append(f"created_dir:{path}")
        elif not path.is_dir():
            raise NotADirectoryError(f"Ожидалась папка workspace, но найден файл: {path}")

    return workspace_status(actions=actions)


def workspace_status(actions: list[str] | None = None) -> dict[str, Any]:
    return {
        "paths_version": PATHS_VERSION,
        "app_root": str(APP_ROOT),
        "data_dir": str(DATA_DIR),
        "projects_dir": str(PROJECTS_DIR),
        "logs_dir": str(APP_LOGS_DIR),
        "cache_dir": str(CACHE_DIR),
        "settings_dir": str(SETTINGS_DIR),
        "templates_dir": str(TEMPLATES_DIR),
        "legacy_projects_dir": str(LEGACY_PROJECTS_DIR),
        "legacy_logs_dir": str(LEGACY_LOGS_DIR),
        "actions": actions or [],
        "ok": True,
    }
