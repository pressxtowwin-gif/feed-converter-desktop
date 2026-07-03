#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only сервис жизненного цикла квартиры."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from ..repository import DataEngineRepository
from .price_service import PriceService

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), DATE_FORMAT)
    except ValueError:
        return None


class ApartmentService:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.repository = DataEngineRepository(self.project_dir)
        self.price_service = PriceService(project_dir)

    def events_for_apartment(self, apartment_id: str) -> list[dict[str, Any]]:
        return self.repository.apartment_events_for(str(apartment_id))

    def lifecycle_summary(self, apartment_id: str) -> dict[str, Any]:
        events = self.events_for_apartment(apartment_id)
        appeared = [e for e in events if str(e.get("event_type", "")).upper() == "APPEARED"]
        removed = [e for e in events if str(e.get("event_type", "")).upper() == "REMOVED"]

        first_seen = appeared[0].get("created_at") if appeared else None
        removed_at = removed[-1].get("created_at") if removed else None
        last_event_at = events[-1].get("created_at") if events else None

        first_dt = _parse_dt(first_seen)
        end_dt = _parse_dt(removed_at) or _parse_dt(last_event_at)
        days_in_feed = None
        if first_dt and end_dt:
            days_in_feed = max((end_dt - first_dt).days, 0)

        price_events = self.price_service.history_for_apartment(apartment_id)
        return {
            "apartment_id": str(apartment_id),
            "first_seen": first_seen,
            "removed_at": removed_at,
            "last_event_at": last_event_at,
            "status": "removed" if removed_at else ("active_or_unknown" if first_seen else "unknown"),
            "days_in_feed": days_in_feed,
            "events_count": len(events),
            "price_changes_count": len(price_events),
            "latest_known_price": price_events[-1].get("new_price") if price_events else None,
            "events": events,
            "price_events": price_events,
        }
