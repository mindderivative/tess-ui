"""0.3.0 M3 Phase 1 (#49): a title bar's vocabulary in views.
`window_region: drag | none` on any node, and the handler names
`window.minimize`, `window.maximize`, `window.restore`,
`window.toggle_maximized` and `window.close`, which call the app's
window actions without a ViewModel method.
"""

import pytest

from tess_ui import App, View, ViewModel
from tess_ui.spec.build import SpecBuildError
from tess_ui.spec.nodes import LoadError

SEED = (0x67, 0x50, 0xA4, 0xFF)

#: the older spec form, for the tests that hand a spec to `View` / `reconcile` directly
BAR = {"id": "root", "kind": "Container", "style": {"width": 400, "height": 300, "flex_direction": "vertical"},
       "children": [{"id": "bar", "kind": "Rect", "window_region": "drag",
                     "style": {"width": 400, "height": 40, "background": "#6750A4"}},
                    {"id": "body", "kind": "Rect", "style": {"width": 400, "height": 200, "background": "#FFFFFF"}}]}


def _text(children, name="Home"):
    """A view file (TDL) named `name` whose root holds `children`."""
    return (f"---\nTDL: 0.2\nName: {name}\n---\nContainer {{\n  Name: {name.lower()}\n"
            f"  Style {{ Width: 400, Height: 300, Flex_Direction: vertical }}\n  Children {{\n{children}  }}\n}}\n")


BAR_TDL = ("    Rect { Name: bar, Window_Region: drag, Style { Width: 400, Height: 40, Background: \"#6750A4\" } }\n"
           "    Rect { Name: body, Style { Width: 400, Height: 200, Background: \"#FFFFFF\" } }\n")


def _opened(tmp_path, app, children, name="Home"):
    """The view `name` written to the project, opened and shown on `app` (a view isn't on the window until it is shown, so presses and clicks reach it)."""
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / f"{name}_View.tdl").write_text(_text(children, name), encoding="utf-8")
    view = app.open_view(name)
    app.show(name.lower())
    return view


def _app(tmp_path, **kwargs):
    app = App(root=tmp_path, **kwargs)
    app.bind(ViewModel, views=["home", "other", "minimize", "maximize", "restore", "close"])
    return app


def test_window_region_reaches_tre(tmp_path):
    app = _app(tmp_path)
    view = _opened(tmp_path, app, BAR_TDL)
    assert view.node("root.bar").get("window_region") == "drag" and view.node("root.body").get("window_region") is None
    other = _opened(tmp_path, app, BAR_TDL.replace("drag", "none"), "Other")
    assert other.node("root.bar").get("window_region") == "none"


def test_a_press_on_the_bar_moves_the_window(tmp_path):
    """`tess_re` takes a primary press on a drag region: the pressed node gets
    `pointer_cancel`, not `pointer_up` or a click."""
    app = _app(tmp_path)
    view = _opened(tmp_path, app, BAR_TDL)
    seen = []
    for event in ("pointer_up", "pointer_cancel"):
        view.node("root.bar").on(event, lambda e, event=event: seen.append(event))
    app.window.advance(0)
    app.window.simulate("pointer_down", node=view.node("root.bar"))
    app.window.simulate("pointer_up", node=view.node("root.bar"))
    assert seen == ["pointer_cancel"]


def test_a_wrong_window_region_is_one_line(tmp_path):
    app = _app(tmp_path)
    with pytest.raises((SpecBuildError, ValueError), match="'window_region:' is one of drag, none, got 'title'"):
        _opened(tmp_path, app, BAR_TDL.replace("drag", "title"))


def test_reconcile_follows_window_region():
    view = View(BAR)
    dropped = {**BAR, "children": [{k: v for k, v in BAR["children"][0].items() if k != "window_region"},
                                   BAR["children"][1]]}
    view.reconcile(spec=dropped)
    assert view.node("bar").get("window_region") is None  # dropped: back to tess_re's default
    view.reconcile(spec=BAR)
    assert view.node("bar").get("window_region") == "drag"


def test_a_component_call_can_be_the_title_bar(tmp_path):
    app = _app(tmp_path, theme_seed=SEED)  # TopAppBar's colours are theme roles
    view = _opened(tmp_path, app, "    TopAppBar { Name: top, Title: Notes, Window_Region: drag, Style { Width: 400 } }\n")
    assert view.node("root.top").get("window_region") == "drag"


# -- the window.* handlers ----------------------------------------------------------

def _button(action):
    return ("    Rect {\n      Name: button\n      Handlers { On_Click { Call { Action: window." + action + " } } }\n"
            "      Style { Width: 40, Height: 40, Background: \"#6750A4\" }\n    }\n")


def test_the_handlers_call_the_apps_actions(tmp_path, monkeypatch):
    app = _app(tmp_path)
    view = _opened(tmp_path, app, _button("toggle_maximized"))
    app.window.simulate("click", node=view.node("root.button"))
    assert app.maximized.get() is True  # before run(): how the window opens
    app.window.simulate("click", node=view.node("root.button"))
    assert app.maximized.get() is False
    called = []
    for action in ("minimize", "maximize", "restore", "close"):
        monkeypatch.setattr(app, action, lambda action=action: called.append(action))
        other = _opened(tmp_path, app, _button(action), action.title())
        app.window.simulate("click", node=other.node("root.button"))
    assert called == ["minimize", "maximize", "restore", "close"]


def _calls(action, args=""):
    return ("    Rect {\n      Name: button\n      Handlers { On_Click { Call { Action: " + action + args + " } } }\n"
            "      Style { Width: 40, Height: 40, Background: \"#6750A4\" }\n    }\n")


def test_an_unknown_window_action_is_a_load_error_naming_the_line(tmp_path):
    app = _app(tmp_path)
    with pytest.raises(LoadError, match=r"Home_View\.tdl:\d+:\d+: error: 'window\.fullscreen' isn't a window action") as caught:
        _opened(tmp_path, app, _button("fullscreen"))
    assert "window.minimize" in str(caught.value) and caught.value.line == 11  # the actions there are are listed; the line is the handler's


def test_an_unknown_window_action_called_with_arguments_is_found_too(tmp_path):
    """A call with arguments is statements, not a bare action name: they are checked as well."""
    app = _app(tmp_path)
    with pytest.raises(LoadError, match=r"'window\.minimise' isn't a window action.*did you mean 'window\.minimize'"):
        _opened(tmp_path, app, _calls("window.minimise", ", Args: [<| 1 |>]"))


def test_an_unknown_surface_action_is_a_load_error(tmp_path):
    app = _app(tmp_path)
    with pytest.raises(LoadError, match=r"'surface\.explode' isn't a surface action.*surface\.dismiss"):
        _opened(tmp_path, app, _calls("surface.explode"))


def test_a_window_action_in_a_tooltip_button_is_checked_too(tmp_path):
    app = _app(tmp_path)
    tip = ("    Rect {\n      Name: button\n      Style { Width: 40, Height: 40, Background: \"#6750A4\" }\n"
           "      Tooltip { Text: Close, Title: T, Actions { Item { Label: Go, On_Click: window.fullscreen } } }\n    }\n")
    with pytest.raises(LoadError, match="'window.fullscreen' isn't a window action"):
        _opened(tmp_path, app, tip)


def test_a_window_action_written_at_a_view_call_is_checked_too(tmp_path):
    app = _app(tmp_path)
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Btn_View.tdl").write_text("---\nTDL: 0.2\nName: Btn\n---\nRect { Name: face, Style { Width: 40, Height: 40, Background: \"#6750A4\" } }\n")
    with pytest.raises(LoadError, match="'surface.explode' isn't a surface action"):
        _opened(tmp_path, app, "    Btn { Name: b, Handlers { On_Click: surface.explode } }\n")


def _button_spec(action):
    """The older spec form of the same button, for a `View` built from a spec: only that path checks a window action's name when a ViewModel attaches
    (a composed view's `window.<name>` is looked up when it runs)."""
    return {"id": "root", "kind": "Container", "style": {"width": 400, "height": 300},
            "children": [{"id": "button", "kind": "Rect", "handlers": {"on_click": f"window.{action}"},
                          "style": {"width": 40, "height": 40, "background": "#6750A4"}}]}


def test_an_unknown_window_action_is_one_line():
    view = View(_button_spec("fullscreen"))
    with pytest.raises(ValueError, match='widget "button": handler "on_click" names "window.fullscreen", which '
                                         "isn't a window action \\(window.minimize, "):
        ViewModel(view)


def test_a_window_action_needs_an_apps_window():
    view = View(_button_spec("close"))  # a window of its own, no App
    with pytest.raises(ValueError, match="but this view isn't on an App's window"):
        ViewModel(view)


def test_a_control_takes_window_region_too():
    """A control (here a Switch) is built by Tesserae, not from a `tess_re`
    primitive, so its node is set, and patched, separately."""
    spec = {"id": "root", "kind": "Container", "style": {"width": 300, "height": 100},
            "children": [{"id": "s", "kind": "Switch", "style": {}, "window_region": "none"}]}
    view = View(spec, theme_seed=SEED)
    assert view._built.controls["s"].node.get("window_region") == "none"
    view.reconcile({**spec, "children": [{"id": "s", "kind": "Switch", "style": {}}]})
    assert view._built.controls["s"].node.get("window_region") is None
