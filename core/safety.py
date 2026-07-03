#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.safety

Safety-проверки перед обновлением Excel по XML-фиду.

Главный принцип:
- Safety не меняет Excel и XML.
- Safety только анализирует входные данные и возвращает отчет.
- Критические ситуации требуют подтверждения человека.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .excel_table import read_existing_rows_by_id, normalize_id

SAFETY_VERSION = "0.7-safety-foundation"


@dataclass
class SafetyMessage:
    level: str  # INFO / WARNING / CRITICAL
    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SafetyReport:
    project_code: str
    xml_path: str
    feed_format: str
    xml_size_bytes: int
    feed_rows: int
    excel_rows_before: int | None = None
    messages: list[SafetyMessage] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        return any(m.level == "CRITICAL" for m in self.messages)

    @property
    def has_warnings(self) -> bool:
        return any(m.level == "WARNING" for m in self.messages)

    def add(self, level: str, code: str, message: str, **details: Any) -> None:
        self.messages.append(SafetyMessage(level=level, code=code, message=message, details=details))

    def to_dict(self) -> dict[str, Any]:
        return {
            "safety_version": SAFETY_VERSION,
            "project_code": self.project_code,
            "xml_path": self.xml_path,
            "feed_format": self.feed_format,
            "xml_size_bytes": self.xml_size_bytes,
            "feed_rows": self.feed_rows,
            "excel_rows_before": self.excel_rows_before,
            "has_critical": self.has_critical,
            "has_warnings": self.has_warnings,
            "messages": [
                {
                    "level": m.level,
                    "code": m.code,
                    "message": m.message,
                    "details": m.details,
                }
                for m in self.messages
            ],
        }

    def format_for_console(self) -> str:
        lines: list[str] = []
        lines.append("Проверка безопасности перед обновлением")
        lines.append("-" * 60)
        lines.append(f"Версия Safety: {SAFETY_VERSION}")
        lines.append(f"Проект: {self.project_code}")
        lines.append(f"Формат фида: {self.feed_format}")
        lines.append(f"Размер XML: {self.xml_size_bytes} байт")
        lines.append(f"Квартир в XML: {self.feed_rows}")
        if self.excel_rows_before is not None:
            lines.append(f"Квартир в Excel до обновления: {self.excel_rows_before}")
        lines.append("-" * 60)
        if not self.messages:
            lines.append("OK: критических предупреждений нет.")
        else:
            for m in self.messages:
                prefix = {"INFO": "ℹ", "WARNING": "⚠", "CRITICAL": "❌"}.get(m.level, "-")
                lines.append(f"{prefix} [{m.level}] {m.message}")
                if m.details:
                    parts = ", ".join(f"{k}={v}" for k, v in m.details.items())
                    lines.append(f"   {parts}")
        lines.append("-" * 60)
        if self.has_critical:
            lines.append("Есть критические предупреждения. Нужно подтверждение человека.")
        elif self.has_warnings:
            lines.append("Есть предупреждения, но обновление можно продолжать.")
        else:
            lines.append("Обновление можно продолжать.")
        return "\n".join(lines)


class SafetyCriticalError(RuntimeError):
    """Ошибка-блокировка обновления до подтверждения человека."""

    def __init__(self, report: SafetyReport):
        super().__init__("Safety обнаружил критические предупреждения")
        self.report = report


def _count_feed_ids(rows: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    missing = 0
    for row in rows:
        apt_id = normalize_id(row.get("ID квартиры"))
        if not apt_id:
            missing += 1
            continue
        if apt_id in seen:
            duplicates.add(apt_id)
        seen.add(apt_id)
    return missing, len(duplicates), sorted(duplicates)


def run_safety_checks(
    *,
    project_code: str,
    xml_path: str | Path,
    rows: list[dict[str, Any]],
    feed_format: str,
    excel_path: str | Path | None = None,
    critical_drop_percent: float = 50.0,
    tiny_xml_bytes: int = 1024,
) -> SafetyReport:
    """Запускает базовые safety-проверки.

    critical_drop_percent=50 означает: если квартир в XML стало на 50% или больше меньше,
    чем в Excel, это критическое предупреждение и обновление требует подтверждения.
    """

    xml_path = Path(xml_path)
    xml_size = xml_path.stat().st_size if xml_path.exists() else 0
    report = SafetyReport(
        project_code=project_code,
        xml_path=str(xml_path),
        feed_format=feed_format or "unknown",
        xml_size_bytes=xml_size,
        feed_rows=len(rows),
    )

    if not xml_path.exists():
        report.add("CRITICAL", "xml_missing", "XML-файл не найден", xml_path=str(xml_path))
        return report

    if xml_size == 0:
        report.add("CRITICAL", "xml_empty", "XML-файл пустой", xml_path=str(xml_path))
    elif xml_size < tiny_xml_bytes:
        report.add("WARNING", "xml_tiny", "XML-файл подозрительно маленький", bytes=xml_size)

    if not feed_format or feed_format == "unknown":
        report.add("CRITICAL", "unknown_format", "Не удалось определить формат фида")

    if len(rows) == 0:
        report.add("CRITICAL", "no_apartments", "В фиде не найдено ни одной квартиры")

    missing_ids, duplicate_count, duplicate_examples = _count_feed_ids(rows)
    if missing_ids > 0:
        report.add("CRITICAL", "missing_ids", "В фиде есть квартиры без ID", count=missing_ids)
    if duplicate_count > 0:
        report.add(
            "CRITICAL",
            "duplicate_ids",
            "В фиде найдены дублирующиеся ID квартир",
            duplicate_count=duplicate_count,
            examples=duplicate_examples[:10],
        )

    if excel_path is not None and Path(excel_path).exists():
        try:
            existing_by_id, _old_columns, excel_rows_before = read_existing_rows_by_id(excel_path)
            report.excel_rows_before = excel_rows_before
            feed_ids = {normalize_id(row.get("ID квартиры")) for row in rows if normalize_id(row.get("ID квартиры"))}

            if excel_rows_before > 0:
                drop = excel_rows_before - len(feed_ids)
                if drop > 0:
                    drop_percent = (drop / excel_rows_before) * 100
                    if drop_percent >= critical_drop_percent:
                        report.add(
                            "CRITICAL",
                            "large_apartment_drop",
                            "Количество квартир в XML резко меньше, чем в текущей таблице",
                            excel_rows_before=excel_rows_before,
                            feed_rows=len(feed_ids),
                            drop=drop,
                            drop_percent=round(drop_percent, 2),
                        )
                    elif drop_percent >= 20:
                        report.add(
                            "WARNING",
                            "noticeable_apartment_drop",
                            "Количество квартир в XML заметно меньше, чем в текущей таблице",
                            excel_rows_before=excel_rows_before,
                            feed_rows=len(feed_ids),
                            drop=drop,
                            drop_percent=round(drop_percent, 2),
                        )

            if existing_by_id and len(feed_ids) > 0:
                overlap = len(set(existing_by_id) & feed_ids)
                overlap_percent = (overlap / len(existing_by_id)) * 100
                if overlap_percent < 50:
                    report.add(
                        "CRITICAL",
                        "low_id_overlap",
                        "Менее половины ID из текущей таблицы найдены в XML. Возможно, ссылка ведет не на тот фид",
                        excel_ids=len(existing_by_id),
                        feed_ids=len(feed_ids),
                        overlap=overlap,
                        overlap_percent=round(overlap_percent, 2),
                    )
        except Exception as exc:
            report.add("WARNING", "excel_read_warning", "Не удалось прочитать Excel для сравнения с фидом", error=str(exc))

    return report
