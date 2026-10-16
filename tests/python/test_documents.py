"""Tests fuer das Einlesen von Dateien (Kodierung, Grenzen, URLs)."""

import tempfile
import unittest
from pathlib import Path

from mdviewer import documents, i18n
from mdviewer.documents import DocumentError


class ReadDocumentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, data: bytes) -> Path:
        path = self.dir / name
        path.write_bytes(data)
        return path

    def test_utf8_datei(self):
        path = self.write("a.md", "# Überschrift\n\nUmlaute: äöüß\n".encode("utf-8"))
        doc = documents.read_document(path)
        self.assertEqual(doc.encoding, "utf-8")
        self.assertFalse(doc.assumed_encoding)
        self.assertIn("Überschrift", doc.text)
        self.assertEqual(doc.name, "a.md")
        self.assertIsNone(doc.notice())
        self.assertTrue(doc.is_markdown)

    def test_utf8_bom(self):
        path = self.write("bom.md", b"\xef\xbb\xbf# Titel\n")
        doc = documents.read_document(path)
        self.assertEqual(doc.encoding, "utf-8-sig")
        # BOM darf nicht im Text landen
        self.assertEqual(doc.text, "# Titel\n")

    def test_cp1252_wird_erkannt_und_gemeldet(self):
        path = self.write("windows.md", "Grüße aus München\n".encode("cp1252"))
        doc = documents.read_document(path)
        self.assertEqual(doc.encoding, "cp1252")
        self.assertTrue(doc.assumed_encoding)
        self.assertIn("Grüße", doc.text)
        self.assertIn("cp1252", doc.notice())

    def test_zeilenenden_werden_vereinheitlicht(self):
        path = self.write("crlf.md", b"Zeile1\r\nZeile2\rZeile3\n")
        doc = documents.read_document(path)
        self.assertEqual(doc.text, "Zeile1\nZeile2\nZeile3\n")

    def test_fehlende_datei(self):
        with self.assertRaises(DocumentError) as ctx:
            documents.read_document(self.dir / "gibtsnicht.md")
        self.assertEqual(ctx.exception.key, "error.not_found")

    def test_verzeichnis_statt_datei(self):
        sub = self.dir / "ordner"
        sub.mkdir()
        with self.assertRaises(DocumentError) as ctx:
            documents.read_document(sub)
        self.assertEqual(ctx.exception.key, "error.is_dir")

    def test_zu_grosse_datei(self):
        path = self.write("gross.md", b"x" * 4096)
        with self.assertRaises(DocumentError) as ctx:
            documents.read_document(path, max_bytes=1024)
        self.assertEqual(ctx.exception.key, "error.too_large")
        self.assertIn("kB", ctx.exception.values["limit"])

    def test_binaerdatei(self):
        path = self.write("bild.md", b"PK\x03\x04\x00\x00binary")
        with self.assertRaises(DocumentError) as ctx:
            documents.read_document(path)
        self.assertEqual(ctx.exception.key, "error.binary")

    def test_grosse_datei_erzeugt_hinweis(self):
        path = self.write("gross.md", b"# Titel\n" + b"Text\n" * 300000)
        doc = documents.read_document(path)
        self.assertTrue(doc.is_large)
        self.assertIn("MB", doc.notice())

    def test_tilde_wird_erweitert(self):
        # ~ ohne HOME-Treffer -> Fehlermeldung statt Absturz
        with self.assertRaises(DocumentError):
            documents.read_document("~/definitiv/nicht/vorhanden.md")

    def test_url_variante_mit_umlauten_und_leerzeichen(self):
        path = self.write("Mein Dokument ä.md", b"# x\n")
        self.assertTrue(documents.path_to_url(path).startswith("file:///"))
        self.assertIn("%20", documents.path_to_url(path))
        base = documents.directory_url(path)
        self.assertTrue(base.endswith("/"))
        self.assertNotIn("Mein", base.split("/")[-2])  # Ordner-URL, nicht Datei-URL


class HelperTest(unittest.TestCase):
    def test_detect_encoding(self):
        self.assertEqual(documents.detect_encoding("ä".encode("utf-8")), ("utf-8", False))
        self.assertEqual(documents.detect_encoding(b"\xff\xfeh\x00i\x00"), ("utf-16-le", True))
        encoding, assumed = documents.detect_encoding("ä".encode("cp1252"))
        self.assertEqual(encoding, "cp1252")
        self.assertTrue(assumed)

    def test_looks_binary(self):
        self.assertFalse(documents.looks_binary(b"# Titel\n"))
        self.assertTrue(documents.looks_binary(b"abc\x00def"))

    def test_is_markdown(self):
        for name in ("a.md", "b.MARKDOWN", "c.txt", "d.mkd"):
            self.assertTrue(documents.is_markdown(name), name)
        for name in ("a.png", "b.pdf", "c.md.html"):
            self.assertFalse(documents.is_markdown(name), name)

    def test_format_size_deutsch_und_englisch(self):
        i18n.set_language("de")
        self.assertEqual(documents.format_size(512), "512 B")
        self.assertEqual(documents.format_size(1500), "1,5 kB")
        i18n.set_language("en")
        self.assertEqual(documents.format_size(1500), "1.5 kB")
        i18n.set_language("de")

    def test_format_number(self):
        i18n.set_language("de")
        self.assertEqual(documents.format_number(12345), "12.345")
        i18n.set_language("en")
        self.assertEqual(documents.format_number(12345), "12,345")
        i18n.set_language("de")
        self.assertEqual(documents.format_number("keine zahl"), "keine zahl")

    def test_format_timestamp(self):
        i18n.set_language("de")
        self.assertEqual(documents.format_timestamp(0).count(":"), 1)
        i18n.set_language("en")
        self.assertIn("-", documents.format_timestamp(0))
        i18n.set_language("de")


if __name__ == "__main__":
    unittest.main()
