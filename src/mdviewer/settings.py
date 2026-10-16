"""Einstellungen (JSON in ~/.config/md-viewer/settings.json)."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from . import i18n, paths

log = logging.getLogger(__name__)

MAX_RECENT_FILES = 12
_SETTINGS_VERSION = 1
_SETTINGS_VERSION_KEY = "_version"

DEFAULTS: dict[str, Any] = {
    "language": i18n.DEFAULT_LANGUAGE,
    "theme": "auto",  # auto | light | dark
    "line_width": "normal",  # normal | wide | full
    "zoom": 100,
    "toc_visible": True,
    "breaks": False,
    "highlight": True,
    "math": True,
    "math_inline": True,
    "block_remote_images": True,
    "auto_reload": True,
    "recent_files": [],
    "window_width": 1100,
    "window_height": 780,
    "window_maximized": False,
}

_BOOL_KEYS = {
    "toc_visible",
    "breaks",
    "highlight",
    "math",
    "math_inline",
    "block_remote_images",
    "auto_reload",
    "window_maximized",
}

_ENUMS = {
    "theme": ("auto", "light", "dark"),
    "line_width": ("normal", "wide", "full"),
    "language": tuple(i18n.LANGUAGES),
}

_RANGES = {
    "zoom": (50, 250),
    "window_width": (480, 12000),
    "window_height": (360, 12000),
}


def _clamp(value: Any, low: int, high: int, fallback: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(low, min(high, number))


class Settings:
    """Einstellungen laden/speichern - fehlertolerant, niemals krachend."""

    def __init__(self, path: os.PathLike[str] | str | None = None) -> None:
        self.path = Path(path) if path else paths.settings_file()
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._loaded = False

    # ---------------------------------------------------------------- Laden

    def load(self) -> "Settings":
        self._data = dict(DEFAULTS)
        needs_save = False
        try:
            raw = self.path.read_text(encoding="utf-8")
            stored = json.loads(raw)
        except FileNotFoundError:
            self._loaded = True
            return self
        except (OSError, json.JSONDecodeError) as error:
            log.warning("Einstellungen konnten nicht gelesen werden (%s) - nutze Standardwerte", error)
            self._loaded = True
            return self

        if isinstance(stored, dict):
            stored_version_value = stored.get(_SETTINGS_VERSION_KEY, 0)
            stored_version = (
                stored_version_value
                if isinstance(stored_version_value, int) and not isinstance(stored_version_value, bool)
                else 0
            )
            for key, value in stored.items():
                if key in DEFAULTS:
                    self._data[key] = value
            if stored_version < _SETTINGS_VERSION:
                # Before versioned settings, false was the application default and
                # was written even when the user had never changed the option.
                # Migrate that ambiguous legacy value to the safer default once.
                if "block_remote_images" in stored and not bool(stored["block_remote_images"]):
                    self._data["block_remote_images"] = True
                needs_save = True
        self._normalize()
        self._loaded = True
        if needs_save:
            self.save()
        return self

    def _normalize(self) -> None:
        """Unplausible Werte aus fremden/alten Dateien zurechtbiegen."""
        for key in _BOOL_KEYS:
            self._data[key] = bool(self._data.get(key, DEFAULTS[key]))
        for key, allowed in _ENUMS.items():
            if self._data.get(key) not in allowed:
                self._data[key] = DEFAULTS[key]
        for key, (low, high) in _RANGES.items():
            self._data[key] = _clamp(self._data.get(key), low, high, int(DEFAULTS[key]))
        recents = self._data.get("recent_files")
        if not isinstance(recents, list):
            recents = []
        cleaned: list[str] = []
        for entry in recents:
            if isinstance(entry, str) and entry and entry not in cleaned:
                cleaned.append(entry)
            if len(cleaned) >= MAX_RECENT_FILES:
                break
        self._data["recent_files"] = cleaned
        if not isinstance(self._data.get("language"), str):
            self._data["language"] = DEFAULTS["language"]

    # -------------------------------------------------------------- Zugriff

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any, *, save: bool = True) -> Any:
        self._data[key] = value
        self._normalize()
        if save:
            self.save()
        return self._data[key]

    def update(self, values: dict[str, Any], *, save: bool = True) -> None:
        self._data.update(values)
        self._normalize()
        if save:
            self.save()

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def reset(self, *, save: bool = True) -> None:
        self._data = dict(DEFAULTS)
        if save:
            self.save()

    # --------------------------------------------------------------- Speichern

    def save(self) -> bool:
        """Atomar schreiben (temp + rename); Fehler werden nur protokolliert."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            stored = dict(self._data)
            stored[_SETTINGS_VERSION_KEY] = _SETTINGS_VERSION
            payload = json.dumps(stored, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=str(self.path.parent), prefix=".settings-", suffix=".tmp", delete=False
            ) as handle:
                handle.write(payload)
                temp_name = handle.name
            os.replace(temp_name, self.path)
            return True
        except OSError as error:
            log.warning("Einstellungen konnten nicht gespeichert werden: %s", error)
            return False

    # ------------------------------------------------------ Zuletzt geoeffnet

    def recent_files(self) -> list[str]:
        return list(self._data.get("recent_files", []))

    def add_recent(self, file_path: os.PathLike[str] | str, *, save: bool = True) -> list[str]:
        entry = str(Path(file_path).expanduser())
        recents = [item for item in self.recent_files() if item != entry]
        recents.insert(0, entry)
        self._data["recent_files"] = recents[:MAX_RECENT_FILES]
        if save:
            self.save()
        return self.recent_files()

    def remove_recent(self, file_path: os.PathLike[str] | str, *, save: bool = True) -> list[str]:
        entry = str(Path(file_path).expanduser())
        self._data["recent_files"] = [item for item in self.recent_files() if item != entry]
        if save:
            self.save()
        return self.recent_files()

    def clear_recents(self, *, save: bool = True) -> None:
        self._data["recent_files"] = []
        if save:
            self.save()

    # ------------------------------------------------ Werte fuer das WebView

    def viewer_settings(self) -> dict[str, Any]:
        """Einstellungen, die der Viewer im WebView kennt (siehe viewer.js)."""
        return {
            "language": self.get("language"),
            "theme": self.get("theme"),
            "zoom": self.get("zoom"),
            "tocVisible": bool(self.get("toc_visible")),
            "blockRemoteImages": bool(self.get("block_remote_images")),
            "lineWidth": self.get("line_width"),
        }

    def render_options(self) -> dict[str, bool]:
        """Rendereinstellungen (siehe renderer.js, DEFAULT_RENDER_OPTIONS)."""
        return {
            "breaks": bool(self.get("breaks")),
            "highlight": bool(self.get("highlight")),
            "math": bool(self.get("math")),
            "mathInline": bool(self.get("math_inline")),
        }
