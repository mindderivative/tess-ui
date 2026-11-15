"""#197: `Svg` -- a document from a file or inline, tinted by the theme through `currentColor`, described by `alt`."""

import json

import pytest

from tess_ui import App, Signal, ViewModel, tokens

HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20" viewBox="0 0 40 20">'
SQUARE = HEAD + '<rect width="40" height="20" fill="currentColor"/></svg>'
CIRCLE = HEAD + '<circle cx="20" cy="10" r="8" fill="currentColor"/></svg>'


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.picture = Signal("square.svg")
        self.clicked = Signal(0)


def opened(tmp_path, body, files=(("square.svg", SQUARE), ("circle.svg", CIRCLE))):
    (tmp_path / "Views").mkdir(exist_ok=True)
    for name, text in files:
        (tmp_path / "Views" / name).write_text(text)
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        '---\nTDL: 0.2\nName: main\nTesserae: "0.6"\n---\n'
        "Container {\n  Name: main\n  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 100, Height: 100 }\n  Children {\n" + body + "\n  }\n}\n")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


def role(view, name):
    return (view._scheme or tokens.BASELINE)[name]


def alpha_count(view):
    rgba, _, _ = view.window.snapshot()
    return sum(1 for i in range(3, len(rgba), 4) if rgba[i])


def test_a_file_is_drawn_and_currentcolor_is_the_foreground(tmp_path):
    view, _ = opened(tmp_path, "Svg { Name: s, Src: square.svg, Style { Width: 40, Height: 20, Foreground: primary } }")
    node = view.node("root.s")
    assert node.get("svg_color") == role(view, "primary") and "<rect" in node.get("svg") and alpha_count(view) == 40 * 20


def test_a_document_can_be_written_inline(tmp_path):
    view, _ = opened(tmp_path, f"Svg {{ Name: s, Content: {json.dumps(SQUARE)}, Style {{ Width: 40, Height: 20, Foreground: on_surface }} }}")
    assert alpha_count(view) == 40 * 20


def test_the_tint_follows_the_theme(tmp_path):
    view, _ = opened(tmp_path, "Svg { Name: s, Src: square.svg, Style { Width: 40, Height: 20, Foreground: on_surface } }")
    light = view.node("root.s").get("svg_color")
    assert light == role(view, "on_surface")


def test_a_picture_with_alt_is_an_image_and_one_without_is_decorative(tmp_path):
    view, _ = opened(tmp_path, "Svg { Name: a, Src: square.svg, Alt: A bar, Style { Width: 40, Height: 20 } }\n"
                               "Svg { Name: b, Src: square.svg, Style { Width: 40, Height: 20 } }\n"
                               "Svg { Name: c, Src: square.svg, Style { Width: 40, Height: 20 }, Handlers { On_Click { Set { Target: clicked, Value: <| clicked + 1 |> } } } }")
    a, b, c = (view.node(f"root.{n}") for n in "abc")
    assert (a.get("role"), a.get("label")) == ("img", "A bar") and not a.get("a11y_hidden")
    assert b.get("a11y_hidden") is True and not c.get("a11y_hidden")


def test_the_source_follows_a_signal(tmp_path):
    view, vm = opened(tmp_path, "Svg { Name: s, Src: <| picture |>, Style { Width: 40, Height: 20, Foreground: primary } }")
    assert "<rect" in view.node("root.s").get("svg")
    vm.picture.set("circle.svg")
    view.window.advance(16)
    assert "<circle" in view.node("root.s").get("svg") and alpha_count(view) < 40 * 20


def test_one_of_src_and_content_is_needed(tmp_path):
    from tess_ui.spec.nodes import LoadError

    with pytest.raises(LoadError, match="give one of 'src', 'content'"):
        opened(tmp_path, "Svg { Name: s }")
    with pytest.raises(LoadError, match="'src' and 'content' cannot both be given"):
        opened(tmp_path, f"Svg {{ Name: s, Src: square.svg, Content: {json.dumps(SQUARE)} }}")


def test_a_missing_file_names_the_widget_and_the_file(tmp_path):
    with pytest.raises(Exception, match=r"nowhere\.svg"):
        opened(tmp_path, "Svg { Name: s, Src: nowhere.svg, Style { Width: 40, Height: 20 } }")


def test_a_document_that_is_not_svg_is_an_error_naming_the_widget(tmp_path):
    with pytest.raises(Exception, match=r"s\b"):
        opened(tmp_path, "Svg { Name: s, Src: bad.svg, Style { Width: 40, Height: 20 } }", files=(("bad.svg", "not a document"),))


def test_it_matches_the_python_widgets_drawing(tmp_path):
    from tess_ui.widgets import svg

    view, _ = opened(tmp_path, "Svg { Name: s, Src: square.svg, Style { Width: 40, Height: 20, Foreground: primary } }")
    py_app = App(width=100, height=100)
    py = svg(py_app.window, tmp_path / "Views" / "square.svg", 40, 20, color="primary")
    assert py.node.get("svg") == view.node("root.s").get("svg")
