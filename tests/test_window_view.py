"""#98, #204: a `Window` root is the OS window -- its title, size, flags and `borderless` -- and a view can ask for its size to be remembered."""

import json
import sys

import pytest

from tess_ui import App, windowstate

SEED = (0x67, 0x50, 0xA4, 0xFF)


def _window(extra=""):
    """A `Window` view named `main` (a title bar over its content); `extra` is more of the Window's own properties, one to a line."""
    return ("---\nTDL: 0.2\nName: main\n---\nWindow {\n  Name: main\n  Title: Tasks\n  Borderless: true\n  Min_Width: 320\n  Min_Height: 200\n"
            "  Style { Width: 640, Height: 400, Background: surface, Flex_Direction: vertical }\n" + extra +
            "  Children {\n    TitleBar { Name: bar, Title: Tasks, Icon: home }\n"
            "    Text { Name: hello, Text: Hello, Typography_Role: headline_small, Style { Foreground: on_surface } }\n  }\n}\n")


def _project(tmp_path, text=None, name="Main"):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / f"{name}_View.tdl").write_text(_window() if text is None else text)
    return tmp_path


def _app(tmp_path, **kwargs):
    return App(root=tmp_path, theme_seed=SEED, dark=True, **kwargs)


def _open(app):
    view = app.open_view("Main")
    app.window.advance(16)
    return view


# -- the app ----------------------------------------------------------------------------------

def test_opening_a_window_view_sets_the_os_window(tmp_path):
    app = _app(_project(tmp_path))
    view = _open(app)
    assert app.borderless is True and app.resize_border == 6
    assert (app.min_width, app.min_height) == (320, 200)
    assert app.window.get("title") == "Tasks"
    assert (app.window.get("width"), app.window.get("height")) == (640.0, 400.0)
    assert view.node("root").get("layout_height") == 400.0
    assert view.node("root.hello").get("text") == "Hello"


def test_a_second_window_view_is_an_error(tmp_path):
    _project(tmp_path)
    _project(tmp_path, _window().replace("Name: main", "Name: other"), name="Other")
    app = _app(tmp_path)
    _open(app)
    with pytest.raises(ValueError, match="an app has one window"):
        app.open_view("Other")


def test_editing_the_window_view_while_running_sets_the_window_again(tmp_path):
    from tess_ui.spec.watch import ComposedWatcher

    app = _app(_project(tmp_path))
    view = _open(app)
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    path = tmp_path / "Views" / "Main_View.tdl"
    path.write_text(_window().replace("Title: Tasks\n  Borderless: true\n  Min_Width: 320", "Title: Renamed\n  Borderless: false\n  Min_Width: 100"))
    stat = path.stat()
    import os

    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert watcher.poll() is True
    assert app.window.get("title") == "Renamed" and app.borderless is False and app.min_width == 100


# -- borderless on App -------------------------------------------------------------------------

def test_borderless_sets_the_os_window_and_its_resize_border():
    app = App(theme_seed=SEED, borderless=True)
    assert app.borderless is True and app.window.get("decorations") is False and app.resize_border == 6
    app.borderless = False
    assert app.borderless is False and app.window.get("decorations") is True and app.resize_border == 0
    app.borderless = True
    assert app.borderless is True and app.resize_border == 6
    assert App(theme_seed=SEED).borderless is False


# -- the OS window's options (#204) ---------------------------------------------------------------

def test_a_window_without_flags_leaves_the_os_window_alone(tmp_path):
    app = _app(_project(tmp_path))
    _open(app)
    assert app.fullscreen is False and app.window.get("transparent") is False and app.window.get("click_through") is False


def test_opening_a_window_with_flags_sets_the_os_window(tmp_path):
    app = _app(_project(tmp_path, _window("  Fullscreen: true\n  Transparent: true\n  Click_Through: true\n")))
    _open(app)
    assert app.fullscreen is True and app.window.get("transparent") is True and app.window.get("click_through") is True


def test_a_window_view_takes_maximized(tmp_path):
    app = _app(_project(tmp_path, _window("  Fullscreen: true\n  Maximized: true\n")))
    _open(app)
    assert app.fullscreen is True and app.maximized.get() is True


# -- remembering the window (#204) ---------------------------------------------------------------------------------------------

def _remembering(tmp_path, monkeypatch, value="true"):
    monkeypatch.setenv("TESS_UI_STATE_DIR", str(tmp_path / "state"))
    return _app(_project(tmp_path, _window(f"  Remember: {value}\n")))


def _settle(app, n=40):
    for _ in range(n):
        app.window.advance(16)


def test_the_size_is_written_a_moment_after_it_changes(tmp_path, monkeypatch):
    app = _remembering(tmp_path, monkeypatch)
    _open(app)
    app.window.resize(700, 450)
    app.window.simulate("resize", width=700, height=450)
    _settle(app)
    saved = json.loads((tmp_path / "state" / "tasks.window.json").read_text())
    assert (saved["width"], saved["height"], saved["maximized"]) == (700.0, 450.0, False)


def test_the_next_run_opens_at_the_saved_size(tmp_path, monkeypatch):
    monkeypatch.setenv("TESS_UI_STATE_DIR", str(tmp_path / "state"))
    windowstate.save("Tasks", {"width": 777.0, "height": 333.0, "maximized": False})
    app = _app(_project(tmp_path, _window("  Remember: true\n")))
    _open(app)
    assert (app.window.get("width"), app.window.get("height")) == (777.0, 333.0)


def test_a_name_keeps_the_state_under_that_name(tmp_path, monkeypatch):
    app = _remembering(tmp_path, monkeypatch, "notes")
    _open(app)
    app.window.simulate("resize", width=640, height=400)
    _settle(app)
    assert (tmp_path / "state" / "notes.window.json").exists() and not (tmp_path / "state" / "tasks.window.json").exists()


def test_a_maximized_window_is_remembered_and_keeps_the_size_it_had_before(tmp_path, monkeypatch):
    app = _remembering(tmp_path, monkeypatch)
    _open(app)
    app.window.resize(700, 450)
    app.window.simulate("resize", width=700, height=450)
    _settle(app)
    app.window.simulate("maximized", maximized=True)  # the user maximized it
    app.window.resize(1200, 800)
    app.window.simulate("resize", width=1200, height=800)  # the screen-sized window
    _settle(app)
    saved = json.loads((tmp_path / "state" / "tasks.window.json").read_text())
    assert saved["maximized"] is True and (saved["width"], saved["height"]) == (700.0, 450.0)


def test_a_damaged_or_wild_file_gives_less_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setenv("TESS_UI_STATE_DIR", str(tmp_path / "state"))
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "tasks.window.json").write_text("{not json")
    assert windowstate.load("Tasks") == {}
    (tmp_path / "state" / "tasks.window.json").write_text(json.dumps({"width": 1e9, "height": "tall", "x": 5, "y": 6, "maximized": "yes"}))
    assert windowstate.load("Tasks") == {"x": 5.0, "y": 6.0}  # the good fields stay
    app = _app(_project(tmp_path, _window("  Remember: true\n")))
    _open(app)  # runs


def test_a_window_that_does_not_ask_leaves_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TESS_UI_STATE_DIR", str(tmp_path / "state"))
    app = _app(_project(tmp_path))
    _open(app)
    app.window.simulate("resize", width=500, height=300)
    _settle(app)
    assert not (tmp_path / "state").exists()
