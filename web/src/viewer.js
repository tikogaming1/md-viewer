/**
 * Viewer-Logik: nimmt Markdown vom Python-Teil entgegen, rendert es in das DOM
 * und kuemmert sich um Inhaltsverzeichnis, Suche, Lightbox, Theme und Kopieren.
 *
 * Alles DOM-bezogene laeuft ueber das uebergebene window/document, damit die
 * komplette Klasse in jsdom getestet werden kann.
 */
import createDOMPurify from 'dompurify';
import { renderDocument, DEFAULT_RENDER_OPTIONS } from './renderer.js';
import { t, setLanguage } from './i18n.js';

/** Erlaubte Attribute/Tags fuer den Sanitizer (DOMPurify). */
const PURIFY_CONFIG = {
  USE_PROFILES: { html: true },
  ADD_ATTR: [
    'id',
    'class',
    'align',
    'start',
    'reversed',
    'colspan',
    'rowspan',
    'checked',
    'disabled',
    'type',
    'title',
    'open',
    'loading',
    'aria-hidden',
    'aria-label',
    'aria-describedby',
    'data-src',
    'data-blocked',
    'data-lightbox',
    'data-lang',
  ],
  ADD_DATA_URI_TAGS: ['img'],
  // Standardliste von DOMPurify + file: (relative Bildpfade in lokalen Dokumenten)
  ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?|mailto|tel|callto|sms|cid|xmpp|file):|[^a-z]|[a-z+.\-]+(?:[^a-z+.\-:]|$))/i,
  FORBID_TAGS: ['style', 'form', 'iframe', 'frame', 'frameset', 'object', 'embed', 'base', 'link', 'meta', 'script'],
  FORBID_ATTR: ['ping', 'srcset', 'formaction', 'background', 'onerror', 'onload'],
  KEEP_CONTENT: true,
};

const SELECTORS = {
  sidebar: '#sidebar',
  toc: '#toc',
  tocTitle: '#toc-title',
  content: '#content',
  article: '#doc',
  footer: '#article-footer',
  findbar: '#findbar',
  findInput: '#find-input',
  findCount: '#find-count',
  findPrev: '#find-prev',
  findNext: '#find-next',
  findClose: '#find-close',
  toast: '#toast',
  lightbox: '#lightbox',
  lightboxImage: '#lightbox-image',
  lightboxCaption: '#lightbox-caption',
};

/** 1x1 transparentes GIF als Platzhalter fuer blockierte Bilder. */
const PLACEHOLDER_IMAGE =
  'data:image/svg+xml;charset=utf-8,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="140" viewBox="0 0 640 140">' +
      '<rect x="2" y="2" width="636" height="136" rx="8" fill="#8881" stroke="#8886" stroke-width="2" stroke-dasharray="10 8"/>' +
      '<text x="320" y="76" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#8888">🖼</text>' +
      '</svg>',
  );

const HEADING_SELECTOR = 'h1, h2, h3, h4, h5, h6';
/** Maximale Textbreite je Einstellung (siehe web/viewer.css --content-max) */
const LINE_WIDTHS = { normal: '1012px', wide: '1440px', full: 'none' };
/** Kopfzeilen, die nicht ins Inhaltsverzeichnis gehoeren (Fussnoten-Label etc.) */
const HIDDEN_HEADING = '.sr-only, .footnotes, .front-matter, .doc-empty';
const REMOTE_URL = /^https?:\/\//i;
const EXTERNAL_URL = /^(https?|mailto|tel):/i;
const MARKDOWN_FILE = /\.(md|markdown|mdown|mkdn|mkd|mdwn|mdtxt|mdtext|text|txt)$/i;

/**
 * Reine Hilfsfunktion (testbar ohne DOM): ermittelt den Index der aktiven
 * Ueberschrift beim Scrollen.
 *
 * @param {number[]} tops Positionen (oben) der Ueberschriften, aufsteigend
 * @param {number} referenceTop Position der Referenzlinie im Dokument
 * @returns {number} Index oder -1
 */
export function pickActiveHeading(tops, referenceTop) {
  let active = -1;
  for (let i = 0; i < tops.length; i += 1) {
    if (tops[i] <= referenceTop) active = i;
    else break;
  }
  return active;
}

/**
 * Erzeugt einen Viewer.
 *
 * @param {Window} win
 * @param {Document} doc
 * @param {{emit?: (message: object) => void, settings?: object}} [config]
 */
export function createViewer(win, doc, config = {}) {
  const emit = typeof config.emit === 'function' ? config.emit : () => {};
  const el = {};
  for (const [key, selector] of Object.entries(SELECTORS)) {
    const found = doc.querySelector(selector);
    if (!found) throw new Error(`Viewer: Element ${selector} fehlt in index.html`);
    el[key] = found;
  }

  const purify = createDOMPurify(win);

  const state = {
    payload: null,
    markdown: '',
    kind: 'welcome',
    baseHref: '',
    fileUrl: '',
    options: { ...DEFAULT_RENDER_OPTIONS },
    settings: {
      language: 'de',
      theme: 'auto',
      zoom: 100,
      tocVisible: true,
      blockRemoteImages: false,
      notices: true,
      lineWidth: 'normal',
    },
    headings: [],
    activeHeading: -1,
    hits: [],
    hitIndex: -1,
    katexLoading: null,
    katexReady: false,
    scrollScheduled: false,
  };

  const pageUrl = win.location?.href ?? 'file:///index.html';
  const assetUrl = (relative) => new win.URL(relative, pageUrl).href;

  // ---------------------------------------------------------------- Rendering

  function setBaseHref(href) {
    let base = doc.head.querySelector('base');
    if (!href) {
      if (base) base.remove();
      return;
    }
    if (!base) {
      base = doc.createElement('base');
      doc.head.appendChild(base);
    }
    base.setAttribute('href', href);
  }

  function applyContentPolicy() {
    const meta = doc.head.querySelector('meta[http-equiv="Content-Security-Policy"]');
    if (!meta) return;
    const images = state.settings.blockRemoteImages
      ? "img-src 'self' file: data:"
      : "img-src 'self' file: data: https: http:";
    meta.setAttribute(
      'content',
      [
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        images,
        "font-src 'self' file: data:",
        "media-src 'self' file: data:",
        "connect-src 'none'",
        "form-action 'none'",
        "base-uri 'self'",
      ].join('; '),
    );
  }

  function sanitize(html) {
    return purify.sanitize(html, PURIFY_CONFIG);
  }

  function markBlockedImages(root) {
    if (!state.settings.blockRemoteImages) return;
    for (const img of root.querySelectorAll('img')) {
      const src = img.getAttribute('src') ?? '';
      if (!REMOTE_URL.test(src)) continue;
      img.setAttribute('data-src', src);
      img.setAttribute('data-blocked', '1');
      img.setAttribute('src', PLACEHOLDER_IMAGE);
      img.setAttribute('title', t('imageBlocked'));
      img.setAttribute('alt', img.getAttribute('alt') || t('imageBlockedShort'));
    }
  }

  function markImages(root) {
    for (const img of root.querySelectorAll('img')) {
      const parent = img.parentElement;
      if (parent && parent.tagName === 'A') continue;
      if (img.getAttribute('data-blocked') === '1') continue;
      img.setAttribute('data-lightbox', '1');
      if (!img.getAttribute('loading')) img.setAttribute('loading', 'lazy');
    }
  }

  function markTaskLists(root) {
    for (const box of root.querySelectorAll('input[type="checkbox"]')) {
      box.setAttribute('disabled', '');
      const item = box.closest('li');
      if (item) item.classList.add('task-list-item');
      const list = box.closest('ul, ol');
      if (list) list.classList.add('contains-task-list');
    }
  }

  function addHeadingAnchors(root) {
    for (const heading of root.querySelectorAll(HEADING_SELECTOR)) {
      if (heading.matches(HIDDEN_HEADING)) continue;
      if (!heading.id) heading.id = slugify(heading.textContent ?? '');
      const anchor = doc.createElement('a');
      anchor.className = 'heading-anchor';
      anchor.setAttribute('href', `#${heading.id}`);
      anchor.setAttribute('aria-hidden', 'true');
      anchor.setAttribute('tabindex', '-1');
      anchor.setAttribute('title', t('anchorCopy'));
      heading.appendChild(anchor);
    }
  }

  function addCodeCopyButtons(root) {
    for (const pre of Array.from(root.querySelectorAll('pre'))) {
      if (pre.parentElement?.classList.contains('code-block')) continue;
      const wrapper = doc.createElement('div');
      wrapper.className = 'code-block';
      const lang = pre.querySelector('code')?.className.match(/language-([\w+#.-]+)/)?.[1] ?? '';
      if (lang) wrapper.setAttribute('data-language', lang);
      pre.replaceWith(wrapper);
      wrapper.appendChild(pre);
      const button = doc.createElement('button');
      button.type = 'button';
      button.className = 'code-copy';
      button.setAttribute('title', t('copyCode'));
      button.textContent = t('copy');
      wrapper.appendChild(button);
    }
  }

  function slugify(text) {
    return String(text ?? '')
      .trim()
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s-]/gu, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '') || 'abschnitt';
  }

  function buildFragment(html) {
    const template = doc.createElement('template');
    template.innerHTML = sanitize(html);
    const fragment = template.content;
    markBlockedImages(fragment);
    markImages(fragment);
    markTaskLists(fragment);
    addHeadingAnchors(fragment);
    addCodeCopyButtons(fragment);
    return fragment;
  }

  function buildFrontMatterBlock(text, format) {
    const details = doc.createElement('details');
    details.className = 'front-matter';
    const summary = doc.createElement('summary');
    summary.textContent = `${t('frontMatter')} (${String(format ?? 'yaml').toUpperCase()})`;
    const pre = doc.createElement('pre');
    const code = doc.createElement('code');
    code.className = `language-${format === 'toml' ? 'ini' : 'yaml'}`;
    code.textContent = text;
    pre.appendChild(code);
    details.append(summary, pre);
    return details;
  }

  function buildNotice(text) {
    if (!text) return null;
    const box = doc.createElement('div');
    box.className = 'doc-notice';
    const label = doc.createElement('span');
    label.className = 'doc-notice-text';
    label.textContent = text;
    const close = doc.createElement('button');
    close.type = 'button';
    close.className = 'doc-notice-close';
    close.setAttribute('aria-label', t('findClose'));
    close.textContent = '✕';
    box.append(label, close);
    return box;
  }

  function buildEmptyState() {
    const box = doc.createElement('div');
    box.className = 'doc-empty';
    const title = doc.createElement('h2');
    title.textContent = t('welcome');
    const hint = doc.createElement('p');
    hint.textContent = t('tocEmpty');
    box.append(title, hint);
    return box;
  }

  function clearArticle() {
    while (el.article.firstChild) el.article.removeChild(el.article.firstChild);
  }

  /** Sichtbare Ueberschriften (ohne Fussnoten-Label, Frontmatter, Leerzustand). */
  function collectHeadings() {
    return Array.from(el.article.querySelectorAll(HEADING_SELECTOR)).filter(
      (heading) => !heading.matches(HIDDEN_HEADING) && !heading.closest(HIDDEN_HEADING),
    );
  }

  function computeStats() {
    const text = el.article.textContent ?? '';
    const words = text.trim() ? text.trim().split(/\s+/u).length : 0;
    return {
      words,
      characters: text.length,
      readingMinutes: words > 0 ? Math.max(1, Math.round(words / 200)) : 0,
      headings: collectHeadings().length,
      codeBlocks: el.article.querySelectorAll('pre').length,
      tables: el.article.querySelectorAll('table').length,
      images: el.article.querySelectorAll('img').length,
      // ohne die von uns ergaenzten Abschnitts-Anker
      links: el.article.querySelectorAll('a[href]:not(.heading-anchor)').length,
    };
  }

  function formatNumber(value) {
    const locale = state.settings.language === 'en' ? 'en-US' : 'de-DE';
    try {
      return Number(value ?? 0).toLocaleString(locale);
    } catch {
      return String(value ?? 0);
    }
  }

  /** Fusszeile mit Dokumentstatistik (Vorlage kommt aus Python/i18n). */
  function renderFooter(stats) {
    const template = state.payload?.footer;
    if (!template) {
      el.footer.textContent = '';
      el.footer.hidden = true;
      return;
    }
    const values = {
      words: formatNumber(stats.words),
      characters: formatNumber(stats.characters),
      minutes: stats.readingMinutes,
      headings: formatNumber(stats.headings),
      codeBlocks: formatNumber(stats.codeBlocks),
      file: state.payload?.fileName ?? '',
    };
    el.footer.textContent = String(template).replace(/\{(\w+)\}/g, (match, key) =>
      Object.prototype.hasOwnProperty.call(values, key) ? String(values[key]) : match,
    );
    el.footer.hidden = false;
  }

  function render() {
    const result = renderDocument(state.markdown, state.options);
    state.render = result;
    setBaseHref(state.baseHref);
    applyContentPolicy();

    const fragment = buildFragment(result.html);
    clearArticle();
    el.article.classList.toggle('is-welcome', state.kind === 'welcome');
    el.article.classList.toggle('has-front-matter', Boolean(result.frontMatter));

    const notice = state.settings.notices ? buildNotice(state.payload?.notice) : null;
    if (notice) el.article.appendChild(notice);
    if (result.frontMatter) {
      el.article.appendChild(buildFrontMatterBlock(result.frontMatter, result.frontMatterFormat));
    }
    el.article.appendChild(fragment);
    if (result.isEmpty) el.article.appendChild(buildEmptyState());

    resetFind();
    buildToc();
    const stats = computeStats();
    renderFooter(stats);
    if (state.kind === 'welcome') {
      el.sidebar.hidden = true;
    } else {
      el.sidebar.hidden = !state.settings.tocVisible;
    }

    emit({
      type: 'rendered',
      documentKind: state.kind,
      hasMath: result.hasMath,
      empty: result.isEmpty,
      firstHeading: state.headings.length ? state.headings[0].text : null,
      stats,
    });

    if (result.hasMath) {
      ensureKatex()
        .then((ok) => {
          if (ok && !renderMathElement()) {
            win.console?.error?.('[md-viewer] Mathematik konnte nicht gesetzt werden');
            emit({ type: 'warning', message: 'KaTeX: Satz fehlgeschlagen' });
          }
        })
        .catch((error) => {
          win.console?.error?.('[md-viewer] KaTeX konnte nicht geladen werden', error);
          emit({ type: 'warning', message: `KaTeX: ${error?.message ?? error}` });
        });
    }
    return result;
  }

  // ------------------------------------------------------------------- KaTeX

  function loadScript(url) {
    return new Promise((resolve, reject) => {
      const script = doc.createElement('script');
      script.src = url;
      script.async = true;
      script.addEventListener('load', () => resolve(true));
      script.addEventListener('error', () => reject(new Error(`Konnte ${url} nicht laden`)));
      doc.head.appendChild(script);
    });
  }

  function setStyleLinkEnabled(id, enabled) {
    const link = doc.getElementById(id);
    if (!link) return;
    if (enabled) link.removeAttribute('disabled');
    else link.setAttribute('disabled', '');
  }

  function ensureKatex() {
    if (state.katexReady) return Promise.resolve(true);
    if (state.katexLoading) return state.katexLoading;
    state.katexLoading = (async () => {
      try {
        await loadScript(assetUrl('vendor/katex/katex.min.js'));
        await loadScript(assetUrl('vendor/katex/auto-render.min.js'));
      } catch (error) {
        state.katexLoading = null;
        win.console?.error?.('[md-viewer] vendor/katex nicht ladbar', error);
        return false;
      }
      setStyleLinkEnabled('css-katex', true);
      state.katexReady = true;
      return true;
    })();
    return state.katexLoading;
  }

  function renderMathElement() {
    const renderer = win.renderMathInElement ?? win.katex?.renderMathInElement;
    if (typeof renderer !== 'function') return false;
    const delimiters = [
      { left: '$$', right: '$$', display: true },
      { left: '\\[', right: '\\]', display: true },
      { left: '\\(', right: '\\)', display: false },
    ];
    if (state.options.mathInline) delimiters.push({ left: '$', right: '$', display: false });
    try {
      renderer(el.article, {
        delimiters,
        throwOnError: false,
        errorColor: '#cf222e',
        ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option'],
        ignoredClasses: ['heading-anchor', 'code-copy', 'doc-notice'],
      });
      return true;
    } catch {
      return false;
    }
  }

  // --------------------------------------------------------------------- TOC

  function buildToc() {
    el.toc.textContent = '';
    state.headings = [];
    state.activeHeading = -1;

    const headings = collectHeadings().filter((heading) => heading.id);
    state.headings = headings.map((heading) => ({
      id: heading.id,
      level: Number(heading.tagName.slice(1)),
      text: (heading.textContent ?? '').trim(),
    }));

    if (!state.headings.length) {
      const empty = doc.createElement('p');
      empty.className = 'toc-empty';
      empty.textContent = t('tocEmpty');
      el.toc.appendChild(empty);
      el.tocTitle.textContent = t('tocTitle');
      return;
    }

    const minLevel = Math.min(...state.headings.map((h) => h.level));
    for (const heading of state.headings) {
      const link = doc.createElement('a');
      link.className = 'toc-link';
      link.setAttribute('href', `#${heading.id}`);
      link.setAttribute('data-target', heading.id);
      link.setAttribute('title', heading.text);
      link.style.setProperty('--level', String(heading.level - minLevel));
      link.classList.toggle('toc-level-1', heading.level === minLevel);
      link.textContent = heading.text || heading.id;
      el.toc.appendChild(link);
    }
    el.tocTitle.textContent = t('tocTitle');
  }

  function scrollToTop(top) {
    try {
      el.content.scrollTo({ top, behavior: 'smooth' });
    } catch {
      try {
        el.content.scrollTop = top;
      } catch {
        /* jsdom & Co. */
      }
    }
  }

  function scrollToId(id) {
    if (!id) return false;
    const target = el.article.querySelector(`#${cssEscape(id)}`) ?? doc.getElementById(id);
    if (!target) return false;
    const contentTop = el.content.getBoundingClientRect?.().top ?? 0;
    const top = (target.getBoundingClientRect?.().top ?? 0) - contentTop + (el.content.scrollTop ?? 0) - 16;
    scrollToTop(Math.max(0, top));
    setActiveHeading(state.headings.findIndex((h) => h.id === id));
    return true;
  }

  function cssEscape(value) {
    if (win.CSS?.escape) return win.CSS.escape(value);
    return String(value).replace(/["\\]/g, '\\$&');
  }

  function setActiveHeading(index) {
    if (index === state.activeHeading) return;
    state.activeHeading = index;
    const links = el.toc.querySelectorAll('.toc-link');
    links.forEach((link, i) => link.classList.toggle('is-active', i === index));
    links[index]?.scrollIntoView?.({ block: 'nearest' });
  }

  function updateActiveHeading() {
    if (!state.headings.length) return;
    const contentTop = el.content.getBoundingClientRect?.().top ?? 0;
    const tops = state.headings.map((heading) => {
      const node = el.article.querySelector(`#${cssEscape(heading.id)}`);
      return (node?.getBoundingClientRect?.().top ?? 0) - contentTop;
    });
    const atBottom =
      (el.content.scrollTop ?? 0) + (el.content.clientHeight ?? 0) >= (el.content.scrollHeight ?? 0) - 24;
    const index = atBottom && tops.length ? tops.length - 1 : pickActiveHeading(tops, 24);
    setActiveHeading(index);
  }

  function onScroll() {
    if (state.scrollScheduled) return;
    state.scrollScheduled = true;
    const run = () => {
      state.scrollScheduled = false;
      updateActiveHeading();
    };
    if (typeof win.requestAnimationFrame === 'function') win.requestAnimationFrame(run);
    else run();
  }

  // ------------------------------------------------------------------ Suche

  function findTextNodes(root) {
    const nodes = [];
    const skip = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'MARK']);
    const walker = doc.createTreeWalker(root, 4 /* NodeFilter.SHOW_TEXT */, {
      acceptNode(node) {
        if (!node.nodeValue?.trim()) return 2 /* REJECT */;
        let parent = node.parentElement;
        while (parent) {
          if (skip.has(parent.tagName)) return 2;
          if (parent.classList.contains('code-copy')) return 2;
          parent = parent.parentElement;
        }
        return 1 /* ACCEPT */;
      },
    });
    while (walker.nextNode()) nodes.push(walker.currentNode);
    return nodes;
  }

  function resetFind() {
    for (const mark of state.hits) {
      const parent = mark.parentNode;
      if (!parent) continue;
      parent.replaceChild(doc.createTextNode(mark.textContent ?? ''), mark);
      parent.normalize?.();
    }
    state.hits = [];
    state.hitIndex = -1;
    updateFindCount();
  }

  function updateFindCount() {
    if (!el.findCount) return;
    const total = state.hits.length;
    if (!total) {
      el.findCount.textContent = state.findQuery ? t('findNoHits') : '';
      el.findCount.classList.add('is-empty');
      return;
    }
    el.findCount.classList.remove('is-empty');
    el.findCount.textContent =
      total === 1 ? t('findOne') : t('findCount', { current: state.hitIndex + 1, total });
  }

  function runFind(query) {
    state.findQuery = query ?? '';
    resetFind();
    if (!state.findQuery.trim()) {
      updateFindCount();
      return 0;
    }
    const needle = state.findQuery.toLocaleLowerCase();
    for (const node of findTextNodes(el.article)) {
      const text = node.nodeValue ?? '';
      const haystack = text.toLocaleLowerCase();
      let index = haystack.indexOf(needle);
      if (index === -1) continue;
      const fragment = doc.createDocumentFragment();
      let cursor = 0;
      while (index !== -1) {
        if (index > cursor) fragment.appendChild(doc.createTextNode(text.slice(cursor, index)));
        const mark = doc.createElement('mark');
        mark.className = 'search-hit';
        mark.textContent = text.slice(index, index + needle.length);
        fragment.appendChild(mark);
        state.hits.push(mark);
        cursor = index + needle.length;
        index = haystack.indexOf(needle, cursor);
      }
      if (cursor < text.length) fragment.appendChild(doc.createTextNode(text.slice(cursor)));
      node.parentNode?.replaceChild(fragment, node);
    }
    state.hitIndex = state.hits.length ? 0 : -1;
    focusHit(0);
    return state.hits.length;
  }

  function focusHit(index) {
    if (!state.hits.length) {
      updateFindCount();
      return;
    }
    const total = state.hits.length;
    state.hitIndex = ((index % total) + total) % total;
    state.hits.forEach((mark, i) => mark.classList.toggle('is-current', i === state.hitIndex));
    const current = state.hits[state.hitIndex];
    const contentTop = el.content.getBoundingClientRect?.().top ?? 0;
    const top =
      (current.getBoundingClientRect?.().top ?? 0) - contentTop + (el.content.scrollTop ?? 0) - (el.content.clientHeight ?? 0) / 3;
    scrollToTop(Math.max(0, top));
    updateFindCount();
  }

  function openFind() {
    el.findbar.hidden = false;
    el.findInput.focus?.();
    el.findInput.select?.();
    if (state.findQuery) runFind(state.findQuery);
    return state.hits.length;
  }

  function closeFind() {
    el.findbar.hidden = true;
    resetFind();
    state.findQuery = '';
    el.findInput.value = '';
    updateFindCount();
  }

  // ---------------------------------------------------------------- Lightbox

  function openLightbox(img) {
    const src = img.getAttribute('src') ?? '';
    if (!src) return;
    el.lightboxImage.setAttribute('src', src);
    el.lightboxImage.setAttribute('alt', img.getAttribute('alt') ?? '');
    const caption = img.getAttribute('alt') ?? '';
    el.lightboxCaption.textContent = caption;
    el.lightboxCaption.hidden = !caption;
    el.lightbox.hidden = false;
  }

  function closeLightbox() {
    el.lightbox.hidden = true;
    el.lightboxImage.removeAttribute('src');
  }

  function unblockImage(img) {
    const src = img.getAttribute('data-src');
    if (!src) return false;
    img.setAttribute('src', src);
    img.removeAttribute('data-src');
    img.removeAttribute('data-blocked');
    img.setAttribute('data-lightbox', '1');
    img.removeAttribute('title');
    return true;
  }

  // -------------------------------------------------------------- Interaktion

  function toast(message, timeout = 2600) {
    if (!message) return;
    el.toast.textContent = message;
    el.toast.hidden = false;
    el.toast.classList.add('is-visible');
    if (state.toastTimer) win.clearTimeout(state.toastTimer);
    state.toastTimer = win.setTimeout(() => {
      el.toast.classList.remove('is-visible');
      el.toast.hidden = true;
    }, timeout);
    return message;
  }

  function resolveFileUrl(href) {
    try {
      return new win.URL(href, state.baseHref || state.fileUrl || undefined).href;
    } catch {
      return null;
    }
  }

  /** Kopieren: erst klassisch (WebKit), dann Clipboard-API, zuletzt GTK via Python. */
  function copyText(text) {
    if (!text) return false;
    try {
      const area = doc.createElement('textarea');
      area.value = text;
      area.setAttribute('readonly', '');
      area.className = 'clipboard-helper';
      area.style.setProperty('position', 'fixed');
      area.style.setProperty('top', '-1000px');
      doc.body.appendChild(area);
      area.select();
      const copied = typeof doc.execCommand === 'function' ? doc.execCommand('copy') : false;
      area.remove();
      if (copied) return true;
    } catch {
      /* weiter unten */
    }
    try {
      const clipboard = win.navigator?.clipboard;
      if (clipboard?.writeText) {
        clipboard.writeText(text).catch(() => emit({ type: 'copy-text', text }));
        return true;
      }
    } catch {
      /* weiter unten */
    }
    emit({ type: 'copy-text', text });
    return true;
  }

  function onArticleClick(event) {
    const target = event.target;
    if (!target || typeof target.closest !== 'function') return;

    const copyButton = target.closest('.code-copy');
    if (copyButton) {
      const code = copyButton.parentElement?.querySelector('code');
      const ok = copyText(code?.textContent ?? '');
      copyButton.textContent = ok ? '✓' : t('copy');
      win.setTimeout(() => {
        copyButton.textContent = t('copy');
      }, 1600);
      toast(ok ? t('copied') : t('copyFailed'));
      return;
    }

    const img = target.closest('img');
    if (img && img.getAttribute('data-blocked') === '1') {
      event.preventDefault();
      unblockImage(img);
      return;
    }

    const anchor = target.closest('a');
    if (!anchor) {
      if (img) openLightbox(img);
      return;
    }
    const href = anchor.getAttribute('href') ?? '';
    if (anchor.classList.contains('heading-anchor')) {
      event.preventDefault();
      scrollToId(anchor.getAttribute('href').slice(1));
      copyText(`${state.fileUrl || state.baseHref || ''}${anchor.getAttribute('href')}`);
      toast(t('anchorCopied'));
      return;
    }
    if (href.startsWith('#')) {
      event.preventDefault();
      scrollToId(decodeURIComponent(href.slice(1)));
      return;
    }
    if (!href) return;
    event.preventDefault();
    if (EXTERNAL_URL.test(href)) {
      emit({ type: 'open-external', url: href });
      return;
    }
    const resolved = resolveFileUrl(href);
    if (!resolved) return;
    if (resolved.startsWith('file:') && MARKDOWN_FILE.test(resolved)) {
      emit({ type: 'open-path', url: resolved });
    } else {
      emit({ type: 'open-external', url: resolved });
    }
  }

  function onTocClick(event) {
    const link = event.target?.closest?.('.toc-link');
    if (!link) return;
    event.preventDefault();
    scrollToId(link.getAttribute('data-target'));
  }

  function onKeyDown(event) {
    const key = event.key;
    if (key === 'Escape') {
      if (!el.lightbox.hidden) {
        closeLightbox();
        return;
      }
      if (!el.findbar.hidden) {
        closeFind();
        return;
      }
    }
    const inFind = event.target === el.findInput;
    if (key === 'Enter' && inFind) {
      event.preventDefault();
      focusHit(state.hitIndex + (event.shiftKey ? -1 : 1));
      return;
    }
    if ((event.ctrlKey || event.metaKey) && (key === 'f' || key === 'F')) {
      event.preventDefault();
      openFind();
      return;
    }
    if (key === 'F3') {
      event.preventDefault();
      focusHit(state.hitIndex + (event.shiftKey ? -1 : 1));
    }
  }

  function bindEvents() {
    el.article.addEventListener('click', onArticleClick);
    el.toc.addEventListener('click', onTocClick);
    el.content.addEventListener('scroll', onScroll, { passive: true });
    el.findInput.addEventListener('input', () => runFind(el.findInput.value));
    el.findNext.addEventListener('click', () => focusHit(state.hitIndex + 1));
    el.findPrev.addEventListener('click', () => focusHit(state.hitIndex - 1));
    el.findClose.addEventListener('click', closeFind);
    el.lightbox.addEventListener('click', (event) => {
      if (event.target === el.lightbox || event.target === el.lightboxImage) closeLightbox();
    });
    el.article.addEventListener('click', (event) => {
      const noticeClose = event.target?.closest?.('.doc-notice-close');
      if (noticeClose) noticeClose.closest('.doc-notice')?.remove();
    });
    doc.addEventListener('keydown', onKeyDown);
  }

  // ---------------------------------------------------------------- Einstellungen

  function setTheme(theme) {
    state.settings.theme = theme ?? 'auto';
    applyTheme();
  }

  function resolveTheme() {
    if (state.settings.theme !== 'auto') return state.settings.theme;
    const prefersDark = win.matchMedia?.('(prefers-color-scheme: dark)')?.matches;
    return prefersDark ? 'dark' : 'light';
  }

  function applyTheme() {
    const resolved = resolveTheme();
    doc.documentElement.setAttribute('data-theme', resolved);
    try {
      doc.documentElement.style.colorScheme = resolved;
    } catch {
      /* ignorieren */
    }
    setStyleLinkEnabled('css-md-dark', resolved === 'dark');
    setStyleLinkEnabled('css-md-light', resolved !== 'dark');
    setStyleLinkEnabled('css-hl-dark', resolved === 'dark');
    setStyleLinkEnabled('css-hl-light', resolved !== 'dark');
    if (state.katexReady) setStyleLinkEnabled('css-katex', true);
  }

  /** Zeilenbreite setzen (normal / wide / full) - reine CSS-Aenderung. */
  function applyLineWidth(width) {
    const key = Object.prototype.hasOwnProperty.call(LINE_WIDTHS, width) ? width : 'normal';
    state.settings.lineWidth = key;
    const target = doc.documentElement;
    if (target?.style?.setProperty) target.style.setProperty('--content-max', LINE_WIDTHS[key]);
    return key;
  }

  /** Zoom (in Prozent) ohne Neu-Rendern setzen. */
  function setZoom(percent) {
    const value = Number(percent);
    if (Number.isFinite(value)) {
      state.settings.zoom = Math.max(50, Math.min(250, Math.round(value)));
    }
    el.article.style.setProperty('zoom', String(state.settings.zoom / 100));
    return state.settings.zoom;
  }

  function applySettings(next = {}) {
    const previous = { ...state.settings, options: { ...state.options } };
    if (next.language) setLanguage(next.language);
    if (next.theme) state.settings.theme = next.theme;
    if (typeof next.zoom === 'number') state.settings.zoom = next.zoom;
    if (typeof next.tocVisible === 'boolean') state.settings.tocVisible = next.tocVisible;
    if (typeof next.lineWidth === 'string') applyLineWidth(next.lineWidth);
    if (typeof next.blockRemoteImages === 'boolean') state.settings.blockRemoteImages = next.blockRemoteImages;
    if (typeof next.notices === 'boolean') state.settings.notices = next.notices;
    for (const key of Object.keys(DEFAULT_RENDER_OPTIONS)) {
      if (typeof next[key] === 'boolean') state.options[key] = next[key];
    }

    applyTheme();
    setZoom(state.settings.zoom);
    if (state.kind !== 'welcome') el.sidebar.hidden = !state.settings.tocVisible;

    const needsRerender =
      previous.breaks !== state.options.breaks ||
      previous.highlight !== state.options.highlight ||
      previous.mathInline !== state.options.mathInline ||
      previous.blockRemoteImages !== state.settings.blockRemoteImages ||
      previous.language !== state.settings.language;
    if (needsRerender && state.payload) render();
    return { ...state.settings, ...state.options };
  }

  // -------------------------------------------------------------------- API

  /** Scrollposition setzen - zweimal, weil WebKit erst nach dem Layout rechnet. */
  function restoreScroll(top) {
    const apply = () => {
      try {
        el.content.scrollTop = top;
      } catch {
        /* jsdom & Co. */
      }
    };
    apply();
    if (typeof win.requestAnimationFrame === 'function') win.requestAnimationFrame(apply);
  }

  function load(payload) {
    state.payload = { ...payload };
    state.kind = payload.kind ?? 'document';
    state.markdown = payload.text ?? '';
    state.baseHref = payload.baseHref ?? '';
    state.fileUrl = payload.url ?? '';
    const keepScroll = Boolean(payload.keepScroll);
    const previousScroll = keepScroll ? (el.content.scrollTop ?? 0) : 0;
    if (payload.settings) applySettings(payload.settings);
    if (payload.renderOptions) {
      for (const key of Object.keys(DEFAULT_RENDER_OPTIONS)) {
        if (typeof payload.renderOptions[key] === 'boolean') state.options[key] = payload.renderOptions[key];
      }
    }
    setZoom(state.settings.zoom);
    el.findbar.hidden = true;
    const result = render();
    if (keepScroll) restoreScroll(previousScroll);
    else restoreScroll(0);
    return { hasMath: result.hasMath, empty: result.isEmpty, zoom: state.settings.zoom };
  }

  function stats() {
    return {
      ...computeStats(),
      headingList: state.headings,
      theme: resolveTheme(),
      hits: state.hits.length,
    };
  }

  function getBodyHtml() {
    return el.article.innerHTML;
  }

  function destroy() {
    if (state.toastTimer) win.clearTimeout(state.toastTimer);
    doc.removeEventListener('keydown', onKeyDown);
  }

  function handleMediaChange() {
    if (state.settings.theme === 'auto') applyTheme();
  }

  bindEvents();
  applyTheme();
  applyLineWidth(state.settings.lineWidth);
  if (typeof win.matchMedia === 'function') {
    const query = win.matchMedia('(prefers-color-scheme: dark)');
    if (query?.addEventListener) query.addEventListener('change', handleMediaChange);
    else if (query?.addListener) query.addListener(handleMediaChange);
  }

  return {
    load,
    render,
    stats,
    toast,
    getBodyHtml,
    setTheme,
    applySettings,
    setZoom,
    applyLineWidth,
    setBaseHref,
    openFind,
    closeFind,
    runFind,
    findNext: () => focusHit(state.hitIndex + 1),
    findPrev: () => focusHit(state.hitIndex - 1),
    scrollToId,
    updateActiveHeading,
    resolveTheme,
    destroy,
    state,
  };
}
