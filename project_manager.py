#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
project_manager.py
Версия: 0.9.3-gui-foundation

Менеджер проектов ЖК для локального XML→Excel конвертера.

Команды:
    python3 project_manager.py --version
    python3 project_manager.py list
    python3 project_manager.py create
    python3 project_manager.py info <project_code>
    python3 project_manager.py settings <project_code>
    python3 project_manager.py set-feed <project_code>
    python3 project_manager.py download-feed <project_code>
    python3 project_manager.py update <project_code>
    python3 project_manager.py logs [project_code]
    python3 project_manager.py data-status <project_code>
    python3 project_manager.py snapshots <project_code>
    python3 project_manager.py events <project_code>
    python3 project_manager.py prices <project_code>
    python3 project_manager.py data-services <project_code>
    python3 project_manager.py stats <project_code>
    python3 project_manager.py history <project_code>
    python3 project_manager.py apartment <project_code> <apartment_id>
    python3 project_manager.py price <project_code> <apartment_id>
    python3 project_manager.py config-status <project_code>
    python3 project_manager.py doctor <project_code>
    python3 project_manager.py workspace
    python3 project_manager.py gui
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from core.project_service import (
    create_project,
    download_feed,
    list_projects,
    set_feed_url,
    update_project,
    data_engine_status,
    project_snapshots,
    project_events,
    project_price_events,
    data_services_status,
    project_statistics,
    project_apartment_count_history,
    project_apartment_details,
    project_price_history,
    project_config_status,
    project_integrity_doctor,
)
from core.settings import normalize_settings, read_settings
from core.logger import read_last_lines
from core.safety import SafetyCriticalError
from core.paths import (
    APP_ROOT,
    PROJECTS_DIR,
    APP_LOGS_DIR,
    ensure_workspace,
    workspace_status,
    PATHS_VERSION,
)

PROJECT_MANAGER_VERSION = "0.9.3-gui-foundation"
ROOT_DIR = APP_ROOT


def project_dir(project_code: str) -> Path:
    return PROJECTS_DIR / project_code


def cmd_list(args: argparse.Namespace) -> None:
    projects = list_projects(PROJECTS_DIR)
    if not projects:
        print("Проекты не найдены.")
        return
    print("Проекты:")
    for item in projects:
        status = "вкл" if item.get("enabled") else "выкл"
        print(f"- {item['code']} | {item['name']} | {status} | последнее обновление: {item.get('last_update') or '—'}")


def cmd_info(args: argparse.Namespace) -> None:
    pdir = project_dir(args.project_code)
    settings = normalize_settings(read_settings(pdir))
    print(f"Проект: {settings.get('project_name', args.project_code)}")
    print(f"Код: {settings.get('project_code', args.project_code)}")
    print(f"Папка: {pdir}")
    print(f"Основная таблица: {pdir / 'tables' / settings.get('main_excel', 'lots.xlsx')}")
    print(f"XML: {pdir / 'xml' / 'current.xml'}")
    print(f"Формат последнего фида: {settings.get('feed_format_last_detected', '—')}")
    print(f"Последнее обновление: {settings.get('last_update') or '—'}")
    print(f"Feed URL: {settings.get('feed_url') or '—'}")


def cmd_settings(args: argparse.Namespace) -> None:
    pdir = project_dir(args.project_code)
    settings = normalize_settings(read_settings(pdir))
    print(json.dumps(settings, ensure_ascii=False, indent=4))


def cmd_set_feed(args: argparse.Namespace) -> None:
    current = normalize_settings(read_settings(project_dir(args.project_code))).get("feed_url", "")
    print(f"Текущая ссылка: {current or '—'}")
    new_url = args.url or input("Введите новую XML-ссылку: ").strip()
    if not new_url:
        raise SystemExit("Ссылка не указана.")
    result = set_feed_url(PROJECTS_DIR, args.project_code, new_url)
    print("Готово. Ссылка обновлена.")
    if result["old_url"]:
        print(f"Старая ссылка сохранена в feed_history: {result['old_url']}")


def cmd_download_feed(args: argparse.Namespace) -> None:
    result = download_feed(PROJECTS_DIR, args.project_code)
    print("Фид скачан.")
    print(f"Файл: {result['xml_path']}")
    print(f"Размер: {result['bytes']} байт")


def cmd_create(args: argparse.Namespace) -> None:
    project_name = args.name or input("Название ЖК: ").strip()
    if not project_name:
        raise SystemExit("Название ЖК не указано.")

    source = args.source or input("XML-ссылка или путь к XML-файлу: ").strip()
    if not source:
        raise SystemExit("Источник XML не указан.")

    excel_name = args.excel or input("Имя Excel-файла [lots.xlsx]: ").strip() or "lots.xlsx"

    result = create_project(
        PROJECTS_DIR,
        project_name=project_name,
        source=source,
        excel_name=excel_name,
        project_code=args.code,
    )

    print("Проект создан.")
    print(f"Код проекта: {result['project_code']}")
    print(f"Папка: {result['project_dir']}")
    print(f"Формат фида: {result['feed_format']}")
    print(f"Квартир: {result['rows']}")
    print(f"Таблица: {result['excel_path']}")


def _print_update_result(result: dict[str, Any]) -> None:
    print(f"Версия ядра обновления: {result['engine_version']}")
    print(f"Версия Safety: {result.get('safety_version', '—')}")
    print(f"Версия Data Engine: {result.get('data_engine_version', '—')}")
    if result.get("update_id"):
        print(f"Update ID: {result.get('update_id')}")
    print(f"Событий квартир записано: {result.get('saved_apartment_events', 0)}")
    print(f"Событий цен записано: {result.get('saved_price_events', 0)}")
    print(f"Проект: {result['project_name']}")
    print(f"Формат фида: {result['feed_format']}")
    print(f"Квартир в XML: {result['feed_rows']}")
    print(f"Квартир в Excel до обновления: {result['excel_rows_before']}")
    print(f"Удалено строк: {result['deleted']}")
    print(f"Добавлено строк: {result['added']}")
    print(f"Обновлено квартир: {result['updated_apartments']}")
    print(f"Обновлено ячеек: {result['updated_cells']}")
    print(f"Квартир в Excel после обновления: {result['excel_rows_after']}")
    print("\nГотово.")
    print(f"Основная таблица обновлена: {result['excel_path']}")
    print(f"Резервная копия старой версии: {result['backup_path']}")


def cmd_update(args: argparse.Namespace) -> None:
    try:
        result = update_project(PROJECTS_DIR, args.project_code, download=not args.no_download, force=args.force)
        _print_update_result(result)
    except SafetyCriticalError as exc:
        print(exc.report.format_for_console())
        if args.yes:
            print("\nПолучено автоматическое подтверждение (--yes). Продолжаю обновление.")
            result = update_project(PROJECTS_DIR, args.project_code, download=not args.no_download, force=True)
            _print_update_result(result)
            return

        answer = input("Продолжить обновление несмотря на критические предупреждения? Введите YES для подтверждения: ").strip()
        if answer == "YES":
            result = update_project(PROJECTS_DIR, args.project_code, download=not args.no_download, force=True)
            _print_update_result(result)
        else:
            print("Обновление отменено. Excel-таблица не изменена.")



def cmd_gui(args: argparse.Namespace) -> None:
    """Запустить графический интерфейс PySide6."""
    try:
        from app import main as gui_main
    except ImportError as exc:
        raise SystemExit(
            "Не удалось запустить GUI. Проверьте, что установлен PySide6: "
            "python3 -m pip install PySide6"
        ) from exc
    gui_main()


def cmd_logs(args: argparse.Namespace) -> None:
    if args.project_code:
        log_path = project_dir(args.project_code) / "logs" / "project.log"
        title = f"Лог проекта {args.project_code}"
    else:
        log_path = APP_LOGS_DIR / "app.log"
        title = "Общий лог приложения"

    lines = read_last_lines(log_path, args.limit)
    print(title)
    print(f"Файл: {log_path}")
    if not lines:
        print("Записей пока нет.")
        return
    print("-" * 80)
    for line in lines:
        print(line)


def cmd_data_status(args: argparse.Namespace) -> None:
    status = data_engine_status(PROJECTS_DIR, args.project_code)
    print(f"Data Engine: {status.get('data_engine_version', '—')}")
    print(f"База истории: {status.get('db_path', '—')}")
    print(f"Версия схемы: {status.get('schema_version', '—')}")
    print("Таблицы:")
    for table in status.get("tables", []):
        print(f"- {table}")
    metadata = status.get("metadata", {})
    if metadata:
        print("Metadata:")
        for key, value in metadata.items():
            print(f"- {key}: {value}")




def cmd_workspace(args: argparse.Namespace) -> None:
    status = ensure_workspace()
    print(f"Portable Workspace: {status.get('paths_version', '—')}")
    print(f"Корень программы: {status.get('app_root')}")
    print(f"Папка данных: {status.get('data_dir')}")
    print(f"Проекты: {status.get('projects_dir')}")
    print(f"Логи: {status.get('logs_dir')}")
    print(f"Кэш: {status.get('cache_dir')}")
    print(f"Настройки приложения: {status.get('settings_dir')}")
    print(f"Шаблоны: {status.get('templates_dir')}")
    actions = status.get('actions') or []
    if actions:
        print("Действия:")
        for action in actions:
            print(f"- {action}")
    else:
        print("Действия: изменений не потребовалось")
    print("Статус: workspace готов")

def cmd_doctor(args: argparse.Namespace) -> None:
    status = project_integrity_doctor(PROJECTS_DIR, args.project_code)
    print(f"Project Integrity Engine: {status.get('integrity_engine_version', '—')}")
    print(f"Проект: {status.get('project_code')}" )
    print(f"Папка: {status.get('project_dir')}")
    print("-" * 80)
    print(f"settings.json: {status.get('settings_path')}")
    print(f"history.db: {status.get('history_db')}")
    print(f"manifest: {status.get('manifest_path')}")
    print("Папки:")
    for path in status.get('required_dirs', []):
        print(f"- {path}")
    print("Действия:")
    actions = status.get('actions') or []
    if actions:
        for action in actions:
            print(f"- {action}")
    else:
        print("- изменений не потребовалось")
    if status.get('ok'):
        print("Статус: структура проекта актуальна")
    else:
        print("Статус: есть проблемы")

def cmd_config_status(args: argparse.Namespace) -> None:
    status = project_config_status(PROJECTS_DIR, args.project_code)
    print(f"Configuration Engine: {status.get('config_engine_version', '—')}")
    print(f"Файл настроек: {status.get('settings_path', '—')}")
    print(f"Версия схемы: {status.get('schema_version', '—')}")
    print(f"Проект: {status.get('project_name') or '—'} ({status.get('project_code') or '—'})")
    print(f"Feed URL: {status.get('feed_url') or '—'}")
    print(f"Тип фида: {status.get('feed_type') or '—'}")
    print(f"Основная таблица: {status.get('main_excel') or '—'}")
    print("Поля обновления:")
    for key, value in (status.get('update_fields') or {}).items():
        print(f"- {key}: {'обновлять' if value else 'не трогать'}")
    print("Safety:")
    for key, value in (status.get('safety') or {}).items():
        print(f"- {key}: {value}")
    print(f"Напоминаний: {status.get('reminders_count', 0)}")
    if status.get('is_valid'):
        print("Статус: настройки корректны")
    else:
        print("Статус: есть проблемы")
        for error in status.get('errors', []):
            print(f"! {error}")


def _format_size(bytes_value: int) -> str:
    try:
        value = int(bytes_value or 0)
    except Exception:
        value = 0
    if value >= 1024 * 1024:
        return f"{value / (1024 * 1024):.2f} МБ"
    if value >= 1024:
        return f"{value / 1024:.1f} КБ"
    return f"{value} байт"


def cmd_snapshots(args: argparse.Namespace) -> None:
    rows = project_snapshots(PROJECTS_DIR, args.project_code, limit=args.limit)
    print(f"Последние snapshots проекта: {args.project_code}")
    if not rows:
        print("Записей пока нет.")
        return
    print("-" * 100)
    for row in rows:
        status = row.get("update_result", "")
        print(
            f"#{row.get('id')} | {row.get('created_at')} | {status} | "
            f"квартир: {row.get('apartments_total')} | "
            f"+{row.get('apartments_added')} / -{row.get('apartments_removed')} | "
            f"обновлено квартир: {row.get('apartments_updated')} | "
            f"ячеек: {row.get('updated_cells')} | "
            f"цен: {row.get('prices_changed')} | "
            f"формат: {row.get('feed_type')} | "
            f"XML: {_format_size(row.get('feed_size', 0))} | "
            f"{row.get('update_duration_ms')} мс"
        )
        if row.get("failure_reason"):
            print(f"   Причина: {row.get('failure_reason')}")
    print("-" * 100)



def cmd_events(args: argparse.Namespace) -> None:
    rows = project_events(PROJECTS_DIR, args.project_code, limit=args.limit)
    print(f"Последние события квартир проекта: {args.project_code}")
    if not rows:
        print("Записей пока нет.")
        return
    print("-" * 100)
    for row in rows:
        print(
            f"#{row.get('id')} | update #{row.get('update_id')} | "
            f"{row.get('created_at')} | {row.get('event_type')} | ID: {row.get('apartment_id')}"
        )
    print("-" * 100)


def cmd_prices(args: argparse.Namespace) -> None:
    rows = project_price_events(PROJECTS_DIR, args.project_code, limit=args.limit)
    print(f"Последние изменения цен проекта: {args.project_code}")
    if not rows:
        print("Записей пока нет.")
        return
    print("-" * 100)
    for row in rows:
        print(
            f"#{row.get('id')} | update #{row.get('update_id')} | "
            f"{row.get('created_at')} | ID: {row.get('apartment_id')} | "
            f"{row.get('old_price')} → {row.get('new_price')}"
        )
    print("-" * 100)


def cmd_data_services(args: argparse.Namespace) -> None:
    status = data_services_status(PROJECTS_DIR, args.project_code)
    print(f"Data Engine: {status.get('data_engine_version', '—')}")
    print("Read-only сервисы:")
    for service_name in status.get("services", []):
        print(f"- {service_name}")
    print(f"Последних snapshots доступно: {status.get('recent_snapshots_count', 0)}")
    print(f"Последних изменений цен доступно: {status.get('recent_price_changes_count', 0)}")
    summary = status.get("summary", {})
    if summary:
        print("Краткая сводка:")
        print(f"- обновлений всего: {summary.get('updates_total')}")
        print(f"- первое обновление: {summary.get('first_update') or '—'}")
        print(f"- последнее обновление: {summary.get('last_update') or '—'}")
        print(f"- текущих квартир: {summary.get('current_apartments') or '—'}")


def _format_int(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{int(value):,}".replace(",", " ")
    except Exception:
        return str(value)


def _format_money(value: Any) -> str:
    if value is None or value == "":
        return "—"
    try:
        return f"{int(float(value)):,}".replace(",", " ") + " ₽"
    except Exception:
        return str(value)


def cmd_stats(args: argparse.Namespace) -> None:
    stats = project_statistics(PROJECTS_DIR, args.project_code)
    print(f"Статистика проекта: {args.project_code}")
    print("-" * 80)
    print(f"Обновлений всего: {_format_int(stats.get('updates_total'))}")
    print(f"Первое обновление: {stats.get('first_update') or '—'}")
    print(f"Последнее обновление: {stats.get('last_update') or '—'}")
    print(f"Текущих квартир: {_format_int(stats.get('current_apartments'))}")
    print(f"Максимум квартир: {_format_int(stats.get('max_apartments'))}")
    print(f"Минимум квартир: {_format_int(stats.get('min_apartments'))}")
    avg_ms = stats.get('avg_update_duration_ms')
    if avg_ms is not None:
        try:
            print(f"Среднее время обновления: {float(avg_ms):.0f} мс")
        except Exception:
            print(f"Среднее время обновления: {avg_ms}")
    else:
        print("Среднее время обновления: —")
    print(f"Последний Update ID: {stats.get('latest_update_id') or '—'}")
    print(f"Результат последнего обновления: {stats.get('latest_update_result') or '—'}")


def cmd_history(args: argparse.Namespace) -> None:
    rows = project_apartment_count_history(PROJECTS_DIR, args.project_code, limit=args.limit)
    print(f"Динамика количества квартир: {args.project_code}")
    if not rows:
        print("Записей пока нет.")
        return
    print("-" * 80)
    for row in rows:
        print(
            f"update #{row.get('update_id')} | {row.get('created_at')} | "
            f"{row.get('update_result')} | квартир: {_format_int(row.get('apartments_total'))}"
        )
    print("-" * 80)


def cmd_apartment(args: argparse.Namespace) -> None:
    info = project_apartment_details(PROJECTS_DIR, args.project_code, args.apartment_id)
    print(f"Квартира ID: {args.apartment_id}")
    print(f"Проект: {args.project_code}")
    print("-" * 80)
    print(f"Первое появление: {info.get('first_seen') or '—'}")
    print(f"Исчезла из фида: {info.get('removed_at') or '—'}")
    print(f"Последнее событие: {info.get('last_event_at') or '—'}")
    print(f"Статус: {info.get('status') or '—'}")
    print(f"Дней в фиде: {_format_int(info.get('days_in_feed'))}")
    print(f"Событий по квартире: {_format_int(info.get('events_count'))}")
    print(f"Изменений цены: {_format_int(info.get('price_changes_count'))}")
    print(f"Последняя известная цена: {_format_money(info.get('latest_known_price'))}")

    events = info.get('events') or []
    if events:
        print("\nСобытия:")
        for e in events:
            print(f"- update #{e.get('update_id')} | {e.get('created_at')} | {e.get('event_type')}")

    price_events = info.get('price_events') or []
    if price_events:
        print("\nИстория цены:")
        for p in price_events:
            print(
                f"- update #{p.get('update_id')} | {p.get('created_at')} | "
                f"{_format_money(p.get('old_price'))} → {_format_money(p.get('new_price'))}"
            )


def cmd_price(args: argparse.Namespace) -> None:
    rows = project_price_history(PROJECTS_DIR, args.project_code, args.apartment_id)
    print(f"История цены квартиры: {args.apartment_id}")
    print(f"Проект: {args.project_code}")
    if not rows:
        print("Изменений цены пока нет.")
        return
    print("-" * 80)
    for row in rows:
        print(
            f"update #{row.get('update_id')} | {row.get('created_at')} | "
            f"{_format_money(row.get('old_price'))} → {_format_money(row.get('new_price'))}"
        )
    print("-" * 80)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Менеджер проектов XML→Excel")
    parser.add_argument("--version", action="store_true", help="Показать версию")

    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("list", help="Показать список проектов")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("info", help="Показать информацию о проекте")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_info)

    p = sub.add_parser("settings", help="Показать settings.json проекта")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_settings)

    p = sub.add_parser("set-feed", help="Заменить XML-ссылку проекта")
    p.add_argument("project_code")
    p.add_argument("--url", default="", help="Новая XML-ссылка")
    p.set_defaults(func=cmd_set_feed)

    p = sub.add_parser("download-feed", help="Скачать XML по ссылке из settings.json")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_download_feed)

    p = sub.add_parser("create", help="Создать новый проект")
    p.add_argument("--name", default="", help="Название ЖК")
    p.add_argument("--source", default="", help="XML-ссылка или путь к XML")
    p.add_argument("--excel", default="", help="Имя Excel-файла")
    p.add_argument("--code", default=None, help="Технический код папки, необязательно")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update", help="Обновить проект")
    p.add_argument("project_code")
    p.add_argument("--no-download", action="store_true", help="Не скачивать фид по URL, использовать xml/current.xml")
    p.add_argument("--force", action="store_true", help="Обновить даже при критических предупреждениях Safety")
    p.add_argument("--yes", action="store_true", help="Автоматически подтвердить критические предупреждения Safety")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("logs", help="Показать последние строки лога")
    p.add_argument("project_code", nargs="?", default="", help="Код проекта; если не указан, показывается общий лог")
    p.add_argument("--limit", type=int, default=30, help="Сколько строк показать")
    p.set_defaults(func=cmd_logs)

    p = sub.add_parser("data-status", help="Показать статус Data Engine проекта")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_data_status)

    p = sub.add_parser("snapshots", help="Показать последние snapshots обновлений проекта")
    p.add_argument("project_code")
    p.add_argument("--limit", type=int, default=10, help="Сколько записей показать")
    p.set_defaults(func=cmd_snapshots)

    p = sub.add_parser("events", help="Показать события появления/исчезновения квартир")
    p.add_argument("project_code")
    p.add_argument("--limit", type=int, default=20, help="Сколько записей показать")
    p.set_defaults(func=cmd_events)

    p = sub.add_parser("prices", help="Показать события изменения цен")
    p.add_argument("project_code")
    p.add_argument("--limit", type=int, default=20, help="Сколько записей показать")
    p.set_defaults(func=cmd_prices)

    p = sub.add_parser("data-services", help="Проверить read-only сервисный слой Data Engine")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_data_services)


    p = sub.add_parser("stats", help="Показать общую статистику проекта")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("history", help="Показать динамику количества квартир по обновлениям")
    p.add_argument("project_code")
    p.add_argument("--limit", type=int, default=30, help="Сколько записей показать; 0 = все")
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("apartment", help="Показать историю конкретной квартиры")
    p.add_argument("project_code")
    p.add_argument("apartment_id")
    p.set_defaults(func=cmd_apartment)

    p = sub.add_parser("price", help="Показать историю цены конкретной квартиры")
    p.add_argument("project_code")
    p.add_argument("apartment_id")
    p.set_defaults(func=cmd_price)

    p = sub.add_parser("config-status", help="Проверить и мигрировать настройки проекта")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_config_status)

    p = sub.add_parser("doctor", help="Проверить и восстановить структуру проекта")
    p.add_argument("project_code")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("workspace", help="Проверить portable workspace приложения")
    p.set_defaults(func=cmd_workspace)

    p = sub.add_parser("gui", help="Запустить графический интерфейс")
    p.set_defaults(func=cmd_gui)

    return parser


def main() -> None:
    ensure_workspace()
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        print(PROJECT_MANAGER_VERSION)
        return

    if not args.command:
        parser.print_help()
        return

    try:
        args.func(args)
    except Exception as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
