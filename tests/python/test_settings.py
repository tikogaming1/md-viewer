"""Tests fuer die Einstellungen (Validierung, Speichern, zuletzt geoeffnet)."""

import json
import tempfile
import unittest
from pathlib import Path

from mdviewer.settings import DEFAULTS, MAX_RECENT_FILES, Settings


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "settings.json"
        self.settings = Settings(self.path).load()

    def tearDown(self):
        self.tmp.cleanup()

    def test_standardwerte(self):
        self.assertEqual(self.settings.get("theme"), "auto")
        self.assertEqual(self.settings.get("zoom"), 100)
        self.assertTrue(self.settings.get("toc_visible"))
        self.assertTrue(self.settings.get("block_remote_images"))
        self.assertEqual(self.settings.get("recent_files"), [])

    def test_legacy_false_fuer_remote_bilder_wird_einmalig_migriert(self):
        self.path.write_text(
            json.dumps({"theme": "dark", "block_remote_images": False}), encoding="utf-8"
        )

        migrated = Settings(self.path).load()
        self.assertTrue(migrated.get("block_remote_images"))
        stored = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(stored["_version"], 1)

        # Nach der einmaligen Migration kann der Nutzer die Einstellung wieder
        # bewusst deaktivieren; ein weiterer Start respektiert diese Auswahl.
        migrated.set("block_remote_images", False)
        self.assertFalse(Settings(self.path).load().get("block_remote_images"))

    def test_setzen_und_lesen(self):
        self.settings.set("zoom", 140)
        self.assertEqual(self.settings.get("zoom"), 140)
        self.settings.set("theme", "dark")
        self.assertEqual(self.settings.get("theme"), "dark")

    def test_zoom_wird_begrenzt(self):
        self.assertEqual(self.settings.set("zoom", 5000), 250)
        self.assertEqual(self.settings.set("zoom", 1), 50)
        self.assertEqual(self.settings.set("zoom", "quatsch"), DEFAULTS["zoom"])

    def test_unbekannte_aufzaehlung_faellt_zurueck(self):
        self.assertEqual(self.settings.set("theme", "neon"), "auto")
        self.assertEqual(self.settings.set("line_width", "breit"), "normal")
        self.assertEqual(self.settings.set("language", "fr"), "de")

    def test_bools_werden_gezwungen(self):
        self.settings.set("auto_reload", 0)
        self.assertFalse(self.settings.get("auto_reload"))
        self.settings.set("auto_reload", "ja")
        self.assertTrue(self.settings.get("auto_reload"))

    def test_speichern_und_laden(self):
        self.settings.set("zoom", 120)
        self.settings.set("theme", "light")
        self.assertTrue(self.path.exists())

        again = Settings(self.path).load()
        self.assertEqual(again.get("zoom"), 120)
        self.assertEqual(again.get("theme"), "light")

    def test_kaputte_datei_fuehrt_zu_standardwerten(self):
        self.path.write_text("{ das ist kein json", encoding="utf-8")
        settings = Settings(self.path).load()
        self.assertEqual(settings.get("zoom"), DEFAULTS["zoom"])

    def test_unbekannte_schluessel_werden_ignoriert(self):
        self.path.write_text(json.dumps({"zoom": 130, "hacker": True}), encoding="utf-8")
        settings = Settings(self.path).load()
        self.assertEqual(settings.get("zoom"), 130)
        self.assertNotIn("hacker", settings.to_dict())

    def test_unplausible_werte_aus_datei(self):
        self.path.write_text(
            json.dumps({"zoom": 99999, "theme": "blau", "recent_files": "keine liste", "window_width": "x"}),
            encoding="utf-8",
        )
        settings = Settings(self.path).load()
        self.assertEqual(settings.get("zoom"), 250)
        self.assertEqual(settings.get("theme"), "auto")
        self.assertEqual(settings.get("recent_files"), [])
        self.assertEqual(settings.get("window_width"), DEFAULTS["window_width"])

    def test_zuletzt_geoeffnet(self):
        self.settings.add_recent("/a/one.md")
        self.settings.add_recent("/a/two.md")
        self.assertEqual(self.settings.recent_files(), ["/a/two.md", "/a/one.md"])
        # erneutes Oeffnen schiebt nach vorne, ohne Dublette
        self.settings.add_recent("/a/one.md")
        self.assertEqual(self.settings.recent_files(), ["/a/one.md", "/a/two.md"])
        self.settings.clear_recents()
        self.assertEqual(self.settings.recent_files(), [])

    def test_liste_ist_begrenzt(self):
        for index in range(MAX_RECENT_FILES + 5):
            self.settings.add_recent(f"/a/{index}.md", save=False)
        self.assertEqual(len(self.settings.recent_files()), MAX_RECENT_FILES)
        self.assertEqual(self.settings.recent_files()[0], f"/a/{MAX_RECENT_FILES + 4}.md")

    def test_viewer_werte_fuer_das_webview(self):
        self.settings.update({"theme": "dark", "zoom": 130, "toc_visible": False, "block_remote_images": True})
        viewer = self.settings.viewer_settings()
        self.assertEqual(viewer["theme"], "dark")
        self.assertEqual(viewer["zoom"], 130)
        self.assertFalse(viewer["tocVisible"])
        self.assertTrue(viewer["blockRemoteImages"])
        self.assertEqual(viewer["language"], "de")

        options = self.settings.render_options()
        self.assertEqual(
            set(options), {"breaks", "highlight", "math", "mathInline"}
        )
        self.assertTrue(options["math"])

    def test_speichern_ohne_rechte_kracht_nicht(self):
        settings = Settings(Path("/proc/definitiv/nicht/schreibbar.json")).load()
        self.assertFalse(settings.save())


if __name__ == "__main__":
    unittest.main()
