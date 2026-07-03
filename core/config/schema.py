#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Схема настроек проекта Feed Converter.

v0.9.0 Configuration Engine.
Задача схемы — хранить единые значения по умолчанию и постепенно
добавлять новые параметры в старые проекты без ручного редактирования.
"""

from __future__ import annotations

CONFIG_SCHEMA_VERSION = 1
CONFIG_ENGINE_VERSION = "0.9.1-configuration-engine-compatible"

DEFAULT_UPDATE_FIELDS: dict[str, bool] = {
    # Эти правила начнут использоваться в следующих версиях.
    # Пока Configuration Engine только хранит и нормализует настройки.
    "ID квартиры": True,
    "Отделка": True,
    "Цена": True,
    "Цена со скидкой": True,
    "Описание": True,
    "Планировка": True,
    "Телефон": True,
    "Изображения": True,
}

DEFAULT_SAFETY: dict[str, object] = {
    # Порог резкого падения количества квартир.
    # Например 0.5 означает: если квартир стало меньше чем 50% от прошлого числа,
    # Safety должен считать это критической ситуацией.
    "min_apartment_ratio": 0.5,
    "require_unique_ids": True,
    "require_non_empty_feed": True,
}

DEFAULT_REMINDERS: list[dict[str, object]] = []


def default_settings() -> dict[str, object]:
    return {
        "config_schema_version": CONFIG_SCHEMA_VERSION,
        "project_name": "",
        "project_code": "",
        "feed_type": "auto",
        "feed_format_last_detected": "",
        "feed_url": "",
        "feed_history": [],
        "main_excel": "lots.xlsx",
        "created_at": "",
        "last_update": "",
        "enabled": True,
        "update_fields": dict(DEFAULT_UPDATE_FIELDS),
        "safety": dict(DEFAULT_SAFETY),
        "reminders": list(DEFAULT_REMINDERS),
        "notes": "",
    }
