#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Minimal entry point for Feed Converter Desktop."""

from __future__ import annotations

import sys

try:
    from PySide6.QtWidgets import QApplication
except ImportError as exc:  # pragma: no cover - нужен понятный вывод пользователю
    print("PySide6 не установлен.")
    print("Установите его командой:")
    print("python3 -m pip install PySide6")
    raise SystemExit(1) from exc

from ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
