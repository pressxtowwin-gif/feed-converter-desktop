#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""core.downloader — загрузка XML-фидов по URL."""

from __future__ import annotations

import urllib.request
from pathlib import Path


def is_url(value: str) -> bool:
    value = value.strip().lower()
    return value.startswith("http://") or value.startswith("https://")


def download_url_to_file(url: str, output_path: str | Path, timeout: int = 60) -> int:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 feed-converter/0.5",
            "Accept": "application/xml,text/xml,*/*",
        },
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read()

    if not data.strip():
        raise ValueError("Скачанный XML пустой")

    output_path.write_bytes(data)
    return len(data)
