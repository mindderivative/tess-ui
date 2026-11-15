"""0.3.0 M3 Phase 2 (#50): `kind: TitleBar`, expanded into a drag-region
bar with the app's icon, title and content, and the window buttons,
which call the app's actions and follow `app.maximized`.
"""

import sys

import pytest

from tess_ui import App, View, ViewModel
from tess_ui.icons import icon_path
from tess_ui.spec.title_bar import BUTTONS, TitleBarError, expand_title_bars

SEED = (0x67, 0x50, 0xA4, 0xFF)


def _page(bar):
    return {"id": "root", "kind": "Container", "style": {"width": 600, "height": 400, "flex_direction": "vertical"},
            "children": [bar, {"id": "body", "kind": "Rect",
                               "style": {"width": 600, "height": 300, "background": "surface"}}]}


TDL = "---\nTDL: 0.2\nName: Home\n---\n"


def _file_text(bar_tdl):
    """The view file: a TitleBar block (`bar_tdl`, TDL) over a body."""
    return (TDL + "Container {\n  Name: home\n  Style { Width: 600, Height: 400, Flex_Direction: vertical }\n  Children {\n" + bar_tdl
            + "    Rect { Name: body, Style { Width: 600, Height: 300, Background: surface } }\n  }\n}\n")


def _app_with(tmp_path, bar_tdl, **app_kwargs):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Home_View.tdl").write_text(_file_text(bar_tdl), encoding="utf-8")
    app = App(root=tmp_path, width=600, height=400, theme_seed=SEED, borderless=True, **app_kwargs)
    # The bar as Windows and Linux show it, with its own buttons: on macOS
    # the OS's traffic lights show instead and they hide (test_title_bar_macos).
    app._native_controls.set(False)
    app.bind(ViewModel, views=["home"])
    view = app.open_view("Home")
    app.show("home")
    app.window.advance(16)
    return app, view


BAR = {"id": "bar", "kind": "TitleBar", "title": "Notes", "icon": "home", "style": {"width": 600}}
BAR_TDL = "    TitleBar { Name: bar, Title: Notes, Icon: home, Style { Width: 600 } }\n"


def test_the_expansion():
    given = _page(BAR)
    spec = expand_title_bars(given)
    assert given == _page(BAR)  # the spec given is left as it was (a view keeps it for hot reload)
    bar = spec["children"][0]
    assert (bar["kind"], bar["window_region"], bar["classes"]) == ("Container", "drag", ["title_bar"])
    assert [c["id"] for c in bar["children"]] == ["bar.inset", "bar.icon", "bar.title", "bar.content",
                                                  "bar.buttons"]
    buttons = bar["children"][4]["children"]
    assert [b["id"] for b in buttons] == ["bar.minimize", "bar.maximize", "bar.close"]
    assert [b["handlers"]["on_click"] for b in buttons] == ["window.minimize", "window.toggle_maximized",
                                                            "window.close"]
    assert buttons[2]["classes"] == ["title_bar_button", "title_bar_close"]


def test_the_window_glyphs_are_in_the_icon_set():
    for name in ("window_minimize", "window_maximize", "window_restore", "close"):
        assert icon_path(name)


def test_it_lays_out_as_a_desktop_title_bar(tmp_path):
    app, view = _app_with(tmp_path, BAR_TDL)
    x = {i: view.node(i).get("layout_x") for i in ("root.bar.icon", "root.bar.title", "root.bar.content", "root.bar.minimize",
                                                     "root.bar.maximize", "root.bar.close")}
    assert x["root.bar.icon"] < x["root.bar.title"] < x["root.bar.content"] < x["root.bar.minimize"]
    assert x["root.bar.maximize"] - x["root.bar.minimize"] == x["root.bar.close"] - x["root.bar.maximize"] == 46  # flush
    assert x["root.bar.close"] + 46 == 600  # at the right edge
    assert view.node("root.bar").get("layout_height") == 40.0 and view.node("root.bar").get("window_region") == "drag"


def test_the_buttons_act_and_maximize_follows_the_window(tmp_path, monkeypatch):
    app, view = _app_with(tmp_path, BAR_TDL)
    glyph = lambda name: view.node(f"root.bar.maximize.{name}").get("opacity")  # noqa: E731
    assert (glyph("window_maximize"), glyph("window_restore")) == (1.0, 0.0)
    app.window.simulate("click", node=view.node("root.bar.maximize"))
    assert app.maximized.get() is True  # before run(): how it opens
    assert (glyph("window_maximize"), glyph("window_restore")) == (0.0, 1.0)
    app.window.simulate("maximized", maximized=False)  # as the OS would report a restore
    assert (glyph("window_maximize"), glyph("window_restore")) == (1.0, 0.0)
    called = []
    monkeypatch.setattr(app, "minimize", lambda: called.append("minimize"))
    monkeypatch.setattr(app, "close", lambda: called.append("close"))
    app.window.simulate("click", node=view.node("root.bar.minimize"))
    app.window.simulate("click", node=view.node("root.bar.close"))
    assert called == ["minimize", "close"]


def test_the_bar_drags_and_the_buttons_dont(tmp_path):
    """A press where the title is moves the window (the bar, the drag
    region, gets `pointer_cancel`); a button has a click handler, so a
    press on it is pressed and released as usual."""
    app, view = _app_with(tmp_path, BAR_TDL)
    seen = []
    for node_id in ("root.bar", "root.bar.close"):  # Tesserae's shared listeners: `node.on` would replace its own
        for event in ("pointer_up", "pointer_cancel"):
            view._events.listen(view.node(node_id), event, lambda e, n=node_id, ev=event: seen.append((n, ev)))

    def press(node_id):  # at the node's centre, as a pointer would
        node = view.node(node_id)
        x = node.get("layout_x") + node.get("layout_width") / 2
        y = node.get("layout_y") + node.get("layout_height") / 2
        app.window.simulate("pointer_down", x=x, y=y)
        app.window.simulate("pointer_up", x=x, y=y)

    app.window.advance(0)
    press("root.bar.title")
    assert seen == [("root.bar", "pointer_cancel")]
    seen.clear()
    app.window.advance(1000)  # not a double-click
    press("root.bar.close")
    assert ("root.bar.close", "pointer_up") in seen and ("root.bar", "pointer_cancel") not in seen


def test_its_children_are_the_content(tmp_path):
    bar = ("    TitleBar {\n      Name: bar, Title: Notes, Icon: home, Style { Width: 600 }\n      Children {\n"
           "        Rect { Name: search, Style { Width: 120, Height: 24, Background: surface_container } }\n      }\n    }\n")
    app, view = _app_with(tmp_path, bar)
    search = view.node("root.bar.search")
    assert search.get("layout_x") >= view.node("root.bar.content").get("layout_x")
    assert search.get("layout_x") + 120 <= view.node("root.bar.minimize").get("layout_x")


def test_fewer_buttons_and_no_icon_or_title():
    spec = expand_title_bars(_page({"id": "bar", "kind": "TitleBar", "buttons": ["close"]}))
    assert [c["id"] for c in spec["children"][0]["children"]] == ["bar.inset", "bar.content", "bar.buttons"]
    assert [b["id"] for b in spec["children"][0]["children"][2]["children"]] == ["bar.close"]
    none = expand_title_bars(_page({"id": "bar", "kind": "TitleBar", "buttons": []}))
    assert [c["id"] for c in none["children"][0]["children"]] == ["bar.inset", "bar.content"]


@pytest.mark.parametrize("bar, message", [
    ({"id": "bar", "kind": "TitleBar", "subtitle": "x"}, "widget 'bar': a TitleBar takes .*; not subtitle"),
    ({"id": "bar", "kind": "TitleBar", "title": 3}, "widget 'bar': a TitleBar's title is text, got 3"),
    ({"id": "bar", "kind": "TitleBar", "icon": ["home"]}, "a TitleBar's icon is an icon name"),
    ({"id": "bar", "kind": "TitleBar", "buttons": ["help"]}, f"buttons are some of {', '.join(BUTTONS)}"),
    ({"id": "bar", "kind": "TitleBar", "buttons": ["close", "close"]}, "each once"),
])
def test_a_title_bar_written_wrongly_is_one_line(bar, message):
    with pytest.raises(TitleBarError, match=message):
        expand_title_bars(_page(bar))


def test_reconcile_and_the_stylesheet_classes():
    view = View(_page(BAR), theme_seed=SEED)  # the older spec form: `reconcile` takes the spec a view was built from
    view.reconcile(_page({**BAR, "title": "Notes, edited"}))
    assert view.node("bar.title").get("text") == "Notes, edited"
    assert expand_title_bars(_page({**BAR, "classes": ["mine"]}))["children"][0]["classes"] == ["title_bar", "mine"]


@pytest.mark.parametrize("height", [32, 56])
def test_any_height_and_every_part_follows(tmp_path, height):
    app, view = _app_with(tmp_path, f"    TitleBar {{ Name: bar, Title: Notes, Icon: home, Style {{ Width: 600, Height: {height} }} }}\n")
    g = lambda i, k: view.node(i).get(k)  # noqa: E731
    assert g("root.bar", "layout_height") == height
    for part in ("root.bar.inset", "root.bar.content", "root.bar.buttons", "root.bar.minimize", "root.bar.maximize", "root.bar.close"):
        assert g(part, "layout_height") == height, part
    for glyph in ("root.bar.minimize.window_minimize", "root.bar.close.close", "root.bar.maximize.window_maximize",
                  "root.bar.maximize.window_restore"):  # centred at any height
        assert g(glyph, "layout_y") - g("root.bar", "layout_y") == (height - 16) / 2, glyph


def test_the_example_builds(monkeypatch):
    """`examples/custom_title_bar` (M4 Phase 3): a TitleBar with a search
    field in it, and a bar built by hand from `window_region` and a
    `window.close` handler."""
    from pathlib import Path

    import importlib.util

    folder = Path(__file__).resolve().parent.parent / "examples" / "custom_title_bar"
    # by its path, under a name of its own: other tests import a Home_ViewModel too
    spec = importlib.util.spec_from_file_location("custom_title_bar_Home_ViewModel", folder / "Home_ViewModel.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    HomeViewModel = module.HomeViewModel

    app = App(width=720, height=420, theme_seed=SEED, borderless=True, root=folder, search=["."])
    app._native_controls.set(False)
    app.bind(HomeViewModel)
    view = app.open_view("Home")
    app.show("Home")
    app.window.advance(16)
    assert view.node("root.bar").get("window_region") == "drag" and view.node("root.body.own_bar").get("window_region") == "drag"
    search = view.node("root.bar.search").get("layout_x")
    assert view.node("root.bar.content").get("layout_x") <= search < view.node("root.bar.minimize").get("layout_x")
    closed = []
    monkeypatch.setattr(app, "close", lambda: closed.append(True))
    app.window.simulate("click", node=view.node("root.body.own_bar.own_close"))
    assert closed == [True]
