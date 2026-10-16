/**
 * Texte der Viewer-Oberflaeche (die Fenster-/Menue-Texte liegen in Python,
 * src/mdviewer/i18n.py). Sprache wird von Python ueber setSettings() gesetzt.
 */
const STRINGS = {
  de: {
    tocTitle: 'Inhaltsverzeichnis',
    tocEmpty: 'Keine Überschriften im Dokument',
    showToc: 'Inhaltsverzeichnis',
    noticeTitle: 'Hinweis',
    findTitle: 'Im Dokument suchen',
    findPlaceholder: 'Suchbegriff …',
    findNext: 'Weitersuchen (Enter)',
    findPrev: 'Zurück (Umschalt+Enter)',
    findClose: 'Suche schließen (Esc)',
    findNoHits: 'Keine Treffer',
    findCount: '{current} von {total} Treffern',
    findOne: '1 Treffer',
    copy: 'Kopieren',
    copied: 'In die Zwischenablage kopiert',
    copyFailed: 'Kopieren nicht möglich',
    copyCode: 'Code kopieren',
    anchorCopy: 'Abschnittslink kopieren',
    anchorCopied: 'Link zu diesem Abschnitt kopiert',
    openExternal: 'Im Browser öffnen',
    openLinkedDoc: 'Dokument öffnen',
    frontMatter: 'Frontmatter',
    imageBlocked: 'Externes Bild blockiert – zum Laden klicken',
    imageBlockedShort: 'Externes Bild blockiert',
    imageCaption: 'Bild',
    closeOverlay: 'Schließen (Esc)',
    zoomIn: 'Vergrößern',
    zoomOut: 'Verkleinern',
    welcome: 'Willkommen',
    tableOfContentsShort: 'Übersicht',
    linksExternal: 'Externer Link',
    loading: 'Lade Dokument …',
    themeLight: 'Hell',
    themeDark: 'Dunkel',
  },
  en: {
    tocTitle: 'Table of contents',
    tocEmpty: 'No headings in this document',
    showToc: 'Table of contents',
    noticeTitle: 'Note',
    findTitle: 'Find in document',
    findPlaceholder: 'Search …',
    findNext: 'Next match (Enter)',
    findPrev: 'Previous (Shift+Enter)',
    findClose: 'Close search (Esc)',
    findNoHits: 'No matches',
    findCount: '{current} of {total} matches',
    findOne: '1 match',
    copy: 'Copy',
    copied: 'Copied to clipboard',
    copyFailed: 'Copying failed',
    copyCode: 'Copy code',
    anchorCopy: 'Copy link to this section',
    anchorCopied: 'Link to this section copied',
    openExternal: 'Open in browser',
    openLinkedDoc: 'Open document',
    frontMatter: 'Frontmatter',
    imageBlocked: 'Remote image blocked – click to load',
    imageBlockedShort: 'Remote image blocked',
    imageCaption: 'Image',
    closeOverlay: 'Close (Esc)',
    zoomIn: 'Zoom in',
    zoomOut: 'Zoom out',
    welcome: 'Welcome',
    tableOfContentsShort: 'Overview',
    linksExternal: 'External link',
    loading: 'Loading document …',
    themeLight: 'Light',
    themeDark: 'Dark',
  },
};

let activeLanguage = 'de';

export function setLanguage(language) {
  activeLanguage = STRINGS[language] ? language : 'de';
  return activeLanguage;
}

export function getLanguage() {
  return activeLanguage;
}

export function t(key, replacements = {}) {
  const table = STRINGS[activeLanguage] ?? STRINGS.de;
  let value = table[key] ?? STRINGS.de[key] ?? key;
  for (const [name, replacement] of Object.entries(replacements)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

export { STRINGS };
