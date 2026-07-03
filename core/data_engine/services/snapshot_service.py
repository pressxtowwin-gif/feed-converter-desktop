#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only сервис snapshots Data Engine.

Сервис ничего не записывает в базу. Он только превращает сырые записи
repository в удобные структуры для консольного менеджера и будущего GUI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..repository import DataEngineRepository


class SnapshotService:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.repository = DataEngineRepository(self.project_dir)

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.repository.snapshots(limit=limit, ascending=False)

    def apartment_count_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        rows = self.repository.snapshots(limit=limit, ascending=True)
        return [
            {
                "update_id": row.get("id"),
                "created_at": row.get("created_at"),
                "apartments_total": row.get("apartments_total"),
                "update_result": row.get("update_result"),
            }
            for row in rows
        ]
