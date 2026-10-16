/**
 * Testumgebung: laedt web/index.html in jsdom und erzeugt darin einen Viewer.
 * Damit laeuft die komplette DOM-Logik (TOC, Suche, Lightbox, Theme) im Test.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { JSDOM, VirtualConsole } from 'jsdom';
import { createViewer } from '../../web/src/viewer.js';

export const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
export const webDir = path.join(repoRoot, 'web');

export function readWebFile(relative) {
  return readFileSync(path.join(webDir, relative), 'utf8');
}

export function createDom({ url = 'file:///usr/lib/md-viewer/web/index.html' } = {}) {
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', () => {});
  const dom = new JSDOM(readWebFile('index.html'), { url, virtualConsole });
  return dom;
}

/** @returns {{dom: JSDOM, win: Window, doc: Document, viewer: object, messages: object[]}} */
export function createViewerFixture(options = {}) {
  const dom = createDom(options);
  const messages = [];
  const win = dom.window;
  const viewer = createViewer(win, win.document, {
    emit: (message) => messages.push(message),
  });
  if (options.settings) viewer.applySettings(options.settings);
  return { dom, win, doc: win.document, viewer, messages };
}

export const DEMO_MARKDOWN = `# Titel des Dokuments

Ein Absatz mit **fett**, *kursiv*, \`Code\` und einem [Link](https://example.com/docs).

## Zweiter Abschnitt

- [x] erledigt
- [ ] offen

| Spalte A | Spalte B |
| -------- | -------- |
| 1        | 2        |

\`\`\`js
const x = 1;
console.log(x);
\`\`\`

## Dritter Abschnitt

> [!NOTE]
> Ein Hinweis-Block.

Fußnote hier[^1].

[^1]: Der Fußnotentext.

![Bild](bild.png)

### Unterabschnitt

Schluss.
`;

export const DEMO_PAYLOAD = {
  kind: 'document',
  path: '/home/user/docs/beispiel.md',
  fileName: 'beispiel.md',
  baseHref: 'file:///home/user/docs/',
  url: 'file:///home/user/docs/beispiel.md',
  text: DEMO_MARKDOWN,
  encoding: 'UTF-8',
  settings: { language: 'de', theme: 'light', zoom: 100, tocVisible: true },
  footer: '{file} · {words} Wörter · {minutes} Min.',
};
