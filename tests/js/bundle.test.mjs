/**
 * Ende-zu-Ende-Test des *gebauten* Bundles in einer nachgebauten Browsersitzung.
 *
 * Geprueft wird genau das, was im .deb steckt: web/index.html + web/bundle/viewer.min.js
 * (+ CSS/Assets). Damit faellt auf, wenn das Bundle nicht laedt, DOMPurify fehlt oder
 * die Bruecke zu Python nicht stimmt.
 *
 * Voraussetzung: "npm run build" wurde ausgefuehrt (bundle/viewer.min.js existiert).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import jsdomPkg from 'jsdom';

const { JSDOM, VirtualConsole } = jsdomPkg;
import { repoRoot, readWebFile, DEMO_PAYLOAD } from './helpers.mjs';

const bundlePath = path.join(repoRoot, 'web', 'bundle', 'viewer.min.js');
const hasBundle = existsSync(bundlePath);
const indexUrl = `file://${path.join(repoRoot, 'web', 'index.html')}`;

/**
 * Startet index.html mit dem echten Bundle und zeichnet alle Brueckennachrichten auf.
 *
 * Standard ist der *App-Ablauf*: die Seite meldet sich bereit, danach schickt der
 * Test (wie Python es tut) die Nutzlast ueber MDViewer.load().
 */
async function renderInSimulatedBrowser({ payload = DEMO_PAYLOAD, markdown, mode = 'app' } = {}) {
  let html = readWebFile('index.html');
  const demo = markdown === undefined ? payload : { ...payload, text: markdown };
  // "<" escapen: sonst beendet ein "</script>" im Markdown den eingefuegten Block.
  const literal = JSON.stringify(demo).replace(/</g, '\\u003c');
  const bootstrapping = mode === 'demo' ? `window.MD_DEMO = ${literal};` : `window.__payload = ${literal};`;
  // Funktion als Ersatz: sonst deutet String.replace ein "$$" im Markdown als Escape.
  html = html.replace(
    '<script src="bundle/viewer.min.js"></script>',
    () => `<script>
       window.__messages = [];
       window.webkit = { messageHandlers: { app: { postMessage: (raw) => window.__messages.push(raw) } } };
       ${bootstrapping}
     </script>
     <script src="bundle/viewer.min.js"></script>`,
  );

  const virtualConsole = new VirtualConsole();
  const errors = [];
  virtualConsole.on('jsdomError', (error) => errors.push(error));
  virtualConsole.on('error', (message) => errors.push(new Error(String(message))));

  const dom = new JSDOM(html, {
    url: indexUrl,
    runScripts: 'dangerously',
    resources: 'usable',
    virtualConsole,
  });

  await new Promise((resolve) => {
    if (dom.window.document.readyState === 'complete') resolve();
    else dom.window.addEventListener('load', resolve);
  });
  // Nach dem load-Ereignis laeuft das Rendern; einen Tick warten (KaTeX laedt nach).
  await new Promise((resolve) => setTimeout(resolve, 30));
  const result = { dom, win: dom.window, doc: dom.window.document, errors };
  result.messages = () => dom.window.__messages.map((raw) => JSON.parse(raw));
  if (mode === 'app') {
    // Genau der Aufruf, den viewer_page.py per evaluate_javascript schickt
    dom.window.MDViewer.load(dom.window.__payload);
    await new Promise((resolve) => setTimeout(resolve, 30));
  }
  return result;
}

test('Bundle laedt und rendert das Dokument (Ende-zu-Ende)', { skip: !hasBundle }, async () => {
  const { win, doc, errors, messages } = await renderInSimulatedBrowser();
  const article = doc.getElementById('doc');

  // Skript ist geladen und die Schnittstelle vorhanden
  assert.equal(typeof win.MDViewer, 'object');
  assert.equal(win.MDViewer.ready, true);
  assert.equal(win.MDViewer.bridgeAvailable, true);
  assert.equal(errors.length, 0, `Fehler im Browserlauf: ${errors.map(String).join(' | ')}`);

  // Die Seite meldet sich bereit, danach kommt das gerenderte Dokument
  assert.ok(messages().some((m) => m.type === 'ready'));
  const rendered = messages().find((m) => m.type === 'rendered');
  assert.ok(rendered, 'rendered-Nachricht fehlt');
  assert.equal(rendered.documentKind, 'document');
  assert.ok(rendered.stats.words > 20);

  // Inhalt wirklich gerendert
  assert.match(article.innerHTML, /<h1 id="titel-des-dokuments">/);
  assert.match(article.innerHTML, /class="markdown-alert markdown-alert-note"/);
  assert.match(article.innerHTML, /class="hljs-keyword"/);
  assert.match(article.innerHTML, /<table>/);
  assert.match(article.innerHTML, /class="contains-task-list"/);
  assert.match(article.innerHTML, /class="code-copy"/);
  assert.equal(article.querySelectorAll('.heading-anchor').length, 4);

  // Inhaltsverzeichnis und Fusszeile
  const tocLinks = doc.querySelectorAll('#toc .toc-link');
  assert.equal(tocLinks.length, 4);
  assert.equal(doc.getElementById('sidebar').hidden, false);
  assert.match(doc.getElementById('article-footer').textContent, /beispiel\.md/);

  // Stylesheets sind vorhanden und das dunkle Theme ist abgeschaltet
  assert.equal(doc.querySelectorAll('link[rel="stylesheet"]').length, 6);
  assert.ok(doc.getElementById('css-md-dark').hasAttribute('disabled'));
  assert.equal(doc.getElementById('css-md-katex') === null, true);
  win.close();
});

test('Vorschaumodus (window.MD_DEMO) rendert ohne Python-Bruecke', { skip: !hasBundle }, async () => {
  const { win, doc, messages } = await renderInSimulatedBrowser({ mode: 'demo' });
  assert.equal(doc.querySelectorAll('#toc .toc-link').length, 4);
  assert.match(doc.getElementById('doc').innerHTML, /<h1 id="titel-des-dokuments">/);
  assert.equal(win.MDViewer.ready, true);
  // im Vorschaumodus meldet sich die Seite nicht als "bereit" (kein Python da)
  assert.equal(messages().some((m) => m.type === 'ready'), false);
  win.close();
});

test('Bundle entfernt unsicheren Inhalt (DOMPurify aktiv)', { skip: !hasBundle }, async () => {
  const { win, doc } = await renderInSimulatedBrowser({
    markdown: `<script>window.__boese = true;</script>

<img src="x.png" onerror="window.__boese = true">

[Klick](javascript:window.__boese=true)

<iframe src="https://example.com"></iframe>
`,
  });
  assert.equal(win.__boese, undefined);
  const html = doc.getElementById('doc').innerHTML;
  assert.doesNotMatch(html, /<script/i);
  assert.doesNotMatch(html, /onerror/i);
  assert.doesNotMatch(html, /javascript:/i);
  assert.doesNotMatch(html, /<iframe/i);
  win.close();
});

test('Suche und Theme funktionieren im Bundle', { skip: !hasBundle }, async () => {
  const { win, doc } = await renderInSimulatedBrowser({
    markdown: 'Apfel Banane Apfel\n\n## Abschnitt\n\nNoch ein Apfel.\n',
  });
  // So wie ein Benutzer: Strg+F, dann tippen
  win.MDViewer.openFind();
  const input = doc.getElementById('find-input');
  input.value = 'Apfel';
  input.dispatchEvent(new win.Event('input', { bubbles: true }));
  assert.equal(doc.querySelectorAll('mark.search-hit').length, 3);
  assert.equal(doc.getElementById('find-count').textContent, '1 von 3 Treffern');
  win.MDViewer.findNext();
  assert.equal(doc.getElementById('find-count').textContent, '2 von 3 Treffern');

  win.MDViewer.setTheme('dark');
  assert.equal(doc.documentElement.getAttribute('data-theme'), 'dark');
  assert.equal(doc.getElementById('css-md-dark').hasAttribute('disabled'), false);

  win.MDViewer.setZoom(150);
  assert.equal(doc.getElementById('doc').style.getPropertyValue('zoom'), '1.5');
  win.close();
});

test('Kopieren im Bundle meldet den Text an die Bruecke', { skip: !hasBundle }, async () => {
  const { win, doc, messages } = await renderInSimulatedBrowser({ markdown: '```js\nconst x = 1;\n```\n' });
  // Ohne Clipboard-API in jsdom schlaegt execCommand fehl -> Rueckfall ueber die Bruecke.
  win.document.execCommand = undefined;
  const button = doc.querySelector('.code-copy');
  button.dispatchEvent(new win.MouseEvent('click', { bubbles: true, cancelable: true }));
  const copy = messages().find((m) => m.type === 'copy-text');
  assert.ok(copy, 'copy-text wurde nicht gemeldet');
  assert.match(copy.text, /const x = 1;/);
  win.close();
});

test('Das Beispiel-Dokument aus docs/ rendert vollstaendig', { skip: !hasBundle }, async () => {
  const markdown = readFileSync(path.join(repoRoot, 'docs', 'beispiel.md'), 'utf8');
  const { win, doc, messages } = await renderInSimulatedBrowser({
    payload: { ...DEMO_PAYLOAD, fileName: 'beispiel.md' },
    markdown,
  });
  const article = doc.getElementById('doc');

  // Frontmatter
  assert.ok(doc.querySelector('.front-matter'), 'Frontmatter-Block fehlt');
  // Alle fuenf Hinweis-Typen
  for (const kind of ['note', 'tip', 'important', 'warning', 'caution']) {
    assert.ok(article.querySelector(`.markdown-alert-${kind}`), `${kind}-Block fehlt`);
  }
  // Fussnoten
  assert.ok(article.querySelector('.footnotes'), 'Fussnoten fehlen');
  // Die eingefuegte Nutzlast muss unveraendert ankommen (u. a. "$$" der Anzeige-Mathematik)
  assert.match(win.__payload.text, /\$\$[\s\S]+\$\$/, 'Nutzlast wurde beim Einsetzen beschaedigt');
  assert.match(doc.getElementById('doc').textContent, /\\int_0\^\\infty/);

  // Mathematik wurde erkannt *und* von KaTeX gesetzt (laedt katex.min.js nach)
  assert.equal(messages().find((m) => m.type === 'rendered').hasMath, true);
  await new Promise((resolve) => setTimeout(resolve, 900));
  const typeset = doc.querySelectorAll('#doc .katex').length;
  assert.ok(typeset >= 3, `KaTeX hat nur ${typeset} Formeln gesetzt`);
  assert.equal(doc.getElementById('css-katex').hasAttribute('disabled'), false);
  assert.equal(messages().some((m) => m.type === 'warning'), false, 'Warnungen beim Mathesatz');
  // Aufklappbarer HTML-Bereich bleibt erhalten
  assert.ok(article.querySelector('details'));
  // Viele Eintraege im Inhaltsverzeichnis
  assert.ok(doc.querySelectorAll('#toc .toc-link').length >= 10);
  win.close();
});
