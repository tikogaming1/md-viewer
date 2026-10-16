#!/bin/bash
# Prueft das gebaute .deb ohne Installation:
#   1. Paket entpacken
#   2. Dateien und Rechte kontrollieren
#   3. Startprogramm aus dem Paket aufrufen (--version)
#   4. Python-Paket aus dem Paket importieren und Web-Assets finden
#   5. Webserver-Auslieferung der Assets pruefen (index.html + Bundle lesbar)
#
# Aufruf:  scripts/smoke-test-deb.sh [paket.deb]
set -u

DEB="${1:-$(find release -maxdepth 1 -type f -name 'md-viewer_*_all.deb' 2>/dev/null | sort -V | tail -1)}"
if [ -z "$DEB" ] || [ ! -f "$DEB" ]; then
  echo "FEHLER: kein Paket gefunden (erst 'make deb' ausfuehren)" >&2
  exit 1
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
EXTRACT="$WORK/root"
FAILURES=0

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$1"; FAILURES=$((FAILURES + 1)); }

step "Paket: $DEB"
dpkg-deb --info "$DEB" | sed -n '2,8p'

step "Automatische Abhaengigkeiten"
DEPENDS="$(dpkg-deb -f "$DEB" Depends | tr '\n' ' ')"
for dependency in python3-gi gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0; do
  if [[ "$DEPENDS" == *"$dependency"* ]]; then ok "$dependency ist als Depends deklariert"; else bad "$dependency fehlt in Depends"; fi
done
if [[ "$DEPENDS" == *"gir1.2-webkit2-4.1"* || "$DEPENDS" == *"gir1.2-webkit2-4.0"* ]]; then
  ok "WebKit2GTK ist als Depends deklariert"
else
  bad "WebKit2GTK fehlt in Depends"
fi

step "Entpacken"
dpkg-deb -x "$DEB" "$EXTRACT" && ok "entpackt nach $EXTRACT"

step "Dateien und Rechte"
for path in \
  usr/bin/md-viewer \
  usr/lib/python3/dist-packages/mdviewer/__init__.py \
  usr/lib/python3/dist-packages/mdviewer/app.py \
  usr/lib/md-viewer/web/index.html \
  usr/lib/md-viewer/web/viewer.css \
  usr/lib/md-viewer/web/bundle/viewer.min.js \
  usr/lib/md-viewer/web/vendor/github-markdown-light.css \
  usr/lib/md-viewer/web/vendor/katex/katex.min.js \
  usr/share/applications/md-viewer.desktop \
  usr/share/metainfo/md-viewer.metainfo.xml \
  usr/share/icons/hicolor/256x256/apps/md-viewer.png \
  usr/share/doc/md-viewer/copyright \
  usr/share/man/man1/md-viewer.1.gz
do
  if [ -e "$EXTRACT/$path" ]; then ok "$path"; else bad "$path fehlt"; fi
done

if [ -x "$EXTRACT/usr/bin/md-viewer" ]; then ok "Starter ist ausfuehrbar"; else bad "Starter ist nicht ausfuehrbar"; fi
if head -1 "$EXTRACT/usr/bin/md-viewer" | grep -q '^#!/bin/sh'; then ok "Starter hat Shebang"; else bad "Shebang fehlt"; fi
if [ ! -d "$EXTRACT/usr/lib/md-viewer/web/src" ]; then ok "web/src nicht mitinstalliert"; else bad "web/src ist im Paket"; fi

step "Startprogramm"
VERSION_OUTPUT="$(PYTHONPATH="$EXTRACT/usr/lib/python3/dist-packages" MD_VIEWER_WEB_DIR="$EXTRACT/usr/lib/md-viewer/web" \
  sh "$EXTRACT/usr/bin/md-viewer" --version 2>&1)"
case "$VERSION_OUTPUT" in
  "MD Viewer "*) ok "Ausgabe: $VERSION_OUTPUT" ;;
  *) bad "unerwartete Ausgabe: $VERSION_OUTPUT" ;;
esac

step "Bibliothek aus dem Paket"
RESULT="$(PYTHONPATH="$EXTRACT/usr/lib/python3/dist-packages" MD_VIEWER_WEB_DIR="$EXTRACT/usr/lib/md-viewer/web" python3 -c "
from mdviewer import __version__, documents, exporter, i18n, paths, settings, welcome, viewer_page
web = paths.web_dir()
assert (web / 'index.html').is_file(), web
assert (web / 'bundle' / 'viewer.min.js').is_file(), web
assert i18n.t('menu.open') == 'Öffnen …'
doc = documents.read_document('$EXTRACT/usr/share/doc/md-viewer/copyright')
assert doc.text
print('Version', __version__, '| Web:', web, '| i18n ok | Dokumente ok')
" 2>&1)"
case "$RESULT" in
  "Version "*) ok "$RESULT" ;;
  *) bad "Import/Pruefung fehlgeschlagen: $RESULT" ;;
esac

step "Web-Assets sind vollstaendig"
MISSING="$(cd "$EXTRACT/usr/lib/md-viewer/web" && python3 - <<'PY'
import re, sys
from pathlib import Path
missing = []
for html in (Path('index.html'),):
    text = html.read_text(encoding='utf-8')
    for ref in re.findall(r'(?:href|src)="([^"]+)"', text):
        if ref.startswith(('http', '#')):
            continue
        if not Path(ref).is_file():
            missing.append(f'{html}: {ref}')
print('\n'.join(missing))
PY
)"
if [ -z "$MISSING" ]; then ok "alle in index.html verwiesenen Dateien vorhanden"; else bad "fehlende Dateien: $MISSING"; fi

for font in KaTeX_Main-Regular.woff2 KaTeX_Size4-Regular.woff2; do
  if [ -f "$EXTRACT/usr/lib/md-viewer/web/vendor/katex/fonts/$font" ]; then ok "Schrift $font"; else bad "Schrift $font fehlt"; fi
done

step "Desktop-Datei"
if grep -q '^Exec=md-viewer %F$' "$EXTRACT/usr/share/applications/md-viewer.desktop"; then ok "Exec-Zeile"; else bad "Exec-Zeile fehlt"; fi
if grep -q 'text/markdown' "$EXTRACT/usr/share/applications/md-viewer.desktop"; then ok "MIME-Typ text/markdown"; else bad "MIME-Typ fehlt"; fi
if grep -q '^Icon=md-viewer$' "$EXTRACT/usr/share/applications/md-viewer.desktop"; then ok "Icon-Eintrag"; else bad "Icon-Eintrag fehlt"; fi

printf '\n'
if [ "$FAILURES" -eq 0 ]; then
  printf '\033[32mAlle Pruefungen bestanden.\033[0m\n'
  exit 0
fi
printf '\033[31m%s Pruefung(en) fehlgeschlagen.\033[0m\n' "$FAILURES"
exit 1
