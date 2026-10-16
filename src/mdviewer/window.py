"""Das Hauptfenster: Kopfzeile, Tabs, Statusleiste, Menue, Live-Neuladen."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import APP_NAME, WEBSITE, __version__, exporter, i18n, paths, welcome
from .compat import Toolkit, can_print, launch_external
from .documents import (
    Document,
    DocumentError,
    format_clock,
    format_number,
    format_size,
    format_timestamp,
    read_document,
)
from .settings import Settings
from .viewer_page import ViewerPage

log = logging.getLogger(__name__)

#: Zoomstufen in Prozent
ZOOM_STEPS = (50, 60, 70, 80, 90, 100, 110, 125, 150, 175, 200, 250)

WINDOW_CSS = """
.mdv-statusbar {
  padding: 4px 12px;
  border-top: 1px solid alpha(currentColor, 0.15);
}
.mdv-statusbar label {
  font-size: 90%;
  opacity: 0.8;
}
.mdv-subtitle {
  font-size: 80%;
  opacity: 0.7;
}
.mdv-title {
  font-weight: bold;
}
.mdv-reload {
  color: #2ec27e;
  font-weight: bold;
}
"""


@dataclass
class Tab:
    """Ein Tab: Viewer-Seite + zugehoerige Datei + Dateibeobachter."""

    page: ViewerPage
    document: Document | None = None
    label: Any = None
    label_text: Any = None
    close_button: Any = None
    monitor: Any = None
    reload_source: int = 0
    last_reload: float | None = None
    error_message: str | None = None
    kind: str = "welcome"
    #: einmaliger Aufruf, sobald das Dokument fertig gerendert ist (z. B. CLI-Export)
    render_callback: Callable[["Tab"], None] | None = None

    @property
    def title(self) -> str:
        if self.document is not None:
            return self.document.name
        return i18n.t("header.untitled")


class MainWindow:
    """Nicht direkt von Gtk.ApplicationWindow abgeleitet - das Gtk-Objekt kommt
    ueber ``self.window``. So bleibt die Klasse auch ohne GTK importierbar
    (und damit testbar)."""

    def __init__(
        self,
        application: Any,
        toolkit: Toolkit,
        settings: Settings,
        *,
        developer: bool = False,
    ) -> None:
        self.toolkit = toolkit
        self.settings = settings
        self.application = application
        self.developer = developer
        self.tabs: list[Tab] = []

        Gtk = toolkit.Gtk
        i18n.set_language(settings.get("language"))
        self.window = Gtk.ApplicationWindow(application=application)
        self.window.set_title(APP_NAME)
        self.window.set_default_size(int(settings.get("window_width")), int(settings.get("window_height")))
        self.window.set_icon_name("md-viewer")
        self._apply_css()

        self._build_header()
        self._build_body()
        self._build_actions()
        self._setup_accels()
        self._setup_dnd()
        self._update_title()

        if settings.get("window_maximized"):
            self.window.maximize()
        self.window.connect("delete-event", self._on_delete_event)
        self._watch_system_theme()

    def _watch_system_theme(self) -> None:
        """Bei Design "System" auf Wechsel des Systemdesigns reagieren."""
        try:
            gtk_settings = self.toolkit.Gtk.Settings.get_default()
            if gtk_settings is not None:
                gtk_settings.connect("notify::gtk-application-prefer-dark-theme", self._on_system_theme_changed)
        except Exception:  # pragma: no cover - defensiv
            log.debug("Systemdesign kann nicht beobachtet werden")

    def _on_system_theme_changed(self, *_args: Any) -> None:
        if str(self.settings.get("theme")) != "auto":
            return
        for tab in self.tabs:
            tab.page.set_theme("auto")

    # ------------------------------------------------------------------ Aufbau

    def _apply_css(self) -> None:
        Gtk, Gdk = self.toolkit.Gtk, self.toolkit.Gdk
        provider = Gtk.CssProvider()
        try:
            provider.load_from_data(WINDOW_CSS)
        except TypeError:  # aeltere PyGObject-Version erwartet Bytes
            provider.load_from_data(WINDOW_CSS.encode("utf-8"))
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _build_header(self) -> None:
        Gtk = self.toolkit.Gtk
        header = Gtk.HeaderBar()
        header.set_show_close_button(True)
        header.set_title(APP_NAME)
        self.window.set_titlebar(header)
        self.header = header

        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_tooltip_text(i18n.t("menu.title"))
        self.menu_button.set_image(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        self.menu_button.show_all()
        header.pack_start(self.menu_button)

        self.open_button = Gtk.Button()
        self.open_button.set_image(Gtk.Image.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON))
        self.open_button.set_tooltip_text(i18n.t("header.open"))
        self.open_button.set_action_name("win.open")
        self.open_button.get_style_context().add_class("suggested-action")
        header.pack_start(self.open_button)

        self.find_button = Gtk.Button()
        self.find_button.set_image(Gtk.Image.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON))
        self.find_button.set_tooltip_text(i18n.t("header.find"))
        self.find_button.set_action_name("win.find")
        header.pack_end(self.find_button)

        self.toc_button = Gtk.ToggleButton()
        self.toc_button.set_image(Gtk.Image.new_from_icon_name("view-list-symbolic", Gtk.IconSize.BUTTON))
        self.toc_button.set_tooltip_text(i18n.t("header.toc"))
        self.toc_button.set_action_name("win.toggle-toc")
        header.pack_end(self.toc_button)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.title_label = Gtk.Label(xalign=0.5)
        self.title_label.get_style_context().add_class("mdv-title")
        self.subtitle_label = Gtk.Label(xalign=0.5)
        self.subtitle_label.get_style_context().add_class("mdv-subtitle")
        for label in (self.title_label, self.subtitle_label):
            label.set_ellipsize(self.toolkit.Pango.EllipsizeMode.MIDDLE)
            label.set_max_width_chars(48)
        title_box.pack_start(self.title_label, False, False, 0)
        title_box.pack_start(self.subtitle_label, False, False, 0)
        self.title_box = title_box
        header.set_custom_title(title_box)

    def _build_body(self) -> None:
        Gtk = self.toolkit.Gtk
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_show_border(False)
        self.notebook.connect("switch-page", self._on_switch_page)
        self.notebook.connect("page-removed", self._on_page_removed)

        new_tab_button = Gtk.Button()
        new_tab_button.set_image(Gtk.Image.new_from_icon_name("tab-new-symbolic", Gtk.IconSize.MENU))
        new_tab_button.set_relief(Gtk.ReliefStyle.NONE)
        new_tab_button.set_tooltip_text(i18n.t("tab.new"))
        new_tab_button.set_action_name("win.open-tab")
        new_tab_button.show_all()
        self.notebook.set_action_widget(new_tab_button, Gtk.PackType.END)

        self.statusbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.statusbar.get_style_context().add_class("mdv-statusbar")
        self.status_stats = Gtk.Label(xalign=0)
        self.status_stats.set_ellipsize(self.toolkit.Pango.EllipsizeMode.END)
        self.status_details = Gtk.Label(xalign=1)
        self.status_details.set_ellipsize(self.toolkit.Pango.EllipsizeMode.START)
        self.statusbar.pack_start(self.status_stats, False, False, 0)
        self.statusbar.pack_end(self.status_details, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.pack_start(self.notebook, True, True, 0)
        box.pack_start(self.statusbar, False, False, 0)
        self.window.add(box)

    # ------------------------------------------------------------------ Menue

    def _build_menu_model(self) -> Any:
        Gio = self.toolkit.Gio
        menu = Gio.Menu()

        file_section = Gio.Menu()
        file_section.append(i18n.t("menu.open"), "win.open")
        file_section.append(i18n.t("menu.open_tab"), "win.open-tab")
        file_section.append(i18n.t("menu.reload"), "win.reload")
        file_section.append(i18n.t("menu.export_html"), "win.export-html")
        file_section.append(i18n.t("menu.print"), "win.print")
        menu.append_section(None, file_section)

        self.recent_menu = Gio.Menu()
        menu.append_submenu(i18n.t("menu.recent"), self.recent_menu)

        view_section = Gio.Menu()
        view_section.append(i18n.t("menu.find"), "win.find")
        view_section.append(i18n.t("menu.toc"), "win.toggle-toc")
        view_section.append(i18n.t("menu.zoom_in"), "win.zoom-in")
        view_section.append(i18n.t("menu.zoom_out"), "win.zoom-out")
        view_section.append(i18n.t("menu.zoom_reset"), "win.zoom-reset")
        menu.append_section(i18n.t("menu.view"), view_section)

        theme_menu = Gio.Menu()
        for key, value in (("menu.theme_auto", "auto"), ("menu.theme_light", "light"), ("menu.theme_dark", "dark")):
            item = Gio.MenuItem.new(i18n.t(key), None)
            item.set_action_and_target_value("win.theme", self.toolkit.GLib.Variant.new_string(value))
            theme_menu.append_item(item)
        menu.append_submenu(i18n.t("menu.theme"), theme_menu)

        width_menu = Gio.Menu()
        for key, value in (
            ("menu.width_normal", "normal"),
            ("menu.width_wide", "wide"),
            ("menu.width_full", "full"),
        ):
            item = Gio.MenuItem.new(i18n.t(key), None)
            item.set_action_and_target_value("win.line-width", self.toolkit.GLib.Variant.new_string(value))
            width_menu.append_item(item)
        menu.append_submenu(i18n.t("menu.width"), width_menu)

        rendering = Gio.Menu()
        for key, action in (
            ("menu.auto_reload", "win.auto-reload"),
            ("menu.block_remote_images", "win.block-remote-images"),
            ("menu.breaks", "win.breaks"),
            ("menu.math", "win.math"),
            ("menu.math_inline", "win.math-inline"),
        ):
            item = Gio.MenuItem.new(i18n.t(key), action)
            rendering.append_item(item)
        menu.append_section(i18n.t("menu.rendering"), rendering)

        language_menu = Gio.Menu()
        for code, label in i18n.LANGUAGES.items():
            item = Gio.MenuItem.new(label, None)
            item.set_action_and_target_value("win.language", self.toolkit.GLib.Variant.new_string(code))
            language_menu.append_item(item)
        menu.append_submenu(i18n.t("menu.language"), language_menu)

        menu.append(i18n.t("menu.copy_path"), "win.copy-path")

        help_section = Gio.Menu()
        help_section.append(i18n.t("menu.shortcuts"), "win.shortcuts")
        help_section.append(i18n.t("menu.about"), "win.about")
        menu.append_section(i18n.t("menu.help"), help_section)

        quit_section = Gio.Menu()
        quit_section.append(i18n.t("menu.quit"), "app.quit")
        menu.append_section(None, quit_section)
        return menu

    def _refresh_recent_menu(self) -> None:
        Gio, GLib = self.toolkit.Gio, self.toolkit.GLib
        self.recent_menu.remove_all()
        recents = self.settings.recent_files()
        if not recents:
            item = Gio.MenuItem.new(i18n.t("menu.recent_empty"), None)
            item.set_attribute_value("enabled", GLib.Variant.new_boolean(False))
            self.recent_menu.append_item(item)
            return
        for entry in recents:
            name = Path(entry).name or entry
            item = Gio.MenuItem.new(f"{name} — {Path(entry).parent}", None)
            item.set_action_and_target_value("win.open-recent", GLib.Variant.new_string(entry))
            self.recent_menu.append_item(item)
        self.recent_menu.append(i18n.t("menu.recent_clear"), "win.clear-recents")

    # -------------------------------------------------------------- Aktionen

    def _action(self, name: str, handler: Callable[..., None], *, parameter: str | None = None, state: Any = None) -> Any:
        Gio, GLib = self.toolkit.Gio, self.toolkit.GLib
        if state is None and parameter is None:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda *_args: handler())
        elif parameter is not None and state is None:
            action = Gio.SimpleAction.new(name, GLib.VariantType.new(parameter))
            action.connect("activate", lambda _action, value: handler(value))
        else:
            action = Gio.SimpleAction.new_stateful(name, None, state)
            action.connect("change-state", lambda _action, value: handler(value))
        self.window.add_action(action)
        return action

    def _build_actions(self) -> None:
        GLib = self.toolkit.GLib
        self._action("open", self.on_open)
        self._action("open-tab", self.on_open_new_tab)
        self._action("reload", self.on_reload)
        self._action("close-tab", self.on_close_tab)
        self._action("find", self.on_find)
        self._action("find-next", self.on_find_next)
        self._action("find-prev", self.on_find_prev)
        self._action("zoom-in", lambda: self.set_zoom(self._next_zoom(+1)))
        self._action("zoom-out", lambda: self.set_zoom(self._next_zoom(-1)))
        self._action("zoom-reset", lambda: self.set_zoom(100))
        self._action("export-html", self.on_export_html)
        self._action("print", self.on_print)
        self._action("shortcuts", self.on_shortcuts)
        self._action("about", self.on_about)
        self._action("copy-path", self.on_copy_path)
        self._action("open-recent", self.on_open_recent, parameter="s")

        self.toc_action = self._action(
            "toggle-toc", self.on_toggle_toc, state=GLib.Variant.new_boolean(bool(self.settings.get("toc_visible")))
        )
        self.theme_action = self._action(
            "theme", self.on_theme, state=GLib.Variant.new_string(str(self.settings.get("theme")))
        )
        self.width_action = self._action(
            "line-width", self.on_line_width, state=GLib.Variant.new_string(str(self.settings.get("line_width")))
        )
        self.language_action = self._action(
            "language", self.on_language, state=GLib.Variant.new_string(str(self.settings.get("language")))
        )
        self.auto_reload_action = self._action(
            "auto-reload", self.on_auto_reload, state=GLib.Variant.new_boolean(bool(self.settings.get("auto_reload")))
        )
        self.block_images_action = self._action(
            "block-remote-images",
            self.on_block_remote_images,
            state=GLib.Variant.new_boolean(bool(self.settings.get("block_remote_images"))),
        )
        self.breaks_action = self._action(
            "breaks", self.on_breaks, state=GLib.Variant.new_boolean(bool(self.settings.get("breaks")))
        )
        self.math_action = self._action(
            "math", self.on_math, state=GLib.Variant.new_boolean(bool(self.settings.get("math")))
        )
        self.math_inline_action = self._action(
            "math-inline", self.on_math_inline, state=GLib.Variant.new_boolean(bool(self.settings.get("math_inline")))
        )
        self._action("clear-recents", self.on_clear_recents)

        self.menu_button.set_menu_model(self._build_menu_model())
        self._refresh_recent_menu()

    def _setup_accels(self) -> None:
        accels = {
            "win.open": ["<Primary>o"],
            "win.open-tab": ["<Primary><Shift>o"],
            "win.reload": ["<Primary>r", "F5"],
            "win.close-tab": ["<Primary>w"],
            "win.find": ["<Primary>f"],
            "win.find-next": ["F3"],
            "win.find-prev": ["<Shift>F3"],
            "win.toggle-toc": ["<Primary>b"],
            "win.zoom-in": ["<Primary>plus", "<Primary>equal", "<Primary>KP_Add"],
            "win.zoom-out": ["<Primary>minus", "<Primary>KP_Subtract"],
            "win.zoom-reset": ["<Primary>0"],
            "win.export-html": ["<Primary>e"],
            "win.print": ["<Primary>p"],
            "win.shortcuts": ["<Primary>question", "<Primary><Shift>slash"],
            "app.quit": ["<Primary>q"],
        }
        for name, keys in accels.items():
            try:
                self.application.set_accels_for_action(name, keys)
            except Exception:  # pragma: no cover - defensiv
                log.debug("Tastenkuerzel fuer %s nicht gesetzt", name)

    # ------------------------------------------------------- Drag und Drop

    def _setup_dnd(self) -> None:
        Gtk, Gdk = self.toolkit.Gtk, self.toolkit.Gdk
        try:
            targets = [Gtk.TargetEntry.new("text/uri-list", 0, 0)]
            self.window.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
            self.window.connect("drag-data-received", self._on_drag_data_received)
        except Exception:  # pragma: no cover
            log.exception("Drag-and-Drop konnte nicht eingerichtet werden")

    def _on_drag_data_received(self, _widget: Any, _context: Any, _x: int, _y: int, data: Any, _info: int, _time: int) -> None:
        Gio = self.toolkit.Gio
        try:
            uris = list(data.get_uris() or [])
        except Exception:  # pragma: no cover
            return
        paths = []
        for uri in uris:
            try:
                local = Gio.File.new_for_uri(uri).get_path()
            except Exception:  # pragma: no cover
                local = None
            if local:
                paths.append(local)
        self.open_paths(paths)

    # ------------------------------------------------------------- Tabs/Fenster

    def _new_page(self) -> ViewerPage:
        return ViewerPage(self.toolkit, self.settings, developer=self.developer)

    def new_tab(self, *, welcome_doc: bool = False, select: bool = True) -> Tab:
        Gtk = self.toolkit.Gtk
        page = self._new_page()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        label = Gtk.Label(label=i18n.t("header.untitled"))
        label.set_ellipsize(self.toolkit.Pango.EllipsizeMode.END)
        label.set_max_width_chars(24)
        close = Gtk.Button()
        close.set_image(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.MENU))
        close.set_relief(Gtk.ReliefStyle.NONE)
        close.set_tooltip_text(i18n.t("tab.close"))
        box.pack_start(label, False, False, 0)
        box.pack_end(close, False, False, 0)
        box.show_all()

        tab = Tab(page=page, label=box, label_text=label, close_button=close)
        close.connect("clicked", lambda *_args: self.close_tab(tab))

        page.on_ready = lambda: self._on_page_ready(tab)
        page.on_rendered = lambda message: self._on_page_rendered(tab, message)
        page.on_open_external = launch_external
        page.on_open_path = lambda url: self.open_uri(url)
        page.on_copy_text = self.copy_to_clipboard
        page.on_error = lambda message: self._show_error(message, i18n.t("error.js.title"))

        index = self.notebook.append_page(page.container, box)
        self.notebook.set_tab_reorderable(page.container, True)
        self.tabs.append(tab)
        self.notebook.set_current_page(index)
        page.load_page()

        if welcome_doc:
            page.show_welcome(welcome.build_welcome_markdown(), welcome.welcome_footer())

        if select:
            self.notebook.set_current_page(index)
        self._update_title()
        self._update_toc_button()
        return tab

    def tab_for_widget(self, widget: Any) -> Tab | None:
        for tab in self.tabs:
            if tab.page.container is widget:
                return tab
        return None

    def tab_for_path(self, path: str | Path) -> Tab | None:
        wanted = str(Path(path).expanduser())
        for tab in self.tabs:
            if tab.document is not None and str(tab.document.path) == wanted:
                return tab
        return None

    def current_tab(self) -> Tab | None:
        index = self.notebook.get_current_page()
        if index < 0:
            return None
        return self.tab_for_widget(self.notebook.get_nth_page(index))

    def _select_tab(self, tab: Tab) -> None:
        index = self.notebook.page_num(tab.page.container)
        if index >= 0:
            self.notebook.set_current_page(index)
            self.notebook.set_current_page(index)

    def close_tab(self, tab: Tab | None = None) -> None:
        tab = tab or self.current_tab()
        if tab is None:
            return
        self._stop_monitor(tab)
        index = self.notebook.page_num(tab.page.container)
        if index < 0:
            return
        self.notebook.remove_page(index)
        if tab in self.tabs:
            self.tabs.remove(tab)
        if not self.tabs:
            # Nie ohne Inhalt dastehen: Startseite anzeigen
            self.new_tab(welcome_doc=True)
        else:
            self._update_title()
            self._update_status(self.current_tab())

    # ------------------------------------------------------------ Datei oeffnen

    def open_paths(self, paths: list[str], *, new_tabs: bool | None = None) -> None:
        """Oeffnet mehrere Dateien; die erste darf den Willkommens-Tab uebernehmen."""
        for position, path in enumerate(paths):
            if new_tabs is not None:
                use_new_tab = new_tabs
            elif position == 0 and self._current_is_welcome():
                use_new_tab = False
            else:
                use_new_tab = True
            self.open_path(path, new_tab=use_new_tab)

    def _current_is_welcome(self) -> bool:
        tab = self.current_tab()
        return tab is None or tab.document is None

    def open_path(
        self,
        path: str | Path,
        *,
        new_tab: bool = True,
        keep_scroll: bool = False,
        on_rendered: Callable[[Tab], None] | None = None,
    ) -> Tab | None:
        """Oeffnet eine Datei; zeigt Fehler als Dokument im Viewer an."""
        target = Path(path).expanduser()
        existing = self.tab_for_path(target)
        if existing is not None and not new_tab:
            self._select_tab(existing)
            return existing

        try:
            document = read_document(target)
        except DocumentError as error:
            return self.show_error_document(error.message(), path=str(target))

        if new_tab or not self.tabs:
            tab = self.new_tab(select=True)
        else:
            tab = self.current_tab() or self.new_tab(select=True)

        tab.document = document
        tab.kind = "document"
        tab.error_message = None
        tab.render_callback = on_rendered
        tab.page.show_document(document, keep_scroll=keep_scroll)
        tab.label_text.set_text(document.name)
        tab.label.set_tooltip_text(i18n.t("tab.tooltip", name=document.name, path=str(document.path)))
        self._center_title(document)

        self.settings.add_recent(document.path)
        self._refresh_recent_menu()
        self._start_monitor(tab)
        self._update_title()
        self._update_status(tab)
        return tab

    def open_uri(self, uri: str) -> Tab | None:
        """Oeffnet eine file://-URL (aus Links im Dokument oder per Drag-and-Drop)."""
        Gio = self.toolkit.Gio
        try:
            gfile = Gio.File.new_for_uri(uri)
            local = gfile.get_path()
        except Exception:  # pragma: no cover
            local = None
        if not local:
            log.debug("Kein lokaler Pfad fuer %s", uri)
            return None
        return self.open_path(local, new_tab=True)

    def show_error_document(self, message: str, *, path: str | None = None) -> Tab:
        """Zeigt eine Fehlermeldung als Markdown-Dokument im aktuellen Tab."""
        tab = self.current_tab()
        if tab is None or tab.document is not None:
            tab = self.new_tab(select=True)
        paragraphs = [line.strip() for line in message.splitlines() if line.strip()]
        parts = [f"# ⚠️ {i18n.t('error.title')}", ""]
        parts.extend(paragraphs)
        if path:
            parts += ["", "---", "", f"`{path}`"]
        text = "\n\n".join(parts) + "\n"
        tab.error_message = message
        tab.kind = "error"
        tab.label_text.set_text(i18n.t("error.title"))
        tab.page.show_error(text)
        self._update_title()
        self.status_stats.set_text(message.splitlines()[0])
        self.status_details.set_text(path or "")
        if path:
            self._center_title(None, subtitle=path)
        return tab

    def _center_title(self, document: Document | None, *, subtitle: str | None = None) -> None:
        name = document.name if document else (subtitle or i18n.t("header.untitled"))
        self.title_label.set_text(name)
        if document is not None:
            self.subtitle_label.set_text(str(document.path.parent))
        else:
            self.subtitle_label.set_text(subtitle or "")

    def _update_title(self) -> None:
        tab = self.current_tab()
        if tab is None:
            self.window.set_title(APP_NAME)
            return
        if tab.document is not None:
            self.window.set_title(f"{tab.document.name} — {APP_NAME}")
        elif tab.kind == "error":
            self.window.set_title(f"{i18n.t('error.title')} — {APP_NAME}")
        else:
            self.window.set_title(APP_NAME)

    def _update_toc_button(self) -> None:
        visible = bool(self.settings.get("toc_visible"))
        try:
            self.toc_button.set_active(visible)
        except Exception:  # pragma: no cover
            pass

    def _update_status(self, tab: Tab | None = None) -> None:
        tab = tab or self.current_tab()
        if tab is None:
            self.status_stats.set_text(i18n.t("status.no_file"))
            self.status_details.set_text("")
            return
        stats = tab.page.stats or {}
        words = int(stats.get("words", 0) or 0)
        if words:
            self.status_stats.set_text(
                i18n.t(
                    "status.stats",
                    words=format_number(words),
                    characters=format_number(stats.get("characters", 0)),
                    minutes=stats.get("readingMinutes", 0),
                )
            )
        else:
            self.status_stats.set_text(i18n.t("status.stats_empty"))

        if tab.document is not None:
            details = i18n.t(
                "status.details",
                path=str(tab.document.path),
                size=format_size(tab.document.size),
                encoding=tab.document.encoding.upper(),
            )
            details += " · " + i18n.t("status.modified", time=format_timestamp(tab.document.modified))
            if tab.last_reload:
                details += " · " + i18n.t("status.reloaded", time=format_clock(tab.last_reload))
            self.status_details.set_text(details)
            self._center_title(tab.document)
        else:
            self.status_details.set_text(f"{APP_NAME} {__version__}")

    # ------------------------------------------------------------ Dateibeobachter

    def _start_monitor(self, tab: Tab) -> None:
        Gio = self.toolkit.Gio
        self._stop_monitor(tab)
        if tab.document is None or not self.settings.get("auto_reload"):
            return
        try:
            flags = getattr(Gio.FileMonitorFlags, "WATCH_MOVES", Gio.FileMonitorFlags.NONE)
            monitor = Gio.File.new_for_path(str(tab.document.path.parent)).monitor_directory(flags, None)
            monitor.connect("changed", self._on_monitor_changed, tab)
            tab.monitor = monitor
        except Exception:  # pragma: no cover
            log.exception("Dateibeobachter konnte nicht gestartet werden")

    def _stop_monitor(self, tab: Tab) -> None:
        GLib = self.toolkit.GLib
        if tab.reload_source:
            try:
                GLib.source_remove(tab.reload_source)
            except Exception:  # pragma: no cover
                pass
            tab.reload_source = 0
        if tab.monitor is not None:
            try:
                tab.monitor.cancel()
            except Exception:  # pragma: no cover
                pass
            tab.monitor = None

    def _on_monitor_changed(self, _monitor: Any, file: Any, _other: Any, _event: Any, tab: Tab) -> None:
        GLib = self.toolkit.GLib
        if tab.document is None:
            return
        try:
            name = file.get_basename() if file is not None else None
        except Exception:  # pragma: no cover
            name = None
        if name is not None and name != tab.document.name:
            return
        if not self.settings.get("auto_reload"):
            return
        if tab.reload_source:
            try:
                GLib.source_remove(tab.reload_source)
            except Exception:  # pragma: no cover
                pass
        tab.reload_source = GLib.timeout_add(300, self._auto_reload, tab)

    def _auto_reload(self, tab: Tab) -> bool:
        """Wird 300 ms nach der letzten Aenderung aufgerufen."""
        tab.reload_source = 0
        if tab.document is None:
            return False
        try:
            document = read_document(tab.document.path)
        except DocumentError as error:
            log.warning("Automatisches Neuladen fehlgeschlagen: %s", error.message())
            if tab.page.page_loaded:
                tab.page.toast(error.message())
            self.status_details.set_text(error.message().splitlines()[0])
            return False
        if document.text == tab.document.text and document.modified == tab.document.modified:
            return False  # nichts inhaltliches geaendert
        tab.document = document
        tab.last_reload = __import__("time").time()
        notice = document.notice()
        extra = i18n.t("notice.changed")
        tab.page.show_document(document, notice=f"{extra}\n{notice}" if notice else extra, keep_scroll=True)
        self._update_status(tab)
        return False

    def refresh_auto_reload(self) -> None:
        """Nach dem Umschalten der Einstellung: Beobachter neu setzen."""
        for tab in self.tabs:
            if self.settings.get("auto_reload"):
                self._start_monitor(tab)
            else:
                self._stop_monitor(tab)

    # ------------------------------------------------------ Aktionen (Inhalt)

    def on_open(self) -> None:
        self._choose_and_open(new_tab=None)

    def on_open_new_tab(self) -> None:
        self._choose_and_open(new_tab=True)

    def _choose_and_open(self, *, new_tab: bool | None) -> None:
        Gtk = self.toolkit.Gtk
        chooser = Gtk.FileChooserNative.new(
            i18n.t("open.title"), self.window, Gtk.FileChooserAction.OPEN, i18n.t("open.accept"), i18n.t("open.cancel")
        )
        try:
            markdown_filter = Gtk.FileFilter()
            markdown_filter.set_name(i18n.t("open.filter_markdown"))
            for pattern in ("*.md", "*.markdown", "*.mdown", "*.mkd", "*.mkdn", "*.mdwn", "*.mdtxt", "*.mdtext"):
                markdown_filter.add_pattern(pattern)
            markdown_filter.add_mime_type("text/markdown")
            chooser.add_filter(markdown_filter)

            text_filter = Gtk.FileFilter()
            text_filter.set_name(i18n.t("open.filter_text"))
            text_filter.add_mime_type("text/plain")
            for pattern in ("*.txt", "*.text", "*.rst"):
                text_filter.add_pattern(pattern)
            chooser.add_filter(text_filter)

            all_filter = Gtk.FileFilter()
            all_filter.set_name(i18n.t("open.filter_all"))
            all_filter.add_pattern("*")
            chooser.add_filter(all_filter)

            response = chooser.run()
            if response == Gtk.ResponseType.ACCEPT:
                filename = chooser.get_filename()
                if filename:
                    self.open_path(filename, new_tab=bool(new_tab) or self._current_is_welcome() is False)
        finally:
            chooser.destroy()

    def on_open_recent(self, value: Any) -> None:
        entry = value.get_string() if hasattr(value, "get_string") else str(value)
        self.open_path(entry, new_tab=not self.tabs or not self._current_is_welcome())

    def on_clear_recents(self) -> None:
        self.settings.clear_recents()
        self._refresh_recent_menu()

    def on_reload(self) -> None:
        tab = self.current_tab()
        if tab is None:
            return
        if tab.document is not None:
            self.open_path(tab.document.path, new_tab=False, keep_scroll=True)
        elif tab.page.page_loaded:
            tab.page.reload_page()

    def on_close_tab(self) -> None:
        self.close_tab()

    def on_find(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.page.open_find()

    def on_find_next(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.page.find_again()

    def on_find_prev(self) -> None:
        tab = self.current_tab()
        if tab is not None:
            tab.page.find_previous()

    def _next_zoom(self, direction: int) -> int:
        current = int(self.settings.get("zoom"))
        steps = list(ZOOM_STEPS)
        if direction > 0:
            for value in steps:
                if value > current:
                    return value
            return steps[-1]
        for value in reversed(steps):
            if value < current:
                return value
        return steps[0]

    def set_zoom(self, zoom: int) -> None:
        zoom = max(50, min(250, int(zoom)))
        self.settings.set("zoom", zoom)
        for tab in self.tabs:
            tab.page.set_zoom(zoom)
        tab = self.current_tab()
        if tab is not None:
            tab.page.toast(i18n.t("toast.zoom", zoom=zoom))

    def on_toggle_toc(self, value: Any) -> None:
        visible = value.get_boolean() if hasattr(value, "get_boolean") else bool(value)
        self.toc_action.set_state(self.toolkit.GLib.Variant.new_boolean(visible))
        self.settings.set("toc_visible", visible)
        for tab in self.tabs:
            tab.page.update_settings()

    def _resolve_theme(self) -> str:
        theme = str(self.settings.get("theme"))
        if theme != "auto":
            return theme
        try:
            gtk_settings = self.toolkit.Gtk.Settings.get_default()
            prefer_dark = bool(gtk_settings.get_property("gtk-application-prefer-dark-theme"))
        except Exception:  # pragma: no cover
            prefer_dark = False
        return "dark" if prefer_dark else "light"

    def on_theme(self, value: Any) -> None:
        theme = value.get_string() if hasattr(value, "get_string") else str(value)
        self.theme_action.set_state(self.toolkit.GLib.Variant.new_string(theme))
        self.settings.set("theme", theme)
        for tab in self.tabs:
            tab.page.set_theme(theme)

    def on_line_width(self, value: Any) -> None:
        width = value.get_string() if hasattr(value, "get_string") else str(value)
        self.width_action.set_state(self.toolkit.GLib.Variant.new_string(width))
        self.settings.set("line_width", width)
        for tab in self.tabs:
            tab.page.update_settings()

    def on_language(self, value: Any) -> None:
        language = value.get_string() if hasattr(value, "get_string") else str(value)
        self.language_action.set_state(self.toolkit.GLib.Variant.new_string(language))
        self.settings.set("language", language)
        i18n.set_language(language)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Alle sichtbaren Texte nach einem Sprachwechsel neu setzen."""
        i18n.set_language(self.settings.get("language"))
        for tab in self.tabs:
            if tab.document is None and tab.kind in {"welcome", "error"}:
                if tab.kind == "welcome":
                    tab.page.show_welcome(welcome.build_welcome_markdown(), welcome.welcome_footer())
                continue
            tab.page.update_settings()
            tab.label_text.set_text(tab.title)
        self.menu_button.set_tooltip_text(i18n.t("menu.title"))
        self.open_button.set_tooltip_text(i18n.t("header.open"))
        self.find_button.set_tooltip_text(i18n.t("header.find"))
        self.toc_button.set_tooltip_text(i18n.t("header.toc"))
        self.menu_button.set_menu_model(self._build_menu_model())
        self._refresh_recent_menu()
        self._update_toc_button()
        self._update_title()
        self._update_status(self.current_tab())

    def on_auto_reload(self, value: Any) -> None:
        enabled = value.get_boolean() if hasattr(value, "get_boolean") else bool(value)
        self.auto_reload_action.set_state(self.toolkit.GLib.Variant.new_boolean(enabled))
        self.settings.set("auto_reload", enabled)
        self.refresh_auto_reload()

    def on_block_remote_images(self, value: Any) -> None:
        enabled = value.get_boolean() if hasattr(value, "get_boolean") else bool(value)
        self.block_images_action.set_state(self.toolkit.GLib.Variant.new_boolean(enabled))
        self.settings.set("block_remote_images", enabled)
        for tab in self.tabs:
            tab.page.update_settings()
        tab = self.current_tab()
        if tab is not None and enabled:
            tab.page.toast(i18n.t("notice.remote_images"))

    def on_breaks(self, value: Any) -> None:
        enabled = value.get_boolean() if hasattr(value, "get_boolean") else bool(value)
        self.breaks_action.set_state(self.toolkit.GLib.Variant.new_boolean(enabled))
        self.settings.set("breaks", enabled)
        for tab in self.tabs:
            tab.page.update_settings()

    def on_math(self, value: Any) -> None:
        enabled = value.get_boolean() if hasattr(value, "get_boolean") else bool(value)
        self.math_action.set_state(self.toolkit.GLib.Variant.new_boolean(enabled))
        self.settings.set("math", enabled)
        for tab in self.tabs:
            tab.page.update_settings()

    def on_math_inline(self, value: Any) -> None:
        enabled = value.get_boolean() if hasattr(value, "get_boolean") else bool(value)
        self.math_inline_action.set_state(self.toolkit.GLib.Variant.new_boolean(enabled))
        self.settings.set("math_inline", enabled)
        for tab in self.tabs:
            tab.page.update_settings()

    # ------------------------------------------------------------------ Export

    def on_export_html(self) -> None:
        Gtk = self.toolkit.Gtk
        tab = self.current_tab()
        if tab is None or tab.document is None:
            self._show_error(i18n.t("status.no_file"))
            return
        document = tab.document
        chooser = Gtk.FileChooserNative.new(
            i18n.t("export.title"), self.window, Gtk.FileChooserAction.SAVE, i18n.t("export.accept"), i18n.t("open.cancel")
        )
        try:
            chooser.set_do_overwrite_confirmation(True)
            chooser.set_current_name(exporter.suggested_file_name(document.path))
            chooser.set_current_folder(str(document.path.parent))
            html_filter = Gtk.FileFilter()
            html_filter.set_name(i18n.t("export.filter_html"))
            html_filter.add_pattern("*.html")
            html_filter.add_pattern("*.htm")
            html_filter.add_mime_type("text/html")
            chooser.add_filter(html_filter)
            response = chooser.run()
            if response != Gtk.ResponseType.ACCEPT:
                return
            target = chooser.get_filename()
        finally:
            chooser.destroy()
        if not target:
            return

        self.export_html_to(target, tab)

    def export_html_to(
        self, target: str | Path, tab: Tab | None = None, *, on_done: Callable[[bool], None] | None = None
    ) -> None:
        """Rendertes HTML holen, als eigenstaendige HTML-Datei speichern."""

        def finish(success: bool) -> None:
            if on_done is not None:
                on_done(success)

        tab = tab or self.current_tab()
        if tab is None or tab.document is None:
            self._show_error(i18n.t("status.no_file"))
            finish(False)
            return
        document = tab.document

        def write(body_html: str | None) -> None:
            if not body_html:
                self._show_error(i18n.t("export.failed", error=i18n.t("error.unknown")))
                finish(False)
                return
            try:
                content = exporter.build_standalone_html(
                    document.name,
                    body_html,
                    theme=self._resolve_theme(),
                    language=i18n.get_language(),
                    base_href=document.base_href,
                    source_path=str(document.path),
                )
                written = exporter.write_html(target, content)
            except OSError as error:
                log.warning("Export fehlgeschlagen: %s", error)
                self._show_error(i18n.t("export.failed", error=str(error)))
                finish(False)
                return
            message = i18n.t("export.done", path=str(written))
            self.status_details.set_text(message)
            if tab.page.page_loaded:
                tab.page.toast(message)
            log.info("%s", message)
            finish(True)

        tab.page.request_body_html(write)

    def on_print(self) -> None:
        tab = self.current_tab()
        if tab is None:
            return
        if can_print(self.toolkit, tab.page.webview) and tab.page.print_page():
            return
        self._show_info(i18n.t("export.printing"))

    # ------------------------------------------------------------- Kleinkram

    def on_copy_path(self) -> None:
        tab = self.current_tab()
        if tab is not None and tab.document is not None:
            self.copy_to_clipboard(str(tab.document.path), notify=True)

    def copy_to_clipboard(self, text: str, *, notify: bool = False) -> bool:
        """Kopiert Text in die GTK-Zwischenablage (Rueckfall fuer den Viewer)."""
        Gtk, Gdk = self.toolkit.Gtk, self.toolkit.Gdk
        success = False
        try:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text, -1)
            clipboard.store()
            success = True
        except Exception:  # pragma: no cover
            log.exception("Kopieren fehlgeschlagen")
        if notify:
            tab = self.current_tab()
            if tab is not None:
                tab.page.toast(i18n.t("toast.copied") if success else i18n.t("toast.copy_failed"))
        return success

    def on_shortcuts(self) -> None:
        Gtk = self.toolkit.Gtk
        dialog = Gtk.Dialog(title=i18n.t("shortcuts.title"), transient_for=self.window, modal=True)
        dialog.add_button(i18n.t("shortcuts.close"), Gtk.ResponseType.CLOSE)
        dialog.set_default_size(520, 520)
        grid = Gtk.Grid(column_spacing=24, row_spacing=6, margin=16)
        for row, (keys, text) in enumerate(i18n.shortcuts_table()):
            key_label = Gtk.Label(xalign=0)
            key_label.set_markup(f"<tt>{self.toolkit.GLib.markup_escape_text(keys)}</tt>")
            grid.attach(key_label, 0, row, 1, 1)
            grid.attach(Gtk.Label(label=text, xalign=0), 1, row, 1, 1)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(grid)
        dialog.get_content_area().add(scroller)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def on_about(self) -> None:
        Gtk = self.toolkit.Gtk
        dialog = Gtk.AboutDialog(transient_for=self.window, modal=True)
        dialog.set_program_name(APP_NAME)
        dialog.set_version(__version__)
        dialog.set_comments(i18n.t("about.comments"))
        dialog.set_website(WEBSITE)
        dialog.set_website_label(i18n.t("about.website"))
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_copyright(f"© 2026 tikogaming1 · {__version__}")
        dialog.set_authors(["tikogaming1"])
        dialog.set_logo_icon_name("md-viewer")
        icon = paths.icon_file()
        if icon is not None:
            try:
                dialog.set_logo(self.toolkit.GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon), 128, 128, True))
            except Exception:  # pragma: no cover
                pass
        dialog.run()
        dialog.destroy()

    def _show_error(self, message: str, title: str | None = None) -> None:
        self._message_dialog(message, title or i18n.t("error.title"), self.toolkit.Gtk.MessageType.ERROR)

    def _show_info(self, message: str) -> None:
        self._message_dialog(message, APP_NAME, self.toolkit.Gtk.MessageType.INFO)

    def _message_dialog(self, message: str, title: str, message_type: Any) -> None:
        Gtk = self.toolkit.Gtk
        lines = message.splitlines() or [message]
        dialog = Gtk.MessageDialog(
            transient_for=self.window,
            modal=True,
            message_type=message_type,
            buttons=Gtk.ButtonsType.OK,
            text=lines[0],
        )
        if len(lines) > 1:
            dialog.format_secondary_text("\n".join(lines[1:]))
        dialog.set_title(title)
        dialog.run()
        dialog.destroy()

    # --------------------------------------------------------------- Signale

    def _on_page_ready(self, tab: Tab) -> None:
        pass

    def _on_page_rendered(self, tab: Tab, message: dict[str, Any]) -> None:
        if tab is self.current_tab():
            self._update_status(tab)
        callback, tab.render_callback = tab.render_callback, None
        if callback is not None:
            try:
                callback(tab)
            except Exception:  # pragma: no cover - darf die Anzeige nicht stoeren
                log.exception("Fehler im Rendern-Rueckruf")

    def _on_switch_page(self, _notebook: Any, _page: Any, _index: int) -> None:
        tab = self.current_tab()
        self._update_title()
        self._update_status(tab)
        if tab is not None:
            tab.page.grab_focus()

    def _on_page_removed(self, _notebook: Any, _page: Any, _index: int) -> None:
        self._update_title()

    def _on_delete_event(self, _window: Any, _event: Any) -> bool:
        self.save_window_state()
        return False

    def save_window_state(self) -> None:
        try:
            width, height = self.window.get_size()
            self.settings.update(
                {
                    "window_width": max(480, int(width)),
                    "window_height": max(360, int(height)),
                    "window_maximized": bool(self.window.is_maximized()),
                }
            )
        except Exception:  # pragma: no cover
            pass

    def present(self, *, welcome_doc: bool = False) -> None:
        self.window.show_all()
        if welcome_doc and not self.tabs:
            self.new_tab(welcome_doc=True)
        self.window.present()

    def destroy(self) -> None:
        for tab in list(self.tabs):
            self._stop_monitor(tab)
        try:
            self.window.destroy()
        except Exception:  # pragma: no cover
            pass
