#!/usr/bin/env node
/**
 * Baut eine statische Vorschau der Oberflaeche nach preview/index.html.
 *
 * Zweck: die Darstellung im Browser pruefen, ohne die App installieren zu
 * muessen. Verwendet exakt die Dateien, die auch im .deb stecken
 * (web/index.html, web/viewer.css, web/bundle, web/vendor).
 *
 * Aufruf:  npm run preview        (danach: python3 -m http.server -d preview)
 *          npm run preview -- --file docs/beispiel.md --theme dark
 */
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const webDir = path.join(root, 'web');
const previewDir = path.join(root, 'preview');

function parseArgs(argv) {
  const options = { file: 'docs/beispiel.md', theme: 'light', zoom: 100, out: previewDir };
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i];
    if (key === '--file') options.file = argv[++i];
    else if (key === '--theme') options.theme = argv[++i];
    else if (key === '--zoom') options.zoom = Number(argv[++i]);
    else if (key === '--out') options.out = path.resolve(argv[++i]);
  }
  return options;
}

async function copyDir(from, to) {
  await fs.mkdir(to, { recursive: true });
  for (const entry of await fs.readdir(from, { withFileTypes: true })) {
    const source = path.join(from, entry.name);
    const target = path.join(to, entry.name);
    if (entry.isDirectory()) await copyDir(source, target);
    else if (entry.isFile()) await fs.copyFile(source, target);
  }
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const markdownPath = path.resolve(root, options.file);
  const markdown = await fs.readFile(markdownPath, 'utf8');

  await fs.rm(options.out, { recursive: true, force: true });
  await fs.mkdir(options.out, { recursive: true });

  for (const name of ['viewer.css', 'bundle', 'vendor']) {
    const source = path.join(webDir, name);
    const target = path.join(options.out, name);
    const stats = await fs.stat(source);
    if (stats.isDirectory()) await copyDir(source, target);
    else await fs.copyFile(source, target);
  }

  // Bilder aus dem Ordner des Beispiels mitnehmen (relative Pfade bleiben so gueltig)
  const sourceDir = path.dirname(markdownPath);
  for (const entry of await fs.readdir(sourceDir, { withFileTypes: true })) {
    if (/\.(png|jpe?g|gif|svg|webp)$/i.test(entry.name)) {
      await fs.copyFile(path.join(sourceDir, entry.name), path.join(options.out, entry.name));
    }
  }

  const demo = {
    kind: 'document',
    fileName: path.basename(markdownPath),
    path: markdownPath,
    url: `file://${markdownPath}`,
    baseHref: './',
    encoding: 'UTF-8',
    text: markdown,
    footer: 'Vorschau (Browser) · {words} Wörter · {characters} Zeichen · ca. {minutes} Min. Lesezeit',
    settings: {
      language: 'de',
      theme: options.theme,
      zoom: options.zoom,
      tocVisible: true,
      blockRemoteImages: true,
    },
  };

  let html = await fs.readFile(path.join(webDir, 'index.html'), 'utf8');
  // Achtung: Funktion als Ersatz, sonst deutet String.replace "$$" als Escape.
  html = html.replace(
    '<title>MD Viewer</title>',
    () => `<title>Vorschau · ${path.basename(markdownPath)}</title>`,
  );
  html = html.replace(
    '<body>',
    () => `<body>
    <div class="preview-banner">
      Statische Vorschau der Oberfläche · dieselben Dateien wie im .deb
      (<code>web/</code>) · <a href="https://github.com/tikogaming1/md-viewer">Projektseite</a>
    </div>`,
  );
  // Nutzlast vor das Bundle setzen: main.js rendert sie ohne Python-Bruecke.
  html = html.replace(
    '<script src="bundle/viewer.min.js"></script>',
    () => `<script>window.MD_DEMO = ${JSON.stringify(demo).replace(/</g, '\\u003c')};</script>
    <script src="bundle/viewer.min.js"></script>
    <script>
      // Bruecken-Ersatz: Aktionen, die normalerweise Python ausfuehrt, hier sichtbar machen.
      window.MDViewer && document.addEventListener('DOMContentLoaded', () => {
        const toast = document.getElementById('toast');
        if (toast) toast.dataset.preview = '1';
      });
    </script>`,
  );
  await fs.writeFile(path.join(options.out, 'index.html'), html, 'utf8');

  const banner = `
/* Nur fuer die Browser-Vorschau (nicht Teil der App) */
.preview-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 90;
  padding: 6px 14px;
  background: #1f6feb;
  color: #ffffff;
  font-size: 12px;
  text-align: center;
}
.preview-banner a { color: #ffffff; }
.preview-banner code { background: rgba(255, 255, 255, 0.2); }
body { padding-top: 28px; }
.findbar { top: 38px; }
`;
  const cssPath = path.join(options.out, 'viewer.css');
  await fs.appendFile(cssPath, banner, 'utf8');

  console.log(`Vorschau erstellt: ${path.relative(root, path.join(options.out, 'index.html'))}`);
  console.log(`  Dokument: ${path.relative(root, markdownPath)}`);
  console.log('  Ansehen:  python3 -m http.server 8099 -d preview   (dann http://localhost:8099/)');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
