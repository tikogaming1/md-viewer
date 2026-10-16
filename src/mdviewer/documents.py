"""Dateien einlesen und beschreiben (Kodierung, Groesse, Zeitstempel, URLs)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import i18n

#: Ab dieser Groesse wird nicht mehr geladen (Markdown in dieser Groesse ist praktisch unlesbar
#: und wuerde den WebView-Prozess ausbremsen).
MAX_BYTES = 16 * 1024 * 1024
#: Ab dieser Groesse weisen wir auf die Renderdauer hin.
LARGE_BYTES = 1024 * 1024
#: Dateiendungen, die als Markdown/Text gelten.
MARKDOWN_SUFFIXES = {
    ".md",
    ".markdown",
    ".mdown",
    ".mkdn",
    ".mkd",
    ".mdwn",
    ".mdtxt",
    ".mdtext",
    ".text",
    ".txt",
    ".rst",
}

_BOMS: tuple[tuple[bytes, str], ...] = (
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
)


class DocumentError(Exception):
    """Fehler mit i18n-Schluessel - die Oberflaeche uebersetzt ihn."""

    def __init__(self, key: str, **values: Any) -> None:
        self.key = key
        self.values = values
        super().__init__(f"{key}: {values}" if values else key)

    def message(self) -> str:
        return i18n.t(self.key, **self.values)


@dataclass(frozen=True)
class Document:
    path: Path
    text: str
    encoding: str
    assumed_encoding: bool
    size: int
    modified: float

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def directory(self) -> Path:
        return self.path.parent

    @property
    def url(self) -> str:
        return path_to_url(self.path)

    @property
    def base_href(self) -> str:
        return directory_url(self.path)

    @property
    def is_markdown(self) -> bool:
        return is_markdown(self.path)

    @property
    def is_large(self) -> bool:
        return self.size >= LARGE_BYTES

    def notice(self) -> str | None:
        """Hinweis fuer den Viewer (Kodierung / Groesse) oder None."""
        messages = []
        if self.assumed_encoding:
            messages.append(i18n.t("notice.encoding", encoding=self.encoding))
        if self.is_large:
            messages.append(i18n.t("notice.large", size=format_size(self.size)))
        return "\n".join(messages) if messages else None


def is_markdown(path: os.PathLike[str] | str) -> bool:
    return Path(path).suffix.lower() in MARKDOWN_SUFFIXES


def path_to_url(path: os.PathLike[str] | str) -> str:
    """file://-URL einer Datei (mit korrekter Kodierung von Leerzeichen/Umlauten)."""
    return Path(os.path.abspath(os.fspath(path))).as_uri()


def directory_url(path: os.PathLike[str] | str) -> str:
    """Basis-URL des Ordners (fuer relative Bilder/Links) - mit Schraegstrich am Ende."""
    target = Path(os.path.abspath(os.fspath(path)))
    if target.is_dir():
        base = target
    else:
        base = target.parent
    return base.as_uri().rstrip("/") + "/"


def detect_encoding(data: bytes) -> tuple[str, bool]:
    """Ermittelt die Kodierung.

    @return (encoding, assumed) - ``assumed`` ist True, wenn nicht UTF-8 vorliegt.
    """
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            return encoding, encoding not in {"utf-8", "utf-8-sig"}
    try:
        data.decode("utf-8")
        return "utf-8", False
    except UnicodeDecodeError:
        pass
    try:
        data.decode("cp1252")
        return "cp1252", True
    except UnicodeDecodeError:
        return "latin-1", True


def looks_binary(data: bytes) -> bool:
    """Nullbytes in den ersten 8 KiB deuten auf eine Binaerdatei hin."""
    return b"\x00" in data[:8192]


def read_document(path: os.PathLike[str] | str, max_bytes: int = MAX_BYTES) -> Document:
    """Liest eine Datei und liefert ein Document-Objekt.

    @raises DocumentError mit i18n-Schluessel bei Problemen.
    """
    target = Path(path).expanduser()
    try:
        resolved = target.resolve(strict=True)
    except FileNotFoundError:
        raise DocumentError("error.not_found", path=str(target)) from None
    except OSError as error:  # z. B. Rechte, kaputte Symlinks
        raise DocumentError("error.read_failed", error=str(error)) from None

    if resolved.is_dir():
        raise DocumentError("error.is_dir", path=str(resolved))

    try:
        size = resolved.stat().st_size
    except OSError as error:
        raise DocumentError("error.read_failed", error=str(error)) from None

    if size > max_bytes:
        raise DocumentError("error.too_large", size=format_size(size), limit=format_size(max_bytes))

    try:
        data = resolved.read_bytes()
        stat = resolved.stat()
    except OSError as error:
        raise DocumentError("error.read_failed", error=str(error)) from None

    if looks_binary(data):
        raise DocumentError("error.binary")

    encoding, assumed = detect_encoding(data)
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        # Notnagel: nie scheitern, nur unschoen aussehen.
        text = data.decode("latin-1")
        encoding, assumed = "latin-1", True

    return Document(
        path=resolved,
        text=text.replace("\r\n", "\n").replace("\r", "\n"),
        encoding=encoding,
        assumed_encoding=assumed,
        size=stat.st_size,
        modified=stat.st_mtime,
    )


def format_number(value: int | float) -> str:
    """Zahl mit Tausendertrennzeichen: 12.345 (deutsch) bzw. 12,345 (englisch)."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return str(value)
    text = f"{number:,}"
    return text.replace(",", ".") if i18n.get_language() == "de" else text


def format_size(num_bytes: int) -> str:
    """Menschenlesbare Groesse (deutsch: Komma statt Punkt)."""
    step = 1000.0
    value = float(max(0, num_bytes))
    for unit in ("B", "kB", "MB", "GB"):
        if value < step or unit == "GB":
            if unit == "B":
                return f"{int(value)} {unit}"
            text = f"{value:.1f}".rstrip("0").rstrip(".")
            return f"{text.replace('.', ',')} {unit}" if i18n.get_language() == "de" else f"{text} {unit}"
        value /= step
    return f"{value:.1f} GB"


def format_timestamp(timestamp: float) -> str:
    """Zeitstempel der letzten Aenderung, sprachabhaengig formatiert."""
    import datetime

    moment = datetime.datetime.fromtimestamp(timestamp)
    if i18n.get_language() == "de":
        return moment.strftime("%d.%m.%Y %H:%M")
    return moment.strftime("%Y-%m-%d %H:%M")


def format_clock(timestamp: float | None = None) -> str:
    import datetime

    moment = datetime.datetime.fromtimestamp(timestamp) if timestamp else datetime.datetime.now()
    return moment.strftime("%H:%M:%S")
