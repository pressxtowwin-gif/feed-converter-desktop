#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only сервис истории цен."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..repository import DataEngineRepository


class PriceService:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.repository = DataEngineRepository(self.project_dir)

    def history_for_apartment(self, apartment_id: str) -> list[dict[str, Any]]:
        return self.repository.price_events_for(str(apartment_id))

    def recent_changes(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.repository.all_price_events(limit=limit, ascending=False)

    def changes_count_for_apartment(self, apartment_id: str) -> int:
        return len(self.history_for_apartment(apartment_id))

    def latest_known_price_for_apartment(self, apartment_id: str) -> Any:
        events = self.history_for_apartment(apartment_id)
        if not events:
            return None
        return events[-1].get("new_price")
