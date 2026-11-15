"""M31 Phase 1: theme files are hot-reloaded, re-theming every screen.

M31 also gave the window `tess_re`'s theme, for the imperative widgets and
tints that read it then. Since M42 Phase 7 nothing does, so the window
is never themed: the app's theme is `app.theme` and its screens'.

The watcher tests use a `FakeHandle`, as `test_watch_thread.py` does:
the watcher queues each reload, and the test runs it on this (main)
thread, as `tess_re`'s loop would.
"""

import importlib.util
import queue
import sys
from pathlib import Path

import pytest

from helpers import elevation, window_unthemed

import tess_ui.fonts as fonts
from tess_ui import App, tokens

SEED = (0x67, 0x50, 0xA4, 0xFF)
RECT = '---\nTDL: 0.2\nName: {name}\n---\nRect {{ Name: {name}, Style {{ Width: 10, Height: 10, Background: "#112233" }} }}\n'
HEAD = "---\nTDL: 0.2\nName: Brand\n---\n"


@pytest.fixture(autouse=True)
def _fresh_font_registry(monkeypatch):
    monkeypatch.setattr(fonts, "_registered", set())


class FakeHandle:
    def __init__(self):
        self.queued: "queue.Queue" = queue.Queue()

    def call_soon(self, fn):
        self.queued.put(fn)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _pair(tmp_path: Path, prefix: str):
    """The view `prefix` (one Rect, its root: node `root`) written to the project, and the ViewModel that serves it."""
    view = _write(tmp_path / "Views" / f"{prefix}_View.tdl", RECT.format(name=prefix.lower()))
    vm_path = _write(
        tmp_path / f"{prefix}_ViewModel.py",
        f"from tess_ui import ViewModel\n\n\nclass {prefix}ViewModel(ViewModel):\n    views = {prefix.lower()!r}\n",
    )
    spec = importlib.util.spec_from_file_location(vm_path.stem, vm_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return view, getattr(module, f"{prefix}ViewModel")


def _open(app: App, tmp_path: Path, prefix: str):
    """The view `prefix`, opened on `app`."""
    _, vm = _pair(tmp_path, prefix)
    app.bind(vm)
    return app.open_view(prefix)


def _theme(elevation: int, primary: str | None = None, seed: str | None = None) -> str:
    text = HEAD + "Theme {\n"
    if seed is not None:
        text += f'  Seed: "{seed}"\n'
    if primary is not None:
        text += f'  Colors {{ Primary: "{primary}" }}\n'
    return text + f"  Styles {{ Item {{ Kind: Rect, Style {{ Elevation: {elevation} }} }} }}\n}}\n"


def _edit_until_queued(handle: FakeHandle, path: Path, text: str, attempts: int = 40):
    for _ in range(attempts):
        path.write_text(text)
        try:
            return handle.queued.get(timeout=0.25)
        except queue.Empty:
            continue
    raise AssertionError(f"the watcher never queued a reload for {path}")


@pytest.fixture
def watching():
    started = []

    def start(app: App):
        handle = FakeHandle()
        started.extend(app._start_watchers(handle))
        return handle

    yield start
    for watcher in started:
        watcher.stop()


# -- the app's theme, not the window's (M42 Phase 7) ----------------


def test_the_window_is_never_themed(tmp_path: Path):
    """Since M42 nothing `tess_re` draws reads the window's theme, so `App`
    no longer sets it (`tess_re` 0.3.5 removes `Window.set_theme`)."""
    app = App(root=tmp_path, theme_seed=SEED, custom_theme_spec={"colors": {"primary": "#0000FF"}})
    _open(app, tmp_path, "Home")
    window = app.show("home")
    app.set_theme_specs(None, {"colors": {"primary": "#00FF00"}})
    app.set_dark(False)
    assert window_unthemed(window)
    assert app.theme.role("primary") == (0, 255, 0, 255)


def test_an_app_with_no_seed_has_no_scheme(tmp_path: Path):
    app = App(root=tmp_path)
    _open(app, tmp_path, "Home")
    assert app.theme.role("primary") is None


def test_the_app_theme_follows_the_views_seed_precedence(tmp_path: Path):
    """A `View` prefers `theme_seed` to the custom theme's `seed:`."""
    theme = _write(tmp_path / "Brand_Theme.tdl", _theme(1, seed="#FF0000"))
    explicit = App(root=tmp_path, theme_seed=SEED, custom_theme=theme)
    from_file = App(root=tmp_path, custom_theme=theme)
    assert explicit.theme.role("primary") == tokens.color_scheme(SEED, True)["primary"]
    assert from_file.theme.role("primary") == tokens.color_scheme((0xFF, 0, 0, 0xFF), True)["primary"]


def test_a_default_themes_colors_reach_the_app_theme(tmp_path: Path):
    base = _write(tmp_path / "Base_Theme.tdl", _theme(1, primary="#00FF00"))
    app = App(root=tmp_path, theme_seed=SEED, default_theme=base)
    assert app.theme.role("primary") == (0, 255, 0, 255)


# -- set_theme_specs --------------------------------------------------


def test_set_theme_specs_rethemes_every_screen(tmp_path: Path):
    app = App(root=tmp_path, theme_seed=SEED, custom_theme_spec={"styles": [{"kind": "Rect", "style": {"elevation": 1}}]})
    home = _open(app, tmp_path, "Home")
    settings = _open(app, tmp_path, "Settings")
    app.show("home")

    app.set_theme_specs(None, {"styles": [{"kind": "Rect", "style": {"elevation": 4}}], "colors": {"primary": "#0000FF"}})

    assert elevation(home.node("root")) == elevation(settings.node("root")) == 4.0
    assert app.theme.role("primary") == (0, 0, 255, 255)


def test_a_rejected_theme_leaves_the_app_as_it_was(tmp_path: Path):
    app = App(root=tmp_path, theme_seed=SEED, custom_theme_spec={"styles": [{"kind": "Rect", "style": {"elevation": 1}}]})
    home = _open(app, tmp_path, "Home")
    with pytest.raises(Exception):
        app.set_theme_specs(None, {"styles": "not a list"})
    assert elevation(home.node("root")) == 1.0
    app.set_theme_specs(None, {"styles": [{"kind": "Rect", "style": {"elevation": 2}}]})  # still usable
    assert elevation(home.node("root")) == 2.0


def test_later_screens_are_built_with_the_new_theme(tmp_path: Path):
    app = App(root=tmp_path, theme_seed=SEED)
    _open(app, tmp_path, "Home")
    app.set_theme_specs(None, {"styles": [{"kind": "Rect", "style": {"elevation": 5}}]})
    later = _open(app, tmp_path, "Later")
    assert elevation(later.node("root")) == 5.0


# -- hot reload of theme files ---------------------------------------


def test_editing_the_custom_theme_file_rethemes_the_running_app(tmp_path: Path, watching):
    theme = _write(tmp_path / "Brand_Theme.tdl", _theme(1))
    app = App(root=tmp_path, theme_seed=SEED, custom_theme=theme)
    home = _open(app, tmp_path, "Home")
    settings = _open(app, tmp_path, "Settings")
    app.show("home")
    handle = watching(app)

    reload = _edit_until_queued(handle, theme, _theme(4, primary="#0000FF"))
    assert elevation(home.node("root")) == 1.0  # nothing applied until the loop runs it
    reload()

    assert elevation(home.node("root")) == elevation(settings.node("root")) == 4.0
    assert app.theme.role("primary") == (0, 0, 255, 255)


def test_editing_the_default_theme_file_keeps_the_custom_theme(tmp_path: Path, watching):
    base = _write(tmp_path / "Base_Theme.tdl", HEAD + "Theme { Styles { Item { Kind: Rect, Style { Corner_Radius: 2 } } } }\n")
    app = App(
        root=tmp_path,
        theme_seed=SEED,
        default_theme=base,
        custom_theme_spec={"styles": [{"kind": "Rect", "style": {"elevation": 3}}]},
    )
    home = _open(app, tmp_path, "Home")
    handle = watching(app)

    _edit_until_queued(handle, base, HEAD + "Theme { Styles { Item { Kind: Rect, Style { Corner_Radius: 7 } } } }\n")()

    assert home.node("root").get("corner_radius") == 7.0
    assert elevation(home.node("root")) == 3.0


def test_a_broken_theme_edit_is_logged_and_the_watcher_carries_on(tmp_path: Path, watching, logs):
    theme = _write(tmp_path / "Brand_Theme.tdl", _theme(1))
    app = App(root=tmp_path, theme_seed=SEED, custom_theme=theme)
    home = _open(app, tmp_path, "Home")
    handle = watching(app)

    message = logs.edit_until(theme, HEAD + "Theme { Styles {\n", "ERROR", "This block is never closed")
    assert str(theme) in message
    assert handle.queued.empty()
    assert elevation(home.node("root")) == 1.0

    _edit_until_queued(handle, theme, _theme(2))()
    assert elevation(home.node("root")) == 2.0
    assert f"re-themed the app from {theme}" in logs.messages("INFO")


def test_theme_specs_are_not_watched(tmp_path: Path, watching):
    app = App(root=tmp_path, theme_seed=SEED, custom_theme_spec={"styles": []})
    _open(app, tmp_path, "Home")
    watchers = app._start_watchers(FakeHandle())
    try:
        assert [type(w).__name__ for w in watchers] == ["ComposedWatcher"]
    finally:
        for w in watchers:
            w.stop()
