"""Tests fuer die explizite GTK/Gdk-Versionsauswahl vor dem GI-Import."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Die Tests laufen auch auf Systemen ohne PyGObject / grafische Oberflaeche.
STUBS = Path(__file__).resolve().parent / "stubs"
if str(STUBS) not in sys.path:
    sys.path.insert(0, str(STUBS))

import gi  # noqa: E402
from mdviewer import compat  # noqa: E402


class ToolkitVersionTest(unittest.TestCase):
    def test_gtk_gdk_und_gdkpixbuf_versionen_werden_vor_webkit_angefordert(self):
        original = gi.require_version
        calls: list[tuple[str, str]] = []

        def record(namespace: str, version: str) -> None:
            calls.append((namespace, version))
            original(namespace, version)

        with patch.object(gi, "require_version", side_effect=record):
            toolkit = compat.load_toolkit(require_webkit=False)

        self.assertEqual(calls[:3], [("Gtk", "3.0"), ("Gdk", "3.0"), ("GdkPixbuf", "2.0")])
        self.assertEqual(toolkit.Gtk.__name__, "gi.repository.Gtk")
        self.assertEqual(toolkit.Gdk.__name__, "gi.repository.Gdk")

    def test_gdk_4_konflikt_wird_als_startfehler_gemeldet(self):
        original = gi.require_version

        def reject_gdk4_conflict(namespace: str, version: str) -> None:
            if namespace == "Gdk" and version == "3.0":
                raise ValueError("Requiring namespace 'Gdk' version '3.0', but '4.0' is already loaded")
            original(namespace, version)

        with patch.object(gi, "require_version", side_effect=reject_gdk4_conflict):
            with self.assertRaises(compat.MissingDependency) as context:
                compat.load_toolkit(require_webkit=False)

        self.assertEqual(context.exception.key, "error.no_gtk.title")
        self.assertIn("Gdk", context.exception.values["error"])
        self.assertIn("4.0", context.exception.values["error"])


if __name__ == "__main__":
    unittest.main()
