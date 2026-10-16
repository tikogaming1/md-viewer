import test from 'node:test';
import assert from 'node:assert/strict';
import { createViewer, pickActiveHeading } from '../../web/src/viewer.js';
import { createViewerFixture, DEMO_PAYLOAD } from './helpers.mjs';

test('pickActiveHeading findet die letzte Ueberschrift oberhalb der Linie', () => {
  const tops = [-100, 10, 200, 500];
  assert.equal(pickActiveHeading(tops, -200), -1);
  assert.equal(pickActiveHeading(tops, -100), 0);
  assert.equal(pickActiveHeading(tops, 0), 0);
  assert.equal(pickActiveHeading(tops, 10), 1);
  assert.equal(pickActiveHeading(tops, 499), 2);
  assert.equal(pickActiveHeading(tops, 1000), 3);
  assert.equal(pickActiveHeading([], 0), -1);
});

test('Viewer rendert ein Dokument in das DOM', () => {
  const { doc, viewer, messages } = createViewerFixture();
  const result = viewer.load(DEMO_PAYLOAD);

  assert.equal(result.empty, false);
  const article = doc.getElementById('doc');
  assert.match(article.innerHTML, /<h1 id="titel-des-dokuments">/);
  assert.match(article.innerHTML, /class="hljs-keyword"/);
  assert.match(article.innerHTML, /markdown-alert-note/);
  assert.ok(messages.some((m) => m.type === 'rendered'));
});

test('Inhaltsverzeichnis wird aus den Ueberschriften gebaut', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);

  const links = doc.querySelectorAll('#toc .toc-link');
  assert.equal(links.length, 4);
  assert.equal(links[0].textContent, 'Titel des Dokuments');
  assert.equal(links[0].getAttribute('data-target'), 'titel-des-dokuments');
  assert.equal(links[0].style.getPropertyValue('--level'), '0'); // h1
  assert.equal(links[1].style.getPropertyValue('--level'), '1'); // h2
  assert.equal(links[2].style.getPropertyValue('--level'), '1'); // h2
  assert.equal(links[3].style.getPropertyValue('--level'), '2'); // h3
  assert.equal(links[0].classList.contains('toc-level-1'), true);
  assert.equal(doc.getElementById('toc-title').textContent, 'Inhaltsverzeichnis');
  assert.equal(doc.getElementById('sidebar').hidden, false);
});

test('die kleinste vorkommende Ueberschrift beginnt bei Stufe 0', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: '## Nur h2\n\n### Tiefer\n' });
  const links = doc.querySelectorAll('#toc .toc-link');
  assert.equal(links.length, 2);
  assert.equal(links[0].style.getPropertyValue('--level'), '0');
  assert.equal(links[1].style.getPropertyValue('--level'), '1');
});

test('Sidebar laesst sich abschalten', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  viewer.applySettings({ tocVisible: false });
  assert.equal(doc.getElementById('sidebar').hidden, true);
  viewer.applySettings({ tocVisible: true });
  assert.equal(doc.getElementById('sidebar').hidden, false);
});

test('Ueberschriften bekommen Anker-Links', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  const anchor = doc.querySelector('#doc h1 .heading-anchor');
  assert.ok(anchor);
  assert.equal(anchor.getAttribute('href'), '#titel-des-dokuments');
});

test('relative Links auf Markdown-Dateien werden an die App gemeldet', () => {
  const { doc, viewer, messages } = createViewerFixture();
  viewer.load({
    ...DEMO_PAYLOAD,
    text: '[Weiter](kapitel/zwei.md) und [Bild](bild.png) und [Web](https://example.org)\n',
  });

  const links = doc.querySelectorAll('#doc a');
  links[0].dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true, cancelable: true }));
  assert.deepEqual(messages.at(-1), { type: 'open-path', url: 'file:///home/user/docs/kapitel/zwei.md' });

  links[1].dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true, cancelable: true }));
  assert.equal(messages.at(-1).type, 'open-external');
  assert.equal(messages.at(-1).url, 'file:///home/user/docs/bild.png');

  links[2].dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true, cancelable: true }));
  assert.deepEqual(messages.at(-1), { type: 'open-external', url: 'https://example.org' });
});

test('interne Anker-Links springen im Dokument (kein App-Aufruf)', () => {
  const { doc, viewer, messages } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: '[Los](#dritter-abschnitt)\n\n## Dritter Abschnitt\n\nText\n' });
  const before = messages.length;
  const link = doc.querySelector('#doc a');
  link.dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true, cancelable: true }));
  assert.equal(messages.length, before);
});

test('Klick auf den Ueberschriften-Anker kopiert den Abschnittslink', () => {
  const { doc, viewer, messages } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  const anchor = doc.querySelector('#doc h1 .heading-anchor');
  anchor.dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true, cancelable: true }));
  const copy = messages.find((m) => m.type === 'copy-text');
  assert.ok(copy);
  assert.equal(copy.text, 'file:///home/user/docs/beispiel.md#titel-des-dokuments');
});

test('Codebloecke bekommen einen Kopier-Knopf', () => {
  const { doc, viewer, messages } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  const button = doc.querySelector('.code-block .code-copy');
  assert.ok(button);
  assert.equal(button.textContent, 'Kopieren');
  button.dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true, cancelable: true }));
  const copy = messages.find((m) => m.type === 'copy-text');
  assert.ok(copy);
  assert.match(copy.text, /const x = 1;/);
  assert.equal(button.textContent, '✓');
});

test('Suche findet Treffer, markiert sie und zaehlt', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: 'Apfel Banane Apfel\n\n## Abschnitt\n\nNoch ein Apfel.\n' });

  const total = viewer.runFind('Apfel');
  assert.equal(total, 3);
  const marks = doc.querySelectorAll('mark.search-hit');
  assert.equal(marks.length, 3);
  assert.equal(marks[0].classList.contains('is-current'), true);
  assert.equal(doc.getElementById('find-count').textContent, '1 von 3 Treffern');

  viewer.findNext();
  assert.equal(doc.getElementById('find-count').textContent, '2 von 3 Treffern');

  viewer.findPrev();
  viewer.findPrev();
  assert.equal(doc.getElementById('find-count').textContent, '3 von 3 Treffern');

  viewer.runFind('gibtsnicht');
  assert.equal(doc.querySelectorAll('mark.search-hit').length, 0);
  assert.equal(doc.getElementById('find-count').textContent, 'Keine Treffer');
});

test('Suche ignoriert Gross-/Kleinschreibung und raeumt Markierungen auf', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: 'Hallo hallo HALLO\n' });
  assert.equal(viewer.runFind('hallo'), 3);
  viewer.closeFind();
  assert.equal(doc.querySelectorAll('mark.search-hit').length, 0);
  assert.equal(doc.getElementById('doc').textContent.trim(), 'Hallo hallo HALLO');
});

test('Suche durchsucht keine Code-Kopier-Knoepfe oder Skripte', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: '```js\nconst treffer = 1;\n```\n' });
  assert.equal(viewer.runFind('Kopieren'), 0);
  assert.equal(viewer.runFind('treffer'), 1);
});

test('Theme-Umschaltung aktiviert die passenden Stylesheets', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.setTheme('dark');
  assert.equal(doc.documentElement.getAttribute('data-theme'), 'dark');
  assert.equal(doc.getElementById('css-md-dark').hasAttribute('disabled'), false);
  assert.equal(doc.getElementById('css-md-light').hasAttribute('disabled'), true);
  assert.equal(doc.getElementById('css-hl-dark').hasAttribute('disabled'), false);

  viewer.setTheme('light');
  assert.equal(doc.documentElement.getAttribute('data-theme'), 'light');
  assert.equal(doc.getElementById('css-md-light').hasAttribute('disabled'), false);
  assert.equal(doc.getElementById('css-md-dark').hasAttribute('disabled'), true);
});

test('Theme "auto" folgt dem System', () => {
  const { viewer, win } = createViewerFixture();
  win.matchMedia = () => ({ matches: true, addEventListener() {}, removeEventListener() {} });
  viewer.setTheme('auto');
  assert.equal(viewer.resolveTheme(), 'dark');
});

test('Zoom wird als CSS-Zoom auf den Artikel angewendet', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.applySettings({ zoom: 150 });
  assert.equal(doc.getElementById('doc').style.getPropertyValue('zoom'), '1.5');
  viewer.applySettings({ zoom: 80 });
  assert.equal(doc.getElementById('doc').style.getPropertyValue('zoom'), '0.8');
});

test('Zeilenbreite wird auf das Dokument angewendet', () => {
  const { doc, viewer } = createViewerFixture();
  const root = doc.documentElement;
  assert.equal(root.style.getPropertyValue('--content-max'), '1012px');
  viewer.applySettings({ lineWidth: 'wide' });
  assert.equal(root.style.getPropertyValue('--content-max'), '1440px');
  viewer.applySettings({ lineWidth: 'full' });
  assert.equal(root.style.getPropertyValue('--content-max'), 'none');
  // unbekannte Werte fallen auf "normal" zurueck
  assert.equal(viewer.applyLineWidth('breit'), 'normal');
  assert.equal(root.style.getPropertyValue('--content-max'), '1012px');
});

test('Frontmatter landet in einem aufklappbaren Block', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: '---\ntitle: Test\ntags: [a, b]\n---\n# Los\n' });
  const details = doc.querySelector('.front-matter');
  assert.ok(details);
  assert.match(details.querySelector('summary').textContent, /Frontmatter/);
  assert.match(details.querySelector('code').textContent, /title: Test/);
  // Frontmatter darf nicht im Inhaltsverzeichnis auftauchen
  assert.equal(doc.querySelectorAll('#toc .toc-link').length, 1);
});

test('Hinweis-Banner erscheint und laesst sich schliessen', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, notice: 'Datei ist nicht UTF-8.' });
  const notice = doc.querySelector('.doc-notice');
  assert.ok(notice);
  assert.equal(notice.textContent.includes('Datei ist nicht UTF-8.'), true);
  notice.querySelector('.doc-notice-close').dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true }));
  assert.equal(doc.querySelector('.doc-notice'), null);
});

test('leere Dokumente zeigen einen Hinweis', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: '' });
  assert.ok(doc.querySelector('.doc-empty'));
});

test('Fusszeile wird aus der Vorlage gefuellt', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: 'Ein zwei drei vier fünf.\n' });
  const footer = doc.getElementById('article-footer');
  assert.equal(footer.hidden, false);
  assert.match(footer.textContent, /beispiel\.md/);
  assert.match(footer.textContent, /5 Wörter/);
});

test('Statistiken werden berechnet und gemeldet', () => {
  const { viewer, messages } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  const rendered = messages.find((m) => m.type === 'rendered');
  assert.ok(rendered.stats.words > 20);
  assert.equal(rendered.stats.headings, 4);
  assert.equal(rendered.stats.codeBlocks, 1);
  assert.equal(rendered.stats.tables, 1);
  // 1 Markdown-Link + Fussnoten-Referenz + Fussnoten-Rueckverweis
  assert.equal(rendered.stats.links, 3);
  assert.ok(rendered.stats.readingMinutes >= 1);
});

test('Blockierte externe Bilder werden erst nach Klick geladen', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({
    ...DEMO_PAYLOAD,
    text: '![Fern](https://example.com/bild.png)\n\n![Lokal](lokal.png)\n',
    settings: { blockRemoteImages: true },
  });
  const images = doc.querySelectorAll('#doc img');
  assert.equal(images[0].getAttribute('data-blocked'), '1');
  assert.equal(images[0].getAttribute('data-src'), 'https://example.com/bild.png');
  assert.match(images[0].getAttribute('src'), /^data:image\/svg\+xml/);
  assert.equal(images[1].getAttribute('data-blocked'), null);
  assert.equal(images[1].getAttribute('src'), 'lokal.png');

  images[0].dispatchEvent(new doc.defaultView.MouseEvent('click', { bubbles: true, cancelable: true }));
  assert.equal(images[0].getAttribute('src'), 'https://example.com/bild.png');
  assert.equal(images[0].getAttribute('data-blocked'), null);
});

test('externe Bilder sind ohne Blockierung erlaubt', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: '![Fern](https://example.com/bild.png)\n' });
  const img = doc.querySelector('#doc img');
  assert.equal(img.getAttribute('src'), 'https://example.com/bild.png');
  assert.equal(img.getAttribute('data-lightbox'), '1');
});

test('Klick auf ein Bild oeffnet die Lightbox, Esc schliesst sie', () => {
  const { doc, win, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: '![Ein Bild](bild.png)\n\nText\n' });
  const img = doc.querySelector('#doc img');
  img.dispatchEvent(new win.MouseEvent('click', { bubbles: true, cancelable: true }));
  assert.equal(doc.getElementById('lightbox').hidden, false);
  assert.equal(doc.getElementById('lightbox-image').getAttribute('src'), 'bild.png');
  assert.equal(doc.getElementById('lightbox-caption').textContent, 'Ein Bild');

  doc.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.equal(doc.getElementById('lightbox').hidden, true);
});

test('base-Href wird aus dem Dokumentpfad gesetzt', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  assert.equal(doc.head.querySelector('base').getAttribute('href'), 'file:///home/user/docs/');
});

test('CSP wird bei blockierten Bildern verschaerft', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, settings: { blockRemoteImages: true } });
  const meta = doc.head.querySelector('meta[http-equiv="Content-Security-Policy"]');
  assert.match(meta.getAttribute('content'), /img-src 'self' file: data:;/);
  viewer.applySettings({ blockRemoteImages: false });
  assert.match(meta.getAttribute('content'), /img-src 'self' file: data: https: http:/);
});

test('Sicherheit: Skripte, Event-Handler und javascript:-Links sind entfernt', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({
    ...DEMO_PAYLOAD,
    text: '<script>alert(1)</script>\n\n<img src="x.png" onerror="alert(2)">\n\n[Klick](javascript:alert(3))\n\n<iframe src="https://example.com"></iframe>\n',
  });
  const html = doc.getElementById('doc').innerHTML;
  assert.doesNotMatch(html, /<script/i);
  assert.doesNotMatch(html, /alert\(1\)/);
  assert.doesNotMatch(html, /onerror/i);
  assert.doesNotMatch(html, /javascript:/i);
  assert.doesNotMatch(html, /<iframe/i);
});

test('Einstellungen mit Rendereinfluss loesen ein Neu-Rendern aus', () => {
  const { doc, viewer, messages } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: 'Zeile1\nZeile2\n' });
  assert.doesNotMatch(doc.getElementById('doc').innerHTML, /<br>/);
  viewer.applySettings({ breaks: true });
  assert.match(doc.getElementById('doc').innerHTML, /<br>/);
  assert.ok(messages.filter((m) => m.type === 'rendered').length >= 2);
});

test('Sprache laesst sich umschalten', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  viewer.applySettings({ language: 'en' });
  assert.equal(doc.getElementById('toc-title').textContent, 'Table of contents');
  assert.equal(doc.querySelector('.toc-link') !== null, true);
  const button = doc.querySelector('.code-copy');
  assert.equal(button.textContent, 'Copy');
});

test('Willkommensdokument blendet die Sidebar aus', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ kind: 'welcome', text: '# Willkommen\n\nBitte Datei öffnen.\n', baseHref: '' });
  assert.equal(doc.getElementById('sidebar').hidden, true);
  assert.match(doc.getElementById('doc').className, /is-welcome/);
});

test('mehrfaches Laden setzt Zustand und Suche zurueck', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load({ ...DEMO_PAYLOAD, text: 'Apfel Apfel\n' });
  viewer.runFind('Apfel');
  assert.equal(doc.querySelectorAll('mark.search-hit').length, 2);
  viewer.load({ ...DEMO_PAYLOAD, text: 'Nichts mehr da.\n' });
  assert.equal(doc.querySelectorAll('mark.search-hit').length, 0);
  assert.equal(doc.getElementById('findbar').hidden, true);
});

test('Suchleiste oeffnen/schliessen', () => {
  const { doc, viewer } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  assert.equal(doc.getElementById('findbar').hidden, true);
  viewer.openFind();
  assert.equal(doc.getElementById('findbar').hidden, false);
  viewer.closeFind();
  assert.equal(doc.getElementById('findbar').hidden, true);
});

test('getBodyHtml liefert das gerenderte HTML fuer den Export', () => {
  const { viewer } = createViewerFixture();
  viewer.load(DEMO_PAYLOAD);
  const html = viewer.getBodyHtml();
  assert.match(html, /<h1 id="titel-des-dokuments">/);
  assert.match(html, /code-copy/);
});

test('Viewer wirft einen klaren Fehler, wenn das Geruest fehlt', () => {
  const { win } = createViewerFixture();
  const emptyDoc = win.document.implementation.createHTMLDocument('leer');
  assert.throws(() => createViewer(win, emptyDoc, { emit: () => {} }), /Element #sidebar fehlt/);
});
