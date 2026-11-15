"""0.3.5 (#84): a built-in component's label never wraps onto a second line.

The engine sizes a text node to its text and rounds the width down to a whole pixel, so an
auto-width label could be a fraction of a pixel too narrow for its own text and wrap
("Add a / task"). Every label of a built-in component is a single line (`wrap: none`), and where its
parent has a width an over-long one ends in an ellipsis. The few texts that are meant to wrap are named here.
"""

import json

import pytest

from tess_ui import App, View
from tess_ui.shipped import shipped_views
from tess_ui.spec.tdl import load_marked_tdl

SHORT = ["OK", "Save", "Add a task", "Sign in", "Continue", "Cancel", "Remove item", "Notifications"]
LONG = "A label that is far too long to fit in any of these components at once"
#: Texts that wrap by design: a dialog's words and a snackbar's message.
WRAPS = {("Dialog", "headline"), ("Dialog", "body"), ("Snackbar", "text"), ("Text", "root"), ("Link", "root")}
#: The parameters that carry a component's own words.
WORDS = ("label", "title", "text", "headline")


def _params_of(name):
    path = shipped_views()[name]
    return load_marked_tdl(path.read_text(encoding="utf-8"), str(path)).get("params") or {}


#: The shipped views that have words of their own (or hold items that do), by name.
LABELLED = sorted(n for n in shipped_views() if any(w in _params_of(n) for w in WORDS)
                  or n in ("DatePickerDay", "NavigationRail", "NavigationDrawer", "Menu", "Tabs", "ButtonGroup"))


def _text_nodes(spec, found=None):
    found = [] if found is None else found
    if spec.get("kind") in ("Text", "Link"):
        found.append(spec["id"])
    for child in spec.get("children") or []:
        _text_nodes(child, found)
    return found


def _call(name, words):
    """The TDL call of the view `name` with `words` in every parameter that carries words (and a handler, an icon, items where it needs them)."""
    params = _params_of(name)
    props = [f"{key.title()}: {json.dumps(words)}" for key in params if key in WORDS]
    props += [f"{key.title()}: noop" for key, decl in params.items() if key.startswith("on_") and "default" not in decl]
    if "icon" in params:
        props.append("Icon: home")
    if "items" in params:
        props.append(f"Items: <| [{{'label': {words!r}, 'text': {words!r}, 'icon': 'home', 'value': 'a', 'screen': 'a'}}] |>")
    return f"{name} {{ Name: x, {', '.join(props)} }}"


@pytest.mark.parametrize("name", LABELLED)
def test_a_label_stays_on_one_line(name, tmp_path):
    (tmp_path / "Views").mkdir()
    for words in [*SHORT, LONG]:
        (tmp_path / "Views" / "Main_View.tdl").write_text(
            f"---\nTDL: 0.2\nName: Main\n---\nContainer {{\n  Name: main\n  Children {{\n    {_call(name, words)}\n  }}\n}}\n")
        app = App(root=tmp_path, width=600, height=400)
        view = app.open_view("Main")
        app.show("main")
        app.window.advance(16)
        for node_id in _text_nodes(view._spec):
            part = node_id.rsplit(".", 1)[-1] if node_id != "x" else "root"
            if (name, part) in WRAPS:
                continue
            node = view.node(node_id)
            try:
                line = node.get("font_size") * (node.get("line_height") or 1.5)
            except ValueError:  # a Link's node is its box; its text is 14 px
                line = 14 * 1.5
            assert node.get("layout_height") <= line * 1.5, \
                f"{name}.{part} wraps {words!r}: {node.get('layout_height')} high, a line is {line:.0f}"


def test_the_sweep_finds_the_text_of_a_button(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        f"---\nTDL: 0.2\nName: Main\n---\nContainer {{\n  Name: main\n  Children {{\n    {_call('Button', 'Save')}\n  }}\n}}\n")
    view = App(root=tmp_path, width=600, height=400).open_view("Main")
    assert any(node_id.endswith(".label") for node_id in _text_nodes(view._spec))


def test_text_takes_wrap_and_overflow():
    spec = {"id": "r", "kind": "Container", "style": {"width": 200, "height": 100}, "children": [
        {"id": "t", "kind": "Text", "text": {"content": "Hello world", "typography_role": "body_large", "wrap": "none",
                                              "overflow": "ellipsis"}, "style": {"foreground": "#FFFFFF"}}]}
    view = View(spec, theme_seed=(1, 2, 3, 255))
    assert (view.node("t").get("wrap"), view.node("t").get("overflow")) == ("none", "ellipsis")


@pytest.mark.parametrize("key, value", [("wrap", "sideways"), ("overflow", "fade")])
def test_a_wrong_wrap_or_overflow_is_a_one_line_error(key, value):
    spec = {"id": "t", "kind": "Text", "text": {"content": "x", "typography_role": "body_large", key: value},
            "style": {"foreground": "#FFFFFF"}}
    with pytest.raises(ValueError, match=rf"text\.{key} must be one of"):
        View(spec, theme_seed=(1, 2, 3, 255))


def test_a_text_field_has_neither():
    spec = {"id": "f", "kind": "TextField", "text": {"content": "", "typography_role": "body_large", "wrap": "none"},
            "style": {"foreground": "#FFFFFF", "background": "#000000", "width": 100, "height": 40}}
    with pytest.raises(ValueError, match="TextField has no text.wrap"):
        View(spec, theme_seed=(1, 2, 3, 255))


def test_a_text_node_is_never_a_fraction_of_a_pixel_too_narrow_for_its_text():
    """The cause of #84: the size set on a Text was its measured width, which the engine rounds down."""
    app = App(width=420, height=540)
    for role in ("label_large", "body_large", "title_medium"):
        for words in ["Add a task", "Tasks", "0 tasks", "Settings", "Notifications"]:
            spec = {"id": "t", "kind": "Text", "text": {"content": words, "typography_role": role}, "style": {"foreground": "#FFFFFF"}}
            view = View(spec, window=app.window, theme_seed=(1, 2, 3, 255))
            app.window.root.add_child(view.root)
            app.window.advance(16)
            node = view.node("t")
            width, _ = app.window.measure_text(words, font_family=node.get("font_family"), font_size=node.get("font_size"),
                                               font_weight=node.get("font_weight"), line_height=node.get("line_height"))
            assert node.get("layout_width") >= width, (role, words, node.get("layout_width"), width)
            view.root.destroy()


def test_a_text_can_be_made_to_wrap_or_not():
    def height(**text):
        app = App(width=300, height=200)
        spec = {"id": "t", "kind": "Text", "text": {"content": LONG, "typography_role": "body_large", **text},
                "style": {"foreground": "#FFFFFF", "width": 120}}
        view = View(spec, window=app.window, theme_seed=(1, 2, 3, 255))
        app.window.root.add_child(view.root)
        app.window.advance(16)
        return view.node("t").get("layout_height")

    assert height() == height(wrap="word")  # wraps by default
    assert height(wrap="none") == 24.0  # one line


def _laid_out(spec):
    app = App(width=600, height=400)
    view = View(spec, window=app.window, theme_seed=(1, 2, 3, 255))
    app.window.root.add_child(view.root)
    app.window.advance(16)
    return app, view


def _centred(parent_style):
    return {"id": "r", "kind": "Container", "style": {"height": 60, "align_content": "left", "padding": 12, **parent_style},
            "children": [{"id": "t", "kind": "Text", "text": {"content": "Add a task", "typography_role": "label_large",
                                                              "text_align": "center"}, "style": {"foreground": "#FFFFFF"}}]}


def test_centred_text_fills_its_parent_so_the_engine_has_a_width_to_centre_in():
    """#85: the engine aligns text within the width it is laid out in; a Text as wide as its text can't be centred."""
    _, view = _laid_out(_centred({"width": 300}))
    assert (view.node("t").get("layout_x"), view.node("t").get("layout_width")) == (12.0, 276.0)


def test_centred_text_in_a_parent_with_no_width_keeps_its_own():
    _, view = _laid_out(_centred({"width": "auto"}))
    assert view.node("t").get("layout_width") == 67.0  # not 0: a percentage of a parent with no width


def test_right_aligned_text_fills_too_and_a_given_width_is_kept():
    spec = _centred({"width": 300})
    spec["children"][0]["text"]["text_align"] = "end"
    _, view = _laid_out(spec)
    assert view.node("t").get("layout_width") == 276.0
    spec["children"][0]["style"]["width"] = 100
    _, view = _laid_out(spec)
    assert view.node("t").get("layout_width") == 100.0


def test_changing_centred_text_keeps_it_filling_its_parent():
    import tess_ui

    class Words(tess_ui.ViewModel):
        def __init__(self, view):
            self.words = tess_ui.Signal("Hi")
            super().__init__(view)

    spec = _centred({"width": 300})
    spec["children"][0]["bindings"] = {"text": "{{ words.get() }}"}
    app, view = _laid_out(spec)
    model = Words(view)
    model.words.set("Add a task")
    app.window.advance(16)
    assert (view.node("t").get("layout_width"), view.node("t").get("min_width")) == (276.0, 67.0)
