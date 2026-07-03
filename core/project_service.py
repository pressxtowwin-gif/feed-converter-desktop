#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.project_service
Операции над проектами ЖК: создание, обновление, загрузка фида, настройки.
"""

from __future__ import annotations

import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .backup import backup_excel
from .downloader import download_url_to_file, is_url
from .excel_table import create_excel_from_feed_rows, update_excel_from_feed_rows
from .feed_parser import load_xml, parse_universal
from .settings import normalize_settings, read_settings, write_settings
from .config import config_status as get_project_config_status, CONFIG_ENGINE_VERSION
from .integrity import ensure_project_structure, doctor_project, INTEGRITY_ENGINE_VERSION
from .logger import write_log, LOG_VERSION
from .safety import run_safety_checks, SafetyCriticalError, SAFETY_VERSION
from .data_engine import (
    initialize_project_data_engine,
    save_project_snapshot,
    recent_project_snapshots,
    save_apartment_events,
    save_price_events,
    recent_project_events,
    recent_project_price_events,
    DATA_ENGINE_VERSION,
    PARSER_VERSION,
    SnapshotService,
    ApartmentService,
    PriceService,
    StatisticsService,
)



def _root_from_projects_dir(projects_dir: str | Path) -> Path:
    # Обычно projects_dir = <root>/projects. Значит root = parent.
    return Path(projects_dir).resolve().parent

def safe_project_code(name: str) -> str:
    # Минимальная транслитерация под рабочие названия ЖК.
    mapping = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
        "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    value = name.strip().lower()
    value = value.replace("жк", "")
    value = "".join(mapping.get(ch, ch) for ch in value)
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "project"


def ensure_project_dirs(project_dir: str | Path) -> None:
    project_dir = Path(project_dir)
    (project_dir / "xml").mkdir(parents=True, exist_ok=True)
    (project_dir / "xml" / "archive").mkdir(parents=True, exist_ok=True)
    (project_dir / "tables").mkdir(parents=True, exist_ok=True)
    (project_dir / "backups").mkdir(parents=True, exist_ok=True)
    (project_dir / "history").mkdir(parents=True, exist_ok=True)


def list_projects(projects_dir: str | Path) -> list[dict[str, Any]]:
    projects_dir = Path(projects_dir)
    result: list[dict[str, Any]] = []
    if not projects_dir.exists():
        return result

    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        ensure_project_structure(project_dir)
        settings = normalize_settings(read_settings(project_dir))
        result.append({
            "code": project_dir.name,
            "name": settings.get("project_name", project_dir.name),
            "feed_url": settings.get("feed_url", ""),
            "main_excel": settings.get("main_excel", ""),
            "last_update": settings.get("last_update", ""),
            "enabled": settings.get("enabled", True),
        })
    return result


def create_project(
    projects_dir: str | Path,
    project_name: str,
    source: str,
    excel_name: str = "lots.xlsx",
    project_code: str | None = None,
) -> dict[str, Any]:
    projects_dir = Path(projects_dir)
    project_code = project_code or safe_project_code(project_name)
    project_dir = projects_dir / project_code

    if project_dir.exists():
        raise FileExistsError(f"Проект уже существует: {project_dir}")

    ensure_project_dirs(project_dir)

    # Источник может быть ссылкой или локальным XML.
    xml_path = project_dir / "xml" / "current.xml"
    if is_url(source):
        downloaded_bytes = download_url_to_file(source, xml_path)
        feed_url = source
    else:
        src_path = Path(source).expanduser()
        if not src_path.is_absolute():
            src_path = Path.cwd() / src_path
        if not src_path.exists():
            raise FileNotFoundError(f"XML-файл не найден: {src_path}")
        shutil.copy2(src_path, xml_path)
        downloaded_bytes = xml_path.stat().st_size
        feed_url = ""

    xml_bytes = load_xml(str(xml_path))
    rows, columns, feed_format = parse_universal(xml_bytes)

    excel_path = project_dir / "tables" / excel_name
    create_excel_from_feed_rows(rows, columns, excel_path)

    settings = {
        "project_name": project_name,
        "project_code": project_code,
        "feed_type": "auto",
        "feed_format_last_detected": feed_format,
        "feed_url": feed_url,
        "feed_history": [],
        "main_excel": excel_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_update": "",
        "enabled": True,
    }
    # v0.9.0: write_settings автоматически добавляет недостающие поля
    # Configuration Engine: update_fields, safety, reminders и версию схемы.
    write_settings(project_dir, settings)
    integrity_status = ensure_project_structure(project_dir)

    # v0.8.0: создаем фундамент Data Engine. Историю пока не записываем.
    data_engine_status = initialize_project_data_engine(project_dir)

    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="create_project",
        message="Проект создан",
        project_code=project_code,
        project_dir=project_dir,
        data={
            "project_name": project_name,
            "feed_format": feed_format,
            "rows": len(rows),
            "excel": str(excel_path),
            "xml": str(xml_path),
            "logger_version": LOG_VERSION,
            "data_engine_version": DATA_ENGINE_VERSION,
            "history_db": data_engine_status.get("db_path"),
            "config_engine_version": CONFIG_ENGINE_VERSION,
            "integrity_engine_version": INTEGRITY_ENGINE_VERSION,
            "integrity_actions": integrity_status.get("actions", []),
        },
    )

    return {
        "project_dir": str(project_dir),
        "project_code": project_code,
        "project_name": project_name,
        "xml_path": str(xml_path),
        "excel_path": str(excel_path),
        "downloaded_bytes": downloaded_bytes,
        "feed_format": feed_format,
        "rows": len(rows),
        "data_engine": data_engine_status,
    }


def set_feed_url(projects_dir: str | Path, project_code: str, new_url: str) -> dict[str, Any]:
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    settings = normalize_settings(read_settings(project_dir))

    old_url = settings.get("feed_url", "")
    if old_url and old_url != new_url:
        history = settings.setdefault("feed_history", [])
        if old_url not in history:
            history.append(old_url)

    settings["feed_url"] = new_url
    write_settings(project_dir, settings)
    integrity_status = ensure_project_structure(project_dir)

    # v0.8.0: создаем фундамент Data Engine. Историю пока не записываем.
    data_engine_status = initialize_project_data_engine(project_dir)

    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="set_feed_url",
        message="XML-ссылка проекта изменена",
        project_code=project_code,
        project_dir=project_dir,
        data={"old_url": old_url, "new_url": new_url},
    )
    return {"old_url": old_url, "new_url": new_url, "project_code": project_code}


def download_feed(projects_dir: str | Path, project_code: str) -> dict[str, Any]:
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    settings = normalize_settings(read_settings(project_dir))
    feed_url = settings.get("feed_url", "")
    if not feed_url:
        raise ValueError("В settings.json не указана feed_url. Используйте set-feed.")

    xml_path = project_dir / "xml" / "current.xml"
    # Архивируем старый current.xml, если есть.
    if xml_path.exists():
        archive_dir = project_dir / "xml" / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        archive_path = archive_dir / f"current_{timestamp}.xml"
        shutil.copy2(xml_path, archive_path)

    size = download_url_to_file(feed_url, xml_path)

    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="download_feed",
        message="XML-фид скачан",
        project_code=project_code,
        project_dir=project_dir,
        data={"bytes": size, "xml_path": str(xml_path), "feed_url": feed_url},
    )
    return {"xml_path": str(xml_path), "bytes": size, "feed_url": feed_url}


def update_project(projects_dir: str | Path, project_code: str, *, download: bool = True, force: bool = False) -> dict[str, Any]:
    started_at = time.perf_counter()
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    settings = normalize_settings(read_settings(project_dir))

    if download and settings.get("feed_url"):
        download_info = download_feed(projects_dir, project_code)
        xml_source = download_info["xml_path"]
    else:
        download_info = None
        xml_source = project_dir / "xml" / "current.xml"
        if not Path(xml_source).exists():
            raise FileNotFoundError(f"Не найден XML: {xml_source}")

    excel_path = project_dir / "tables" / settings.get("main_excel", "lots.xlsx")
    if not excel_path.exists():
        raise FileNotFoundError(f"Не найдена основная таблица: {excel_path}")

    xml_bytes = load_xml(str(xml_source))
    rows, columns, feed_format = parse_universal(xml_bytes)

    safety_report = run_safety_checks(
        project_code=project_code,
        xml_path=xml_source,
        rows=rows,
        feed_format=feed_format,
        excel_path=excel_path,
    )

    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO" if not safety_report.has_critical else "WARNING",
        action="safety_check",
        message="Safety-проверка перед обновлением",
        project_code=project_code,
        project_dir=project_dir,
        data=safety_report.to_dict(),
    )

    if safety_report.has_critical and not force:
        # v0.8.1: заблокированная Safety попытка обновления фиксируется как FAILED snapshot.
        try:
            update_duration_ms = int((time.perf_counter() - started_at) * 1000)
            failed_update_id = save_project_snapshot(project_dir, {
                "update_result": "FAILED",
                "failure_reason": "Safety critical warning",
                "apartments_total": len(rows),
                "apartments_added": 0,
                "apartments_removed": 0,
                "apartments_updated": 0,
                "updated_cells": 0,
                "prices_changed": 0,
                "changes_total": 0,
                "feed_size": Path(xml_source).stat().st_size if Path(xml_source).exists() else 0,
                "feed_type": feed_format,
                "parser_version": PARSER_VERSION,
                "update_duration_ms": update_duration_ms,
                "forced": False,
                "safety_has_warnings": safety_report.has_warnings,
                "safety_has_critical": safety_report.has_critical,
            })
            write_log(
                _root_from_projects_dir(projects_dir),
                level="WARNING",
                action="data_engine_snapshot_failed",
                message="Data Engine записал FAILED snapshot из-за Safety",
                project_code=project_code,
                project_dir=project_dir,
                data={"update_id": failed_update_id, "data_engine_version": DATA_ENGINE_VERSION},
            )
        except Exception as history_exc:
            write_log(
                _root_from_projects_dir(projects_dir),
                level="WARNING",
                action="data_engine_snapshot_error",
                message="Не удалось записать FAILED snapshot",
                project_code=project_code,
                project_dir=project_dir,
                data={"error": str(history_exc), "data_engine_version": DATA_ENGINE_VERSION},
            )
        raise SafetyCriticalError(safety_report)

    backup_path = backup_excel(project_dir, excel_path)

    result = update_excel_from_feed_rows(rows, columns, excel_path, excel_path)

    settings["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    settings["feed_format_last_detected"] = feed_format
    write_settings(project_dir, settings)

    # v0.8.1: Data Engine записывает агрегированный snapshot попытки обновления.
    data_engine_status = initialize_project_data_engine(project_dir)
    update_duration_ms = int((time.perf_counter() - started_at) * 1000)
    changes_total = int(result.get("added", 0) or 0) + int(result.get("deleted", 0) or 0) + int(result.get("updated_cells", 0) or 0)
    try:
        update_id = save_project_snapshot(project_dir, {
            "update_result": "SUCCESS",
            "failure_reason": "",
            "apartments_total": result.get("excel_rows_after", len(rows)),
            "apartments_added": result.get("added", 0),
            "apartments_removed": result.get("deleted", 0),
            "apartments_updated": result.get("updated_apartments", 0),
            "updated_cells": result.get("updated_cells", 0),
            "prices_changed": result.get("prices_changed", 0),
            "changes_total": changes_total,
            "feed_size": Path(xml_source).stat().st_size if Path(xml_source).exists() else 0,
            "feed_type": feed_format,
            "parser_version": PARSER_VERSION,
            "update_duration_ms": update_duration_ms,
            "forced": force,
            "safety_has_warnings": safety_report.has_warnings,
            "safety_has_critical": safety_report.has_critical,
        })
        data_engine_status["last_update_id"] = update_id

        # v0.8.2 / v0.8.3: записываем только события изменений, без ежедневных полных снимков квартир.
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        apartment_events = []
        for apt_id in result.get("added_ids", []) or []:
            apartment_events.append({"apartment_id": apt_id, "event_type": "APPEARED", "created_at": now_str})
        for apt_id in result.get("deleted_ids", []) or []:
            apartment_events.append({"apartment_id": apt_id, "event_type": "REMOVED", "created_at": now_str})

        price_events = []
        for item in result.get("price_changes", []) or []:
            price_events.append({
                "apartment_id": item.get("ID квартиры", ""),
                "old_price": item.get("old_price", ""),
                "new_price": item.get("new_price", ""),
                "created_at": now_str,
            })

        saved_apartment_events = save_apartment_events(project_dir, update_id, apartment_events)
        saved_price_events = save_price_events(project_dir, update_id, price_events)
        data_engine_status["saved_apartment_events"] = saved_apartment_events
        data_engine_status["saved_price_events"] = saved_price_events
    except Exception as history_exc:
        update_id = None
        write_log(
            _root_from_projects_dir(projects_dir),
            level="WARNING",
            action="data_engine_snapshot_error",
            message="Excel обновлен, но snapshot Data Engine записать не удалось",
            project_code=project_code,
            project_dir=project_dir,
            data={"error": str(history_exc), "data_engine_version": DATA_ENGINE_VERSION},
        )

    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="update_project",
        message="Проект обновлен",
        project_code=project_code,
        project_dir=project_dir,
        data={
            "feed_format": feed_format,
            "feed_rows": len(rows),
            "excel_rows_before": result.get("excel_rows_before"),
            "excel_rows_after": result.get("excel_rows_after"),
            "deleted": result.get("deleted"),
            "added": result.get("added"),
            "updated_apartments": result.get("updated_apartments"),
            "updated_cells": result.get("updated_cells"),
            "backup": str(backup_path),
            "safety": safety_report.to_dict(),
            "safety_version": SAFETY_VERSION,
            "force": force,
            "data_engine_version": DATA_ENGINE_VERSION,
            "history_db": data_engine_status.get("db_path"),
            "config_engine_version": CONFIG_ENGINE_VERSION,
            "update_id": data_engine_status.get("last_update_id"),
            "saved_apartment_events": data_engine_status.get("saved_apartment_events", 0),
            "saved_price_events": data_engine_status.get("saved_price_events", 0),
            "parser_version": PARSER_VERSION,
            "update_duration_ms": update_duration_ms,
        },
    )

    result.update({
        "project_code": project_code,
        "project_name": settings.get("project_name", project_code),
        "feed_format": feed_format,
        "excel_path": str(excel_path),
        "backup_path": str(backup_path),
        "download_info": download_info,
        "safety_report": safety_report.to_dict(),
        "safety_has_critical": safety_report.has_critical,
        "safety_has_warnings": safety_report.has_warnings,
        "safety_version": SAFETY_VERSION,
        "force": force,
        "data_engine": data_engine_status,
        "data_engine_version": DATA_ENGINE_VERSION,
        "update_id": data_engine_status.get("last_update_id"),
        "saved_apartment_events": data_engine_status.get("saved_apartment_events", 0),
        "saved_price_events": data_engine_status.get("saved_price_events", 0),
        "parser_version": PARSER_VERSION,
        "update_duration_ms": locals().get("update_duration_ms", 0),
    })
    return result


def project_snapshots(projects_dir: str | Path, project_code: str, limit: int = 10) -> list[dict[str, Any]]:
    """Показать последние snapshots Data Engine по проекту."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)
    rows = recent_project_snapshots(project_dir, limit=limit)
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_snapshots",
        message="Запрошены snapshots проекта",
        project_code=project_code,
        project_dir=project_dir,
        data={"limit": limit, "count": len(rows), "data_engine_version": DATA_ENGINE_VERSION},
    )
    return rows


def project_events(projects_dir: str | Path, project_code: str, limit: int = 20) -> list[dict[str, Any]]:
    """Показать последние события появления/исчезновения квартир."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)
    rows = recent_project_events(project_dir, limit=limit)
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_events",
        message="Запрошены события квартир проекта",
        project_code=project_code,
        project_dir=project_dir,
        data={"limit": limit, "count": len(rows), "data_engine_version": DATA_ENGINE_VERSION},
    )
    return rows


def project_price_events(projects_dir: str | Path, project_code: str, limit: int = 20) -> list[dict[str, Any]]:
    """Показать последние события изменения цен."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)
    rows = recent_project_price_events(project_dir, limit=limit)
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_price_events",
        message="Запрошены события изменения цен проекта",
        project_code=project_code,
        project_dir=project_dir,
        data={"limit": limit, "count": len(rows), "data_engine_version": DATA_ENGINE_VERSION},
    )
    return rows


def data_engine_status(projects_dir: str | Path, project_code: str) -> dict[str, Any]:
    """Инициализировать и показать статус Data Engine проекта."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    status = initialize_project_data_engine(project_dir)
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="data_engine_status",
        message="Проверен статус Data Engine",
        project_code=project_code,
        project_dir=project_dir,
        data={
            "data_engine_version": DATA_ENGINE_VERSION,
            "history_db": status.get("db_path"),
            "schema_version": status.get("schema_version"),
        },
    )
    return status


def data_services_status(projects_dir: str | Path, project_code: str) -> dict[str, Any]:
    """v0.8.4: Проверка read-only сервисного слоя Data Engine.

    Это диагностическая функция: она не записывает данные в базу и не меняет Excel.
    """
    from .data_engine import SnapshotService, ApartmentService, PriceService, StatisticsService

    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)

    snapshot_service = SnapshotService(project_dir)
    price_service = PriceService(project_dir)
    statistics_service = StatisticsService(project_dir)
    # ApartmentService создаем для проверки импорта и готовности к будущему GUI/API.
    apartment_service = ApartmentService(project_dir)

    recent_snapshots = snapshot_service.recent(limit=3)
    recent_prices = price_service.recent_changes(limit=3)
    summary = statistics_service.project_summary()

    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="data_services_status",
        message="Проверен сервисный слой Data Engine",
        project_code=project_code,
        project_dir=project_dir,
        data={
            "data_engine_version": DATA_ENGINE_VERSION,
            "recent_snapshots": len(recent_snapshots),
            "recent_prices": len(recent_prices),
            "apartment_service_ready": apartment_service is not None,
        },
    )

    return {
        "data_engine_version": DATA_ENGINE_VERSION,
        "services": [
            "SnapshotService",
            "ApartmentService",
            "PriceService",
            "StatisticsService",
        ],
        "recent_snapshots_count": len(recent_snapshots),
        "recent_price_changes_count": len(recent_prices),
        "summary": summary,
    }



def project_statistics(projects_dir: str | Path, project_code: str) -> dict[str, Any]:
    """v0.8.5: Общая статистика проекта через read-only сервисный слой."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)
    service = StatisticsService(project_dir)
    stats = service.project_summary()
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_statistics",
        message="Запрошена статистика проекта",
        project_code=project_code,
        project_dir=project_dir,
        data={"data_engine_version": DATA_ENGINE_VERSION},
    )
    return stats


def project_apartment_count_history(projects_dir: str | Path, project_code: str, limit: int = 30) -> list[dict[str, Any]]:
    """v0.8.5: Динамика количества квартир по snapshots."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)
    service = SnapshotService(project_dir)
    normalized_limit = None if int(limit or 0) <= 0 else int(limit)
    rows = service.apartment_count_history(limit=normalized_limit)
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_apartment_count_history",
        message="Запрошена динамика количества квартир",
        project_code=project_code,
        project_dir=project_dir,
        data={"limit": limit, "count": len(rows), "data_engine_version": DATA_ENGINE_VERSION},
    )
    return rows


def project_apartment_details(projects_dir: str | Path, project_code: str, apartment_id: str) -> dict[str, Any]:
    """v0.8.5: История и жизненный цикл конкретной квартиры."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)
    service = ApartmentService(project_dir)
    details = service.lifecycle_summary(str(apartment_id))
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_apartment_details",
        message="Запрошена история квартиры",
        project_code=project_code,
        project_dir=project_dir,
        data={"apartment_id": str(apartment_id), "data_engine_version": DATA_ENGINE_VERSION},
    )
    return details


def project_price_history(projects_dir: str | Path, project_code: str, apartment_id: str) -> list[dict[str, Any]]:
    """v0.8.5: История изменения цены конкретной квартиры."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    initialize_project_data_engine(project_dir)
    service = PriceService(project_dir)
    rows = service.history_for_apartment(str(apartment_id))
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_price_history",
        message="Запрошена история цены квартиры",
        project_code=project_code,
        project_dir=project_dir,
        data={"apartment_id": str(apartment_id), "count": len(rows), "data_engine_version": DATA_ENGINE_VERSION},
    )
    return rows


def project_integrity_doctor(projects_dir: str | Path, project_code: str) -> dict[str, Any]:
    project_dir = Path(projects_dir) / project_code
    result = doctor_project(project_dir)
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_integrity_doctor",
        message="Проверена и восстановлена структура проекта",
        project_code=project_code,
        project_dir=project_dir,
        data={"actions": result.get("actions", []), "integrity_engine_version": INTEGRITY_ENGINE_VERSION},
    )
    return result


def project_config_status(projects_dir: str | Path, project_code: str) -> dict[str, Any]:
    """v0.9.0: Проверить и автоматически мигрировать настройки проекта."""
    project_dir = Path(projects_dir) / project_code
    ensure_project_structure(project_dir)
    status = get_project_config_status(project_dir)
    write_log(
        _root_from_projects_dir(projects_dir),
        level="INFO",
        action="project_config_status",
        message="Проверен Configuration Engine проекта",
        project_code=project_code,
        project_dir=project_dir,
        data={
            "config_engine_version": CONFIG_ENGINE_VERSION,
            "schema_version": status.get("schema_version"),
            "is_valid": status.get("is_valid"),
            "errors": status.get("errors", []),
        },
    )
    return status
