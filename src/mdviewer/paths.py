"""Pfade: Web-Assets, Einstellungen, Zwischenspeicher."""

from __future__ import annotations

import os
from pathlib import Path

from . import APP_SLUG

ENV_WEB_DIR = "MD_VIEWER_WEB_DIR"
ENV_CONFIG_DIR = "MD_VIEWER_CONFIG_DIR"

#: Installationsort der Web-Assets im .deb
SYSTEM_WEB_DIR = Path("/usr/lib") / APP_SLUG / "web"


def web_dir() -> Path:
    """Findet das Verzeichnis mit index.html.

    Reihenfolge: Umgebungsvariable, Systeminstallation, Entwicklungs-Checkout.
    """
    candidates = []
    env = os.environ.get(ENV_WEB_DIR)
    if env:
        candidates.append(Path(env))
    candidates.append(SYSTEM_WEB_DIR)
    # Entwicklungs-Checkout: src/mdviewer/paths.py -> ../../web
    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(repo_root / "web")

    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return candidates[0]


def web_index() -> Path:
    return web_dir() / "index.html"


def config_dir() -> Path:
    env = os.environ.get(ENV_CONFIG_DIR)
    if env:
        return Path(env)
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / APP_SLUG


def settings_file() -> Path:
    return config_dir() / "settings.json"


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / APP_SLUG


def icon_file() -> Path | None:
    """Sucht das App-Icon (Skalierung/SVG) - fuer den Info-Dialog."""
    names = [
        f"/usr/share/icons/hicolor/256x256/apps/{APP_SLUG}.png",
        f"/usr/share/icons/hicolor/128x128/apps/{APP_SLUG}.png",
        f"/usr/share/icons/hicolor/scalable/apps/{APP_SLUG}.svg",
    ]
    repo_root = Path(__file__).resolve().parents[2]
    names.append(str(repo_root / "packaging" / "icons" / "md-viewer-256.png"))
    for name in names:
        path = Path(name)
        if path.is_file():
            return path
    return None


def desktop_file() -> str:
    return f"{APP_SLUG}.desktop"
