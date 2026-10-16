"""Fenster- und Anwendungslogik mit einer gi-Attrappe (ohne echte GTK-Oberflaeche).

Damit laufen die GTK-Pfade hier auch ohne X11/Wayland: Tabs, Statusleiste,
Datei oeffnen, Nachrichten vom Viewer, Export, Live-Neuladen, Sprachwechsel.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

# gi-Attrappe vor allen mdviewer-Importen bereitstellen
STUBS = Path(__file__).resolve().parent / "stubs"
if str(STUBS) not in sys.path:
    sys.path.insert(0, str(STUBS))

from mdviewer import compat, i18n, welcome  # noqa: E402
from mdviewer.settings import Settings  # noqa: E402
from mdviewer.viewer_page import ViewerPage, build_payload, document_payload, js_literal  # noqa: E402
from mdviewer.window import MainWindow  # noqa: E402


class ToolkitMixin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.toolkit = compat.load_toolkit()
        cls.toolkit.Gtk.init([])


class PayloadTest(unittest.TestCase):
    def test_js_literal_escaped_zeilentrenner(self):
        text = js_literal({"text": "a\u2028b"})
        self.assertIn("\\u2028", text)
        self.assertNotIn("\u2028", text)
        json.loads(text.replace("\\u2028", " "))  # bleibt gueltiges JSON

    def test_nutzlast_enthaelt_alles_noetige(self):
        payload = build_payload(
            kind="document",
            text="# Titel",
            path="/a/b.md",
            file_name="b.md",
            base_href="file:///a/",
            url="file:///a/b.md",
            encoding="utf-8",
            settings={"theme": "dark"},
            render_options={"breaks": True},
        )
        self.assertEqual(payload["kind"], "document")
        self.assertEqual(payload["fileName"], "b.md")
        self.assertEqual(payload["baseHref"], "file:///a/")
        self.assertTrue(payload["renderOptions"]["breaks"])
        self.assertFalse(payload["keepScroll"])
        # None-Werte werden weggelassen
        self.assertNotIn("notice", payload)

    def test_document_payload_aus_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notiz.md"
            path.write_text("Grüße\n", encoding="cp1252")
            from mdviewer.documents import read_document

            document = read_document(path)
            settings = Settings(Path(tmp) / "settings.json").load()
            payload = document_payload(document, settings=settings, footer="X")
            self.assertEqual(payload["fileName"], "notiz.md")
            self.assertTrue(payload["baseHref"].endswith("/"))
            self.assertEqual(payload["footer"], "X")
            self.assertIn("cp1252", payload["notice"])
            self.assertIn("settings", payload)


class WindowTest(ToolkitMixin):
    def load_pages(self):
        """Simuliert das 'load-changed: FINISHED' des WebViews."""
        for tab in self.window.tabs:
            tab.page.webview.emit("load-changed", self.toolkit.WebKit.LoadEvent.FINISHED)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.settings = Settings(self.dir / "settings.json").load()
        i18n.set_language("de")
        self.application = self.toolkit.Gtk.Application(application_id="de.tikogaming.MDViewerTest")
        self.window = MainWindow(self.application, self.toolkit, self.settings)
        self.window.present(welcome_doc=True)
        self.load_pages()

    def tearDown(self):
        self.tmp.cleanup()

    def make_file(self, name="notiz.md", text="# Titel\n\nHallo Welt\n"):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def assertScript(self, tab, needle):
        """Prueft, ob irgendein an den Viewer gesendetes Skript den Text enthaelt."""
        scripts = "\n".join(tab.page.webview.scripts)
        self.assertIn(needle, scripts, f"{needle!r} fehlt in den Skriptaufrufen")

    def open(self, path, **kwargs):
        """Oeffnet eine Datei und markiert die Seite als geladen."""
        tab = self.window.open_path(path, **kwargs)
        self.load_pages()
        return tab

    # ------------------------------------------------------------- Grundgeruest

    def test_startseite_wird_gezeigt(self):
        self.assertEqual(len(self.window.tabs), 1)
        tab = self.window.current_tab()
        self.assertIsNone(tab.document)
        self.assertEqual(tab.kind, "welcome")
        self.assertScript(tab, "Willkommen")
        self.assertTrue(self.window.window.visible)

    def test_datei_oeffnen_erzeugt_tab_und_status(self):
        path = self.make_file()
        tab = self.open(path, new_tab=False)
        self.assertIsNotNone(tab)
        self.assertEqual(tab.document.name, "notiz.md")
        self.assertEqual(tab.label_text.get_text(), "notiz.md")
        script = tab.page.webview.last_script()
        self.assertIn("MDViewer.load", script)
        self.assertIn("notiz.md", script)
        self.assertIn("notiz.md", self.window.status_details.get_text())
        self.assertEqual(self.settings.recent_files()[0], str(path))

    def test_zuletzt_geoeffnet_erscheint_im_menue(self):
        path = self.make_file()
        self.open(path, new_tab=False)
        self.assertIn(str(path), self.settings.recent_files())

    def test_fehlende_datei_zeigt_fehlerdokument(self):
        tab = self.window.open_path(self.dir / "gibtsnicht.md")
        self.assertIsNotNone(tab)
        self.assertEqual(tab.kind, "error")
        self.assertIn("nicht gefunden", tab.page.webview.last_script())

    def test_mehrere_dateien_landen_in_eigenen_tabs(self):
        first = self.make_file("eins.md", "# Eins\n")
        second = self.make_file("zwei.md", "# Zwei\n")
        self.window.open_paths([str(first), str(second)])
        self.assertEqual(len(self.window.tabs), 2)
        self.assertEqual(self.window.current_tab().document.name, "zwei.md")

    def test_erste_datei_uebernimmt_den_willkommens_tab(self):
        path = self.make_file()
        self.window.open_paths([str(path)])
        self.assertEqual(len(self.window.tabs), 1)
        self.assertEqual(self.window.current_tab().document.name, "notiz.md")

    def test_tab_schliessen(self):
        path = self.make_file()
        tab = self.open(path)
        self.assertEqual(len(self.window.tabs), 2)
        self.window.close_tab(tab)
        self.assertEqual(len(self.window.tabs), 1)
        # der letzte Tab darf nicht geschlossen werden -> Startseite bleibt
        self.window.close_tab(self.window.current_tab())
        self.assertEqual(len(self.window.tabs), 1)

    def test_tab_fuer_pfad_wird_gefunden(self):
        path = self.make_file()
        self.open(path)
        self.assertIsNotNone(self.window.tab_for_path(path))
        self.assertIsNone(self.window.tab_for_path(self.dir / "anders.md"))

    # ------------------------------------------------------------- Nachrichten

    def test_nachricht_rendered_aktualisiert_statusleiste(self):
        path = self.make_file()
        tab = self.open(path, new_tab=False)
        tab.page._handle_message(
            None,
            json.dumps(
                {
                    "type": "rendered",
                    "stats": {"words": 1234, "characters": 5000, "readingMinutes": 6, "headings": 4},
                }
            ),
        )
        stats_text = self.window.status_stats.get_text()
        self.assertIn("1.234", stats_text)
        self.assertIn("Wörter", stats_text)

    def test_nachricht_copy_text_landet_in_der_zwischenablage(self):
        tab = self.window.current_tab()
        self.clipboard_calls = []
        tab.page.on_copy_text = lambda text: self.clipboard_calls.append(text)
        tab.page._handle_message(None, json.dumps({"type": "copy-text", "text": "Hallo"}))
        self.assertEqual(self.clipboard_calls, ["Hallo"])

    def test_nachricht_open_path_oeffnet_neuen_tab(self):
        target = self.make_file("verlinkt.md", "# Verlinkt\n")
        tab = self.window.current_tab()
        tab.page._handle_message(None, json.dumps({"type": "open-path", "url": target.as_uri()}))
        self.assertEqual(self.window.current_tab().document.name, "verlinkt.md")

    def test_nachricht_open_external_wird_weitergereicht(self):
        tab = self.window.current_tab()
        seen = []
        tab.page.on_open_external = seen.append
        tab.page._handle_message(None, json.dumps({"type": "open-external", "url": "https://example.com"}))
        self.assertEqual(seen, ["https://example.com"])

    def test_kaputte_nachrichten_krachen_nicht(self):
        tab = self.window.current_tab()
        tab.page._handle_message(None, "kein json")
        tab.page._handle_message(None, json.dumps([1, 2, 3]))
        tab.page._handle_message(None, "")

    # ------------------------------------------------------------ Einstellungen

    def test_zoom_wird_gesetzt_und_gespeichert(self):
        self.window.set_zoom(150)
        self.assertEqual(self.settings.get("zoom"), 150)
        self.assertScript(self.window.current_tab(), "setZoom(150)")
        # Begrenzung
        self.window.set_zoom(1000)
        self.assertEqual(self.settings.get("zoom"), 250)

    def test_zoomstufen_verlaufen_aufwaerts_und_abwaerts(self):
        self.settings.set("zoom", 100)
        self.assertEqual(self.window._next_zoom(1), 110)
        self.assertEqual(self.window._next_zoom(-1), 90)
        self.settings.set("zoom", 250)
        self.assertEqual(self.window._next_zoom(1), 250)
        self.settings.set("zoom", 50)
        self.assertEqual(self.window._next_zoom(-1), 50)

    def test_design_wechsel(self):
        self.window.on_theme(self.toolkit.GLib.Variant.new_string("dark"))
        self.assertEqual(self.settings.get("theme"), "dark")
        self.assertScript(self.window.current_tab(), 'setTheme("dark")')

    def test_design_system_loest_hell_oder_dunkel_auf(self):
        self.window.on_theme(self.toolkit.GLib.Variant.new_string("auto"))
        self.assertIn(self.window._resolve_theme(), {"light", "dark"})

    def test_inhaltsverzeichnis_umschalten(self):
        self.window.on_toggle_toc(self.toolkit.GLib.Variant.new_boolean(False))
        self.assertFalse(self.settings.get("toc_visible"))
        self.window.on_toggle_toc(self.toolkit.GLib.Variant.new_boolean(True))
        self.assertTrue(self.settings.get("toc_visible"))

    def test_rendereinstellungen_werden_gespeichert(self):
        self.window.on_breaks(self.toolkit.GLib.Variant.new_boolean(True))
        self.assertTrue(self.settings.get("breaks"))
        self.window.on_math(self.toolkit.GLib.Variant.new_boolean(False))
        self.assertFalse(self.settings.get("math"))
        self.window.on_math_inline(self.toolkit.GLib.Variant.new_boolean(False))
        self.assertFalse(self.settings.get("math_inline"))
        self.window.on_block_remote_images(self.toolkit.GLib.Variant.new_boolean(True))
        self.assertTrue(self.settings.get("block_remote_images"))
        self.window.on_line_width(self.toolkit.GLib.Variant.new_string("wide"))
        self.assertEqual(self.settings.get("line_width"), "wide")

    def test_sprachwechsel_setzt_texte_neu(self):
        self.window.on_language(self.toolkit.GLib.Variant.new_string("en"))
        self.assertEqual(i18n.get_language(), "en")
        self.assertEqual(self.settings.get("language"), "en")
        self.assertScript(self.window.current_tab(), "Welcome")
        i18n.set_language("de")

    def test_automatisches_neuladen_umschalten(self):
        path = self.make_file()
        tab = self.open(path, new_tab=False)
        self.assertIsNotNone(tab.monitor)
        self.window.on_auto_reload(self.toolkit.GLib.Variant.new_boolean(False))
        self.assertIsNone(tab.monitor)
        self.window.on_auto_reload(self.toolkit.GLib.Variant.new_boolean(True))
        self.assertIsNotNone(tab.monitor)

    # ------------------------------------------------------------ Live-Neuladen

    def test_dateiaenderung_laedt_neu(self):
        path = self.make_file()
        tab = self.open(path, new_tab=False)

        fake_file = type("F", (), {"get_basename": staticmethod(lambda: "notiz.md")})()
        self.window._on_monitor_changed(None, fake_file, None, None, tab)
        self.assertTrue(tab.reload_source)
        # Verzoegerung ueberspringen: direkt neu laden
        tab.reload_source = 0
        path.write_text("# Titel\n\nNeuer Text\n", encoding="utf-8")
        self.window._auto_reload(tab)
        self.assertScript(tab, "Neuer Text")
        self.assertIsNotNone(tab.last_reload)

    def test_fremde_datei_im_ordner_loest_kein_neuladen_aus(self):
        path = self.make_file()
        tab = self.open(path, new_tab=False)
        other = type("F", (), {"get_basename": staticmethod(lambda: "andere.md")})()
        tab.reload_source = 0
        self.window._on_monitor_changed(None, other, None, None, tab)
        self.assertEqual(tab.reload_source, 0)

    def test_geloeschte_datei_zeigt_hinweis_statt_leer(self):
        path = self.make_file()
        tab = self.open(path, new_tab=False)
        path.unlink()
        self.window._auto_reload(tab)
        # Inhalt bleibt stehen, nur ein Hinweis wird gesendet
        self.assertScript(tab, "toast")

    # ------------------------------------------------------------------ Export

    def test_html_export_schreibt_datei(self):
        path = self.make_file()
        tab = self.open(path, new_tab=False)
        tab.page.webview.result_text = '<h1 id="titel">Titel</h1><p>Gerendert</p>'
        target = self.dir / "export.html"
        done = []
        self.window.export_html_to(target, tab, on_done=done.append)
        self.assertTrue(target.exists())
        content = target.read_text(encoding="utf-8")
        self.assertIn("Gerendert", content)
        self.assertIn("<title>notiz.md</title>", content)
        self.assertIn("MD Viewer", content)
        self.assertEqual(done, [True])

    def test_export_ohne_dokument_meldet_fehler(self):
        done = []
        self.window.export_html_to(self.dir / "x.html", None, on_done=done.append)
        self.assertEqual(done, [False])

    # ---------------------------------------------------------- Sonstiges

    def test_kopieren_des_pfades(self):
        path = self.make_file()
        self.open(path, new_tab=False)
        self.assertTrue(self.window.copy_to_clipboard(str(path), notify=True))

    def test_zentrale_titelzeile_wird_gesetzt(self):
        path = self.make_file("bericht.md")
        self.open(path, new_tab=False)
        self.assertEqual(self.window.title_label.get_text(), "bericht.md")
        self.assertEqual(self.window.subtitle_label.get_text(), str(self.dir))
        self.assertIn("bericht.md", self.window.window.get_title())

    def test_fenstergroesse_wird_gespeichert(self):
        self.window.save_window_state()
        self.assertGreaterEqual(self.settings.get("window_width"), 480)

    def test_tastenkombinationen_werden_gesetzt(self):
        self.assertEqual(self.application.get_accels_for_action("win.open"), ["<Primary>o"])
        self.assertIn("<Primary>f", self.application.get_accels_for_action("win.find"))

    def test_drag_and_drop_oeffnet_dateien(self):
        path = self.make_file("gedroppt.md", "# Gedroppt\n")

        class Data:
            def get_uris(self):
                return [path.as_uri()]

        self.window._on_drag_data_received(None, None, 0, 0, Data(), 0, 0)
        self.assertEqual(self.window.current_tab().document.name, "gedroppt.md")


class ViewerPageTest(ToolkitMixin):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(Path(self.tmp.name) / "settings.json").load()
        self.page = ViewerPage(self.toolkit, self.settings)

    def tearDown(self):
        self.tmp.cleanup()

    def test_seite_laedt_index_html(self):
        self.page.load_page()
        self.assertTrue(self.page.webview.loaded_uris[0].endswith("index.html"))
        self.assertFalse(self.page.page_loaded)

    def test_nutzlast_wartet_auf_geladene_seite(self):
        from mdviewer.viewer_page import welcome_payload

        self.page.show_payload(welcome_payload(settings=self.settings, text="# Hallo"))
        self.assertEqual(self.page.webview.scripts, [])
        self.page.webview.emit("load-changed", self.toolkit.WebKit.LoadEvent.FINISHED)
        self.assertTrue(self.page.page_loaded)
        self.assertIn("# Hallo", self.page.webview.last_script())

    def test_einstellungen_werden_erneut_geschickt(self):
        from mdviewer.viewer_page import welcome_payload

        self.page.show_payload(welcome_payload(settings=self.settings, text="# A"))
        self.page.webview.emit("load-changed", self.toolkit.WebKit.LoadEvent.FINISHED)
        self.settings.set("theme", "dark")
        self.page.update_settings()
        self.assertIn("dark", self.page.webview.last_script())

    def test_navigationsrichtlinie_ist_verbunden(self):
        self.assertTrue(self.page.webview.signals.get("decide-policy"))
        self.assertTrue(self.page.webview.signals.get("create"))
        self.assertIn("app", self.page.webview.get_user_content_manager().handlers)

    def test_zoom_und_suche_werden_weitergegeben(self):
        self.page.page_loaded = True
        self.page.set_zoom(130)
        self.assertIn("setZoom(130)", self.page.webview.last_script())
        self.page.open_find()
        self.assertIn("openFind", self.page.webview.last_script())
        self.page.find_previous()
        self.assertIn("findPrev", self.page.webview.last_script())
        self.page.toast("Hallo")
        self.assertIn("Hallo", self.page.webview.last_script())

    def test_body_html_wird_gelesen(self):
        self.page.page_loaded = True
        self.page.webview.result_text = "<h1>X</h1>"
        got = []
        self.page.request_body_html(got.append)
        self.assertEqual(got, ["<h1>X</h1>"])

    def test_body_html_ohne_geladene_seite(self):
        got = []
        self.page.request_body_html(got.append)
        self.assertEqual(got, [None])


class WelcomeTest(unittest.TestCase):
    def test_startseite_enthaelt_tastenkombinationen(self):
        i18n.set_language("de")
        text = welcome.build_welcome_markdown()
        self.assertIn("Willkommen", text)
        self.assertIn("Strg+O", text)
        self.assertIn("|", text)
        i18n.set_language("en")
        text_en = welcome.build_welcome_markdown(opened_from="/tmp/x.md")
        self.assertIn("Welcome", text_en)
        self.assertIn("/tmp/x.md", text_en)
        i18n.set_language("de")
        self.assertIn("MD Viewer", welcome.welcome_footer())


if __name__ == "__main__":
    unittest.main()
