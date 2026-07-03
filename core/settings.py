#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core.settings — совместимость со старым кодом.

Начиная с v0.9.0 фактическая логика настроек перенесена в
core.config. Эти функции оставлены как тонкая обертка, чтобы не ломать
уже работающие модули.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import normalize_project_config, read_project_config, write_project_config


def read_settings(project_dir: str | Path) -> dict[str, Any]:
    return read_project_config(project_dir, auto_migrate=True)


def write_settings(project_dir: str | Path, settings: dict[str, Any]) -> None:
    write_project_config(project_dir, settings)


def normalize_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return normalize_project_config(settings)
