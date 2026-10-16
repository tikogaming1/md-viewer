"""Die Gtk.Application: Fenster erzeugen, Dateien von der Kommandozeile oeffnen,
Startfehler verstaendlich melden.

Wichtig: Dieses Modul importiert GTK nicht auf Modulebene - so lassen sich
Argumentbehandlung und Steuerung ohne grafische Umgebung testen.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from . import APP_ID, APP_NAME, __version__, i18n, paths
from .compat import MissingDependency, load_toolkit
from .settings import Settings

log = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISSING_DEPENDENCY = 3
EXIT_ERROR = 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md-viewer",
        description=f"{APP_NAME} - Markdown-Dateien fertig gerendert anzeigen.",
    )
    parser.add_argument("files", nargs="*", metavar="DATEI", help="Markdown-Dateien, die geöffnet werden sollen")
    parser.add_argument("--version", action="store_true", help="Version ausgeben und beenden")
    parser.add_argument("--debug", action="store_true", help="Ausführliche Protokollausgabe (Entwicklung)")
    parser.add_argument(
        "--language",
        choices=sorted(i18n.LANGUAGES),
        help="Sprache der Oberfläche für diesen Start erzwingen",
    )
    parser.add_argument(
        "--export-html",
        metavar="ZIELDATEI",
        help="Die angegebene Datei rendern, als HTML speichern und beenden",
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(list(argv) if argv is not None else None)


def validate_args(args: argparse.Namespace, parser: argparse.ArgumentParser | None = None) -> None:
    """Prueft Kombinationen, die argparse nicht abdeckt (Exit-Code 2)."""
    if args.export_html and len(args.files) != 1:
        message = (
            "--export-html benötigt genau eine Eingabedatei, z. B.\n"
            "    md-viewer --export-html notizen.html notizen.md"
        )
        (parser or build_parser()).error(message)


def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(levelname)s %(name)s: %(message)s",
        force=True,
    )


class ApplicationController:
    """Verbindet Gtk.Application, Fenster und Kommandozeilenargumente."""

    def __init__(
        self,
        application: Any,
        toolkit: Any,
        settings: Settings,
        *,
        developer: bool = False,
        export_target: str | None = None,
    ) -> None:
        self.application = application
        self.toolkit = toolkit
        self.settings = settings
        self.developer = developer
        self.export_target = export_target
        self.window: Any = None
        self._pending: list[str] = []
        self._export_done = False
        self._export_started = False
        self.export_source: str | None = None

    # ------------------------------------------------------------- Signale

    def on_startup(self, _application: Any) -> None:
        try:
            self.toolkit.Gtk.Window.set_default_icon_name(APP_ID)
        except Exception:  # pragma: no cover
            pass

    def on_activate(self, _application: Any) -> None:
        window = self.ensure_window()
        if self._pending:
            paths_to_open = list(self._pending)
            self._pending.clear()
            self.open_files(paths_to_open)
            return
        if self.export_source and not self._export_started:
            self._export_started = True
            self.request_export(self.export_source)
            return
        try:
            window.window.present()
        except Exception:  # pragma: no cover
            pass

    def on_open(self, _application: Any, files: Any, _n_files: int, _hint: str) -> None:
        found: list[str] = []
        for gfile in list(files or []):
            try:
                local = gfile.get_path()
            except Exception:  # pragma: no cover
                local = None
            if local:
                found.append(local)
        if not found:
            return
        if self.window is None:
            self._pending.extend(found)
            self.ensure_window()
            self.on_activate(self.application)
            return
        self.open_files(found)

    def on_shutdown(self, _application: Any) -> None:
        if self.window is not None:
            self.window.save_window_state()
        self.settings.save()

    # -------------------------------------------------------------- Fenster

    def ensure_window(self) -> Any:
        if self.window is None:
            from .window import MainWindow

            self.window = MainWindow(self.application, self.toolkit, self.settings, developer=self.developer)
            self.window.present(welcome_doc=True)
        return self.window

    def open_files(self, paths: list[str]) -> None:
        window = self.ensure_window()
        existing = [p for p in paths if Path(p).exists()]
        missing = [p for p in paths if p not in existing]
        if existing:
            window.open_paths(existing)
        for path in missing:
            window.open_path(path)  # zeigt die Fehlermeldung als Dokument

    # -------------------------------------------------------------- Export

    def request_export(self, source: str) -> None:
        """CLI-Export: Datei rendern, HTML schreiben, Anwendung beenden."""
        window = self.ensure_window()

        def after_render(tab: Any) -> None:
            if self._export_done:
                return
            self._export_done = True
            window.export_html_to(self.export_target, tab, on_done=lambda ok: self.application.quit())

        window.open_path(source, new_tab=False, on_rendered=after_render)


def _report_startup_error(key: str, values: dict[str, Any] | None = None) -> int:
    """Fehlende Systembibliotheken: Dialog zeigen, sonst auf stderr ausgeben."""
    title = i18n.t(key)
    body = i18n.t(key.replace(".title", ".body"), **(values or {}))
    shown = False
    try:
        toolkit = load_toolkit(require_webkit=False)
        Gtk = toolkit.Gtk
        Gtk.init([])
        dialog = Gtk.MessageDialog(modal=True, buttons=Gtk.ButtonsType.OK, text=f"{APP_NAME}: {title}")
        dialog.format_secondary_text(body)
        dialog.set_title(APP_NAME)
        dialog.run()
        dialog.destroy()
        shown = True
    except Exception:  # pragma: no cover - keine Anzeige moeglich
        shown = False
    if not shown:
        print(f"{APP_NAME}: {title}\n\n{body}", file=sys.stderr)
    return EXIT_MISSING_DEPENDENCY


def run(argv: Sequence[str] | None = None) -> int:
    """Startet die Anwendung. Liefert den Exit-Code."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    validate_args(args, parser)

    if args.version:
        print(f"{APP_NAME} {__version__}")
        return EXIT_OK

    setup_logging(args.debug)
    developer = bool(args.debug or os.environ.get("MD_VIEWER_DEBUG"))

    settings = Settings().load()
    if args.language:
        settings.update({"language": args.language}, save=False)
    i18n.set_language(settings.get("language"))

    try:
        toolkit = load_toolkit()
    except MissingDependency as error:
        return _report_startup_error(error.key, error.values)
    except Exception as error:  # pragma: no cover - unerwartete Startfehler
        return _report_startup_error("error.no_gtk.title", {"error": str(error)})

    if not paths.web_index().is_file():
        log.error("Web-Assets fehlen: %s", paths.web_dir())
        try:
            toolkit.Gtk.init([])
            dialog = toolkit.Gtk.MessageDialog(
                modal=True,
                buttons=toolkit.Gtk.ButtonsType.OK,
                text=f"{APP_NAME}: {i18n.t('error.title')}",
            )
            dialog.format_secondary_text(f"index.html nicht gefunden ({paths.web_index()})")
            dialog.run()
        except Exception:  # pragma: no cover
            print(f"{APP_NAME}: index.html nicht gefunden ({paths.web_index()})", file=sys.stderr)
        return EXIT_ERROR

    holder: dict[str, Any] = {}

    class MdiViewerApplication(toolkit.Gtk.Application):
        """Gtk.Application mit eigenen vfuncs.

        Doppelte Verarbeitung (Standard-Handler *und* Callback) waere hier
        gefaehrlich - deshalb ersetzen wir die Standardimplementierung.
        """

        def do_startup(self) -> None:  # noqa: N802 (GTK-Namensschema)
            # Muss verkettet werden: hier initialisiert GTK sich selbst.
            toolkit.Gtk.Application.do_startup(self)
            holder["controller"].on_startup(self)

        def do_activate(self) -> None:  # noqa: N802
            holder["controller"].on_activate(self)

        def do_open(self, files: Any, n_files: int, hint: str) -> int:  # noqa: N802
            holder["controller"].on_open(self, files, n_files, hint)
            return 0

        def do_shutdown(self) -> None:  # noqa: N802
            holder["controller"].on_shutdown(self)
            toolkit.Gtk.Application.do_shutdown(self)

    application = MdiViewerApplication(application_id=APP_ID, flags=toolkit.Gio.ApplicationFlags.HANDLES_OPEN)
    controller = ApplicationController(
        application, toolkit, settings, developer=developer, export_target=args.export_html
    )
    holder["controller"] = controller

    if args.export_html:
        # Der Export laeuft im Hintergrund: Datei rendern, HTML schreiben, beenden.
        controller.export_source = str(Path(args.files[0]).expanduser())
    else:
        controller._pending.extend(str(Path(p).expanduser()) for p in args.files)  # noqa: SLF001

    try:
        return int(application.run([sys.argv[0]]) or 0)
    except KeyboardInterrupt:  # pragma: no cover
        return 130


def main() -> int:
    try:
        return run()
    except KeyboardInterrupt:  # pragma: no cover
        return 130
