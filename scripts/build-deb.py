#!/usr/bin/env python3
"""Baut das Debian-Paket (md-viewer_<version>_all.deb).

Ablauf:
  1. Staging-Baum unter packaging/.stage/ aufbauen
  2. abhaengige Dateien kopieren (Python-Paket, Web-Assets, Icons, Desktop-Datei, Doku)
  3. DEBIAN/control, md5sums und konffiles erzeugen
  4. dpkg-deb --build --root-owner-group

Aufruf:  python3 scripts/build-deb.py [--version X.Y.Z]
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
STAGE = PACKAGING / ".stage"
CONTROL_DIR = PACKAGING / "deb" / "control"
RELEASE = ROOT / "release"
PKG = "md-viewer"

DEB_TRIPLET = "linux-any"  # nur informativ, das Paket ist Architektur "all"


def read_version() -> str:
    text = (ROOT / "src" / "mdviewer" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit("Version nicht gefunden in src/mdviewer/__init__.py")
    return match.group(1)


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, check=True, **kwargs)


def copy_tree(source: Path, target: Path, *, ignore: tuple[str, ...] = ()) -> None:
    def ignore_func(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in ignore}

    shutil.copytree(source, target, ignore=ignore_func, dirs_exist_ok=True)


def write_gzip(source: Path, target: Path, *, replacements: dict[str, str] | None = None) -> None:
    """Schreibt eine gzip-Datei mit festem Zeitstempel (reproduzierbare Pakete)."""
    data = source.read_bytes().decode("utf-8")
    for key, value in (replacements or {}).items():
        data = data.replace(key, value)
    with open(target, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write(data.encode("utf-8"))


def dir_size_kb(path: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                continue
    return max(1, round(total / 1024))


def build_tree(version: str) -> Path:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    debian = STAGE / "DEBIAN"
    debian.mkdir(parents=True)

    # --- Python-Paket -------------------------------------------------------
    py_target = STAGE / "usr" / "lib" / "python3" / "dist-packages" / "mdviewer"
    copy_tree(ROOT / "src" / "mdviewer", py_target, ignore=("__pycache__",))
    # Bytecode vorab erzeugen (schnellerer Start, kein Schreibzugriff noetig)
    try:
        run([sys.executable, "-m", "compileall", "-q", "-b", str(py_target)])
    except (subprocess.CalledProcessError, OSError):  # pragma: no cover
        print("Hinweis: Bytecode konnte nicht vorab erzeugt werden", file=sys.stderr)

    # --- Web-Assets (HTML/CSS/JS inkl. Fremdbibliotheken) -------------------
    # web/src wird nicht mitinstalliert: gebraucht wird nur das fertige Bundle.
    web_target = STAGE / "usr" / "lib" / PKG / "web"
    copy_tree(ROOT / "web", web_target, ignore=("src",))

    # --- Starter, Desktop-Datei, Icon, Doku ---------------------------------
    bin_target = STAGE / "usr" / "bin"
    bin_target.mkdir(parents=True, exist_ok=True)
    launcher = bin_target / PKG
    launcher.write_text(
        "#!/bin/sh\n"
        "# MD Viewer - Markdown-Dateien fertig gerendert anzeigen\n"
        'exec /usr/bin/python3 -m mdviewer "$@"\n',
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    applications = STAGE / "usr" / "share" / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    shutil.copy(CONTROL_DIR / f"{PKG}.desktop", applications / f"{PKG}.desktop")

    metainfo = STAGE / "usr" / "share" / "metainfo"
    metainfo.mkdir(parents=True, exist_ok=True)
    shutil.copy(CONTROL_DIR / "metainfo.xml", metainfo / f"{PKG}.metainfo.xml")

    for size in (16, 22, 24, 32, 48, 64, 128, 256, 512):
        icon_source = PACKAGING / "icons" / f"{PKG}-{size}.png"
        if not icon_source.is_file():
            continue
        icon_dir = STAGE / "usr" / "share" / "icons" / "hicolor" / f"{size}x{size}" / "apps"
        icon_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(icon_source, icon_dir / f"{PKG}.png")

    scalable_dir = STAGE / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps"
    scalable_dir.mkdir(parents=True, exist_ok=True)
    svg = PACKAGING / "icons" / f"{PKG}.svg"
    if svg.is_file():
        shutil.copy(svg, scalable_dir / f"{PKG}.svg")

    man_dir = STAGE / "usr" / "share" / "man" / "man1"
    man_dir.mkdir(parents=True, exist_ok=True)
    write_gzip(CONTROL_DIR / f"{PKG}.1", man_dir / f"{PKG}.1.gz", replacements={"1.0.0": version})

    # --- Dokumentation ------------------------------------------------------
    doc = STAGE / "usr" / "share" / "doc" / PKG
    doc.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "CHANGELOG.md", "LICENSE"):
        source = ROOT / name
        if source.is_file():
            shutil.copy(source, doc / name)
    copyright_text = (CONTROL_DIR / "copyright").read_text(encoding="utf-8").replace("@VERSION@", version)
    (doc / "copyright").write_text(copyright_text, encoding="utf-8")
    write_gzip(CONTROL_DIR / "changelog", doc / "changelog.gz", replacements={"@VERSION@": version})

    # Lizenzen der eingebetteten Fremdbibliotheken
    third_party = doc / "third-party"
    third_party.mkdir(parents=True, exist_ok=True)
    licenses = ROOT / "web" / "vendor" / "licenses"
    if licenses.is_dir():
        for licence in sorted(licenses.glob("*.txt")):
            shutil.copy(licence, third_party / licence.name)
    versions = ROOT / "web" / "vendor" / "VERSIONS.json"
    if versions.is_file():
        shutil.copy(versions, third_party / "VERSIONS.json")

    # --- Steuerdateien ------------------------------------------------------
    control = (CONTROL_DIR / "control.in").read_text(encoding="utf-8")
    installed_size = dir_size_kb(STAGE / "usr")
    control = control.replace("@VERSION@", version).replace("@INSTALLED_SIZE@", str(installed_size))
    (debian / "control").write_text(control, encoding="utf-8")

    # md5sums (Standard fuer dpkg)
    lines = []
    for root, _dirs, files in sorted(os.walk(STAGE)):
        if Path(root).name == "DEBIAN" and Path(root).parent == STAGE:
            continue
        for name in sorted(files):
            path = Path(root) / name
            relative = path.relative_to(STAGE).as_posix()
            if relative.startswith("DEBIAN/"):
                continue
            digest = hashlib.md5(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {relative}")
    (debian / "md5sums").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return STAGE


def build_deb(version: str) -> Path:
    RELEASE.mkdir(parents=True, exist_ok=True)
    target = RELEASE / f"{PKG}_{version}_all.deb"
    if target.exists():
        target.unlink()
    build_tree(version)
    run(
        [
            "dpkg-deb",
            "--build",
            "--root-owner-group",
            "-Zxz",
            "-z9",
            str(STAGE),
            str(target),
        ]
    )
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Debian-Paket fuer MD Viewer bauen")
    parser.add_argument("--version", help="Version (Standard: aus src/mdviewer/__init__.py)")
    args = parser.parse_args()
    version = args.version or read_version()

    if not (ROOT / "web" / "bundle" / "viewer.min.js").is_file():
        print("web/bundle/viewer.min.js fehlt - bitte zuerst 'npm run build' ausfuehren.", file=sys.stderr)
        return 1
    if not (ROOT / "web" / "vendor" / "github-markdown-light.css").is_file():
        print("web/vendor fehlt - bitte zuerst 'npm run vendor' ausfuehren.", file=sys.stderr)
        return 1

    started = time.time()
    target = build_deb(version)
    size = target.stat().st_size / 1024
    print(f"Paket erstellt: {target} ({size:.0f} kB, {time.time() - started:.1f}s)")
    print("Pruefen mit:  dpkg-deb -I " + str(target.relative_to(ROOT)) + " && dpkg-deb -c " + str(target.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
