import test from 'node:test';
import assert from 'node:assert/strict';
import {
  renderDocument,
  extractFrontMatter,
  detectMath,
  escapeHtml,
  DEFAULT_RENDER_OPTIONS,
} from '../../web/src/renderer.js';

test('DEFAULT_RENDER_OPTIONS ist eingefroren und vollstaendig', () => {
  assert.ok(Object.isFrozen(DEFAULT_RENDER_OPTIONS));
  assert.equal(DEFAULT_RENDER_OPTIONS.breaks, false);
  assert.equal(DEFAULT_RENDER_OPTIONS.highlight, true);
});

test('GFM-Tabellen werden gerendert', () => {
  const { html } = renderDocument('| a | b |\n|---|---|\n| 1 | 2 |\n');
  assert.match(html, /<table>/);
  assert.match(html, /<th>a<\/th>/);
  assert.match(html, /<td>1<\/td>/);
  assert.match(html, /<td>2<\/td>/);
});

test('Ueberschriften bekommen GitHub-kompatible IDs (inkl. Duplikate)', () => {
  const { html } = renderDocument('# Hallo Welt\n\n## Hallo Welt\n\n## Ähnlich & schön\n');
  assert.match(html, /<h1 id="hallo-welt">/);
  assert.match(html, /<h2 id="hallo-welt-1">/);
  // GitHub behaelt Unicode-Buchstaben und laesst Leerzeichen als doppelten Bindestrich stehen
  assert.match(html, /<h2 id="ähnlich--schön">/);
});

test('Task-Listen und Durchstreichen (GFM)', () => {
  const { html } = renderDocument('- [x] fertig\n- [ ] offen\n\n~~weg~~\n');
  assert.match(html, /<input checked="" disabled="" type="checkbox">/);
  assert.match(html, /<input disabled="" type="checkbox">/);
  assert.match(html, /<del>weg<\/del>/);
});

test('Fussnoten werden unterstuetzt', () => {
  const { html } = renderDocument('Text[^1]\n\n[^1]: Fussnote\n');
  assert.match(html, /footnote-ref/);
  assert.match(html, /Fussnote/);
});

test('Alerts werden zu markdown-alert-Bloecken', () => {
  const { html } = renderDocument('> [!WARNING]\n> Achtung!\n');
  assert.match(html, /class="markdown-alert markdown-alert-warning"/);
  assert.match(html, /Achtung!/);
});

test('Syntax-Highlighting erzeugt hljs-Spans, unbekannte Sprachen bleiben Text', () => {
  const { html } = renderDocument('```js\nconst a = 1;\n```\n\n```nixgibts\nfoo\n```\n');
  assert.match(html, /class="hljs-keyword"/);
  assert.match(html, /class="language-nixgibts"/);
  assert.match(html, /foo/);
});

test('ohne Sprachangabe wird nicht geraten', () => {
  const { html, } = renderDocument('```\nconst a = 1;\n```\n');
  assert.match(html, /language-plaintext/);
  assert.doesNotMatch(html, /hljs-keyword/);
});

test('highlight:false schaltet das Highlighting ab', () => {
  const { html } = renderDocument('```js\nconst a = 1;\n```\n', { highlight: false });
  assert.doesNotMatch(html, /hljs-keyword/);
  assert.match(html, /language-js/);
});

test('breaks-Option macht aus Zeilenumbruechen <br>', () => {
  assert.doesNotMatch(renderDocument('Zeile1\nZeile2\n').html, /<br>/);
  assert.match(renderDocument('Zeile1\nZeile2\n', { breaks: true }).html, /<br>/);
});

test('extractFrontMatter erkennt YAML und TOML', () => {
  const yaml = extractFrontMatter('---\ntitle: Test\nautor: ich\n---\n# Inhalt\n');
  assert.equal(yaml.format, 'yaml');
  assert.equal(yaml.text, 'title: Test\nautor: ich');
  assert.equal(yaml.body.trim(), '# Inhalt');

  const toml = extractFrontMatter('+++\ntitle = "Test"\n+++\n# Inhalt\n');
  assert.equal(toml.format, 'toml');
  assert.equal(toml.body.trim(), '# Inhalt');
});

test('extractFrontMatter laesst Dokumente ohne Frontmatter unveraendert', () => {
  const input = '# Titel\n\n---\n\nText\n';
  const result = extractFrontMatter(input);
  assert.equal(result.text, null);
  assert.equal(result.body, input);
});

test('renderDocument liefert Frontmatter getrennt vom HTML', () => {
  const result = renderDocument('---\ntitle: T\n---\n# Kopf\n');
  assert.equal(result.frontMatterFormat, 'yaml');
  assert.match(result.html, /<h1 id="kopf">/);
  assert.doesNotMatch(result.html, /title: T/);
});

test('ein reiner Frontmatter-Dump gilt als leeres Dokument', () => {
  const result = renderDocument('---\ntitle: T\n---\n');
  assert.equal(result.isEmpty, true);
  assert.equal(result.html, '');
});

test('detectMath findet Block-, Inline- und Klammer-Notation', () => {
  assert.equal(detectMath('$$x^2$$'), true);
  assert.equal(detectMath('Text mit $x+1$ drin'), true);
  assert.equal(detectMath('\\(a+b\\)'), true);
  assert.equal(detectMath('\\[a+b\\]'), true);
  assert.equal(detectMath('Kein Mathe-Text'), false);
  assert.equal(detectMath('Preis: $x+1$', false), false);
  assert.equal(detectMath('$$x^2$$', false), true);
});

test('math:false schaltet die Erkennung ab', () => {
  assert.equal(renderDocument('$$x$$', { math: false }).hasMath, false);
});

test('escapeHtml maskiert Sonderzeichen', () => {
  assert.equal(escapeHtml('<a href="x">&\'</a>'), '&lt;a href=&quot;x&quot;&gt;&amp;&#39;&lt;/a&gt;');
});

test('Roh-HTML bleibt im Renderer erhalten (Sanitizing passiert im Viewer)', () => {
  const { html } = renderDocument('<div class="x">roh</div>\n');
  assert.match(html, /<div class="x">roh<\/div>/);
});
