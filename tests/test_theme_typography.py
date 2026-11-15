"""M38 Phase 2: a theme's `typography:` applies to display text in views.

Per M38 Q1: a Text's or Link's `typography_role` resolves through the
theme's `typography:` overrides (default theme, then custom); a text
input keeps its own font even with a `typography_role`. This differs from
`tess_re`, where a theme's `typography:` reached only its widget factories.
"""

import importlib.util
import sys

import pytest

from tess_ui import App, View

SEED = (0x67, 0x50, 0xA4, 0xFF)
MONO = "Hack Nerd Font Mono"
THEME = {"typography": {"body_large": {"font_size": 20, "font_family": MONO, "font_weight": 700}}}


def _text(node_id, kind="Text", **text):
    node = {"id": node_id, "kind": kind, "text": {"content": "x", "typography_role": "body_large", **text},
            "style": {"foreground": "#000000"}}
    if kind == "TextField":
        node["style"] = {"background": "#FFFFFF", "width": 100, "height": 30}
    return node


def _spec(*children):
    return {"id": "root", "kind": "Container", "children": list(children)}


def _font(node):
    return node.get("font_family"), node.get("font_size"), node.get("font_weight")


def test_text_and_link_follow_the_themes_typography():
    view = View(_spec(_text("t"), _text("l", "Link")), theme_seed=SEED, custom_theme_spec=THEME)
    link_text = view.node("l").children()[0]  # a Link is a box holding its text (M41)
    assert _font(view.node("t")) == _font(link_text) == (MONO, 20.0, 700.0)


def test_a_text_input_keeps_its_own_font_even_with_a_typography_role():
    view = View(_spec(_text("f", "TextField")), theme_seed=SEED, custom_theme_spec=THEME)
    assert _font(view.node("f")) == ("Roboto", 16.0, 400.0)  # the plain MD3 body_large


def test_a_nodes_own_font_fields_still_win():
    view = View(_spec(_text("t", font_size=30)), theme_seed=SEED, custom_theme_spec=THEME)
    assert _font(view.node("t")) == (MONO, 30.0, 700.0)


def test_a_custom_theme_role_replaces_the_default_themes():
    default = {"typography": {"body_large": {"font_size": 24, "font_weight": 300}}}
    custom = {"typography": {"body_large": {"font_size": 18}}}
    view = View(_spec(_text("t")), theme_seed=SEED, default_theme_spec=default, custom_theme_spec=custom)
    assert _font(view.node("t")) == ("Roboto", 18.0, 400.0)  # weight 300 went with the replaced entry


def test_re_theming_applies_and_removes_overrides():
    view = View(_spec(_text("t")), theme_seed=SEED)
    assert view.node("t").get("font_size") == 16.0
    view.set_theme(theme_seed=SEED, custom_theme_spec=THEME)
    assert _font(view.node("t")) == (MONO, 20.0, 700.0)
    view.set_theme(theme_seed=SEED)
    assert _font(view.node("t")) == ("Roboto", 16.0, 400.0)


def test_a_component_follows_its_hosts_theme_typography(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Card_View.tdl").write_text(
        '---\nTDL: 0.2\nName: Card\n---\nText { Name: card, Text: hi, Typography_Role: body_large, Style { Foreground: "#000000" } }\n')
    (tmp_path / "Views" / "Host_View.tdl").write_text("---\nTDL: 0.2\nName: host\n---\nContainer {\n  Name: host\n  Children {\n    Card { Name: slot }\n  }\n}\n")
    app = App(root=tmp_path, theme_seed=SEED, custom_theme_spec=THEME)
    view = app.open_view("Host")
    assert _font(view.node("root.slot")) == (MONO, 20.0, 700.0)


def test_an_apps_theme_typography_reaches_its_screens(tmp_path):
    (tmp_path / "Views").mkdir()
    view_file = tmp_path / "Views" / "Home_View.tdl"
    view_file.write_text('---\nTDL: 0.2\nName: home\n---\nContainer {\n  Name: home\n  Children {\n    Text { Name: t, Text: x, Typography_Role: body_large, Style { Foreground: "#000000" } }\n  }\n}\n')
    vm_file = tmp_path / "Home_ViewModel.py"
    vm_file.write_text("from tess_ui import ViewModel\n\n\nclass HomeViewModel(ViewModel):\n    views = 'home'\n")
    spec = importlib.util.spec_from_file_location(vm_file.stem, vm_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    app = App(root=tmp_path, theme_seed=SEED, custom_theme_spec=THEME)
    app.bind(module.HomeViewModel)
    view = app.open_view("Home")
    assert view.node("root.t").get("font_size") == 20.0
    app.set_theme_specs(None, {"typography": {"body_large": {"font_size": 12}}})
    assert view.node("root.t").get("font_size") == 12.0


def test_a_malformed_typography_entry_is_an_error():
    with pytest.raises(ValueError, match="typography: 'body_large' has unknown field"):
        View(_spec(_text("t")), theme_seed=SEED, custom_theme_spec={"typography": {"body_large": {"size": 3}}})
