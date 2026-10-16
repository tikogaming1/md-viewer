#!/usr/bin/env python3
"""Erzeugt das App-Icon (SVG + PNGs in allen ueblichen Groessen).

Das Motiv ist bewusst aus einfachen Flaechen aufgebaut (kein Font, kein
Rendering-Zufall): blaues, abgerundetes Quadrat mit weissem "M" und Pfeil
nach unten - das bekannte Markdown-Zeichen.

Aufruf:  python3 scripts/make_icons.py
Ergebnis: packaging/icons/md-viewer.svg und packaging/icons/md-viewer-<size>.png
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "packaging" / "icons"

SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)

BACKGROUND = "#1f6feb"
FOREGROUND = "#ffffff"

#: Geometrie in Anteilen der Kantenlaenge (0..1) - identisch fuer SVG und PNG
RADIUS = 0.19
INSET = 0.055
M_POINTS = [
    (0.175, 0.700),
    (0.175, 0.300),
    (0.275, 0.300),
    (0.360, 0.505),
    (0.445, 0.300),
    (0.545, 0.300),
    (0.545, 0.700),
    (0.455, 0.700),
    (0.455, 0.455),
    (0.390, 0.640),
    (0.330, 0.640),
    (0.265, 0.455),
    (0.265, 0.700),
]
ARROW_STEM = (0.665, 0.300, 0.735, 0.545)  # x1, y1, x2, y2
ARROW_HEAD = [(0.585, 0.530), (0.815, 0.530), (0.700, 0.740)]


def svg(size: int = 128) -> str:
    def s(value: float) -> str:
        return f"{value * size:.2f}"

    m_points = " ".join(f"{s(x)},{s(y)}" for x, y in M_POINTS)
    head = " ".join(f"{s(x)},{s(y)}" for x, y in ARROW_HEAD)
    x1, y1, x2, y2 = ARROW_STEM
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <title>MD Viewer</title>
  <rect x="{s(INSET)}" y="{s(INSET)}" width="{s(1 - 2 * INSET)}" height="{s(1 - 2 * INSET)}"
        rx="{s(RADIUS)}" ry="{s(RADIUS)}" fill="{BACKGROUND}"/>
  <polygon points="{m_points}" fill="{FOREGROUND}"/>
  <rect x="{s(x1)}" y="{s(y1)}" width="{s(x2 - x1)}" height="{s(y2 - y1)}" fill="{FOREGROUND}"/>
  <polygon points="{head}" fill="{FOREGROUND}"/>
</svg>
"""


def magick_command(size: int, target: Path) -> list[str]:
    """ImageMagick-Aufruf fuer ein PNG (deterministisch, ohne Schriftarten)."""
    def p(value: float) -> str:
        return f"{value * size:.2f}"

    m_points = " ".join(f"{p(x)},{p(y)}" for x, y in M_POINTS)
    head = " ".join(f"{p(x)},{p(y)}" for x, y in ARROW_HEAD)
    x1, y1, x2, y2 = ARROW_STEM
    draw = [
        f"roundrectangle {p(INSET)},{p(INSET)} {p(1 - INSET)},{p(1 - INSET)} {p(RADIUS)},{p(RADIUS)}",
        f"polygon {m_points}",
        f"rectangle {p(x1)},{p(y1)} {p(x2)},{p(y2)}",
        f"polygon {head}",
    ]
    return [
        "convert",
        "-size",
        f"{size}x{size}",
        "xc:none",
        "-fill",
        BACKGROUND,
        "-draw",
        draw[0],
        "-fill",
        FOREGROUND,
        "-draw",
        draw[1],
        "-draw",
        draw[2],
        "-draw",
        draw[3],
        "-strip",
        str(target),
    ]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "md-viewer.svg").write_text(svg(), encoding="utf-8")
    print(f"geschrieben: {OUT_DIR / 'md-viewer.svg'}")

    converter = shutil.which("convert") or shutil.which("magick")
    if not converter:
        print("ImageMagick fehlt - es wurde nur das SVG erzeugt.", file=sys.stderr)
        return 1

    written = 0
    for size in SIZES:
        target = OUT_DIR / f"md-viewer-{size}.png"
        command = magick_command(size, target)
        command[0] = converter
        try:
            subprocess.run(command, check=True, capture_output=True)
            written += 1
        except subprocess.CalledProcessError as error:  # pragma: no cover
            print(f"Fehler bei {size}px: {error.stderr.decode(errors='replace')}", file=sys.stderr)
    print(f"{written} PNG-Groessen erzeugt in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
