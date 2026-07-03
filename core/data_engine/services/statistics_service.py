#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only сервис общей статистики проекта."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..repository import DataEngineRepository


class StatisticsService:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.repository = DataEngineRepository(self.project_dir)

    def project_summary(self) -> dict[str, Any]:
        stats = self.repository.snapshot_stats()
        latest = stats.get("latest") or {}
        return {
            "updates_total": stats.get("updates_total") or 0,
            "first_update": stats.get("first_update"),
            "last_update": stats.get("last_update"),
            "current_apartments": latest.get("apartments_total"),
            "latest_update_id": latest.get("id"),
            "latest_update_result": latest.get("update_result"),
            "max_apartments": stats.get("max_apartments"),
            "min_apartments": stats.get("min_apartments"),
            "avg_update_duration_ms": stats.get("avg_update_duration_ms"),
        }
