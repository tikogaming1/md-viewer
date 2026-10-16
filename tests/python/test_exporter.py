"""Tests fuer den HTML-Export (Einbetten der Styles, absolute Pfade)."""

import re
import tempfile
import unittest
from pathlib import Path

from mdviewer import exporter, i18n


class ExporterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.assets = Path(self.tmp.name) / "vendor"
        (self.assets / "katex" / "fonts").mkdir(parents=True)
        (self.assets / "github-markdown-light.css").write_text(".markdown-body{color:#111}", encoding="utf-8")
        (self.assets / "github-markdown-dark.css").write_text(".markdown-body{color:#eee}", encoding="utf-8")
        (self.assets / "hljs-github.min.css").write_text(".hljs{color:red}", encoding="utf-8")
        (self.assets / "hljs-github-dark.min.css").write_text(".hljs{color:blue}", encoding="utf-8")
        (self.assets / "katex" / "katex.min.css").write_text(
            '@font-face{font-family:KaTeX_Main;src:url(fonts/KaTeX_Main-Regular.woff2) format("woff2"),'
            'url(fonts/KaTeX_Main-Regular.woff) format("woff"),'
            'url(fonts/KaTeX_Main-Regular.ttf) format("truetype")}',
            encoding="utf-8",
        )
        (self.assets / "katex" / "fonts" / "KaTeX_Main-Regular.woff2").write_bytes(b"WOF2-testdata")
        i18n.set_language("de")

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, **kwargs):
        params = {"assets_dir": self.assets}
        params.update(kwargs)
        return exporter.build_standalone_html(
            params.pop("title", "Mein <Titel>"),
            params.pop("body_html", '<h1 id="t">Hallo</h1><p>Text</p>'),
            **params,
        )

    def test_grundgeruest_und_titel_escaped(self):
        html = self.build()
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("<title>Mein &lt;Titel&gt;</title>", html)
        self.assertIn('<article class="markdown-body">', html)
        self.assertIn("<h1 id=\"t\">Hallo</h1>", html)
        self.assertIn('lang="de"', html)
        self.assertIn("MD Viewer", html)

    def test_stylesheets_werden_eingebettet(self):
        html = self.build()
        self.assertIn(".markdown-body{color:#111}", html)
        self.assertIn(".hljs{color:red}", html)
        self.assertNotIn("github-markdown-dark.css", html)

    def test_dunkles_theme_nutzt_dunkle_styles(self):
        html = self.build(theme="dark")
        self.assertIn(".markdown-body{color:#eee}", html)
        self.assertIn(".hljs{color:blue}", html)
        self.assertIn('data-theme="dark"', html)
        self.assertIn("#0d1117", html)

    def test_schriften_werden_eingebettet_und_fallbacks_entfernt(self):
        html = self.build()
        self.assertIn("data:font/woff2;base64,", html)
        self.assertNotIn("KaTeX_Main-Regular.woff)", html)
        self.assertNotIn("KaTeX_Main-Regular.ttf", html)

    def test_ohne_schrifteinbettung_bleiben_verweise(self):
        html = self.build(embed_fonts=False)
        self.assertIn("url(fonts/KaTeX_Main-Regular.woff2)", html)

    def test_relative_pfade_werden_absolut(self):
        body = '<img src="bilder/a.png" alt="x"><a href="kapitel.md">Kapitel</a>'
        html = self.build(body_html=body, base_href="file:///home/user/notizen/")
        self.assertIn('src="file:///home/user/notizen/bilder/a.png"', html)
        self.assertIn('href="file:///home/user/notizen/kapitel.md"', html)

    def test_externe_und_interne_ziele_bleiben_unveraendert(self):
        body = (
            '<a href="https://example.com/x">web</a>'
            '<a href="#abschnitt">intern</a>'
            '<img src="data:image/png;base64,AAA">'
            '<img src="/absolut/pfad.png">'
        )
        html = self.build(body_html=body, base_href="file:///home/user/notizen/")
        self.assertIn('href="https://example.com/x"', html)
        self.assertIn('href="#abschnitt"', html)
        self.assertIn("data:image/png;base64,AAA", html)
        # Wurzel-relative Pfade zeigen in einer lokalen Datei auf das Dateisystem-Wurzelverzeichnis
        self.assertIn('src="file:///absolut/pfad.png"', html)

    def test_ohne_basis_bleiben_pfade_relativ(self):
        html = self.build(body_html='<img src="bild.png">')
        self.assertIn('src="bild.png"', html)

    def test_kopierknoepfe_werden_entfernt(self):
        body = '<div class="code-block"><pre><code>x</code></pre><button class="code-copy" title="Code kopieren">Kopieren</button></div>'
        html = self.build(body_html=body)
        self.assertNotIn("code-copy", html)
        self.assertIn("<pre><code>x</code></pre>", html)

    def test_quelle_und_zeitstempel_in_der_fusszeile(self):
        html = self.build(source_path="/home/user/notizen/a.md")
        self.assertIn("export-meta", html)
        self.assertIn("/home/user/notizen/a.md", html)
        self.assertRegex(html, r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}")

    def test_unbekanntes_theme_faellt_auf_hell_zurueck(self):
        html = self.build(theme="neon")
        self.assertIn('data-theme="light"', html)

    def test_dateiname_vorschlag(self):
        self.assertEqual(exporter.suggested_file_name("/a/b/notizen.md"), "notizen.html")
        self.assertEqual(exporter.suggested_file_name("README"), "README.html")
        self.assertEqual(exporter.suggested_file_name(""), "dokument.html")

    def test_write_html_ergaenzt_endung_und_schreibt_utf8(self):
        target = Path(self.tmp.name) / "ausgabe"
        written = exporter.write_html(target, "<html>äöü</html>")
        self.assertEqual(written.name, "ausgabe.html")
        self.assertEqual(written.read_text(encoding="utf-8"), "<html>äöü</html>")

        wieder = exporter.write_html(Path(self.tmp.name) / "schon.html", "<html>x</html>")
        self.assertEqual(wieder.name, "schon.html")


if __name__ == "__main__":
    unittest.main()
