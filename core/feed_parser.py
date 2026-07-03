#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core.feed_parser
Единый парсер XML-фидов недвижимости.

Поддерживает:
- Яндекс.Недвижимость;
- Домклик / Kvartirogramma.

Все форматы приводятся к единой структуре: list[dict].
"""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Optional

COLUMNS_BASE = [
    "ID квартиры",
    "Название ЖК",
    "Корпус",
    "Номер квартиры",
    "Наименование застройщика",
    "Телефон",
    "Адрес",
    "Количество комнат",
    "Отделка",
    "Цена",
    "Цена со скидкой",
    "Этаж",
    "Этажность дома",
    "Общая площадь",
    "Описание",
    "Проектная декларация",
    "Главное изображение",
    "Планировка",
]

YANDEX_FORMAT = "yandex"
DOMCLICK_FORMAT = "domclick"


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def get_namespace(root: ET.Element) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}", 1)[0].strip("{")
    return ""


def q(ns: str, tag: str) -> str:
    return f"{{{ns}}}{tag}" if ns else tag


def child_text(parent: Optional[ET.Element], tag: str, default: str = "") -> str:
    if parent is None:
        return default
    child = parent.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def text(parent: ET.Element, ns: str, path: str, default: str = "") -> str:
    """Возвращает текст вложенного XML-тега. path задается через '/', например price/value."""
    current: Optional[ET.Element] = parent
    for part in path.split("/"):
        if current is None:
            return default
        current = current.find(q(ns, part))
    if current is None or current.text is None:
        return default
    return current.text.strip()


def first_existing_text(parent: ET.Element, ns: str, paths: Iterable[str], default: str = "") -> str:
    for path in paths:
        value = text(parent, ns, path, "")
        if value != "":
            return value
    return default


def load_xml(source: str) -> bytes:
    """Читает XML либо из локального файла, либо по URL."""
    if source.startswith(("http://", "https://")):
        try:
            import requests  # type: ignore
            response = requests.get(source, timeout=60)
            response.raise_for_status()
            return response.content
        except ImportError:
            with urllib.request.urlopen(source, timeout=60) as response:
                return response.read()
    return Path(source).read_bytes()


def detect_feed_format(root: ET.Element) -> str:
    """Автоопределение формата фида."""
    root_name = strip_ns(root.tag).lower()

    if root_name == "complexes" and root.findall(".//complex"):
        return DOMCLICK_FORMAT

    ns = get_namespace(root)
    if root.findall(f".//{q(ns, 'offer')}"):
        return YANDEX_FORMAT

    raise ValueError(
        "Не удалось определить формат XML. Поддерживаются Яндекс.Недвижимость и Домклик/Kvartirogramma."
    )


def normalize_cell_value(value: object) -> object:
    """Преобразует числовые строки в числа, где это безопасно."""
    if not isinstance(value, str):
        return value
    value = value.strip()
    if value == "":
        return ""
    try:
        if value.replace(".", "", 1).isdigit():
            return float(value) if "." in value else int(value)
    except Exception:
        pass
    return value


def build_columns(rows: list[dict[str, object]]) -> list[str]:
    max_images = 0
    for row in rows:
        regular_images = row.get("__regular_images", [])
        if isinstance(regular_images, list):
            max_images = max(max_images, len(regular_images))

    columns = COLUMNS_BASE + [f"Изображение {i}" for i in range(1, max_images + 1)]

    for row in rows:
        regular_images = row.pop("__regular_images", [])
        if not isinstance(regular_images, list):
            regular_images = []
        for i in range(1, max_images + 1):
            row[f"Изображение {i}"] = regular_images[i - 1] if i <= len(regular_images) else ""

    return columns


def parse_yandex(root: ET.Element) -> tuple[list[dict[str, object]], list[str]]:
    ns = get_namespace(root)
    offers = root.findall(f".//{q(ns, 'offer')}")
    rows: list[dict[str, object]] = []

    for offer in offers:
        plan_image = ""
        regular_images: list[str] = []
        first_offer_image = ""

        for image in offer.findall(q(ns, "image")):
            url = (image.text or "").strip()
            if not url:
                continue
            if not first_offer_image:
                first_offer_image = url

            image_tag = image.attrib.get("tag", "")
            if image_tag == "plan":
                if not plan_image:
                    plan_image = url
            elif image_tag == "floor-plan":
                # План этажа пока не включаем в строгий шаблон таблицы.
                continue
            else:
                regular_images.append(url)

        # Новое универсальное правило: если отдельной планировки нет,
        # планировкой считаем первое изображение на уровне квартиры/лота.
        if not plan_image:
            plan_image = first_offer_image

        row = {
            "ID квартиры": offer.attrib.get("internal-id", ""),
            "Название ЖК": text(offer, ns, "building-name"),
            "Корпус": text(offer, ns, "building-section"),
            "Номер квартиры": text(offer, ns, "apartments"),
            "Наименование застройщика": first_existing_text(
                offer, ns, ["sales-agent/organization", "sales-agent/name"]
            ),
            "Телефон": text(offer, ns, "sales-agent/phone"),
            "Адрес": text(offer, ns, "location/address"),
            "Количество комнат": text(offer, ns, "rooms"),
            "Отделка": text(offer, ns, "renovation"),
            "Цена": text(offer, ns, "price/value"),
            "Цена со скидкой": first_existing_text(
                offer,
                ns,
                [
                    "discount-price/value",
                    "price-with-discount/value",
                    "sale-price/value",
                    "price-discount/value",
                ],
            ),
            "Этаж": text(offer, ns, "floor"),
            "Этажность дома": text(offer, ns, "floors-total"),
            "Общая площадь": text(offer, ns, "area/value"),
            "Описание": text(offer, ns, "description"),
            "Проектная декларация": "",
            "Главное изображение": "",
            "Планировка": plan_image,
            "__regular_images": regular_images,
        }
        rows.append(row)

    return rows, build_columns(rows)


def domclick_complex_description(complex_el: ET.Element) -> str:
    """Собирает описание ЖК из доступных блоков Домклик-фида."""
    pieces: list[str] = []

    # Иногда основной description лежит прямо в complex.
    direct_description = child_text(complex_el, "description")
    if direct_description:
        pieces.append(direct_description)

    # В примере есть description_secondary/title + text.
    for desc in complex_el.findall("description_secondary"):
        title = child_text(desc, "title")
        body = child_text(desc, "text")
        if title and body:
            pieces.append(f"{title}. {body}")
        elif body:
            pieces.append(body)

    return "\n\n".join(pieces).strip()


def domclick_phones(complex_el: ET.Element) -> str:
    """Берет телефоны из общего уровня Домклик-фида. Если телефонов несколько — объединяет."""
    candidates = [
        child_text(complex_el, "sales_info/sales_phone"),
        child_text(complex_el, "sales_info/responsible_officer_phone"),
        child_text(complex_el, "developer/phone"),
    ]

    # Дополнительная страховка на случай другой структуры.
    for elem in complex_el.iter():
        tag = strip_ns(elem.tag).lower()
        if "phone" in tag and elem.text and elem.text.strip():
            candidates.append(elem.text.strip())

    unique: list[str] = []
    for phone in candidates:
        phone = (phone or "").strip()
        if phone and phone not in unique:
            unique.append(phone)
    return "; ".join(unique)


def parse_domclick(root: ET.Element) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []

    for complex_el in root.findall("complex"):
        complex_name = child_text(complex_el, "name")
        complex_address = child_text(complex_el, "address")
        complex_images = [
            (img.text or "").strip()
            for img in complex_el.findall("images/image")
            if img.text and img.text.strip()
        ]
        complex_description = domclick_complex_description(complex_el)
        phone = domclick_phones(complex_el)
        developer_name = child_text(complex_el, "developer/name")

        for building in complex_el.findall("buildings/building"):
            building_name = child_text(building, "name")
            building_address = child_text(building, "address") or complex_address
            floors_total = child_text(building, "floors")

            for flat in building.findall("flats/flat"):
                flat_plans = [
                    (plan.text or "").strip()
                    for plan in flat.findall("plans/plan")
                    if plan.text and plan.text.strip()
                ]

                # В Домклик-фиде изображения уровня complex подставляем в каждую квартиру.
                # Изображения уровня квартиры/flats идут первыми, затем общие изображения ЖК.
                regular_images = flat_plans + complex_images

                # Универсальное правило: если отдельной планировки нет,
                # планировкой считаем первое изображение на уровне квартиры/flats.
                plan_image = flat_plans[0] if flat_plans else ""

                row = {
                    "ID квартиры": child_text(flat, "flat_id"),
                    "Название ЖК": complex_name,
                    "Корпус": building_name,
                    "Номер квартиры": child_text(flat, "apartment"),
                    "Наименование застройщика": developer_name,
                    "Телефон": phone,
                    "Адрес": building_address,
                    "Количество комнат": child_text(flat, "room"),
                    "Отделка": child_text(flat, "renovation"),
                    "Цена": child_text(flat, "price"),
                    "Цена со скидкой": "",
                    "Этаж": child_text(flat, "floor"),
                    "Этажность дома": floors_total,
                    "Общая площадь": child_text(flat, "area"),
                    "Описание": complex_description,
                    "Проектная декларация": "",
                    "Главное изображение": "",
                    "Планировка": plan_image,
                    "__regular_images": regular_images,
                }
                rows.append(row)

    return rows, build_columns(rows)


def parse_universal(xml_bytes: bytes) -> tuple[list[dict[str, object]], list[str], str]:
    root = ET.fromstring(xml_bytes)
    feed_format = detect_feed_format(root)

    if feed_format == YANDEX_FORMAT:
        rows, columns = parse_yandex(root)
    elif feed_format == DOMCLICK_FORMAT:
        rows, columns = parse_domclick(root)
    else:
        raise ValueError(f"Неподдерживаемый формат: {feed_format}")

    return rows, columns, feed_format

