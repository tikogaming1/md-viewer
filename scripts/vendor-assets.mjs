#!/usr/bin/env node
/**
 * Kopiert die zur Laufzeit benoetigten Fremd-Assets aus node_modules nach web/vendor/.
 *
 * Diese Dateien werden mit dem Repository ausgeliefert (und landen im .deb), damit das
 * fertige Paket ohne Node.js/npm installierbar und benutzbar ist.
 *
 * Aufruf:  npm run vendor
 */
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const nm = path.join(root, 'node_modules');
const vendor = path.join(root, 'web', 'vendor');

/** Quell-Datei -> Ziel-Datei (relativ zu web/vendor/) */
const FILES = [
  // GitHub-Markdown-Stylesheet (Light + Dark)
  ['github-markdown-css/github-markdown-light.css', 'github-markdown-light.css'],
  ['github-markdown-css/github-markdown-dark.css', 'github-markdown-dark.css'],
  // highlight.js-Themes (sehen aus wie auf github.com)
  ['@highlightjs/cdn-assets/styles/github.min.css', 'hljs-github.min.css'],
  ['@highlightjs/cdn-assets/styles/github-dark.min.css', 'hljs-github-dark.min.css'],
  // KaTeX (Mathematik) - wird vom Viewer nur bei Bedarf nachgeladen
  ['katex/dist/katex.min.js', 'katex/katex.min.js'],
  ['katex/dist/katex.min.css', 'katex/katex.min.css'],
  ['katex/dist/contrib/auto-render.min.js', 'katex/auto-render.min.js'],
];

/** Lizenztexte der mitgelieferten bzw. im Bundle enthaltenen Projekte */
const LICENSES = [
  ['marked/LICENSE', 'marked.txt'],
  ['dompurify/LICENSE', 'dompurify.txt'],
  ['highlight.js/LICENSE', 'highlight.js.txt'],
  ['github-markdown-css/license', 'github-markdown-css.txt'],
  ['katex/LICENSE', 'katex.txt'],
  ['marked-gfm-heading-id/LICENSE', 'marked-gfm-heading-id.txt'],
  ['marked-highlight/LICENSE', 'marked-highlight.txt'],
];

const pkgDirs = [
  'marked',
  'marked-footnote',
  'marked-gfm-heading-id',
  'marked-alert',
  'marked-highlight',
  'dompurify',
  'highlight.js',
  '@highlightjs/cdn-assets',
  'github-markdown-css',
  'katex',
];

async function copyFile(from, to) {
  await fs.mkdir(path.dirname(to), { recursive: true });
  await fs.copyFile(from, to);
  return to;
}

async function main() {
  try {
    await fs.access(nm);
  } catch {
    console.error('node_modules fehlt - bitte zuerst "npm ci" bzw. "npm install" ausfuehren.');
    process.exit(1);
  }

  let count = 0;
  for (const [from, to] of FILES) {
    const src = path.join(nm, from);
    await copyFile(src, path.join(vendor, to));
    count++;
  }

  // KaTeX-Schriften (nur woff2: von allen relevanten WebKit-Versionen unterstuetzt)
  const fontsSrc = path.join(nm, 'katex', 'dist', 'fonts');
  const fontsDest = path.join(vendor, 'katex', 'fonts');
  await fs.mkdir(fontsDest, { recursive: true });
  for (const name of await fs.readdir(fontsSrc)) {
    if (name.endsWith('.woff2')) {
      await copyFile(path.join(fontsSrc, name), path.join(fontsDest, name));
      count++;
    }
  }

  // Lizenztexte
  for (const [from, to] of LICENSES) {
    try {
      await copyFile(path.join(nm, from), path.join(vendor, 'licenses', to));
      count++;
    } catch {
      console.warn(`  Warnung: Lizenzdatei ${from} nicht gefunden`);
    }
  }

  // Versionen dokumentieren (fuer /usr/share/doc/md-viewer im .deb)
  const versions = {};
  for (const dir of pkgDirs) {
    const raw = await fs.readFile(path.join(nm, dir, 'package.json'), 'utf8');
    const pkg = JSON.parse(raw);
    versions[pkg.name] = { version: pkg.version, license: pkg.license ?? 'unbekannt' };
  }
  const meta = {
    hinweis: 'Automatisch erzeugt von scripts/vendor-assets.mjs - nicht manuell bearbeiten.',
    erzeugt: new Date().toISOString().slice(0, 10),
    pakete: versions,
  };
  const metaPath = path.join(vendor, 'VERSIONS.json');
  await fs.writeFile(metaPath, JSON.stringify(meta, null, 2) + '\n');
  count++;

  console.log(`web/vendor/ aktualisiert: ${count} Dateien.`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
