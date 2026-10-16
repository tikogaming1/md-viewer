"""Die Startseite (Markdown, wird vom Viewer selbst gerendert)."""

from __future__ import annotations

from . import __version__, i18n


def build_welcome_markdown(*, opened_from: str | None = None) -> str:
    """Baut das Willkommens-Dokument in der aktiven Sprache."""
    shortcut_rows = "\n".join(
        f"| `{keys}` | {text} |" for keys, text in i18n.shortcuts_table()
    )
    lines = [
        f"# {i18n.t('welcome.title')}",
        "",
        i18n.t("welcome.intro"),
        "",
    ]
    if opened_from:
        lines += [f"> {i18n.t('welcome.opened_with', path=opened_from)}", ""]
    lines += [
        f"## {i18n.t('welcome.features')}",
        "",
        i18n.t("welcome.feature_list"),
        "",
        f"## {i18n.t('welcome.hints')}",
        "",
        i18n.t("welcome.hint_list"),
        "",
        f"## {i18n.t('welcome.shortcuts')}",
        "",
        "| Tastenkürzel | Wirkung |" if i18n.get_language() == "de" else "| Shortcut | Action |",
        "| --- | --- |",
        shortcut_rows,
        "",
        i18n.t("welcome.lang_hint"),
        "",
        f"> [!TIP]",
        f"> {i18n.t('welcome.footer_note')}",
        "",
    ]
    return "\n".join(lines)


def welcome_footer() -> str:
    return i18n.t("footer.welcome", version=__version__, shortcuts="Strg+Umschalt+/")
