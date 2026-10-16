"""MD Viewer - Markdown-Dateien als fertig gerendertes Dokument anzeigen.

Die App besteht aus zwei Teilen:

* ``mdviewer`` (dieses Python-Paket): GTK3-Fenster, Dateiverwaltung, Einstellungen,
  Zwischenablage, Export, Live-Neuladen.
* ``web/`` (HTML/CSS/JS, installiert unter ``/usr/lib/md-viewer/web``): das Rendern
  des Markdowns im WebKit2GTK-WebView (marked + highlight.js + KaTeX + DOMPurify).
"""

__all__ = ["__version__", "APP_ID", "APP_NAME", "APP_SLUG"]

__version__ = "1.1.0"

APP_NAME = "MD Viewer"
APP_SLUG = "md-viewer"
APP_ID = "de.tikogaming.MDViewer"
WEBSITE = "https://github.com/tikogaming1/md-viewer"
