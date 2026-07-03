#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Repository-слой Data Engine.

Это единственное место, где разрешена работа с SQL-запросами.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .database import connect, database_path, initialize_schema
from .models import DATABASE_SCHEMA_VERSION


class DataEngineRepository:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.db_path = database_path(self.project_dir)

    def initialize(self) -> Path:
        with connect(self.project_dir) as conn:
            initialize_schema(conn)
        return self.db_path

    def metadata(self) -> dict[str, str]:
        self.initialize()
        with connect(self.project_dir) as conn:
            rows = conn.execute("SELECT key, value FROM system_metadata ORDER BY key").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

    def tables(self) -> list[str]:
        self.initialize()
        with connect(self.project_dir) as conn:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        return [str(row["name"]) for row in rows]

    def status(self) -> dict[str, Any]:
        self.initialize()
        return {
            "db_path": str(self.db_path),
            "schema_version": DATABASE_SCHEMA_VERSION,
            "metadata": self.metadata(),
            "tables": self.tables(),
        }

    def save_project_snapshot(self, snapshot: dict[str, Any]) -> int:
        """Сохранить агрегированный snapshot попытки обновления и вернуть update_id."""
        self.initialize()
        created_at = snapshot.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        values = {
            "created_at": created_at,
            "update_result": snapshot.get("update_result", "SUCCESS"),
            "failure_reason": snapshot.get("failure_reason", ""),
            "apartments_total": int(snapshot.get("apartments_total", 0) or 0),
            "apartments_added": int(snapshot.get("apartments_added", 0) or 0),
            "apartments_removed": int(snapshot.get("apartments_removed", 0) or 0),
            "apartments_updated": int(snapshot.get("apartments_updated", 0) or 0),
            "updated_cells": int(snapshot.get("updated_cells", 0) or 0),
            "prices_changed": int(snapshot.get("prices_changed", 0) or 0),
            "changes_total": int(snapshot.get("changes_total", 0) or 0),
            "feed_size": int(snapshot.get("feed_size", 0) or 0),
            "feed_type": snapshot.get("feed_type", "") or "",
            "parser_version": snapshot.get("parser_version", "") or "",
            "update_duration_ms": int(snapshot.get("update_duration_ms", 0) or 0),
            "forced": 1 if snapshot.get("forced") else 0,
            "safety_has_warnings": 1 if snapshot.get("safety_has_warnings") else 0,
            "safety_has_critical": 1 if snapshot.get("safety_has_critical") else 0,
        }
        with connect(self.project_dir) as conn:
            cur = conn.execute(
                """
                INSERT INTO project_snapshot (
                    created_at,
                    update_result,
                    failure_reason,
                    apartments_total,
                    apartments_added,
                    apartments_removed,
                    apartments_updated,
                    updated_cells,
                    prices_changed,
                    changes_total,
                    feed_size,
                    feed_type,
                    parser_version,
                    update_duration_ms,
                    forced,
                    safety_has_warnings,
                    safety_has_critical
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    values["created_at"],
                    values["update_result"],
                    values["failure_reason"],
                    values["apartments_total"],
                    values["apartments_added"],
                    values["apartments_removed"],
                    values["apartments_updated"],
                    values["updated_cells"],
                    values["prices_changed"],
                    values["changes_total"],
                    values["feed_size"],
                    values["feed_type"],
                    values["parser_version"],
                    values["update_duration_ms"],
                    values["forced"],
                    values["safety_has_warnings"],
                    values["safety_has_critical"],
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def recent_snapshots(self, limit: int = 10) -> list[dict[str, Any]]:
        self.initialize()
        with connect(self.project_dir) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    created_at,
                    update_result,
                    failure_reason,
                    apartments_total,
                    apartments_added,
                    apartments_removed,
                    apartments_updated,
                    updated_cells,
                    prices_changed,
                    changes_total,
                    feed_size,
                    feed_type,
                    parser_version,
                    update_duration_ms,
                    forced,
                    safety_has_warnings,
                    safety_has_critical
                FROM project_snapshot
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]
    def save_apartment_events(self, update_id: int, events: list[dict[str, Any]]) -> int:
        """Сохранить события появления/исчезновения квартир."""
        self.initialize()
        if not events:
            return 0
        prepared = []
        for event in events:
            apt_id = str(event.get("apartment_id", "")).strip()
            event_type = str(event.get("event_type", "")).strip().upper()
            if not apt_id or not event_type:
                continue
            created_at = event.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prepared.append((int(update_id), apt_id, event_type, created_at))
        if not prepared:
            return 0
        with connect(self.project_dir) as conn:
            conn.executemany(
                """
                INSERT INTO apartment_events (update_id, apartment_id, event_type, created_at)
                VALUES (?, ?, ?, ?)
                """,
                prepared,
            )
            conn.commit()
        return len(prepared)

    def save_price_events(self, update_id: int, events: list[dict[str, Any]]) -> int:
        """Сохранить события изменения цены."""
        self.initialize()
        if not events:
            return 0
        prepared = []
        for event in events:
            apt_id = str(event.get("apartment_id", "")).strip()
            if not apt_id:
                continue
            created_at = event.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            prepared.append((
                int(update_id),
                apt_id,
                event.get("old_price"),
                event.get("new_price"),
                created_at,
            ))
        if not prepared:
            return 0
        with connect(self.project_dir) as conn:
            conn.executemany(
                """
                INSERT INTO price_events (update_id, apartment_id, old_price, new_price, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                prepared,
            )
            conn.commit()
        return len(prepared)

    def recent_apartment_events(self, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        with connect(self.project_dir) as conn:
            rows = conn.execute(
                """
                SELECT id, update_id, apartment_id, event_type, created_at
                FROM apartment_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def recent_price_events(self, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        with connect(self.project_dir) as conn:
            rows = conn.execute(
                """
                SELECT id, update_id, apartment_id, old_price, new_price, created_at
                FROM price_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]


    # v0.8.4 — read-only методы для сервисного слоя.
    def snapshots(self, limit: int | None = None, ascending: bool = True) -> list[dict[str, Any]]:
        self.initialize()
        order = "ASC" if ascending else "DESC"
        sql = f"""
            SELECT
                id,
                created_at,
                update_result,
                failure_reason,
                apartments_total,
                apartments_added,
                apartments_removed,
                apartments_updated,
                updated_cells,
                prices_changed,
                changes_total,
                feed_size,
                feed_type,
                parser_version,
                update_duration_ms,
                forced,
                safety_has_warnings,
                safety_has_critical
            FROM project_snapshot
            ORDER BY id {order}
        """
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (int(limit),)
        with connect(self.project_dir) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def snapshot_stats(self) -> dict[str, Any]:
        self.initialize()
        with connect(self.project_dir) as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS updates_total,
                    MIN(created_at) AS first_update,
                    MAX(created_at) AS last_update,
                    MAX(apartments_total) AS max_apartments,
                    MIN(apartments_total) AS min_apartments,
                    AVG(update_duration_ms) AS avg_update_duration_ms
                FROM project_snapshot
                """
            ).fetchone()
            latest = conn.execute(
                """
                SELECT id, created_at, apartments_total, update_result
                FROM project_snapshot
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        result = dict(row) if row else {}
        result["latest"] = dict(latest) if latest else None
        return result

    def apartment_events_for(self, apartment_id: str) -> list[dict[str, Any]]:
        self.initialize()
        with connect(self.project_dir) as conn:
            rows = conn.execute(
                """
                SELECT id, update_id, apartment_id, event_type, created_at
                FROM apartment_events
                WHERE apartment_id = ?
                ORDER BY id ASC
                """,
                (str(apartment_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def price_events_for(self, apartment_id: str) -> list[dict[str, Any]]:
        self.initialize()
        with connect(self.project_dir) as conn:
            rows = conn.execute(
                """
                SELECT id, update_id, apartment_id, old_price, new_price, created_at
                FROM price_events
                WHERE apartment_id = ?
                ORDER BY id ASC
                """,
                (str(apartment_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def all_price_events(self, limit: int | None = None, ascending: bool = True) -> list[dict[str, Any]]:
        self.initialize()
        order = "ASC" if ascending else "DESC"
        sql = f"""
            SELECT id, update_id, apartment_id, old_price, new_price, created_at
            FROM price_events
            ORDER BY id {order}
        """
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (int(limit),)
        with connect(self.project_dir) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def all_apartment_events(self, limit: int | None = None, ascending: bool = True) -> list[dict[str, Any]]:
        self.initialize()
        order = "ASC" if ascending else "DESC"
        sql = f"""
            SELECT id, update_id, apartment_id, event_type, created_at
            FROM apartment_events
            ORDER BY id {order}
        """
        params: tuple[Any, ...] = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (int(limit),)
        with connect(self.project_dir) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
