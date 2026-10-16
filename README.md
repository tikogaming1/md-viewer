<div align="center">

<img src="packaging/icons/md-viewer-256.png" width="128" alt="MD Viewer">

# MD Viewer

**Markdown-Dateien ansehen – nicht als Quelltext, sondern als fertiges Dokument.**

Eine schlanke Desktop-App für Debian und Ubuntu, verteilt als installierbares
`.deb`-Paket. Die Darstellung entspricht dem, was man von GitHub kennt.

[![CI](https://github.com/tikogaming1/md-viewer/actions/workflows/ci.yml/badge.svg)](https://github.com/tikogaming1/md-viewer/actions/workflows/ci.yml)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-blue.svg)](LICENSE)
[![Paket: .deb](https://img.shields.io/badge/Paket-.deb-A81D33.svg)](#installation)

</div>

---

## Was die App kann

| Funktion | Beschreibung |
| --- | --- |
| **Rendern wie GitHub** | Überschriften, Tabellen, Aufgabenlisten, Durchstreichen, Autolinks, Fußnoten, Hinweis-Blöcke (`> [!NOTE]`) und aufklappbares Frontmatter |
| **Syntax-Highlighting** | Codeblöcke in über 30 Sprachen, Standardthemen von GitHub (hell und dunkel) |
| **Mathematik** | Formeln mit KaTeX (inline `$x^2$` und als Block `$$ … $$`) |
| **Inhaltsverzeichnis** | Seitenleiste mit allen Überschriften; der aktuelle Abschnitt wird beim Scrollen hervorgehoben |
| **Suche** | `Strg+F`, Treffer werden gezählt und hervorgehoben, `Enter`/`Umschalt+Enter` springt weiter |
| **Bilder** | Klick für die Großansicht; relative Pfade werden aus dem Ordner der Datei geladen; externe Bilder optional blockiert |
| **Links** | Relative Links auf andere `.md`-Dateien öffnen im Viewer, Web-Links im Standardbrowser |
| **Tabs** | Mehrere Dokumente gleichzeitig, per Drag und Drop oder `Strg+Umschalt+O` |
| **Live-Neuladen** | Wird die Datei auf der Festplatte geändert, aktualisiert sich die Anzeige |
| **Export** | „Als HTML exportieren“ schreibt eine eigenständige Datei (Styles und Schriften eingebettet); Drucken, wenn WebKitGTK es unterstützt |
| **Lesekomfort** | Hell- und Dunkelmodus (auch automatisch nach Systemeinstellung), Schriftgröße 50–250 %, drei Zeilenbreiten |
| **Offline** | Keine Netzwerkzugriffe, keine Telemetrie, keine Cloud – alles läuft lokal |

## Installation

### Voraussetzungen

Debian 12 (Bookworm) oder neuer, Ubuntu 22.04 oder neuer – mit grafischer Sitzung (X11 oder Wayland).
Die App benötigt `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-gdkpixbuf-2.0` und WebKit2GTK.
Diese Abhängigkeiten sind im `.deb` deklariert und werden von `apt` bei Bedarf automatisch installiert.
Wenn `apt` beim Installieren nur `md-viewer` aufführt, sind die Abhängigkeiten
bereits vorhanden – so war es auch bei der Installation auf Kali.

### Aus dem Release installieren

```bash
# .deb-Datei von der Release-Seite herunterladen, dann:
sudo apt install ./md-viewer_1.1.1_all.deb
```

`apt` löst dabei die Abhängigkeiten auf. Danach erscheint **MD Viewer** im
Anwendungsmenü, und Markdown-Dateien lassen sich direkt aus dem Dateimanager
mit der App öffnen („Öffnen mit …“).

### Aus dem Quelltext bauen

```bash
git clone https://github.com/tikogaming1/md-viewer.git
cd md-viewer
make deps      # Node.js-Abhängigkeiten (npm install)
make test      # Tests (Python + JavaScript)
make deb       # Paket bauen -> release/md-viewer_1.1.1_all.deb
sudo apt install ./release/md-viewer_1.1.1_all.deb
```

Zum Ausprobieren ohne Installation: `make run` (startet aus dem Checkout).

### Deinstallieren

```bash
sudo apt remove md-viewer      # Konfiguration bleibt erhalten
rm -rf ~/.config/md-viewer     # Einstellungen und Liste zuletzt geöffneter Dateien
```

## Bedienung

Beim Start erscheint eine Startseite mit allen Hinweisen. Öffnen Sie ein Dokument über
**Strg+O**, per Drag und Drop ins Fenster, über das Menü oben links oder mit
`md-viewer datei.md` auf der Kommandozeile.

Die **Statusleiste** unten zeigt Wortzahl, Zeichenzahl, geschätzte Lesezeit, Dateigröße,
Kodierung und den Zeitpunkt der letzten Änderung sowie des letzten automatischen Neuladens.

### Tastenkürzel

| Kürzel | Wirkung |
| --- | --- |
| `Strg+O` | Datei öffnen |
| `Strg+Umschalt+O` | Datei in neuem Tab öffnen |
| `Strg+R` / `F5` | Dokument neu laden |
| `Strg+W` | Tab schließen |
| `Strg+F` | Im Dokument suchen |
| `F3` / `Umschalt+F3` | Nächster / vorheriger Treffer |
| `Strg+B` | Inhaltsverzeichnis ein-/ausblenden |
| `Strg+Plus` / `Strg+Minus` / `Strg+0` | Schriftgröße größer / kleiner / zurücksetzen |
| `Strg+E` | Als HTML exportieren |
| `Strg+P` | Drucken |
| `Strg+?` | Übersicht der Tastenkürzel |
| `Strg+Q` | Beenden |

### Kommandozeile

```bash
md-viewer                          # App starten (Startseite)
md-viewer README.md notizen.md     # mehrere Dateien, je ein Tab
md-viewer --export-html out.html README.md   # nur rendern und beenden
md-viewer --language en README.md  # englische Oberfläche
md-viewer --debug README.md        # ausführliche Protokollausgabe
md-viewer --version
```

## Beispieldokument

Im Ordner [`docs/`](docs/) liegt [`beispiel.md`](docs/beispiel.md) – ein Dokument, das alle
Darstellungsmöglichkeiten zeigt (Tabellen, Aufgabenlisten, Hinweis-Blöcke, Fußnoten,
Mathematik, Bilder, aufklappbare Bereiche). Nach der Installation:

```bash
md-viewer /pfad/zum/repo/docs/beispiel.md
```

### Vorschau im Browser

Die Oberfläche läuft im WebKit-WebView und ist mit denselben Dateien auch im Browser
ansehbar – nützlich, um die Darstellung zu prüfen, ohne etwas zu installieren:

```bash
make build
node scripts/build-preview.mjs          # erzeugt preview/
python3 -m http.server 8099 -d preview  # dann http://localhost:8099/ öffnen
```

## Einstellungen

Die App speichert ihre Einstellungen in `~/.config/md-viewer/settings.json` (wird beim
Beenden geschrieben). Die wichtigsten Werte:

| Schlüssel | Werte | Bedeutung |
| --- | --- | --- |
| `theme` | `auto`, `light`, `dark` | Design (`auto` folgt der Systemeinstellung) |
| `zoom` | 50–250 | Schriftgröße in Prozent |
| `line_width` | `normal`, `wide`, `full` | Zeilenbreite des Textes |
| `toc_visible` | `true`, `false` | Inhaltsverzeichnis einblenden |
| `auto_reload` | `true`, `false` | Bei Dateiänderungen neu laden |
| `block_remote_images` | `true`, `false` | Bilder von fremden Servern erst nach Klick laden |
| `breaks` | `true`, `false` | Einzelne Zeilenumbrüche als Zeilenumbruch darstellen |
| `math`, `math_inline` | `true`, `false` | Mathematik mit KaTeX setzen |
| `language` | `de`, `en` | Sprache der Oberfläche |
| `recent_files` | Liste | Die zwölf zuletzt geöffneten Dateien |

Unbekannte oder unplausible Werte werden beim Laden automatisch korrigiert – eine kaputte
Datei kann die App nicht lahmlegen.

## Wie es aufgebaut ist

```
src/mdviewer/            Python: Fenster, Dateien, Einstellungen, Export
  app.py                 Gtk.Application, Kommandozeile, Startfehler
  window.py              Hauptfenster: Kopfzeile, Tabs, Menü, Status, Live-Neuladen
  viewer_page.py         ein WebView je Tab, Nachrichtenkanal nach JavaScript
  compat.py              GTK3/WebKit2GTK 2.x, 4.0 und 4.1 (API-Unterschiede)
  documents.py           Dateien einlesen (Kodierung, Grenzen, URLs)
  exporter.py            eigenständige HTML-Datei erzeugen
  settings.py, i18n.py, paths.py, welcome.py

web/                     Oberfläche im WebView (wird nach /usr/lib/md-viewer/web installiert)
  index.html, viewer.css App-Rahmen, Seitenleiste, Suchleiste, Lightbox
  src/renderer.js        Markdown -> HTML (marked + GFM-Erweiterungen)
  src/viewer.js          DOM-Logik: Inhaltsverzeichnis, Suche, Theme, Bilder
  src/main.js            Brücke zwischen Python und JavaScript
  bundle/viewer.min.js   gebautes Bundle (esbuild) – das wird geladen
  vendor/                mitgelieferte Fremdbibliotheken (siehe unten)

packaging/               Debian-Steuerdateien, Icons, Desktop-Eintrag, Manpage
scripts/                 Bau-, Icon-, Vorschau- und Prüfskripte
tests/                   Python- und JavaScript-Tests
docs/                    Beispieldokumente
```

**Warum GTK + WebKit?** Die App soll schlank sein und keine eigene Browser-Engine
mitbringen. GTK3 und WebKit2GTK sind auf Debian und Ubuntu vorhanden; das `.deb` ist
deshalb nur rund 550 kB groß und lässt sich in wenigen Sekunden installieren. Das
Rendern übernimmt eine lokale Web-Oberfläche – dieselbe Technik, die auch GitHub
für die Markdown-Darstellung verwendet, weshalb die Darstellung praktisch identisch ist.

**Sicherheit:** Das WebView darf nur die mitgelieferte Seite laden (jede andere Navigation
wird blockiert), die Seite darf keine Netzwerkverbindungen aufbauen (CSP: `connect-src
'none'`), und gerendertes Markdown wird mit DOMPurify bereinigt – Skripte, Event-Handler
und `javascript:`-Links werden entfernt. Popups sind unterbunden; Links ins Netz öffnet
die App im Standardbrowser.

### Mitgelieferte Fremdbibliotheken

Alle liegen unter `web/vendor/` und werden mit dem Paket ausgeliefert; die vollständigen
Lizenztexte stehen in `web/vendor/licenses/` und in
`/usr/share/doc/md-viewer/third-party/`.

| Bibliothek | Zweck | Lizenz |
| --- | --- | --- |
| [marked](https://github.com/markedjs/marked) + Erweiterungen (footnote, alert, gfm-heading-id, highlight) | Markdown nach HTML | MIT |
| [highlight.js](https://highlightjs.org/) | Syntax-Highlighting | BSD-3-Clause |
| [github-markdown-css](https://github.com/sindresorhus/github-markdown-css) | Darstellung wie auf GitHub | MIT |
| [KaTeX](https://katex.org/) | Formelsatz | MIT |
| [DOMPurify](https://github.com/cure53/DOMPurify) | Bereinigung des gerenderten HTML | MPL-2.0 oder Apache-2.0 |

## Tests

```bash
make test          # alles: Python (unittest) + JavaScript (node:test)
make test-python   # nur Python
make test-js       # nur JavaScript (baut vorher das Bundle)
make check-deb     # Inhalt und Installation des fertigen Pakets prüfen
```

Die JavaScript-Tests laufen in [jsdom](https://github.com/jsdom/jsdom) und prüfen unter
anderem das Rendern, Inhaltsverzeichnis, Suche, Lightbox, Theme-Wechsel, den Schutz vor
eingeschleustem Code sowie – als Ende-zu-Ende-Test – das *gebaute Bundle*, so wie es im
Paket steckt. Die Python-Tests prüfen Dateien und Kodierung, Einstellungen, Export,
Übersetzungen und – mit einer GI-Attrappe – die Fenster- und Anwendungslogik.

## Fehlersuche

| Problem | Lösung |
| --- | --- |
| „WebKitGTK fehlt“ | `sudo apt install gir1.2-webkit2-4.1` (bzw. `-webkit2-4.0` unter Debian 11/Ubuntu 22.04) |
| Gdk-Fehler mit „version '3.0', but '4.0' is already loaded“ | Ab MD Viewer 1.1.1 wird GTK3/Gdk3 explizit ausgewählt. Installieren Sie das aktuelle Paket; der Konflikt mit zusätzlich installiertem GTK4 wird damit vermieden. |
| Fenster öffnet, Inhalt bleibt leer | Im Terminal `md-viewer --debug datei.md` starten; Hinweise erscheinen auf `stderr` |
| Umlaute falsch | Die Statusleiste zeigt die erkannte Kodierung; speichern Sie die Datei als UTF-8 |
| Kein Drucken | Erst ab WebKitGTK 2.40 möglich – ersatzweise „Als HTML exportieren“ und im Browser drucken |
| Datei zu groß | Die Grenze liegt bei 16 MB; größere Dateien werden nicht geladen |

## Mitwirken

Beiträge sind willkommen: Fork, Branch, `make test`, Pull Request. Für Änderungen an der
Darstellung bitte die JS-Tests erweitern, für Änderungen an der Oberfläche die
Python-Tests.

## Lizenz

[MIT](LICENSE) – © 2026 tikogaming1. Die mitgelieferten Fremdbibliotheken stehen unter
ihren eigenen Lizenzen (siehe oben).
