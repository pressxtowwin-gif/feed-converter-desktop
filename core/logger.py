#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.logger
Единое логирование действий программы.

Пишет события сразу в два места:
1) общий лог проекта приложения: logs/app.log
2) лог конкретного ЖК: projects/<project_code>/logs/project.log

Формат строк простой, читаемый человеком:
2026-06-25 18:42:10 | INFO | marshal | update_project | message | key=value
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


LOG_VERSION = "0.6-logging"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).replace("\n", " ").replace("\r", " ")


def ensure_logs_dir(root_dir: str | Path) -> Path:
    logs_dir = Path(root_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def ensure_project_logs_dir(project_dir: str | Path) -> Path:
    logs_dir = Path(project_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def format_log_line(
    level: str,
    action: str,
    message: str,
    *,
    project_code: str = "system",
    data: dict[str, Any] | None = None,
) -> str:
    parts = [
        _now(),
        level.upper(),
        project_code or "system",
        action,
        message,
    ]
    base = " | ".join(parts)
    if data:
        extra = " | " + " ".join(f"{key}={_safe_value(value)}" for key, value in data.items())
        return base + extra
    return base


def write_log(
    root_dir: str | Path,
    *,
    level: str,
    action: str,
    message: str,
    project_code: str = "system",
    project_dir: str | Path | None = None,
    data: dict[str, Any] | None = None,
) -> str:
    """Записать строку лога и вернуть ее текст."""
    line = format_log_line(
        level=level,
        action=action,
        message=message,
        project_code=project_code,
        data=data,
    )

    logs_dir = ensure_logs_dir(root_dir)
    app_log = logs_dir / "app.log"
    with app_log.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")

    if project_dir is not None:
        project_logs_dir = ensure_project_logs_dir(project_dir)
        project_log = project_logs_dir / "project.log"
        with project_log.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    return line


def read_last_lines(path: str | Path, limit: int = 30) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[-limit:]
