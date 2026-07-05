"""Helpers for opening local files with external applications."""

from __future__ import annotations

import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path


class BrowserOpenError(RuntimeError):
    """Raised when an XML file cannot be opened in the requested browser."""


DEFAULT_BROWSER = "default"
CHROME = "chrome"
SAFARI = "safari"
FIREFOX = "firefox"
EDGE = "edge"

_BROWSER_LABELS = {
    DEFAULT_BROWSER: "браузер по умолчанию",
    CHROME: "Google Chrome",
    SAFARI: "Safari",
    FIREFOX: "Firefox",
    EDGE: "Microsoft Edge",
}

_MAC_APPS = {
    CHROME: "Google Chrome",
    SAFARI: "Safari",
    FIREFOX: "Firefox",
    EDGE: "Microsoft Edge",
}

_WINDOWS_COMMANDS = {
    CHROME: ("chrome", "chrome.exe"),
    FIREFOX: ("firefox", "firefox.exe"),
    EDGE: ("msedge", "msedge.exe"),
}

_LINUX_COMMANDS = {
    CHROME: ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"),
    FIREFOX: ("firefox",),
    EDGE: ("microsoft-edge", "microsoft-edge-stable", "msedge"),
}


def open_xml_in_browser(path: Path, browser: str) -> None:
    """Open an XML file in the selected web browser.

    Args:
        path: Local XML file path.
        browser: One of ``default``, ``chrome``, ``safari``, ``firefox`` or ``edge``.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        BrowserOpenError: If the browser is unknown, unavailable or fails to open.
    """

    xml_path = Path(path)
    if not xml_path.exists():
        raise FileNotFoundError(xml_path)

    normalized_browser = browser.strip().lower()
    if normalized_browser not in _BROWSER_LABELS:
        raise BrowserOpenError(f"Неизвестный браузер: {browser}")

    uri = xml_path.resolve().as_uri()
    if normalized_browser == DEFAULT_BROWSER:
        if webbrowser.open(uri, new=2):
            return
        raise BrowserOpenError("Не удалось открыть XML в браузере по умолчанию.")

    system = platform.system()
    if system == "Darwin":
        _open_named_browser_macos(uri, normalized_browser)
        return
    if system == "Windows":
        _open_named_browser_from_commands(uri, normalized_browser, _WINDOWS_COMMANDS)
        return
    _open_named_browser_from_commands(uri, normalized_browser, _LINUX_COMMANDS)


def _open_named_browser_macos(uri: str, browser: str) -> None:
    app_name = _MAC_APPS.get(browser)
    if not app_name:
        raise BrowserOpenError("Safari поддерживается только на macOS.")
    try:
        subprocess.run(["open", "-a", app_name, uri], check=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise BrowserOpenError(f"{_BROWSER_LABELS[browser]} не найден или не смог открыть XML.") from exc


def _open_named_browser_from_commands(
    uri: str,
    browser: str,
    command_map: dict[str, tuple[str, ...]],
) -> None:
    commands = command_map.get(browser)
    if not commands:
        raise BrowserOpenError(f"{_BROWSER_LABELS[browser]} недоступен на этой платформе.")

    for command in commands:
        executable = shutil.which(command)
        if not executable:
            continue
        try:
            subprocess.Popen([executable, uri])
            return
        except OSError:
            continue

    # Fall back to Python's browser registry where it knows a platform-specific name.
    for name in commands:
        try:
            controller = webbrowser.get(name)
        except webbrowser.Error:
            continue
        if controller.open(uri, new=2):
            return

    raise BrowserOpenError(f"{_BROWSER_LABELS[browser]} не найден. Выберите другой браузер.")
