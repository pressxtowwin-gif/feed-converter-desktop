#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core.backup — резервные копии рабочих Excel-таблиц."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


def backup_excel(project_dir: str | Path, excel_path: str | Path) -> Path:
    project_dir = Path(project_dir)
    excel_path = Path(excel_path)
    backup_dir = project_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = backup_dir / f"{excel_path.stem}_backup_{timestamp}{excel_path.suffix}"
    shutil.copy2(excel_path, backup_path)
    return backup_path
