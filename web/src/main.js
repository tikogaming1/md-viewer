/**
 * Einstiegspunkt im WebView.
 *
 * Bruecke zu Python (WebKit2GTK): window.webkit.messageHandlers.app.postMessage(...)
 * Python -> JS: window.MDViewer.* (aufgerufen per evaluate_javascript).
 */
import { createViewer } from './viewer.js';
import { setLanguage } from './i18n.js';

function makeBridge(win) {
  const handler = win.webkit?.messageHandlers?.app;
  return {
    available: Boolean(handler),
    post(message) {
      const payload = typeof message === 'string' ? message : JSON.stringify(message);
      if (!handler) {
        if (win.console?.debug) win.console.debug('[md-viewer] keine Brücke, Nachricht:', payload);
        return false;
      }
      try {
        handler.postMessage(payload);
        return true;
      } catch (error) {
        win.console?.error?.('[md-viewer] postMessage fehlgeschlagen', error);
        return false;
      }
    },
  };
}

const bridge = makeBridge(window);
let viewer = null;

try {
  viewer = createViewer(window, document, {
    emit: (message) => bridge.post(message),
  });
} catch (error) {
  bridge.post({ type: 'error', message: String(error?.message ?? error) });
  throw error;
}

function parse(value) {
  return typeof value === 'string' ? JSON.parse(value) : value;
}

/** Von Python aufgerufene Schnittstelle. */
window.MDViewer = {
  version: '1.0.0',
  ready: false,
  bridgeAvailable: bridge.available,

  /** payload: Objekt oder JSON-String mit dem Dokument */
  load(payload) {
    const result = viewer.load(parse(payload));
    return JSON.stringify(result ?? {});
  },
  setTheme(theme) {
    viewer.setTheme(theme);
    return 'ok';
  },
  setSettings(settings) {
    if (settings && typeof settings === 'object' && settings.language) setLanguage(settings.language);
    viewer.applySettings(parse(settings));
    return 'ok';
  },
  setLanguage(language) {
    setLanguage(language);
    return language;
  },
  setZoom(percent) {
    return String(viewer.setZoom(percent));
  },
  setLineWidth(width) {
    return viewer.applyLineWidth(parse(width));
  },
  openFind() {
    return String(viewer.openFind());
  },
  closeFind() {
    viewer.closeFind();
    return 'ok';
  },
  findNext() {
    viewer.findNext();
    return 'ok';
  },
  findPrev() {
    viewer.findPrev();
    return 'ok';
  },
  scrollTo(id) {
    return String(viewer.scrollToId(id));
  },
  stats() {
    return JSON.stringify(viewer.stats());
  },
  bodyHtml() {
    return viewer.getBodyHtml();
  },
  toast(message) {
    viewer.toast(parse(message));
    return 'ok';
  },
  scrollTop() {
    try {
      document.getElementById('content')?.scrollTo?.({ top: 0 });
    } catch {
      /* ignorieren */
    }
    return 'ok';
  },
};

window.addEventListener('error', (event) => {
  bridge.post({ type: 'error', message: String(event.message ?? event.error ?? 'Unbekannter Fehler') });
});

viewer.applySettings({ theme: 'auto', zoom: 100, tocVisible: true, language: 'de' });

window.MDViewer.ready = true;

if (window.MD_DEMO) {
  // Nur fuer die statische Vorschau (preview/index.html) ohne Python-Bruecke.
  viewer.load(parse(window.MD_DEMO));
  viewer.setTheme(window.MD_DEMO.settings?.theme ?? 'auto');
} else {
  bridge.post({ type: 'ready' });
}

export { viewer };
