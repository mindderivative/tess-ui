"""0.3.0 M4 Phase 4 (#57): title bars hot-reload like anything else. An
edit to a view with a `TitleBar` (its title, its buttons, its content)
reloads it, and its buttons still act.
"""

import os

import pytest

from tess_ui import App, ViewModel
from tess_ui.spec.watch import ComposedWatcher

SEED = (0x67, 0x50, 0xA4, 0xFF)


def _page(bar_props="", children=""):
    """A view file (TDL): a TitleBar with `bar_props` (one block of properties) and, when given, `children`."""
    inner = f"\n      Children {{ {children} }}" if children else ""
    return ("---\nTDL: 0.2\nName: Home\n---\nContainer {\n  Name: home\n  Style { Width: 600, Height: 400, Flex_Direction: vertical }\n  Children {\n"
            f"    TitleBar {{\n      Name: bar, Style {{ Width: 600 }}, {bar_props}{inner}\n    }}\n  }}\n}}\n")


def _write(path, text):
    before = path.stat().st_mtime_ns if path.exists() else 0
    path.write_text(text, encoding="utf-8")
    later = max(before + 10**9, path.stat().st_mtime_ns)
    os.utime(path, ns=(later, later))  # a change a watcher sees, however fast the test


def _app_with(tmp_path, text):
    (tmp_path / "Views").mkdir(exist_ok=True)
    path = tmp_path / "Views" / "Home_View.tdl"
    _write(path, text)
    app = App(root=tmp_path, width=600, height=400, theme_seed=SEED, borderless=True)
    app._native_controls.set(False)  # the bar as Windows and Linux show it
    app.bind(ViewModel, views=["home"])
    view = app.open_view("Home")
    app.show("home")
    app.window.advance(16)
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    return app, view, path, watcher


def test_editing_a_title_bar_reloads_it(tmp_path, monkeypatch):
    app, view, path, watcher = _app_with(tmp_path, _page("Title: Notes"))
    _write(path, _page("Title: Notes edited, Icon: home", "Rect { Name: tag, Style { Width: 40, Height: 20, Background: primary } }"))
    assert watcher.poll() is True
    app.window.advance(16)
    assert view.node("root.bar.title").get("text") == "Notes edited"
    assert view.node("root.bar.icon") is not None and view.node("root.bar.tag") is not None
    closed = []
    monkeypatch.setattr(app, "close", lambda: closed.append(True))
    app.window.simulate("click", node=view.node("root.bar.close"))  # the reloaded button still acts
    assert closed == [True]
    app.window.simulate("maximized", maximized=True)  # and still follows the window
    assert view.node("root.bar.maximize.window_restore").get("opacity") == 1.0


def test_dropping_buttons_by_hot_reload(tmp_path):
    app, view, path, watcher = _app_with(tmp_path, _page("Title: Notes"))
    _write(path, _page("Title: Notes, Buttons: [close]"))
    assert watcher.poll() is True
    app.window.advance(16)
    assert view.node("root.bar.close").get("layout_x") + 46 == 600  # still at the right edge, alone
    with pytest.raises(ValueError, match="no widget with id 'root.bar.minimize'"):
        view.node("root.bar.minimize")  # gone, not just hidden
