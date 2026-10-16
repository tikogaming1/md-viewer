"""Eine Seite (Tab): WebView + Dokument + Nachrichtenkanal zum Viewer."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from . import __version__, paths
from .compat import (
    Toolkit,
    WebViewAdapter,
    apply_webview_settings,
    connect_script_message,
    create_webview,
)
from .documents import Document
from .settings import Settings

log = logging.getLogger(__name__)

MESSAGE_CHANNEL = "app"


def js_literal(value: Any) -> str:
    """Serialisiert einen Wert als JavaScript-Literal (sicher fuer evaluate_javascript).

    ``u2028``/``u2029`` sind in aelteren JS-Engines Zeilentrenner und wuerden den
    Ausdruck zerreissen - deshalb escapen.
    """
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def build_payload(
    *,
    kind: str = "document",
    text: str = "",
    path: str | None = None,
    file_name: str | None = None,
    base_href: str | None = None,
    url: str | None = None,
    encoding: str | None = None,
    size: int | None = None,
    modified: float | None = None,
    notice: str | None = None,
    footer: str | None = None,
    settings: dict[str, Any] | None = None,
    render_options: dict[str, Any] | None = None,
    keep_scroll: bool = False,
) -> dict[str, Any]:
    """Baut die Nutzlast, die der Viewer im WebView erwartet (siehe viewer.js)."""
    payload: dict[str, Any] = {
        "kind": kind,
        "text": text,
        "appVersion": __version__,
        "keepScroll": bool(keep_scroll),
    }
    optional = {
        "path": path,
        "fileName": file_name,
        "baseHref": base_href,
        "url": url,
        "encoding": encoding,
        "size": size,
        "modified": modified,
        "notice": notice,
        "footer": footer,
        "settings": settings,
        "renderOptions": render_options,
    }
    for key, value in optional.items():
        if value is not None:
            payload[key] = value
    return payload


def document_payload(
    document: Document,
    *,
    settings: Settings,
    notice: str | None = None,
    footer: str | None = None,
    keep_scroll: bool = False,
) -> dict[str, Any]:
    """Nutzlast fuer eine Datei auf der Festplatte."""
    return build_payload(
        kind="document",
        text=document.text,
        path=str(document.path),
        file_name=document.name,
        base_href=document.base_href,
        url=document.url,
        encoding=document.encoding,
        size=document.size,
        modified=document.modified,
        notice=notice if notice is not None else document.notice(),
        footer=footer,
        settings=settings.viewer_settings(),
        render_options=settings.render_options(),
        keep_scroll=keep_scroll,
    )


def welcome_payload(*, settings: Settings, text: str, footer: str | None = None) -> dict[str, Any]:
    return build_payload(
        kind="welcome",
        text=text,
        footer=footer,
        settings=settings.viewer_settings(),
        render_options=settings.render_options(),
    )


class ViewerPage:
    """Haelt ein WebView, das genau ein Dokument darstellt."""

    def __init__(self, toolkit: Toolkit, settings: Settings, *, developer: bool = False) -> None:
        self.toolkit = toolkit
        self.settings = settings
        self.webview = create_webview(toolkit)
        apply_webview_settings(toolkit, self.webview, developer=developer)
        self.adapter = WebViewAdapter(toolkit, self.webview)

        self.index_url = paths.web_index().as_uri()
        self.page_loaded = False
        self.stats: dict[str, Any] = {}
        self.document: Document | None = None
        self.kind = "welcome"
        self._pending: dict[str, Any] | None = None

        #: Callbacks, die das Fenster setzt
        self.on_ready: Callable[[], None] | None = None
        self.on_rendered: Callable[[dict[str, Any]], None] | None = None
        self.on_open_external: Callable[[str], None] | None = None
        self.on_open_path: Callable[[str], None] | None = None
        self.on_copy_text: Callable[[str], None] | None = None
        self.on_error: Callable[[str], None] | None = None

        connect_script_message(toolkit, self.webview, MESSAGE_CHANNEL, self._handle_message)
        self.webview.connect("load-changed", self._on_load_changed)
        self.webview.connect("decide-policy", self._on_decide_policy)
        self.webview.connect("create", self._on_create)

    # ------------------------------------------------------------ Navigation

    @property
    def container(self) -> Any:
        """Das Widget, das in den Tab wandert."""
        return self.webview

    def load_page(self) -> None:
        self.webview.load_uri(self.index_url)

    def reload_page(self) -> None:
        if self._pending is not None:
            self._push(self._pending)
        else:
            self.webview.reload()

    # ------------------------------------------------------------- Nachrichten

    def _on_load_changed(self, _webview: Any, event: Any) -> None:
        finished = getattr(self.toolkit.WebKit.LoadEvent, "FINISHED", 3)
        if event != finished:
            return
        self.page_loaded = True
        if self._pending is not None:
            self._push(self._pending)
        if self.on_ready:
            self.on_ready()

    def _on_decide_policy(self, _webview: Any, decision: Any, decision_type: Any) -> bool:
        """Nur die eigene Seite darf navigieren - alles andere wird blockiert."""
        types = self.toolkit.WebKit.PolicyDecisionType
        try:
            if decision_type == types.RESPONSE or decision_type == types.NEW_WINDOW_ACTION:
                decision.ignore()
                return True
            if decision_type == types.NAVIGATION_ACTION:
                uri = decision.get_navigation_action().get_request().get_uri() or ""
                if uri == self.index_url or uri.startswith(self.index_url + "#") or uri == "about:blank":
                    decision.use()
                else:
                    log.debug("Navigation blockiert: %s", uri)
                    decision.ignore()
                return True
        except Exception:  # pragma: no cover - defensiv
            log.exception("Fehler in decide-policy")
        return False

    def _on_create(self, _webview: Any, navigation_action: Any) -> Any:
        """Fenster, die das Dokument selbst oeffnen moechte, unterbinden."""
        log.debug("Popup blockiert")
        return None

    def _handle_message(self, _value: Any, raw: str | None) -> None:
        if not raw:
            return
        try:
            message = json.loads(raw)
        except (TypeError, ValueError):
            log.debug("Unlesbare Nachricht aus dem Viewer: %r", raw)
            return
        if not isinstance(message, dict):
            return
        kind = message.get("type")
        if kind == "ready":
            if self.on_ready:
                self.on_ready()
        elif kind == "rendered":
            stats = message.get("stats")
            self.stats = stats if isinstance(stats, dict) else {}
            if self.on_rendered:
                self.on_rendered(message)
        elif kind == "open-external" and message.get("url"):
            url = str(message["url"])
            # Nur sichere, explizit erlaubte Schemas nach aussen weiterreichen.
            if url.lower().startswith(("http://", "https://", "mailto:", "tel:")):
                if self.on_open_external:
                    self.on_open_external(url)
        elif kind == "open-path" and message.get("url"):
            url = str(message["url"])
            # Nur lokale Datei-URLs duerfen als Dokument geoeffnet werden.
            if url.lower().startswith("file:"):
                if self.on_open_path:
                    self.on_open_path(url)
        elif kind == "copy-text" and message.get("text") is not None:
            if self.on_copy_text:
                self.on_copy_text(str(message["text"]))
        elif kind == "warning":
            log.warning("Viewer-Hinweis: %s", message.get("message"))
        elif kind == "error":
            text = str(message.get("message") or "Unbekannter Fehler")
            log.warning("Viewer meldet Fehler: %s", text)
            if self.on_error:
                self.on_error(text)
        elif kind == "action":
            self._handle_action(str(message.get("name", "")))

    def _handle_action(self, name: str) -> None:
        """Aktionen, die die Seite selbst ausloest (z. B. Startseite)."""
        log.debug("Aktion aus der Seite: %s", name)

    # ---------------------------------------------------------------- Inhalt

    def _push(self, payload: dict[str, Any]) -> None:
        script = f"window.MDViewer && window.MDViewer.load({js_literal(payload)})"
        self._last_script = script
        self.adapter.evaluate(script, self._log_result)

    @staticmethod
    def _log_result(text: str | None, error: Exception | None) -> None:
        if error is not None:
            log.warning("JavaScript-Fehler: %s", error)

    def show_payload(self, payload: dict[str, Any]) -> None:
        """Zeigt eine Nutzlast; wartet, bis die Seite geladen ist."""
        self._pending = payload
        self.kind = payload.get("kind", "document")
        if self.page_loaded:
            self._push(payload)

    def show_document(self, document: Document, *, notice: str | None = None, keep_scroll: bool = False) -> None:
        self.document = document
        self.show_payload(
            document_payload(document, settings=self.settings, notice=notice, footer=None, keep_scroll=keep_scroll)
        )

    def show_welcome(self, text: str, footer: str | None = None) -> None:
        self.document = None
        self.show_payload(welcome_payload(settings=self.settings, text=text, footer=footer))

    def show_error(self, markdown_text: str) -> None:
        self.document = None
        self.show_payload(welcome_payload(settings=self.settings, text=markdown_text, footer=None))

    def set_theme(self, theme: str) -> None:
        """Designwechsel ohne Neu-Rendern."""
        self._eval(f"window.MDViewer && window.MDViewer.setTheme({js_literal(theme)})")

    def update_settings(self) -> None:
        """Nutzlast mit den aktuellen Einstellungen erneut an den Viewer schicken.

        Da sich Rendereinstellungen (Zeilenumbrueche, Highlighting, ...) nur beim
        Rendern auswirken, wird das Dokument dabei neu aufgebaut - die
        Scrollposition bleibt erhalten (``keepScroll``).
        """
        if self._pending is None:
            return
        updated = dict(self._pending)
        updated["settings"] = self.settings.viewer_settings()
        updated["renderOptions"] = self.settings.render_options()
        updated["keepScroll"] = True
        self._pending = updated
        if self.page_loaded:
            self._push(updated)

    def open_find(self) -> None:
        self._eval("window.MDViewer && window.MDViewer.openFind()")

    def close_find(self) -> None:
        self._eval("window.MDViewer && window.MDViewer.closeFind()")

    def find_again(self) -> None:
        self._eval("window.MDViewer && window.MDViewer.findNext()")

    def find_previous(self) -> None:
        self._eval("window.MDViewer && window.MDViewer.findPrev()")

    def set_zoom(self, percent: int) -> None:
        """Schriftgroesse aendern, ohne das Dokument neu zu rendern."""
        try:
            value = max(50, min(250, int(percent)))
        except (TypeError, ValueError):
            return
        self._eval(f"window.MDViewer && window.MDViewer.setZoom({value})")

    def scroll_top(self) -> None:
        self._eval("window.MDViewer && window.MDViewer.scrollTop()")

    def toast(self, message: str) -> None:
        self._eval(f"window.MDViewer && window.MDViewer.toast({js_literal(message)})")

    def _eval(self, script: str) -> None:
        if not self.page_loaded:
            return
        self.adapter.evaluate(script)

    # ------------------------------------------------------------------ Export

    def request_body_html(self, callback: Callable[[str | None], None]) -> None:
        """Holt das gerenderte HTML aus der Seite (fuer den HTML-Export)."""

        def done(text: str | None, error: Exception | None) -> None:
            if error is not None:
                log.warning("HTML konnte nicht gelesen werden: %s", error)
                callback(None)
                return
            callback(text or "")

        if not self.page_loaded:
            callback(None)
            return
        self.adapter.evaluate("window.MDViewer && window.MDViewer.bodyHtml()", done)

    def print_page(self) -> bool:
        from .compat import print_webview

        return print_webview(self.toolkit, self.webview)

    def grab_focus(self) -> None:
        try:
            self.webview.grab_focus()
        except Exception:  # pragma: no cover
            pass
