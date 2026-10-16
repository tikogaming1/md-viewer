#!/usr/bin/env node
/**
 * Baut web/bundle/viewer.min.js aus web/src/*.js.
 *
 * Ergebnis ist ein einzelnes, selbst-enthaltendes IIFE-Bundle (ES2018), das ohne
 * Netzwerkzugriff im WebKit2GTK-WebView laeuft. Absichtlich *kein* "dist/"-Ordner,
 * damit nichts mit .gitignore-Regeln kollidiert.
 *
 * Aufruf:  npm run bundle
 */
import { build } from 'esbuild';
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outfile = path.join(root, 'web', 'bundle', 'viewer.min.js');

await fs.mkdir(path.dirname(outfile), { recursive: true });

const result = await build({
  entryPoints: [path.join(root, 'web', 'src', 'main.js')],
  outfile,
  bundle: true,
  format: 'iife',
  platform: 'browser',
  // WebKit2GTK 2.38+ (Debian 12) versteht deutlich mehr als ES2018; ES2018 ist ein
  // sicherer gemeinsamer Nenner fuer WebKit2GTK 2.36 (Ubuntu 22.04) bis 2.4x.
  target: ['es2018'],
  minify: true,
  legalComments: 'eof',
  charset: 'utf8',
  metafile: true,
  logLevel: 'info',
  define: {
    'process.env.NODE_ENV': '"production"',
  },
});

const bytes = (await fs.stat(outfile)).size;
const inputs = Object.keys(result.metafile.inputs).length;
console.log(`web/bundle/viewer.min.js: ${(bytes / 1024).toFixed(1)} KiB aus ${inputs} Modulen.`);
