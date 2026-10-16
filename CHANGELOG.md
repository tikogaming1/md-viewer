# Änderungen

Alle nennenswerten Änderungen an MD Viewer. Format angelehnt an
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionen folgen
[semantischer Versionierung](https://semver.org/lang/de/).

## [1.1.2] – 2026-10-16

### Sicherheit

- Externe Bilder werden standardmäßig blockiert. Ein Klick lädt nur das gewählte
  Bild; andere Remote-Bilder bleiben Platzhalter. Eine globale Freigabe ist weiterhin möglich.
- Alte, nicht versionierte Einstellungen werden einmalig migriert, damit ein
  zuvor automatisch gespeichertes `false` nicht die neue Datenschutz-Voreinstellung
  aushebelt. Eine bewusste Freigabe kann danach wieder gespeichert werden.
- Dokumente werden über einen einzelnen regulären Datei-Deskriptor gelesen. FIFO-
  und Geräte-Dateien werden abgewiesen; die begrenzte Leseoperation verhindert
  unbegrenztes Lesen bei Größenänderungen zwischen Prüfung und Zugriff.
- Eingebettete HTML-`style`-Attribute, nicht benötigte Medien-/Bild-Ladeelemente und
  vom Viewer reservierte `data-*`-Marker werden entfernt, damit ein ausdrücklich
  freigegebener Bild-Ursprung keine zusätzlichen Ressourcenabrufe auslöst und Markdown
  den internen Sperrzustand nicht vortäuschen kann.

### Korrektheit und Paketierung

- CSP, Vorschau, Einstellungen, README und Paketbeschreibung stimmen beim
  Verhalten externer Bilder überein. Die CSP-Meta-Regel bleibt statisch, da Browser
  Änderungen nach dem Parsen ignorieren; DOM-Sanitizing und Platzhalter blockieren
  Remote-Bilder vor dem Einfügen, während aktive Verbindungen gesperrt bleiben.
- Eine nicht vorhandene CI-Workflow-Badge wurde aus der README entfernt.
- Die Debian-Abhängigkeiten nennen nur WebKit2GTK-APIs, die mit der deklarierten
  Python-Mindestversion unterstützt werden.

## [1.1.1] – 2026-10-16

### Behoben

- GTK3, Gdk3 und GdkPixbuf 2.0 werden vor dem GI-Import explizit angefordert.
  Damit startet MD Viewer auch auf Systemen mit installiertem GTK4, ohne dass
  versehentlich Gdk 4.0 mit GTK3 kollidiert.
- Die Versionsnummer im WebView-Bundle wird jetzt aus den Projekt-Metadaten
  erzeugt und bleibt mit Python-Paket und .deb synchron.
- Die Paketprüfung kontrolliert, dass GTK3, WebKit2GTK und Python-GI als
  installierbare Debian-Abhängigkeiten deklariert sind.

## [1.1.0] – 2026-10-16

### Sicherheit

- Eingehende Dokument-URLs und externe URI-Schemas werden geprüft; externe
  Handler sind auf http, https, mailto und tel begrenzt.
- `open_uri` akzeptiert nur lokale Markdown- und Textdateien.

### Build und Tests

- Das npm-Testskript verwendet ein Node.js-kompatibles Testdatei-Glob.

## [1.0.0] – 2026-10-16

Erste Veröffentlichung.

### Hinzugefügt

- **Anzeige wie auf GitHub**: Überschriften mit automatischen Anker-IDs, Tabellen,
  Aufgabenlisten, Durchstreichen, Autolinks, Fußnoten, Hinweis-Blöcke
  (`> [!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, `[!CAUTION]`), aufklappbares
  YAML-/TOML-Frontmatter, aufklappbare `<details>`-Bereiche
- **Syntax-Highlighting** mit highlight.js (GitHub-Standardthemen, hell und dunkel)
- **Formelsatz** mit KaTeX (inline und als Block), KaTeX wird nur bei Bedarf nachgeladen
- **Inhaltsverzeichnis** in der Seitenleiste inklusive Hervorhebung des aktuellen
  Abschnitts beim Scrollen; ein-/ausblendbar mit `Strg+B`
- **Suche im Dokument** (`Strg+F`) mit Trefferzählung, Sprungmarken und Tastaturbedienung
- **Bilder**: Großansicht per Klick, Auflösung relativer Pfade aus dem Dokumentordner,
  optionales Blockieren externer Bilder (CSP wird entsprechend verschärft)
- **Links**: relative Links auf Markdown-Dateien öffnen im Viewer (neuer Tab),
  Web-Links und E-Mail-Adressen gehen an die Standardanwendung, interne Anker springen
- **Tabs** für mehrere Dokumente, Dateien per Drag und Drop ins Fenster ziehen
- **Live-Neuladen** überwacht die geöffnete Datei und lädt sie bei Änderungen nach,
  wobei die Scrollposition erhalten bleibt
- **Statusleiste** mit Wort- und Zeichenzahl, Lesezeit, Dateigröße, Kodierung und
  Zeitstempeln
- **Kodierungserkennung**: UTF-8 (mit/ohne BOM), UTF-16, UTF-32, sonst CP1252 oder
  Latin-1 – mit Hinweis im Dokument statt falscher Zeichen
- **Export als eigenständige HTML-Datei** (Styles und KaTeX-Schriften eingebettet,
  relative Pfade werden absolut) sowie Drucken, sofern WebKitGTK es unterstützt
- **Darstellung**: Hell- und Dunkelmodus (auch automatisch nach Systemeinstellung),
  Schriftgröße 50–250 %, drei Zeilenbreiten, ruhige Typografie
- **Zweisprachige Oberfläche** (Deutsch und Englisch) inklusive Startseite,
  Menüs, Dialogen und Statusmeldungen
- **Kommandozeile**: Dateien öffnen, `--export-html`, `--language`, `--debug`,
  `--version`
- **Debian-Paket** (`md-viewer_<version>_all.deb`) mit Desktop-Eintrag,
  MIME-Zuordnung für `text/markdown`, AppStream-Metadaten, Icons in neun Größen,
  Manpage und Lizenzhinweisen
- **Robuste Grundlage**: Schreibfehler in `settings.json` können die App nicht
  lahmlegen, fehlende Systembibliotheken werden verständlich gemeldet,
  WebKit2GTK 2.x, 4.0 und 4.1 werden unterstützt

### Sicherheit

- Gerendertes HTML wird mit DOMPurify bereinigt (Skripte, Event-Handler und
  `javascript:`-Links werden entfernt)
- Das WebView darf ausschließlich die mitgelieferte Seite laden; jede andere
  Navigation und jedes Popup werden blockiert
- Die CSP unterbindet aktive Verbindungen (`connect-src 'none'`); externe Bildabrufe waren in dieser ersten Version noch standardmäßig erlaubt und sind seit 1.1.2 standardmäßig gesperrt
- Keine Telemetrie; Schriften und Bibliotheken liegen lokal bei

[1.1.2]: https://github.com/tikogaming1/md-viewer/releases/tag/v1.1.2
[1.1.1]: https://github.com/tikogaming1/md-viewer/releases/tag/v1.1.1
[1.1.0]: https://github.com/tikogaming1/md-viewer/releases/tag/v1.1.0
[1.0.0]: https://github.com/tikogaming1/md-viewer/releases/tag/v1.0.0
