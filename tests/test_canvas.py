"""#215: `Canvas`, drawing as data -- rects, circles and paths from a `draw:` list, following the Signals it reads."""

import pytest

from tess_ui import App, Signal, ViewModel, tokens
from tess_ui.spec.canvas import plan
from tess_ui.spec.nodes import LoadError


class Recorder:
    """Stands in for tess_re's Painter: what a canvas's draw callback asked it to paint."""

    def __init__(self):
        self.calls = []

    def fill_rect(self, *a):
        self.calls.append(("rect", *a))

    def fill_circle(self, *a):
        self.calls.append(("circle", *a))

    def stroke_path(self, *a):
        self.calls.append(("path", *a))


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.x = Signal(10)


def opened(tmp_path, canvas):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        "---\nTDL: 0.2\nName: main\n---\nContainer {\n  Name: main\n  Style { Flex_Direction: vertical, Width: 200, Height: 100 }\n  Children {\n" + canvas + "  }\n}\n")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    return view, app.bindings.viewmodel_for("main")


def painted(view, name="root.c"):
    rec = Recorder()
    view.node(name).get("draw")(rec)
    return rec.calls


def test_a_canvas_paints_its_commands_in_order_with_theme_colours(tmp_path):
    view, _ = opened(tmp_path, "    Canvas {\n      Name: c\n      Style { Width: 100, Height: 40 }\n      Draw {\n"
                               "        Item { Rect: [0, 1, 20, 4], Color: primary }\n        Item { Circle: [5, 6, 3], Color: \"#FF0000\" }\n"
                               "        Item { Path: [[0, 0], [10, 10], [20, 0, 30, 10]], Color: \"primary@50%\", Width: 2 }\n      }\n    }\n")
    primary = (view._scheme or tokens.BASELINE)["primary"]
    rect, circle, path = painted(view)
    assert rect == ("rect", 0.0, 1.0, 20.0, 4.0, primary)
    assert circle == ("circle", 5.0, 6.0, 3.0, (255, 0, 0, 255))
    assert path[:2] == ("path", [[0.0, 0.0], [10.0, 10.0], [20.0, 0.0, 30.0, 10.0]]) and path[3] == 2.0
    assert path[2][:3] == primary[:3] and path[2][3] == round(primary[3] * 0.5)
    assert view.node("root.c").get("layout_width") == 100


def test_a_canvas_redraws_when_a_signal_it_reads_changes(tmp_path):
    view, vm = opened(tmp_path, "    Canvas {\n      Name: c\n      Style { Width: 100, Height: 40 }\n"
                                "      Draw: <| [{'circle': [x, 5, 2], 'color': 'primary'}] |>\n    }\n")
    assert painted(view)[0][1] == 10.0
    vm.x.set(40)
    view.window.advance(16)
    assert painted(view)[0][1] == 40.0


@pytest.mark.parametrize("draw, message", [
    ({}, "draw is a list of commands"),
    ([3], r"draw\[0\] is a mapping"),
    ([{"color": "primary"}], "needs exactly one of rect, circle, path"),
    ([{"rect": [0, 0, 1, 1], "circle": [0, 0, 1], "color": "primary"}], "needs exactly one of"),
    ([{"rect": [0, 0, 1, 1]}], "rect needs a color"),
    ([{"rect": [0, 0, 1], "color": "primary"}], r"draw\[0\].rect is 4 numbers"),
    ([{"circle": [0, 0, True], "color": "primary"}], r"draw\[0\].circle is 3 numbers"),
    ([{"rect": [0, 0, 1, 1], "color": "primary", "width": 2}], "rect takes color, rect"),
    ([{"path": [[0, 0]], "color": "primary"}], "path is two or more points"),
    ([{"path": [[0, 0], [1, 2, 3]], "color": "primary"}], r"path\[1\] is 2 or 4 or 6 numbers"),
    ([{"path": [[0, 0, 1], [1, 2]], "color": "primary"}], r"path\[0\] is 2 numbers"),
    ([{"path": [[0, 0], [1, 2]], "color": "primary", "width": 0}], "width is a number above 0"),
])
def test_a_bad_command_names_the_widget_and_the_command(draw, message):
    with pytest.raises(ValueError, match=message):
        plan(draw, lambda c: (0, 0, 0, 255))


def test_a_bad_colour_is_a_build_error(tmp_path):
    with pytest.raises(Exception, match="nonsense"):
        opened(tmp_path, "    Canvas { Name: c, Draw { Item { Rect: [0, 0, 1, 1], Color: nonsense } } }\n")


def test_a_canvas_with_nothing_to_draw_draws_nothing(tmp_path):
    view, _ = opened(tmp_path, "    Canvas { Name: c, Style { Width: 10, Height: 10 } }\n")
    assert painted(view) == []


def test_the_view_language_rejects_a_draw_that_is_not_a_list():
    from tess_ui.spec.nodes import parse_view
    with pytest.raises(LoadError):
        parse_view("---\nTDL: 0.2\nName: T\n---\nCanvas { Draw: 3 }\n", "T_View.tdl")


def test_a_path_is_one_pixel_wide_unless_it_says_otherwise():
    assert plan([{"path": [[0, 0], [1, 1]], "color": "primary"}], lambda c: (1, 2, 3, 4)) == [("path", [[0.0, 0.0], [1.0, 1.0]], (1, 2, 3, 4), 1.0)]
