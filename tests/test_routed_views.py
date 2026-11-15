"""0.4.4 (#99): routed screens in a window view: a call of a view with a `route`, and the `navigate.*` handlers."""

import os

import pytest

from tess_ui import App
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.watch import ComposedWatcher

SEED = (0x67, 0x50, 0xA4, 0xFF)
WINDOW = """---
TDL: 0.2
Name: Window
---
Window {
  Name: window
  Title: App
  Style { Width: 600, Height: 300 }
  Children {
    Container {
      Name: rail
      Style { Width: 100, Flex_Direction: vertical }
      Children {
        Rect { Name: go_main, Style { Height: 30, Background: primary }, Handlers { On_Click: navigate.Home } }
        Rect { Name: go_settings, Style { Height: 30, Background: secondary }, Handlers { On_Click: navigate.Pref } }
        Rect { Name: go_back, Style { Height: 30, Background: tertiary }, Handlers { On_Click: navigate.back } }
        Rect { Name: go_forward, Style { Height: 30, Background: error }, Handlers { On_Click: navigate.forward } }
      }
    }
    Container {
      Name: screens
      Style { Flex: fill, Gap: 20 }
      Children {
        Home { Name: main, Route: "" }
        Pref { Name: settings, Route: settings }
      }
    }
  }
}
"""
HOME = """---
TDL: 0.2
Name: Home
---
Container {
  Name: home
  Style { Width: 200, Height: 100 }
  Children {
    Text { Name: hi, Text: Home, Typography_Role: body_large, Style { Foreground: on_surface } }
  }
}
"""
PREF = """---
TDL: 0.2
Name: Pref
---
Container {
  Name: pref
  State { N: 0 }
  Style { Width: 200, Height: 100 }
  Children {
    Text { Name: shown, Text: <| 'clicks ' + str(n) |>, Typography_Role: body_large, Style { Foreground: on_surface } }
    Rect { Name: bump, Style { Width: 20, Height: 20, Background: primary }, Handlers { On_Click { Set { Target: n, Value: <| n + 1 |> } } } }
  }
}
"""


@pytest.fixture
def project(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Window_View.tdl").write_text(WINDOW)
    (tmp_path / "Views" / "Home_View.tdl").write_text(HOME)
    (tmp_path / "Views" / "Pref_View.tdl").write_text(PREF)
    return tmp_path


def _app(project):
    app = App(root=project, theme_seed=SEED, dark=True)
    view = app.open_view("Window")
    app.window.advance(16)
    return app, view


def _shown(view):
    return {name: bool(view.node(f"root.screens.{name}").get("visible")) for name in ("main", "settings")}


def test_routed_views_are_screens_with_routes_and_none_shows_until_a_route_is(project):
    app, view = _app(project)
    assert _shown(view) == {"main": False, "settings": False}
    app.navigate_to("")
    app.window.advance(16)
    assert app.current == "Home" and _shown(view) == {"main": True, "settings": False}
    assert app.current_screen.get() == "Home"


def test_a_hidden_screen_takes_no_room(project):
    app, view = _app(project)
    app.navigate_to("")
    app.window.advance(16)
    assert view.node("root.screens.main.hi").get("layout_width") > 0
    assert view.node("root.screens.settings").get("layout_width") in (0, 0.0) or not view.node("root.screens.settings").get("visible")


def test_navigating_shows_the_other_and_back_returns(project):
    app, view = _app(project)
    app.navigate_to("")
    app.navigate_to("settings")
    assert app.current == "Pref" and _shown(view) == {"main": False, "settings": True}
    app.back()
    assert app.current == "Home" and _shown(view) == {"main": True, "settings": False}
    assert app.can_go_forward.get() is True


def test_the_navigate_handlers_work_from_the_window_view(project):
    app, view = _app(project)
    app.navigate_to("")
    app.window.simulate("click", view.node("root.rail.go_settings"))
    assert app.current == "Pref"
    app.window.simulate("click", view.node("root.rail.go_back"))
    assert app.current == "Home"
    app.window.simulate("click", view.node("root.rail.go_forward"))
    assert app.current == "Pref"
    app.window.simulate("click", view.node("root.rail.go_main"))
    assert app.current == "Home"


def test_a_routed_view_keeps_its_state_while_hidden(project):
    app, view = _app(project)
    app.navigate_to("settings")
    app.window.simulate("click", view.node("root.screens.settings.bump"))
    app.navigate_to("")
    app.navigate_to("settings")
    assert view.node("root.screens.settings.shown").get("text") == "clicks 1"


def test_a_view_routed_twice_is_an_error(project):
    path = project / "Views" / "Window_View.tdl"
    path.write_text(path.read_text().replace("        Pref { Name: settings, Route: settings }\n",
                                             "        Pref { Name: settings, Route: settings }\n        Home { Name: again, Route: again }\n"))
    with pytest.raises(ValueError, match="is already a routed view"):
        App(root=project, theme_seed=SEED, dark=True).open_view("Window")


def test_navigating_to_an_unknown_screen_is_the_apps_error(project):
    path = project / "Views" / "Window_View.tdl"
    path.write_text(path.read_text().replace("navigate.back", "navigate.Nowhere"))
    app, view = _app(project)
    app.navigate_to("")
    before = app.current
    app.window.simulate("click", view.node("root.rail.go_back"))  # a handler's error is logged by the event loop, the app goes on
    assert app.current == before
    with pytest.raises(KeyError, match="Nowhere"):
        app.navigate("Nowhere")


def test_editing_the_window_view_adds_and_removes_screens(project):
    app, view = _app(project)
    path = project / "Views" / "Window_View.tdl"
    original = path.read_text()
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    app.navigate_to("")

    def write(text):
        path.write_text(text)
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))

    write(original.replace("        Pref { Name: settings, Route: settings }\n", ""))  # the settings screen goes
    assert watcher.poll() is True
    view.window.advance(16)
    assert "Pref" not in app._registered
    with pytest.raises(KeyError):
        app.navigate_to("settings")
    write(original)  # and comes back
    assert watcher.poll() is True
    view.window.advance(16)
    app.navigate_to("settings")
    assert app.current == "Pref" and view.node("root.screens.settings").get("visible")


def test_a_rail_of_screens_follows_the_current_screen(project):
    path = project / "Views" / "Window_View.tdl"
    rail = """    NavigationRailScreens {
      Name: nav
      Items {
        Item { Label: Tasks, Icon: home, Screen: Home }
        Item { Label: Prefs, Icon: settings, Screen: Pref }
      }
    }
"""
    path.write_text(path.read_text().replace("    Container {\n      Name: rail\n", rail + "    Container {\n      Name: rail\n", 1))
    app, view = _app(project)
    app.navigate_to("")
    for _ in range(40):
        app.window.advance(16)
    filled = app.theme.role("secondary_container")
    assert view.node("root.nav.item[Home].pill").get("fill") == filled and view.node("root.nav.item[Pref].pill").get("fill") != filled
    app.window.simulate("click", view.node("root.nav.item[Pref]"))
    for _ in range(40):
        app.window.advance(16)
    assert app.current == "Pref"
    assert view.node("root.nav.item[Pref].pill").get("fill") == filled and view.node("root.nav.item[Home].pill").get("fill") != filled
    assert view.node("root.nav.item[Pref].label").get("fill") == app.theme.role("on_surface")


def _host(tmp_path, call):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Home_View.tdl").write_text(HOME)
    (tmp_path / "Views" / "Host_View.tdl").write_text(
        f"---\nTDL: 0.2\nName: Host\n---\nContainer {{\n  Name: host\n  Children {{\n    {call}\n  }}\n}}\n")
    return App(root=tmp_path, theme_seed=SEED)


def test_a_route_outside_a_window_view_is_an_error(tmp_path):
    app = _host(tmp_path, "Home { Name: l, Route: x }")
    with pytest.raises(LoadError, match=r"Host_View\.tdl:8:\d+: error: a `route:` is for a view in the window view"):
        app.open_view("Host")


def test_a_lazy_route_outside_a_window_view_is_an_error_too(tmp_path):
    app = _host(tmp_path, "Home { Name: l, Route { Path: x, Lazy: true } }")
    with pytest.raises(LoadError, match="a `route:` is for a view in the window view"):
        app.open_view("Host")
