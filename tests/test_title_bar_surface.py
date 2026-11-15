"""0.4.4 (#97): a `TitleBar` in a dialog or a sheet (`buttons: [dismiss]`), and `surface.dismiss`; and a
static view's `window.*` and `surface.*` handlers, which need no ViewModel."""

import pytest

from tess_ui import App, View
from tess_ui.overlays import Dialog, dismiss_surface
from tess_ui.spec.title_bar import TitleBarError, expand_title_bars

SEED = (0x67, 0x50, 0xA4, 0xFF)

def _app():
    app = App(width=600, height=400, theme_seed=SEED, dark=True)
    app.window.advance(16)
    return app


# -- the bar -----------------------------------------------------------------------------------

def test_a_dismiss_bar_has_no_window_parts():
    spec = expand_title_bars({"id": "bar", "kind": "TitleBar", "title": "Settings", "buttons": ["dismiss"]})
    ids = []

    def walk(n):
        ids.append(n["id"])
        for c in n.get("children") or []:
            walk(c)

    walk(spec)
    assert spec["window_region"] == "none"
    assert "bar.dismiss" in ids and "bar.inset" not in ids and "bar.minimize" not in ids
    button = next(c for c in spec["children"][-1]["children"])
    assert button["handlers"] == {"on_click": "surface.dismiss"} and button["a11y"] == {"label": "Close"}
    assert "bindings" not in next(c for c in spec["children"] if c["id"] == "bar.title")  # it fades for a window, not a dialog


def test_a_window_bar_is_as_it_was():
    spec = expand_title_bars({"id": "bar", "kind": "TitleBar", "title": "T"})
    assert spec["window_region"] == "drag" and spec["children"][0]["id"] == "bar.inset"


@pytest.mark.parametrize("buttons", [["dismiss", "close"], ["minimize", "dismiss"], ["dismiss", "dismiss"]])
def test_dismiss_is_on_its_own(buttons):
    with pytest.raises(TitleBarError, match="on its own"):
        expand_title_bars({"id": "bar", "kind": "TitleBar", "buttons": buttons})


def test_dismiss_surface_closes_the_nearest_overlay_and_says_if_there_was_none():
    app = _app()
    dialog = Dialog(app.window, "Sure?", "Really.", actions=[("OK", None)])
    dialog.open()
    assert dismiss_surface(dialog.widget.part("panel.action0")) is True and not dialog.is_open
    lone = app.window.create("box", width=10, height=10)
    app.window.root.add_child(lone)
    assert dismiss_surface(lone) is False


# -- handlers that need no ViewModel -------------------------------------------------------------

def test_a_static_views_surface_handler_works_with_no_viewmodel():
    app = _app()
    spec = {"id": "root", "kind": "Container", "children": [
        {"id": "x", "kind": "Rect", "style": {"width": 20, "height": 20, "background": "primary"}, "handlers": {"on_click": "surface.dismiss"}}]}
    view = View(spec, window=app.window)
    assert view.viewmodel is None and view._wiring  # wired without one


def test_a_static_views_window_button_works_with_no_viewmodel(monkeypatch):
    app = _app()
    closed = []
    monkeypatch.setattr(app, "close", lambda: closed.append(True))
    spec = {"id": "root", "kind": "Container", "children": [
        {"id": "x", "kind": "Rect", "style": {"width": 20, "height": 20, "background": "primary"}, "handlers": {"on_click": "window.close"}}]}
    view = View(spec, window=app.window)
    app.window.root.add_child(view.root)
    app.window.advance(16)
    app.window.simulate("click", view.node("x"))
    assert closed == [True]


def test_an_unknown_surface_action_is_one_line_when_a_viewmodel_attaches():
    from tess_ui import ViewModel

    view = View({"id": "root", "kind": "Container", "children": [
        {"id": "x", "kind": "Rect", "style": {"width": 20, "height": 20, "background": "primary"}, "handlers": {"on_click": "surface.explode"}}]})
    with pytest.raises(ValueError, match=r'widget "x": handler "on_click" names "surface.explode", which isn\'t a surface action'):
        ViewModel(view)
