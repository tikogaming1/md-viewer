"""Export: aus dem gerenderten HTML eine eigenstaendige HTML-Datei bauen.

Die Datei enthaelt alle Stylesheets (GitHub-Markdown, highlight.js, KaTeX inklusive
eingebetteter Schriften) und ist damit offline und ohne Zusatzdateien benutzbar.
"""

from __future__ import annotations

import base64
import datetime
import html
import re
from pathlib import Path

from . import APP_NAME, __version__, i18n, paths

THEME_CSS = {
    "light": "github-markdown-light.css",
    "dark": "github-markdown-dark.css",
}
HIGHLIGHT_CSS = {
    "light": "hljs-github.min.css",
    "dark": "hljs-github-dark.min.css",
}
KATEX_CSS = "katex/katex.min.css"

#: KaTeX-Schriftverweise (url(fonts/KaTeX_...woff2))
FONT_URL = re.compile(r"""url\((?P<quote>["']?)fonts/(?P<name>[A-Za-z0-9_.-]+\.woff2)(?P=quote)\)""")
#: Nicht mitgelieferte Fallback-Formate (woff/ttf) entfernen
FONT_FALLBACK = re.compile(r""",\s*url\([^)]*\.(?:woff|ttf)(?:[?#][^)]*)?\)(?:\s*format\([^)]*\))?""")

COPY_BUTTON = re.compile(r"""<button\b[^>]*class="[^"]*code-copy[^"]*"[^>]*>.*?</button>""", re.S)
URL_ATTRIBUTE = re.compile(r"""(?P<attr>\b(?:src|href))\s*=\s*(?P<quote>["'])(?P<url>[^"']*)(?P=quote)""")

_EXTERNAL_PREFIXES = ("#", "data:", "http://", "https://", "mailto:", "tel:", "file:", "blob:", "//")

_LAYOUT_CSS = """
/* --- MD Viewer: Export-Layout (ergaenzt die GitHub-Styles) --- */
html {{ color-scheme: {scheme}; }}
body {{
  margin: 0;
  background: {background};
  color: {foreground};
}}
.markdown-body {{
  max-width: 1012px;
  margin: 0 auto;
  padding: 40px 32px 64px;
  background-color: transparent;
}}
.markdown-body .code-block {{ position: relative; }}
.markdown-body .heading-anchor {{ text-decoration: none; opacity: .35; }}
.markdown-body .heading-anchor::after {{ content: '¶'; font-size: .85em; }}
.markdown-body .heading-anchor:hover {{ opacity: 1; }}
.markdown-body .front-matter {{
  border: 1px solid {border};
  border-radius: 6px;
  background: {panel};
  margin-bottom: 24px;
}}
.markdown-body .front-matter summary {{ cursor: pointer; padding: 8px 14px; font-size: 12px; font-weight: 600; }}
.markdown-body .front-matter pre {{ margin: 0; border-radius: 0 0 6px 6px; }}
.markdown-body .doc-notice {{
  display: flex;
  gap: 12px;
  margin: 0 0 24px;
  padding: 10px 14px;
  border: 1px solid {border};
  border-radius: 8px;
  background: {panel};
  font-size: 13px;
}}
.markdown-body .doc-notice-close {{ display: none; }}
.export-meta {{
  max-width: 1012px;
  margin: 0 auto;
  padding: 0 32px 48px;
  color: {muted};
  font-size: 12px;
  font-family: sans-serif;
}}
@media print {{
  .markdown-body {{ max-width: none; padding: 0; }}
  .export-meta {{ display: none; }}
}}
"""

_COLORS = {
    "light": {"scheme": "light", "background": "#ffffff", "foreground": "#1f2328", "border": "#d0d7de", "panel": "#f6f8fa", "muted": "#59636e"},
    "dark": {"scheme": "dark", "background": "#0d1117", "foreground": "#e6edf3", "border": "#3d444d", "panel": "#151b23", "muted": "#9198a1"},
}


def _read_css(name: str, assets_dir: Path) -> str:
    try:
        return (assets_dir / name).read_text(encoding="utf-8")
    except OSError:
        return ""


def inline_fonts(css: str, fonts_dir: Path) -> str:
    """Betten woff2-Schriften als data:-URI ein (macht den Export eigenstaendig)."""

    def replace(match: re.Match[str]) -> str:
        font_file = fonts_dir / match.group("name")
        try:
            payload = base64.b64encode(font_file.read_bytes()).decode("ascii")
        except OSError:
            return match.group(0)
        return f'url("data:font/woff2;base64,{payload}")'

    css = FONT_URL.sub(replace, css)
    return FONT_FALLBACK.sub("", css)


def absolutize_relative_urls(body_html: str, base_href: str | None) -> str:
    """Relative Bild-/Linkpfade in absolute Datei-URLs umwandeln.

    Damit funktioniert die exportierte Datei auch, wenn sie in einem anderen
    Ordner als das Originaldokument liegt.
    """
    if not base_href:
        return body_html

    from urllib.parse import urljoin

    def replace(match: re.Match[str]) -> str:
        url = match.group("url")
        if not url or url.startswith(_EXTERNAL_PREFIXES):
            return match.group(0)
        absolute = urljoin(base_href, url)
        return f'{match.group("attr")}={match.group("quote")}{html.escape(absolute, quote=True)}{match.group("quote")}'

    return URL_ATTRIBUTE.sub(replace, body_html)


def build_standalone_html(
    title: str,
    body_html: str,
    *,
    theme: str = "light",
    language: str | None = None,
    base_href: str | None = None,
    source_path: str | None = None,
    assets_dir: Path | None = None,
    embed_fonts: bool = True,
) -> str:
    """Baut das komplette HTML-Dokument fuer den Export."""
    theme = theme if theme in THEME_CSS else "light"
    language = language or i18n.get_language()
    assets = Path(assets_dir) if assets_dir else paths.web_dir() / "vendor"

    parts = [
        _read_css(THEME_CSS[theme], assets),
        _read_css(HIGHLIGHT_CSS[theme], assets),
    ]
    katex = _read_css(KATEX_CSS, assets)
    if katex and embed_fonts:
        katex = inline_fonts(katex, assets / "katex" / "fonts")
    parts.append(katex)
    parts.append(_LAYOUT_CSS.format(**_COLORS[theme]))

    style = "\n".join(part for part in parts if part.strip())
    body = absolutize_relative_urls(COPY_BUTTON.sub("", body_html), base_href)

    meta_line = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
    source = f" · {html.escape(source_path)}" if source_path else ""
    generator = f"{APP_NAME} {__version__}"

    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{html.escape(language)}" data-theme="{theme}">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta name="generator" content="{html.escape(generator)}">\n'
        f"<title>{html.escape(title)}</title>\n"
        "<style>\n"
        f"{style}\n"
        "</style>\n"
        "</head>\n"
        "<body>\n"
        f'<article class="markdown-body">\n{body}\n</article>\n'
        f'<footer class="export-meta">{generator} · {meta_line}{source}</footer>\n'
        "</body>\n"
        "</html>\n"
    )


def suggested_file_name(source_path: str | Path) -> str:
    """``/pfad/notiz.md`` -> ``notiz.html``."""
    stem = Path(source_path).stem or "dokument"
    return f"{stem}.html"


def write_html(path: str | Path, content: str) -> Path:
    """Schreibt die Export-Datei (UTF-8) und liefert den Pfad zurueck."""
    target = Path(path).expanduser()
    if target.suffix.lower() not in {".html", ".htm"}:
        target = target.with_suffix(".html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target
