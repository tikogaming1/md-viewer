"""GTK/WebKit laden und die Unterschiede zwischen den WebKit2GTK-Versionen ausgleichen.

Unterstuetzte Umgebungen:

* WebKit2GTK 4.1 (Debian 12, Ubuntu 24.04, Fedora 38+)
* WebKit2GTK 4.0 (Debian 11, Ubuntu 22.04)
* WebKit2GTK 2.x  (aeltere Distributionen, ``gir1.2-webkit2-4.0``/``-3.0``)

Es gibt genau einen Unterschied, den wir kennen muessen: das Auswerten von
JavaScript (``evaluate_javascript`` in 4.1, ``run_javascript`` davor).
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Any, Callable

log = logging.getLogger(__name__)

#: Reihenfolge: neueste zuerst
WEBKIT_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("WebKit2", "4.1"),
    ("WebKit2", "4.0"),
    ("WebKit", "2.0"),
)


class MissingDependency(RuntimeError):
    """Fehlende Systembibliothek (GTK oder WebKit)."""

    def __init__(self, key: str, **values: Any) -> None:
        self.key = key
        self.values = values
        super().__init__(key)


@dataclass
class Toolkit:
    """Geladene GI-Module."""

    gi: Any
    Gtk: Any
    Gdk: Any
    GdkPixbuf: Any
    Gio: Any
    GLib: Any
    Pango: Any
    WebKit: Any
    webkit_namespace: str
    webkit_version: str

    @property
    def modern_javascript(self) -> bool:
        """True, wenn WebKit die neue API (``evaluate_javascript``) anbietet."""
        return self.webkit_version == "4.1"


def load_toolkit(*, require_webkit: bool = True) -> Toolkit:
    """Laedt GTK3 und WebKit; wirft MissingDependency mit i18n-Schluessel."""
    try:
        import gi

        try:
            gi.require_version("Gtk", "3.0")
        except ValueError:
            pass  # schon geladen (z. B. durch eine andere Version) - Import versuchen
        from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango
    except (ImportError, ValueError) as error:  # pragma: no cover - Umgebungsabhaengig
        raise MissingDependency("error.no_gtk.title", error=str(error)) from error

    webkit_module, namespace, version = _import_webkit(gi)
    if webkit_module is None and require_webkit:
        raise MissingDependency("error.no_webkit.title")

    return Toolkit(
        gi=gi,
        Gtk=Gtk,
        Gdk=Gdk,
        GdkPixbuf=GdkPixbuf,
        Gio=Gio,
        GLib=GLib,
        Pango=Pango,
        WebKit=webkit_module,
        webkit_namespace=namespace or "",
        webkit_version=version or "",
    )


def _import_webkit(gi: Any) -> tuple[Any, str | None, str | None]:
    for namespace, version in WEBKIT_CANDIDATES:
        module = None
        try:
            gi.require_version(namespace, version)
        except (ValueError, AttributeError):
            continue
        try:
            module = importlib.import_module(f"gi.repository.{namespace}")
        except ImportError:
            # Manche Installationen legen das Modul nicht als Submodul ab
            try:
                repository = importlib.import_module("gi.repository")
                module = getattr(repository, namespace)
            except (ImportError, AttributeError):
                module = None
        if module is None:
            continue
        log.debug("WebKit gefunden: %s %s", namespace, version)
        return module, namespace, version
    return None, None, None


def create_webview(toolkit: Toolkit) -> Any:
    """Erzeugt ein WebView (Konstruktor unterscheidet sich je Version)."""
    factory = getattr(toolkit.WebKit, "WebView", None)
    if factory is None:  # pragma: no cover
        raise MissingDependency("error.no_webkit.title")
    try:
        return factory()
    except TypeError:  # pragma: no cover - sehr alte GI-Versionen
        return factory.new()


def apply_webview_settings(toolkit: Toolkit, webview: Any, *, developer: bool = False) -> None:
    """Setzt die WebView-Einstellungen defensiv (unbekannte Eigenschaften werden ignoriert)."""
    try:
        settings = webview.get_settings()
    except Exception:  # pragma: no cover
        return
    wanted: list[tuple[str, Any]] = [
        ("enable-javascript", True),
        # Lokale Bilder/Tabellen aus dem Ordner des Dokuments laden
        ("allow-file-access-from-file-urls", True),
        # Aber: kein Zugriff auf beliebige Dateien per Skript
        ("allow-universal-access-from-file-urls", False),
        ("enable-hyperlink-auditing", False),
        ("javascript-can-open-windows-automatically", False),
        ("enable-smooth-scrolling", True),
        ("enable-page-cache", True),
        ("enable-dns-prefetching", False),
        ("enable-developer-extras", bool(developer)),
        ("enable-write-console-messages-to-stdout", bool(developer)),
        ("enable-media-stream", False),
        ("enable-webrtc", False),
        ("enable-javascript-markup", True),
        ("auto-load-images", True),
    ]
    for name, value in wanted:
        try:
            settings.set_property(name, value)
        except (TypeError, AttributeError, ValueError):
            continue


def _js_value_to_text(value: Any) -> str | None:
    """Holt aus einem WebKit-/JSC-Ergebnis den String-Wert (versionsunabhaengig)."""
    if value is None:
        return None
    getter = getattr(value, "get_js_value", None)
    if callable(getter):
        try:
            value = getter()
        except Exception:  # pragma: no cover
            return None
    if value is None:
        return None
    if isinstance(value, str):
        return value
    to_string = getattr(value, "to_string", None)
    if callable(to_string):
        try:
            text = to_string()
        except Exception:  # pragma: no cover
            return None
        return text if isinstance(text, str) else None
    return None


class WebViewAdapter:
    """Einheitliche JavaScript-Auswertung fuer 2.x/4.0/4.1."""

    def __init__(self, toolkit: Toolkit, webview: Any) -> None:
        self.toolkit = toolkit
        self.webview = webview
        self.modern = toolkit.modern_javascript

    def evaluate(self, script: str, on_done: Callable[[str | None, Exception | None], None] | None = None) -> None:
        """Wertet JavaScript aus; ``on_done(text, error)`` wird immer aufgerufen."""
        if self.modern:
            try:
                self.webview.evaluate_javascript(script, -1, None, None, None, self._on_modern_done, on_done)
            except Exception as error:  # pragma: no cover
                self._finish(on_done, None, error)
        else:
            try:
                self.webview.run_javascript(script, None, self._on_legacy_done, on_done)
            except Exception as error:  # pragma: no cover
                self._finish(on_done, None, error)

    # -- Callbacks -----------------------------------------------------------

    def _on_modern_done(self, webview: Any, result: Any, user_data: Any) -> None:
        text, error = None, None
        try:
            value = webview.evaluate_javascript_finish(result)
            text = _js_value_to_text(value)
        except Exception as exception:  # GLib.Error oder TypeError
            error = exception
        self._finish(user_data, text, error)

    def _on_legacy_done(self, webview: Any, result: Any, user_data: Any) -> None:
        text, error = None, None
        try:
            value = webview.run_javascript_finish(result)
            text = _js_value_to_text(value)
        except Exception as exception:
            error = exception
        self._finish(user_data, text, error)

    @staticmethod
    def _finish(callback: Callable[[str | None, Exception | None], None] | None, text: str | None, error: Exception | None) -> None:
        if callback is None:
            return
        try:
            callback(text, error)
        except Exception:  # pragma: no cover - Fehler im Callback nicht weiterreichen
            log.exception("Fehler im JavaScript-Callback")


def connect_script_message(toolkit: Toolkit, webview: Any, name: str, handler: Callable[[Any, str | None], None]) -> bool:
    """Registriert einen Nachrichtenkanal JS -> Python.

    ``handler(value, raw_text)`` bekommt den dekodierten JS-Wert und den Rohtext.
    """
    try:
        manager = webview.get_user_content_manager()
        manager.register_script_message_handler(name)
        signal = f"script-message-received::{name}"

        def on_message(_manager: Any, value: Any) -> None:
            # In aelteren Versionen kann hier ein JavascriptResult ankommen
            resolved = value
            getter = getattr(resolved, "get_js_value", None)
            if callable(getter):
                try:
                    resolved = getter()
                except Exception:  # pragma: no cover
                    resolved = value
            raw = _js_value_to_text(resolved)
            handler(resolved, raw)

        manager.connect(signal, on_message)
        return True
    except Exception:  # pragma: no cover - Umgebungsabhaengig
        log.exception("Nachrichtenkanal %r konnte nicht registriert werden", name)
        return False


def can_print(toolkit: Toolkit, webview: Any) -> bool:
    """WebKit2GTK kann erst ab 2.40 selbst drucken."""
    return callable(getattr(webview, "print", None))


def print_webview(toolkit: Toolkit, webview: Any) -> bool:
    printer = getattr(webview, "print", None)
    if not callable(printer):
        return False
    try:
        printer()
        return True
    except Exception:  # pragma: no cover
        log.exception("Drucken fehlgeschlagen")
        return False


def launch_external(uri: str) -> bool:
    """Oeffnet eine URL/Datei mit der Standardanwendung."""
    from urllib.parse import urlparse

    parsed = urlparse(uri)
    if parsed.scheme and parsed.scheme not in {"http", "https", "mailto", "tel", "file", "ftp"}:
        log.warning("Nicht erlaubtes URI-Schema: %s", parsed.scheme)
        return False
    try:
        from gi.repository import Gio  # type: ignore

        return bool(Gio.AppInfo.launch_default_for_uri(uri, None))
    except Exception:
        pass
    # Notnagel, falls GIO/AppInfo nicht verfuegbar ist
    import subprocess

    try:
        subprocess.Popen(["xdg-open", uri], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        log.warning("Konnte %s nicht oeffnen", uri)
        return False
