"""Texte der Anwendung (Deutsch und Englisch).

Die Texte der *Web-Oberflaeche* liegen in ``web/src/i18n.js``; hier stehen alle
Texte, die die GTK-Oberflaeche selbst zeigt: Menues, Dialoge, Statusleiste,
Startseite, Fehlermeldungen.
"""

from __future__ import annotations

from typing import Any

DEFAULT_LANGUAGE = "de"

LANGUAGES = {"de": "Deutsch", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "de": {
        # Fenster / Kopfzeile
        "app.name": "MD Viewer",
        "app.comment": "Markdown-Dateien fertig gerendert anzeigen",
        "header.untitled": "Kein Dokument geöffnet",
        "header.toc": "Inhaltsverzeichnis ein-/ausblenden",
        "header.find": "Im Dokument suchen",
        "header.open": "Markdown-Datei öffnen",
        "tab.close": "Tab schließen",
        "tab.new": "Neuer Tab",
        "tab.tooltip": "{name}\n{path}",

        # Menue
        "menu.title": "Hauptmenü",
        "menu.open": "Öffnen …",
        "menu.open_tab": "In neuem Tab öffnen …",
        "menu.reload": "Neu laden",
        "menu.recent": "Zuletzt geöffnet",
        "menu.recent_empty": "Keine Einträge",
        "menu.recent_clear": "Liste leeren",
        "menu.find": "Suchen …",
        "menu.export_html": "Als HTML exportieren …",
        "menu.export_pdf": "Als PDF exportieren …",
        "menu.print": "Drucken …",
        "menu.view": "Ansicht",
        "menu.toc": "Inhaltsverzeichnis",
        "menu.theme": "Design",
        "menu.theme_auto": "Systemeinstellung",
        "menu.theme_light": "Hell",
        "menu.theme_dark": "Dunkel",
        "menu.width": "Zeilenbreite",
        "menu.width_normal": "Normal",
        "menu.width_wide": "Breit",
        "menu.width_full": "Volle Breite",
        "menu.zoom_in": "Vergrößern",
        "menu.zoom_out": "Verkleinern",
        "menu.zoom_reset": "Schriftgröße zurücksetzen",
        "menu.rendering": "Darstellung",
        "menu.auto_reload": "Bei Änderungen automatisch neu laden",
        "menu.block_remote_images": "Externe Bilder blockieren",
        "menu.breaks": "Einzelne Zeilenumbrüche umbrechen",
        "menu.math": "Mathematik mit KaTeX setzen",
        "menu.math_inline": "Inline-Mathematik ($...$) erkennen",
        "menu.language": "Sprache",
        "menu.help": "Hilfe",
        "menu.copy_path": "Dateipfad kopieren",
        "menu.shortcuts": "Tastenkürzel",
        "menu.about": "Über MD Viewer",
        "menu.quit": "Beenden",

        # Dateidialoge
        "open.title": "Markdown-Datei öffnen",
        "open.filter_markdown": "Markdown-Dateien",
        "open.filter_text": "Textdateien",
        "open.filter_all": "Alle Dateien",
        "open.accept": "Öffnen",
        "open.cancel": "Abbrechen",
        "export.title": "Als HTML exportieren",
        "export.accept": "Speichern",
        "export.filter_html": "HTML-Datei",
        "export.suggested_name": "{stem}.html",
        "export.done": "HTML-Datei gespeichert: {path}",
        "export.failed": "Export fehlgeschlagen: {error}",
        "export.printing": "Drucken wird von der installierten WebKitGTK-Version nicht unterstützt. Bitte „Als HTML exportieren“ verwenden.",

        # Statusleiste
        "status.no_file": "Keine Datei geöffnet",
        "status.stats": "{words} Wörter · {characters} Zeichen · ca. {minutes} Min. Lesezeit",
        "status.stats_empty": "Leeres Dokument",
        "status.details": "{path} · {size} · {encoding}",
        "status.modified": "geändert {time}",
        "status.reloaded": "Automatisch neu geladen ({time})",
        "status.reload_failed": "Automatisches Neuladen fehlgeschlagen",

        # Hinweise im Dokument
        "notice.encoding": "Die Datei ist {encoding}-kodiert (kein UTF-8). Umlaute und Sonderzeichen werden nach bestem Wissen umgewandelt.",
        "notice.large": "Große Datei ({size}). Das Rendern kann einen Moment dauern.",
        "notice.changed": "Die Datei wurde auf der Festplatte geändert und neu geladen.",
        "notice.missing": "Die Datei ist nicht mehr vorhanden (gelöscht oder verschoben?).",
        "notice.remote_images": "Externe Bilder sind standardmäßig blockiert – zum Laden auf das Bild klicken.",
        "notice.scroll_reset": "Inhalt wurde neu aufgebaut, die Scrollposition bleibt erhalten.",

        # Fehler
        "error.title": "Fehler",
        "error.read_failed": "Die Datei konnte nicht gelesen werden:\n{error}",
        "error.not_found": "Die Datei wurde nicht gefunden:\n{path}",
        "error.is_dir": "Dies ist ein Verzeichnis, keine Datei:\n{path}",
        "error.not_regular": "Dies ist keine reguläre Datei und kann nicht geöffnet werden:\n{path}",
        "error.too_large": "Die Datei ist zu groß ({size}). Maximal werden {limit} unterstützt.",
        "error.binary": "Die Datei scheint eine Binärdatei zu sein und kann nicht als Markdown angezeigt werden.",
        "error.no_webkit.title": "WebKitGTK fehlt",
        "error.no_webkit.body": "Zum Anzeigen von Markdown benötigt MD Viewer die Bibliothek „webkit2gtk“.\n\nInstallieren Sie sie mit:\n\n    sudo apt install gir1.2-webkit2-4.1\n\n(Debian 12/Ubuntu 24.04 und neuer) bzw.\n\n    sudo apt install gir1.2-webkit2-4.0\n\n(Debian 11/Ubuntu 22.04)",
        "error.no_gtk.title": "Grafische Oberfläche nicht verfügbar",
        "error.no_gtk.body": "MD Viewer braucht eine grafische Sitzung (X11 oder Wayland) mit GTK3 und WebKit2GTK.\n\nBitte prüfen Sie, ob diese Laufzeitpakete installiert sind:\n\n    sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 gir1.2-webkit2-4.1\n\nDetails:\n{error}",
        "error.js.title": "Fehler im Viewer",
        "error.unknown": "Unbekannter Fehler",
        "error.dropped_unsupported": "{name}: Dieser Dateityp kann nicht angezeigt werden.",

        # Dialoge
        "shortcuts.title": "Tastenkürzel",
        "shortcuts.close": "Schließen",
        "about.website": "Projektseite",
        "about.license": "MIT-Lizenz",
        "about.comments": "Ein schlanker Markdown-Betrachter für den Desktop.\n\nMarkdown wird wie auf GitHub dargestellt: Tabellen, Task-Listen, Fußnoten, Hinweis-Blöcke, Syntax-Highlighting und Mathematik (KaTeX). Alle Bibliotheken liegen lokal; externe Bilder sind standardmäßig blockiert und werden nur auf bewussten Klick geladen. Es gibt keine Telemetrie.",

        # Fusszeile der Startseite / Dokumentstatistik
        "footer": "{file} · {words} Wörter · {characters} Zeichen · ca. {minutes} Min. Lesezeit",
        "footer.welcome": "MD Viewer {version} · {shortcuts} für alle Tastenkürzel",

        # Startseite (Markdown)
        "welcome.title": "Willkommen bei MD Viewer",
        "welcome.intro": "Ziehen Sie eine Markdown-Datei in dieses Fenster oder öffnen Sie sie über **Strg+O** – der Inhalt erscheint fertig gerendert, so wie Sie es von GitHub kennen.",
        "welcome.features": "Was angezeigt wird",
        "welcome.feature_list": "- Überschriften mit Inhaltsverzeichnis in der Seitenleiste\n- Tabellen, Aufgabenlisten und Durchstreichen (GFM)\n- Codeblöcke mit Syntax-Highlighting und Kopier-Knopf\n- Hinweis-Blöcke wie `> [!NOTE]`, Fußnoten, aufklappbare Bereiche\n- Mathematik mit KaTeX ($x^2$, $$\\int_0^1 x\\,dx$$)\n- Frontmatter-Block (YAML/TOML) aufklappbar am Dokumentanfang",
        "welcome.hints": "Praktisch beim Lesen",
        "welcome.hint_list": "- **Live-Neuladen:** ändert sich die Datei auf der Festplatte, aktualisiert der Viewer sie automatisch\n- **Suchen:** Strg+F, Enter springt zum nächsten Treffer\n- **Bilder:** anklicken für die Großansicht; relative Bildpfade werden aus dem Ordner der Datei geladen; externe Bilder sind standardmäßig blockiert und laden erst nach Klick\n- **Links:** relative Links auf andere `.md`-Dateien öffnen diese im Viewer, Web-Links gehen an den Standardbrowser\n- **Kopieren:** Codeblöcke und Überschriften-Links landen per Klick in der Zwischenablage",
        "welcome.shortcuts": "Tastenkürzel",
        "welcome.footer_note": "Viel Vergnügen beim Lesen!",
        "welcome.lang_hint": "Die Sprache lässt sich im Menü unter „Hilfe → Sprache“ umstellen.",
        "welcome.opened_with": "Geöffnet aus: {path}",

        # Tastenkürzel-Liste (Taste, Beschreibung)
        "shortcut.open": "Datei öffnen",
        "shortcut.open_tab": "In neuem Tab öffnen",
        "shortcut.reload": "Dokument neu laden",
        "shortcut.find": "Im Dokument suchen",
        "shortcut.find_next": "Nächster Treffer",
        "shortcut.close_tab": "Tab schließen",
        "shortcut.toc": "Inhaltsverzeichnis umschalten",
        "shortcut.zoom_in": "Vergrößern",
        "shortcut.zoom_out": "Verkleinern",
        "shortcut.zoom_reset": "Schriftgröße zurücksetzen",
        "shortcut.export": "Als HTML exportieren",
        "shortcut.print": "Drucken",
        "shortcut.quit": "Beenden",
        "shortcut.escape": "Suche schließen",

        # kurze Rückmeldungen im Dokument
        "toast.copied": "In die Zwischenablage kopiert",
        "toast.copy_failed": "Kopieren nicht möglich",
        "toast.zoom": "Schriftgröße: {zoom} %",
        "toast.path": "Pfad kopiert: {path}",
    },
    "en": {
        "app.name": "MD Viewer",
        "app.comment": "View Markdown files as rendered documents",
        "header.untitled": "No document open",
        "header.toc": "Toggle table of contents",
        "header.find": "Find in document",
        "header.open": "Open Markdown file",
        "tab.close": "Close tab",
        "tab.new": "New tab",
        "tab.tooltip": "{name}\n{path}",

        "menu.title": "Main menu",
        "menu.open": "Open …",
        "menu.open_tab": "Open in new tab …",
        "menu.reload": "Reload",
        "menu.recent": "Recent files",
        "menu.recent_empty": "No entries",
        "menu.recent_clear": "Clear list",
        "menu.find": "Find …",
        "menu.export_html": "Export as HTML …",
        "menu.export_pdf": "Export as PDF …",
        "menu.print": "Print …",
        "menu.view": "View",
        "menu.toc": "Table of contents",
        "menu.theme": "Theme",
        "menu.theme_auto": "Follow system",
        "menu.theme_light": "Light",
        "menu.theme_dark": "Dark",
        "menu.width": "Line width",
        "menu.width_normal": "Normal",
        "menu.width_wide": "Wide",
        "menu.width_full": "Full width",
        "menu.zoom_in": "Zoom in",
        "menu.zoom_out": "Zoom out",
        "menu.zoom_reset": "Reset font size",
        "menu.rendering": "Rendering",
        "menu.auto_reload": "Reload automatically when the file changes",
        "menu.block_remote_images": "Block remote images",
        "menu.breaks": "Wrap single line breaks",
        "menu.math": "Typeset math with KaTeX",
        "menu.math_inline": "Detect inline math ($...$)",
        "menu.language": "Language",
        "menu.help": "Help",
        "menu.copy_path": "Copy file path",
        "menu.shortcuts": "Keyboard shortcuts",
        "menu.about": "About MD Viewer",
        "menu.quit": "Quit",

        "open.title": "Open Markdown file",
        "open.filter_markdown": "Markdown files",
        "open.filter_text": "Text files",
        "open.filter_all": "All files",
        "open.accept": "Open",
        "open.cancel": "Cancel",
        "export.title": "Export as HTML",
        "export.accept": "Save",
        "export.filter_html": "HTML file",
        "export.suggested_name": "{stem}.html",
        "export.done": "HTML file saved: {path}",
        "export.failed": "Export failed: {error}",
        "export.printing": "Printing is not supported by the installed WebKitGTK version. Please use “Export as HTML”.",

        "status.no_file": "No file open",
        "status.stats": "{words} words · {characters} characters · ~{minutes} min read",
        "status.stats_empty": "Empty document",
        "status.details": "{path} · {size} · {encoding}",
        "status.modified": "modified {time}",
        "status.reloaded": "Reloaded automatically ({time})",
        "status.reload_failed": "Automatic reload failed",

        "notice.encoding": "The file is encoded as {encoding} (not UTF-8). Characters are converted as best as possible.",
        "notice.large": "Large file ({size}). Rendering may take a moment.",
        "notice.changed": "The file changed on disk and was reloaded.",
        "notice.missing": "The file is gone (deleted or moved?).",
        "notice.remote_images": "Remote images are blocked by default – click an image to load it.",
        "notice.scroll_reset": "Content was rebuilt, the scroll position is kept.",

        "error.title": "Error",
        "error.read_failed": "The file could not be read:\n{error}",
        "error.not_found": "The file was not found:\n{path}",
        "error.is_dir": "This is a directory, not a file:\n{path}",
        "error.not_regular": "This is not a regular file and cannot be opened:\n{path}",
        "error.too_large": "The file is too large ({size}). The limit is {limit}.",
        "error.binary": "The file looks like a binary file and cannot be shown as Markdown.",
        "error.no_webkit.title": "WebKitGTK is missing",
        "error.no_webkit.body": "MD Viewer needs the “webkit2gtk” library to render Markdown.\n\nInstall it with:\n\n    sudo apt install gir1.2-webkit2-4.1\n\n(Debian 12/Ubuntu 24.04 and newer) or\n\n    sudo apt install gir1.2-webkit2-4.0\n\n(Debian 11/Ubuntu 22.04)",
        "error.no_gtk.title": "No graphical interface available",
        "error.no_gtk.body": "MD Viewer needs a graphical session (X11 or Wayland) with GTK3 and WebKit2GTK.\n\nPlease verify that these runtime packages are installed:\n\n    sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 gir1.2-webkit2-4.1\n\nDetails:\n{error}",
        "error.js.title": "Error in the viewer",
        "error.unknown": "Unknown error",
        "error.dropped_unsupported": "{name}: this file type cannot be displayed.",

        "shortcuts.title": "Keyboard shortcuts",
        "shortcuts.close": "Close",
        "about.website": "Project page",
        "about.license": "MIT licence",
        "about.comments": "A slim Markdown viewer for the desktop.\n\nMarkdown is rendered the way GitHub shows it: tables, task lists, footnotes, alert blocks, syntax highlighting and math (KaTeX). All libraries are local; remote images are blocked by default and load only after an explicit click. No telemetry is sent.",

        "footer": "{file} · {words} words · {characters} characters · ~{minutes} min read",
        "footer.welcome": "MD Viewer {version} · press {shortcuts} to see all shortcuts",

        "welcome.title": "Welcome to MD Viewer",
        "welcome.intro": "Drop a Markdown file into this window or open one with **Ctrl+O** – the content appears fully rendered, just like on GitHub.",
        "welcome.features": "What is rendered",
        "welcome.feature_list": "- Headings with a table of contents in the sidebar\n- Tables, task lists and strikethrough (GFM)\n- Code blocks with syntax highlighting and a copy button\n- Alert blocks like `> [!NOTE]`, footnotes, collapsible sections\n- Math with KaTeX ($x^2$, $$\\int_0^1 x\\,dx$$)\n- Frontmatter block (YAML/TOML) collapsible at the top of the document",
        "welcome.hints": "Handy while reading",
        "welcome.hint_list": "- **Live reload:** when the file changes on disk the viewer updates itself\n- **Search:** Ctrl+F, Enter jumps to the next match\n- **Images:** click for a large view; relative image paths are loaded from the file's folder; remote images are blocked by default and load only after a click\n- **Links:** relative links to other `.md` files open in the viewer, web links go to your browser\n- **Copy:** code blocks and heading links go to the clipboard with one click",
        "welcome.shortcuts": "Keyboard shortcuts",
        "welcome.footer_note": "Happy reading!",
        "welcome.lang_hint": "The language can be changed in the menu under “Help → Language”.",
        "welcome.opened_with": "Opened from: {path}",

        "shortcut.open": "Open file",
        "shortcut.open_tab": "Open in a new tab",
        "shortcut.reload": "Reload document",
        "shortcut.find": "Find in document",
        "shortcut.find_next": "Next match",
        "shortcut.close_tab": "Close tab",
        "shortcut.toc": "Toggle table of contents",
        "shortcut.zoom_in": "Zoom in",
        "shortcut.zoom_out": "Zoom out",
        "shortcut.zoom_reset": "Reset font size",
        "shortcut.export": "Export as HTML",
        "shortcut.print": "Print",
        "shortcut.quit": "Quit",
        "shortcut.escape": "Close search",

        "toast.copied": "Copied to clipboard",
        "toast.copy_failed": "Copying failed",
        "toast.zoom": "Font size: {zoom} %",
        "toast.path": "Path copied: {path}",
    },
}

#: (Tastenkombination, Textschluessel)
SHORTCUTS: list[tuple[str, str]] = [
    ("Strg+O", "shortcut.open"),
    ("Strg+Umschalt+O", "shortcut.open_tab"),
    ("Strg+R", "shortcut.reload"),
    ("Strg+F", "shortcut.find"),
    ("F3 / Umschalt+F3", "shortcut.find_next"),
    ("Strg+W", "shortcut.close_tab"),
    ("Strg+B", "shortcut.toc"),
    ("Strg++", "shortcut.zoom_in"),
    ("Strg+-", "shortcut.zoom_out"),
    ("Strg+0", "shortcut.zoom_reset"),
    ("Strg+E", "shortcut.export"),
    ("Strg+P", "shortcut.print"),
    ("Esc", "shortcut.escape"),
    ("Strg+Q", "shortcut.quit"),
]

_language = DEFAULT_LANGUAGE


def set_language(language: str | None) -> str:
    """Setzt die aktive Sprache; unbekannte Werte fallen auf Deutsch zurueck."""
    global _language
    _language = language if language in STRINGS else DEFAULT_LANGUAGE
    return _language


def get_language() -> str:
    return _language


def t(key: str, **values: Any) -> str:
    """Uebersetzter Text.

    Ohne ``values`` bleibt der Text unveraendert - so koennen Vorlagen mit
    ``{platzhaltern}`` (z. B. die Statistik-Fusszeile fuer den Viewer) direkt
    weitergegeben werden.
    """
    table = STRINGS.get(_language, STRINGS[DEFAULT_LANGUAGE])
    text = table.get(key) or STRINGS[DEFAULT_LANGUAGE].get(key) or key
    if not values:
        return text
    try:
        return text.format(**values)
    except (KeyError, IndexError):
        return text


def shortcuts_table() -> list[tuple[str, str]]:
    return [(keys, t(key)) for keys, key in SHORTCUTS]
