/**
 * Markdown -> HTML. Reine Funktionen, kein DOM-Zugriff: dadurch identisch im
 * WebView und in Node.js (Tests) nutzbar.
 *
 * Der Renderer bildet das Verhalten von github.com nach:
 *  - GFM (Tabellen, Task-Listen, Durchstreichen, Autolinks)
 *  - Ueberschriften-IDs wie auf GitHub ("gfm-heading-id")
 *  - Alert-Bloecke  > [!NOTE] / [!WARNING] ...
 *  - Fussnoten
 *  - Syntax-Highlighting mit highlight.js (Aussehen wie auf GitHub)
 */
import { Marked } from 'marked';
import markedFootnote from 'marked-footnote';
import { gfmHeadingId } from 'marked-gfm-heading-id';
import markedAlert from 'marked-alert';
import { markedHighlight } from 'marked-highlight';
import hljs from 'highlight.js/lib/common';

/** Voreinstellungen; koennen im Viewer (Einstellungen-Dialog) geaendert werden. */
export const DEFAULT_RENDER_OPTIONS = Object.freeze({
  /** Einzelne Zeilenumbrueche als <br> behandeln (GitHub-Kommentare statt README) */
  breaks: false,
  /** Syntax-Highlighting in Codebloecken */
  highlight: true,
  /** Mathematik ($$...$$, \(...\), \[...\]) mit KaTeX rendern */
  math: true,
  /** Zusaetzlich inline-Mathematik $...$ erkennen (kann bei Preisen stoeren) */
  mathInline: true,
});

/** Findet YAML- (---) bzw. TOML-Frontmatter (+++) am Dateianfang. */
const FRONT_MATTER = {
  yaml: /^\uFEFF?---[ \t]*\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/,
  toml: /^\uFEFF?\+\+\+[ \t]*\r?\n([\s\S]*?)\r?\n\+\+\+[ \t]*(?:\r?\n|$)/,
};

/** Grobe Erkennung, ob im Dokument Mathematik vorkommt (nur fuer das Nachladen von KaTeX). */
const MATH_BLOCK = /\$\$[\s\S]+?\$\$|\\\([\s\S]+?\\\)|\\\[[\s\S]+?\\\]/;
const MATH_INLINE = /(^|[^\\$])\$[^\s$][^$\n]{0,400}\$/m;

/**
 * Extrahiert Frontmatter vom Dokumentanfang.
 * @returns {{text: string|null, format: string|null, body: string}}
 */
export function extractFrontMatter(markdown) {
  const source = String(markdown ?? '');
  for (const [format, pattern] of Object.entries(FRONT_MATTER)) {
    const match = source.match(pattern);
    if (match) {
      return { text: match[1], format, body: source.slice(match[0].length) };
    }
  }
  return { text: null, format: null, body: source };
}

/** Erkennt, ob KaTeX benoetigt wird. */
export function detectMath(markdown, mathInline = true) {
  const text = String(markdown ?? '');
  if (MATH_BLOCK.test(text)) return true;
  return Boolean(mathInline) && MATH_INLINE.test(text);
}

function highlightFunction(enabled) {
  return (code, lang) => {
    if (!enabled) return false;
    const language = String(lang ?? '').trim().toLowerCase();
    // Ohne Sprachangabe nicht raten - genau wie GitHub.
    if (!language || !hljs.getLanguage(language)) return false;
    try {
      return hljs.highlight(code, { language, ignoreIllegals: true }).value;
    } catch {
      return false;
    }
  };
}

/**
 * Baut eine frische marked-Instanz. Bewusst pro Aufruf: die Ueberschriften-IDs
 * werden intern zwischengespeichert und muessen bei jedem Rendern neu beginnen.
 */
export function createEngine(options = {}) {
  const opts = { ...DEFAULT_RENDER_OPTIONS, ...options };
  const engine = new Marked();
  engine.use(
    markedAlert(),
    markedFootnote({ footnoteClassName: 'footnotes' }),
    gfmHeadingId({ prefix: '' }),
    markedHighlight({
      langPrefix: 'language-',
      emptyLangClass: 'language-plaintext',
      highlight: highlightFunction(opts.highlight),
    }),
  );
  engine.setOptions({
    gfm: true,
    breaks: Boolean(opts.breaks),
    pedantic: false,
    async: false,
    headerIds: false,
    mangle: false,
  });
  return engine;
}

/**
 * Rendert Markdown zu HTML.
 *
 * @param {string} markdown
 * @param {object} [options] siehe DEFAULT_RENDER_OPTIONS
 * @returns {{html: string, frontMatter: string|null, frontMatterFormat: string|null,
 *            hasMath: boolean, isEmpty: boolean}}
 */
export function renderDocument(markdown, options = {}) {
  const opts = { ...DEFAULT_RENDER_OPTIONS, ...options };
  const source = String(markdown ?? '');
  const { text, format, body } = extractFrontMatter(source);
  const isEmpty = body.trim() === '';
  const html = isEmpty ? '' : createEngine(opts).parse(body);
  return {
    html,
    frontMatter: text,
    frontMatterFormat: format,
    hasMath: opts.math ? detectMath(body, opts.mathInline) : false,
    isEmpty,
  };
}

/** HTML-Escaping fuer Textknoten in generiertem Markup. */
export function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
