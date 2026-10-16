"""Attrappen fuer gi.repository (Gtk, Gdk, Gio, GLib, Pango, WebKit2)."""

from __future__ import annotations

import sys
import types
from typing import Any

MODULES = ("Gtk", "Gdk", "GdkPixbuf", "Gio", "GLib", "Pango", "WebKit2", "WebKit")


class _Meta(type):
    """Klassen-Attribute (z. B. Gtk.ButtonsType.OK) automatisch erzeugen."""

    def __getattr__(cls, item: str) -> Any:
        if item.startswith("__"):
            raise AttributeError(item)
        value = _make_class(f"{cls.__name__}.{item}")
        setattr(cls, item, value)
        return value


class StubObject(metaclass=_Meta):
    """Objekt, das jeden Aufruf und Zugriff uebernimmt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._args = args
        self._kwargs = kwargs

    # -- Methoden-Attrappen ------------------------------------------------
    def __getattr__(self, item: str) -> Any:
        if item.startswith("__"):
            raise AttributeError(item)

        def method(*_args: Any, **_kwargs: Any) -> "StubObject":
            return StubObject()

        setattr(self, item, method)
        return method

    # -- Buchhaltung -------------------------------------------------------
    def __int__(self) -> int:
        return 0

    def __index__(self) -> int:
        return 0

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
        return f"<{type(self).__name__}>"

    def __lt__(self, other: Any) -> bool:
        return 0 < _as_int(other)

    def __le__(self, other: Any) -> bool:
        return 0 <= _as_int(other)

    def __gt__(self, other: Any) -> bool:
        return 0 > _as_int(other)

    def __ge__(self, other: Any) -> bool:
        return 0 >= _as_int(other)

    def __eq__(self, other: Any) -> bool:
        return 0 == _as_int(other)

    def __hash__(self) -> int:
        return id(self)

    def __iter__(self):
        return iter(())


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _make_class(name: str) -> type:
    short = name.split(".")[-1]
    return _Meta(short, (StubObject,), {"__module__": __name__})


# --------------------------------------------------------------- Widgets


class Widget(StubObject):
    """Basis fuer Widgets, die Signale wirklich weiterleiten."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.signals: dict[str, list[tuple[Any, tuple]]] = {}
        self.visible = False

    def connect(self, signal: str, handler: Any, *extra: Any) -> int:
        self.signals.setdefault(signal, []).append((handler, extra))
        return len(self.signals[signal])

    def emit(self, signal: str, *args: Any) -> None:
        for handler, extra in self.signals.get(signal, []):
            handler(self, *args, *extra)

    def show_all(self) -> None:
        self.visible = True

    def show(self) -> None:
        self.visible = True


class Notebook(Widget):
    """Gtk.Notebook mit echter Seitenverwaltung (fuer Tab-Tests)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pages: list[Any] = []
        self.labels: list[Any] = []
        self.current = -1
        self.action_widget = None

    def append_page(self, child: Any, label: Any) -> int:
        self.pages.append(child)
        self.labels.append(label)
        if self.current < 0:
            self.current = 0
        return len(self.pages) - 1

    def page_num(self, child: Any) -> int:
        try:
            return self.pages.index(child)
        except ValueError:
            return -1

    def get_nth_page(self, index: int) -> Any:
        if 0 <= index < len(self.pages):
            return self.pages[index]
        return None

    def get_current_page(self) -> int:
        return self.current

    def set_current_page(self, index: int) -> None:
        previous = self.current
        self.current = index
        if 0 <= index < len(self.pages) and previous != index:
            self.emit("switch-page", self.pages[index], index)

    def remove_page(self, index: int) -> None:
        if 0 <= index < len(self.pages):
            self.pages.pop(index)
            self.labels.pop(index)
            self.current = min(self.current, len(self.pages) - 1)

    def set_action_widget(self, widget: Any, _pack_type: Any) -> None:
        self.action_widget = widget

    def set_tab_reorderable(self, *_args: Any) -> None:
        pass

    def set_scrollable(self, *_args: Any) -> None:
        pass

    def set_show_border(self, *_args: Any) -> None:
        pass


class Variant(StubObject):
    """GLib.Variant mit echtem Wert (wird fuer Action-Zustaende gebraucht)."""

    def __init__(self, value: Any = None) -> None:
        super().__init__()
        self.value = value

    @classmethod
    def new_boolean(cls, value: Any) -> "Variant":
        return cls(bool(value))

    @classmethod
    def new_string(cls, value: Any) -> "Variant":
        return cls(str(value))

    @classmethod
    def new_int32(cls, value: Any) -> "Variant":
        return cls(int(value))

    def get_boolean(self) -> bool:
        return bool(self.value)

    def get_string(self) -> str:
        return str(self.value)

    def get_int32(self) -> int:
        return int(self.value)

    def __str__(self) -> str:
        return str(self.value)


class Label(Widget):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.text = str(kwargs.get("label", ""))
        self.markup = ""

    def set_text(self, text: Any) -> None:
        self.text = str(text)

    def get_text(self) -> str:
        return self.text

    def set_markup(self, markup: str) -> None:
        self.markup = markup

    def get_label(self) -> str:
        return self.text


class ToggleButton(Widget):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.active = False

    def set_active(self, active: bool) -> None:
        self.active = bool(active)

    def get_active(self) -> bool:
        return self.active

    def set_action_name(self, name: str) -> None:
        self.action_name = name

    def toggle(self) -> None:
        self.active = not self.active
        self.emit("toggled", self.active)


class Button(ToggleButton):
    def set_relief(self, *_args: Any) -> None:
        pass

    def click(self) -> None:
        self.emit("clicked")


class Window(Widget):
    """Gtk.Window/ApplicationWindow mit Aktionsregister."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actions: dict[str, Any] = {}
        self.title = kwargs.get("title", "")
        self.maximized = False
        self.size = (1024, 768)

    def add_action(self, action: Any) -> None:
        self.actions[getattr(action, "name", str(action))] = action

    def set_title(self, title: str) -> None:
        self.title = title

    def get_title(self) -> str:
        return self.title

    def set_default_size(self, width: int, height: int) -> None:
        self.size = (int(width), int(height))

    def get_size(self) -> tuple[int, int]:
        return self.size

    def maximize(self) -> None:
        self.maximized = True

    def is_maximized(self) -> bool:
        return self.maximized

    def set_titlebar(self, *_args: Any) -> None:
        pass

    def set_icon_name(self, *_args: Any) -> None:
        pass

    def add(self, _widget: Any) -> None:
        pass

    def present(self) -> None:
        self.visible = True

    def drag_dest_set(self, *_args: Any) -> None:
        pass

    def get_size_request(self) -> tuple[int, int]:
        return self.size


class Application(StubObject):
    """Gtk.Application: merkt sich Aktionen und Tastenkombinationen."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.actions: dict[str, str] = {}
        self.accels: dict[str, list[str]] = {}
        self.quit_called = False

    def set_accels_for_action(self, name: str, keys: list[str]) -> None:
        self.accels[name] = list(keys)

    def get_accels_for_action(self, name: str) -> list[str]:
        return self.accels.get(name, [])

    def quit(self) -> None:
        self.quit_called = True

    def run(self, _argv: list[str]) -> int:
        return 0


class SimpleAction(Widget):
    """Gio.SimpleAction: Handler aufzeichnen und ausloesen koennen."""

    def __init__(self, name: str | None = None, parameter_type: Any = None, state: Any = None) -> None:
        super().__init__()
        self.name = name
        self.parameter_type = parameter_type
        self.state = state
        self.active_parameters: list[Any] = []

    @classmethod
    def new(cls, name: str, parameter_type: Any) -> "SimpleAction":
        return cls(name, parameter_type)

    @classmethod
    def new_stateful(cls, name: str, parameter_type: Any, state: Any) -> "SimpleAction":
        return cls(name, parameter_type, state)

    def set_state(self, state: Any) -> None:
        # Wie bei GSimpleAction: set_state loest *kein* change-state aus.
        self.state = state

    def get_state(self) -> Any:
        return self.state

    def activate(self, parameter: Any = None) -> None:
        self.active_parameters.append(parameter)
        for handler, _extra in self.signals.get("activate", []):
            handler(self, parameter)

    def change_state(self, value: Any) -> None:
        for handler, _extra in self.signals.get("change-state", []):
            handler(self, value)

    def __str__(self) -> str:
        return str(self.name)


class Settings(StubObject):
    """Gtk.Settings mit gespeicherten Eigenschaften."""

    _instance: "Settings | None" = None

    def __init__(self) -> None:
        super().__init__()
        self.properties: dict[str, Any] = {"gtk-application-prefer-dark-theme": False}

    @classmethod
    def get_default(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_property(self, name: str) -> Any:
        return self.properties.get(name)

    def set_property(self, name: str, value: Any) -> None:
        self.properties[name] = value


class FileFilter(StubObject):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.name = ""
        self.patterns: list[str] = []

    def set_name(self, name: str) -> None:
        self.name = name

    def add_pattern(self, pattern: str) -> None:
        self.patterns.append(pattern)

    def add_mime_type(self, _mime: str) -> None:
        pass


class Clipboard(StubObject):
    text: str | None = None

    @classmethod
    def get(cls, _selection: Any) -> "Clipboard":
        cls._instance = cls()
        return cls._instance

    def set_text(self, text: str, _length: int) -> None:
        Clipboard.text = text

    def store(self) -> None:
        pass


class File(StubObject):
    """Gio.File mit echtem Pfad (fuer file://-URLs aus Links/Drag und Drop)."""

    def __init__(self, path: Any = None) -> None:
        super().__init__()
        self.path = str(path) if path else None

    @classmethod
    def new_for_path(cls, path: Any) -> "File":
        return cls(path)

    @classmethod
    def new_for_uri(cls, uri: str) -> "File":
        from urllib.parse import unquote, urlparse

        parsed = urlparse(str(uri))
        if parsed.scheme != "file":
            return cls(None)
        return cls(unquote(parsed.path))

    def get_path(self) -> str | None:
        return self.path

    def get_basename(self) -> str | None:
        import os

        return os.path.basename(self.path) if self.path else None

    def monitor_directory(self, *_args: Any) -> "Widget":
        return Widget()

    def monitor_file(self, *_args: Any) -> "Widget":
        return Widget()


class _StubValue(StubObject):
    #: In WebKitGTK 4.1 hat ein JSC.Value kein get_js_value() - genau wie hier.
    get_js_value = None

    def __init__(self, text: str = "") -> None:
        super().__init__()
        self._text = text

    def to_string(self) -> str:
        return self._text

    def is_string(self) -> bool:
        return True


class UserContentManager(Widget):
    def __init__(self) -> None:
        super().__init__()
        self.handlers: list[str] = []

    def register_script_message_handler(self, name: str) -> None:
        self.handlers.append(name)


class WebView(Widget):
    """WebKit2.WebView mit aufgezeichneten Skriptaufrufen."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.scripts: list[str] = []
        self.loaded_uris: list[str] = []
        self.result_text = ""
        self._settings = StubObject()
        self._manager = UserContentManager()

    # -- API, die der Adapter benutzt --------------------------------------
    def get_settings(self) -> Any:
        return self._settings

    def get_user_content_manager(self) -> Any:
        return self._manager

    def load_uri(self, uri: str) -> None:
        self.loaded_uris.append(uri)

    def reload(self) -> None:
        self.loaded_uris.append("<reload>")

    def evaluate_javascript(self, script: str, _length: int, _world: Any, _uri: Any, _cancel: Any, callback: Any, user_data: Any) -> None:
        self.scripts.append(script)
        if callback is not None:
            callback(self, None, user_data)

    def evaluate_javascript_finish(self, _result: Any) -> Any:
        return _StubValue(self.result_text)

    # -- Testhilfen --------------------------------------------------------
    def last_script(self) -> str:
        return self.scripts[-1] if self.scripts else ""


class CssProvider(StubObject):
    def load_from_data(self, _data: Any) -> None:  # noqa: D401
        self.loaded = True


# --------------------------------------------------------------- Module


def _build_module(name: str, **special: Any) -> types.ModuleType:
    module = types.ModuleType(f"gi.repository.{name}")
    module.__dict__.update(special)
    module.__stub__ = True

    def __getattr__(item: str, _name: str = name) -> Any:
        if item.startswith("__"):
            raise AttributeError(item)
        value = _make_class(f"{_name}.{item}")
        setattr(module, item, value)
        return value

    module.__getattr__ = __getattr__  # type: ignore[attr-defined]
    return module


_gtk = _build_module(
    "Gtk",
    Notebook=Notebook,
    Widget=Widget,
    Label=Label,
    Button=Button,
    ToggleButton=ToggleButton,
    Window=Window,
    ApplicationWindow=Window,
    Application=Application,
    FileFilter=FileFilter,
    CssProvider=CssProvider,
    Settings=Settings,
)
_gtk.Clipboard = Clipboard  # type: ignore[attr-defined]
_gio = _build_module("Gio", SimpleAction=SimpleAction, File=File)
_glib = _build_module("GLib", Variant=Variant)
_gdk = _build_module("Gdk", SELECTION_CLIPBOARD=0)
_gdkpixbuf = _build_module("GdkPixbuf")
_pango = _build_module("Pango")
_webkit = _build_module("WebKit2", WebView=WebView, UserContentManager=UserContentManager)
_webkit_legacy = _build_module("WebKit", WebView=WebView)

_names = {
    "Gtk": _gtk,
    "Gio": _gio,
    "GLib": _glib,
    "Gdk": _gdk,
    "GdkPixbuf": _gdkpixbuf,
    "Pango": _pango,
    "WebKit2": _webkit,
    "WebKit": _webkit_legacy,
}

for _name, _module in _names.items():
    setattr(sys.modules[__name__], _name, _module)
    # auch als echtes Submodul registrieren (wie bei PyGObject)
    sys.modules[f"gi.repository.{_name}"] = _module

__all__ = list(_names)
