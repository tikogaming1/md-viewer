/**
 * Test fuer scripts/build-preview.mjs (die Browser-Vorschau).
 *
 * Die Vorschau wird in einen temporaeren Ordner gebaut und geprueft. Damit ist
 * abgesichert, dass die ausgelieferte Vorschau funktioniert und dass Inhalte beim
 * Einsetzen nicht beschaedigt werden - genau dort lag schon einmal ein Fehler
 * (String.replace deutete "$$" im Markdown als Escape).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { repoRoot } from './helpers.mjs';

const builder = path.join(repoRoot, 'scripts', 'build-preview.mjs');
const hasBundle = existsSync(path.join(repoRoot, 'web', 'bundle', 'viewer.min.js'));

function buildPreview({ args = [] } = {}) {
  const out = mkdtempSync(path.join(tmpdir(), 'md-viewer-preview-'));
  execFileSync(process.execPath, [builder, '--out', out, ...args], {
    cwd: repoRoot,
    stdio: 'pipe',
  });
  return out;
}

test('Vorschau wird gebaut und verweist auf vorhandene Dateien', { skip: !hasBundle }, () => {
  const out = buildPreview();
  try {
    const html = readFileSync(path.join(out, 'index.html'), 'utf8');

    // Der echte App-Rahmen wird verwendet
    assert.match(html, /<article class="markdown-body" id="doc">/);
    assert.match(html, /preview-banner/);
    assert.match(html, /window\.MD_DEMO = \{/);

    // Alle verwiesenen Dateien wurden mitkopiert
    for (const ref of html.matchAll(/(?:href|src)="([^"]+)"/g)) {
      const target = ref[1];
      if (target.startsWith('http') || target.startsWith('#') || target.startsWith('data:')) continue;
      assert.ok(existsSync(path.join(out, target)), `fehlt in der Vorschau: ${target}`);
    }

    // Vendor-Assets und Bundle sind vollstaendig dabei
    assert.ok(existsSync(path.join(out, 'bundle', 'viewer.min.js')));
    assert.ok(existsSync(path.join(out, 'vendor', 'github-markdown-dark.css')));
    assert.ok(existsSync(path.join(out, 'vendor', 'katex', 'fonts', 'KaTeX_Main-Regular.woff2')));
  } finally {
    rmSync(out, { recursive: true, force: true });
  }
});

test('Markdown-Inhalte bleiben beim Einsetzen unveraendert', { skip: !hasBundle }, () => {
  const out = buildPreview({ args: ['--file', 'docs/beispiel.md'] });
  try {
    const html = readFileSync(path.join(out, 'index.html'), 'utf8');
    const original = readFileSync(path.join(repoRoot, 'docs', 'beispiel.md'), 'utf8');

    // Kein "$"-Escape, kein "</script>"-Bruch, keine Umlaut-Probleme
    assert.match(html, /\$\$/, 'Anzeige-Mathematik ($$) wurde beschaedigt');
    assert.match(html, /e\^\{-x\^2\}/);
    assert.match(html, /Überschrift/);
    assert.match(html, /\\begin\{pmatrix\}/);

    // Die Nutzlast enthaelt den Text des Dokuments vollstaendig
    const match = html.match(/window\.MD_DEMO = (\{.*?\});<\/script>/s);
    assert.ok(match, 'MD_DEMO-Nutzlast nicht gefunden');
    const payload = JSON.parse(match[1].replace(/\\u003c/g, '<'));
    assert.equal(payload.text, original);
    assert.equal(payload.kind, 'document');
    assert.equal(payload.settings.theme, 'light');
    assert.equal(payload.settings.blockRemoteImages, true);
  } finally {
    rmSync(out, { recursive: true, force: true });
  }
});

test('Vorschau nimmt Design und Zoom als Option an', { skip: !hasBundle }, () => {
  const out = buildPreview({ args: ['--theme', 'dark', '--zoom', '130'] });
  try {
    const html = readFileSync(path.join(out, 'index.html'), 'utf8');
    assert.match(html, /"theme":"dark"/);
    assert.match(html, /"zoom":130/);
    assert.match(html, /data-theme="light"/); // Startwert im HTML, wird von JS umgestellt
  } finally {
    rmSync(out, { recursive: true, force: true });
  }
});
