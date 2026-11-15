"""0.3.0 M3 Phase 3 (#51): a TitleBar's look. Material 3 roles on its
parts' classes, in the cascade's first layer, so a theme or stylesheet
restyles any part; the title, icon and buttons fade while the window
isn't the focused one; close's hover and pressed layers are red.
"""

from tess_ui import App, Theme, ViewModel
from tess_ui.spec.title_bar import INACTIVE

SEED = (0x67, 0x50, 0xA4, 0xFF)
HOME = """---
TDL: 0.2
Name: Home
---
Container {
  Name: home
  Style { Width: 600, Height: 400 }
  Children {
    TitleBar { Name: bar, Title: Notes, Icon: home, Style { Width: 600 } }
  }
}
"""


def _app_with(tmp_path, **app_kwargs):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Home_View.tdl").write_text(HOME, encoding="utf-8")
    app = App(root=tmp_path, width=600, height=400, theme_seed=SEED, borderless=True, **app_kwargs)
    app.bind(ViewModel, views=["home"])
    view = app.open_view("Home")
    app.show("home")
    app.window.advance(16)
    return app, view


def test_the_parts_are_the_themes_roles(tmp_path):
    app, view = _app_with(tmp_path)
    theme = Theme.resolve(theme_seed=SEED, dark=app.dark)  # the app follows the OS's appearance
    assert view.node("root.bar").get("fill") == theme.role("surface")
    for part in ("root.bar.title", "root.bar.icon", "root.bar.close.close", "root.bar.maximize.window_maximize"):
        assert view.node(part).get("fill") == theme.role("on_surface"), part


def test_a_stylesheet_restyles_any_part(tmp_path):
    sheet = {"styles": [{"classes": ["title_bar"], "style": {"background": "#102030"}},
                        {"classes": ["title_bar_title"], "style": {"foreground": "#FF8800"}},
                        {"classes": ["title_bar_glyph"], "style": {"foreground": "#00FF00"}}]}
    app, view = _app_with(tmp_path, stylesheet_spec=sheet)
    assert view.node("root.bar").get("fill") == (0x10, 0x20, 0x30, 255)
    assert view.node("root.bar.title").get("fill") == (0xFF, 0x88, 0x00, 255)
    assert view.node("root.bar.minimize.window_minimize").get("fill") == (0x00, 0xFF, 0x00, 255)


def test_an_apps_own_default_theme_keeps_the_bars_look(tmp_path):
    """An app's `default_theme` replaces Tesserae's shipped one entirely;
    the bar's look is under it, so its parts still have their colours."""
    app, view = _app_with(tmp_path, default_theme_spec={"styles": [{"kind": "Rect", "style": {"corner_radius": 4}}]})
    assert view.node("root.bar.title").get("fill") == Theme.resolve(theme_seed=SEED, dark=app.dark).role("on_surface")


def test_it_fades_while_the_window_isnt_focused(tmp_path):
    app, view = _app_with(tmp_path)
    parts = ("root.bar.title", "root.bar.icon", "root.bar.buttons")
    assert all(view.node(p).get("opacity") == INACTIVE for p in parts)  # not focused before it opens
    app.window.simulate("active", active=True)
    assert all(view.node(p).get("opacity") == 1.0 for p in parts)
    app.window.simulate("active", active=False)
    assert all(view.node(p).get("opacity") == INACTIVE for p in parts)
    assert view.node("root.bar.content").get("opacity") == 1.0  # the app's own content isn't faded


def test_close_is_red_and_the_others_are_not(tmp_path):
    app, view = _app_with(tmp_path)
    theme = Theme.resolve(theme_seed=SEED, dark=app.dark)  # the app follows the OS's appearance
    assert view.interaction("root.bar.close").tint == theme.role("error")
    assert view.interaction("root.bar.minimize").tint == theme.role("on_surface")


def test_it_rethemes_with_the_app(tmp_path):
    app, view = _app_with(tmp_path)
    for dark in (not app.dark, app.dark):
        app.set_dark(dark)
        theme = Theme.resolve(theme_seed=SEED, dark=dark)
        assert view.node("root.bar").get("fill") == theme.role("surface")
        assert view.node("root.bar.title").get("fill") == theme.role("on_surface")
        assert view.interaction("root.bar.close").tint == theme.role("error")


def test_a_theme_restyles_it_too(tmp_path):
    """The bar's look is under every theme, not just under stylesheets."""
    theme = {"styles": [{"classes": ["title_bar_title"], "style": {"foreground": "#123456"}}]}
    app, view = _app_with(tmp_path, default_theme_spec=theme)
    assert view.node("root.bar.title").get("fill") == (0x12, 0x34, 0x56, 255)


def test_a_title_bar_works_in_an_app_with_no_theme_seed(tmp_path):
    """0.3.3 (#82): a bare `App(borderless=True)` failed with "unknown color identifier"; the bar's
    roles are MD3's baseline palette now, and close is still red."""
    from tess_ui import tokens

    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Home_View.tdl").write_text(HOME, encoding="utf-8")
    app = App(root=tmp_path, width=600, height=400, borderless=True)
    app.bind(ViewModel, views=["home"])
    view = app.open_view("Home")
    app.show("home")
    app.window.advance(16)
    baseline = tokens.baseline_scheme()
    assert view.node("root.bar").get("fill") == baseline["surface"]
    assert view.node("root.bar.title").get("fill") == baseline["on_surface"]
    assert view.interaction("root.bar.close").tint == baseline["error"]
