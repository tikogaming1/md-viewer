"""Tests fuer Texte (i18n) und Pfadauflösung."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mdviewer import i18n, paths


class I18nTest(unittest.TestCase):
    def tearDown(self):
        i18n.set_language("de")

    def test_deutsche_und_englische_texte(self):
        i18n.set_language("de")
        self.assertEqual(i18n.t("menu.open"), "Öffnen …")
        i18n.set_language("en")
        self.assertEqual(i18n.t("menu.open"), "Open …")

    def test_unbekannte_sprache_faellt_auf_deutsch(self):
        self.assertEqual(i18n.set_language("klingonisch"), "de")
        self.assertEqual(i18n.set_language(None), "de")

    def test_platzhalter(self):
        i18n.set_language("de")
        text = i18n.t("status.stats", words="120", characters="700", minutes=2)
        self.assertIn("120", text)
        self.assertIn("700", text)

    def test_unbekannter_schluessel_liefert_schluessel(self):
        self.assertEqual(i18n.t("gibt.es.nicht"), "gibt.es.nicht")

    def test_fusszeilenvorlage_behaelt_platzhalter(self):
        i18n.set_language("de")
        template = i18n.t("footer")
        self.assertIn("{words}", template)
        self.assertIn("{minutes}", template)

    def test_fehlende_platzhalter_krachen_nicht(self):
        i18n.set_language("de")
        self.assertIn("{path}", i18n.t("status.details"))

    def test_beide_sprachen_sind_vollstaendig(self):
        de_keys = set(i18n.STRINGS["de"])
        en_keys = set(i18n.STRINGS["en"])
        self.assertEqual(de_keys - en_keys, set(), "Schlüssel fehlen in Englisch")
        self.assertEqual(en_keys - de_keys, set(), "Schlüssel fehlen in Deutsch")
        self.assertEqual(i18n.STRINGS["de"]["app.name"], "MD Viewer")

    def test_tastenkombinationen_tabelle(self):
        table = i18n.shortcuts_table()
        self.assertTrue(len(table) >= 10)
        self.assertTrue(all(isinstance(keys, str) and isinstance(text, str) for keys, text in table))
        self.assertIn("Strg+O", [keys for keys, _ in table])


class PathsTest(unittest.TestCase):
    def test_web_dir_findet_das_checkout(self):
        web = paths.web_dir()
        self.assertTrue((web / "index.html").is_file(), f"index.html fehlt in {web}")
        self.assertTrue((web / "bundle" / "viewer.min.js").is_file())
        self.assertTrue((web / "vendor" / "github-markdown-light.css").is_file())

    def test_umgebungsvariable_hat_vorrang(self):
        with tempfile.TemporaryDirectory() as tmp:
            custom = Path(tmp)
            (custom / "index.html").write_text("<html></html>", encoding="utf-8")
            with mock.patch.dict(os.environ, {paths.ENV_WEB_DIR: str(custom)}):
                self.assertEqual(paths.web_dir(), custom)

    def test_einstellungsdatei_und_zwischenspeicher(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {paths.ENV_CONFIG_DIR: os.path.join(tmp, "cfg")}):
                self.assertEqual(paths.settings_file().name, "settings.json")
                self.assertIn("cfg", str(paths.settings_file()))

    def test_icon_wird_gefunden_oder_ist_none(self):
        icon = paths.icon_file()
        self.assertTrue(icon is None or icon.is_file())


if __name__ == "__main__":
    unittest.main()
