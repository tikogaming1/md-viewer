"""Minimaler gi-Ersatz fuer Tests ohne GTK.

Der Sandkasten (und jede CI ohne X11) hat kein PyGObject. Damit die
GTK-Klassen trotzdem geladen und ihre Logik getestet werden kann, stellt
dieses Paket ein "gi.repository" mit Attrappen bereit, das sich wie die
echten Module verhaelt: unbekannte Attribute werden automatisch zu
Klassen/Funktionen, einige wenige Widgets (Notebook, WebView) sind
handgeschrieben, damit Tests echtes Verhalten sehen.
"""

from . import repository  # noqa: F401

__all__ = ["require_version", "require_versions", "repository"]


def require_version(name: str, version: str) -> None:
    """Akzeptiert alles, was in repository._MODULES steht."""
    if name not in repository.MODULES:
        raise ValueError(f"Namespace {name} nicht verfuegbar (Attrappe)")


def require_versions(versions: dict[str, str]) -> None:
    for name in versions:
        require_version(name, versions[name])


def get_required_version(name: str) -> str | None:
    return None
