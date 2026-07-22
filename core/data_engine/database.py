#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Низкоуровневая работа с SQLite для Data Engine.

Важно: остальной код проекта не должен напрямую обращаться к sqlite3.
Для этого есть repository.py и engine.py.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .models import DATABASE_FILENAME, DATABASE_SCHEMA_VERSION


def history_dir(project_dir: str | Path) -> Path:
    path = Path(project_dir) / "history"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path(project_dir: str | Path) -> Path:
    return history_dir(project_dir) / DATABASE_FILENAME


def connect(project_dir: str | Path) -> sqlite3.Connection:
    db_path = database_path(project_dir)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _column_names(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _column_names(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def initialize_schema(conn: sqlite3.Connection) -> None:
    """Создать и обновить базовые таблицы Data Engine, если их еще нет."""
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS system_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS project_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            update_result TEXT NOT NULL DEFAULT 'SUCCESS',
            failure_reason TEXT NOT NULL DEFAULT '',
            apartments_total INTEGER NOT NULL DEFAULT 0,
            apartments_added INTEGER NOT NULL DEFAULT 0,
            apartments_removed INTEGER NOT NULL DEFAULT 0,
            apartments_updated INTEGER NOT NULL DEFAULT 0,
            updated_cells INTEGER NOT NULL DEFAULT 0,
            restored_excel_rows INTEGER NOT NULL DEFAULT 0,
            repaired_excel_apartments INTEGER NOT NULL DEFAULT 0,
            repaired_excel_cells INTEGER NOT NULL DEFAULT 0,
            prices_changed INTEGER NOT NULL DEFAULT 0,
            changes_total INTEGER NOT NULL DEFAULT 0,
            feed_size INTEGER NOT NULL DEFAULT 0,
            feed_type TEXT NOT NULL DEFAULT '',
            parser_version TEXT NOT NULL DEFAULT '',
            update_duration_ms INTEGER NOT NULL DEFAULT 0,
            forced INTEGER NOT NULL DEFAULT 0,
            safety_has_warnings INTEGER NOT NULL DEFAULT 0,
            safety_has_critical INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # Миграционная страховка для баз, созданных в v0.8.0.
    _ensure_column(conn, "project_snapshot", "update_result", "TEXT NOT NULL DEFAULT 'SUCCESS'")
    _ensure_column(conn, "project_snapshot", "failure_reason", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "project_snapshot", "apartments_updated", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "project_snapshot", "updated_cells", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "project_snapshot", "restored_excel_rows", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "project_snapshot", "repaired_excel_apartments", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "project_snapshot", "repaired_excel_cells", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "project_snapshot", "feed_type", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "project_snapshot", "parser_version", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(conn, "project_snapshot", "forced", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "project_snapshot", "safety_has_warnings", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "project_snapshot", "safety_has_critical", "INTEGER NOT NULL DEFAULT 0")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS apartment_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            update_id INTEGER,
            apartment_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(update_id) REFERENCES project_snapshot(id)
        )
        """
    )
    _ensure_column(conn, "apartment_events", "update_id", "INTEGER")
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apartment_events_apartment_id
        ON apartment_events(apartment_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_apartment_events_update_id
        ON apartment_events(update_id)
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS price_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            update_id INTEGER,
            apartment_id TEXT NOT NULL,
            old_price INTEGER,
            new_price INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(update_id) REFERENCES project_snapshot(id)
        )
        """
    )
    _ensure_column(conn, "price_events", "update_id", "INTEGER")
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_price_events_apartment_id
        ON price_events(apartment_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_price_events_update_id
        ON price_events(update_id)
        """
    )

    cur.execute(
        """
        INSERT OR REPLACE INTO system_metadata(key, value)
        VALUES('database_schema_version', ?)
        """,
        (str(DATABASE_SCHEMA_VERSION),),
    )

    conn.commit()
