#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Высокоуровневый фасад Data Engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import DATA_ENGINE_VERSION
from .repository import DataEngineRepository


class DataEngine:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.repository = DataEngineRepository(self.project_dir)

    def initialize(self) -> Path:
        return self.repository.initialize()

    def status(self) -> dict[str, Any]:
        result = self.repository.status()
        result["data_engine_version"] = DATA_ENGINE_VERSION
        return result

    def save_project_snapshot(self, snapshot: dict[str, Any]) -> int:
        return self.repository.save_project_snapshot(snapshot)

    def recent_snapshots(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.repository.recent_snapshots(limit=limit)

    def save_apartment_events(self, update_id: int, events: list[dict[str, Any]]) -> int:
        return self.repository.save_apartment_events(update_id, events)

    def save_price_events(self, update_id: int, events: list[dict[str, Any]]) -> int:
        return self.repository.save_price_events(update_id, events)

    def recent_apartment_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.repository.recent_apartment_events(limit=limit)

    def recent_price_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.repository.recent_price_events(limit=limit)


def initialize_project_data_engine(project_dir: str | Path) -> dict[str, Any]:
    engine = DataEngine(project_dir)
    db_path = engine.initialize()
    status = engine.status()
    status["db_path"] = str(db_path)
    return status


def save_project_snapshot(project_dir: str | Path, snapshot: dict[str, Any]) -> int:
    engine = DataEngine(project_dir)
    engine.initialize()
    return engine.save_project_snapshot(snapshot)


def recent_project_snapshots(project_dir: str | Path, limit: int = 10) -> list[dict[str, Any]]:
    engine = DataEngine(project_dir)
    engine.initialize()
    return engine.recent_snapshots(limit=limit)


def save_apartment_events(project_dir: str | Path, update_id: int, events: list[dict[str, Any]]) -> int:
    engine = DataEngine(project_dir)
    engine.initialize()
    return engine.save_apartment_events(update_id, events)


def save_price_events(project_dir: str | Path, update_id: int, events: list[dict[str, Any]]) -> int:
    engine = DataEngine(project_dir)
    engine.initialize()
    return engine.save_price_events(update_id, events)


def recent_project_events(project_dir: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    engine = DataEngine(project_dir)
    engine.initialize()
    return engine.recent_apartment_events(limit=limit)


def recent_project_price_events(project_dir: str | Path, limit: int = 20) -> list[dict[str, Any]]:
    engine = DataEngine(project_dir)
    engine.initialize()
    return engine.recent_price_events(limit=limit)
