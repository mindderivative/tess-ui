"""#141, #142: the Material 3 badge -- a dot or a pill with a count, alone or over the corner of its host."""

import pytest

from tess_ui import App, Signal, ViewModel, tokens
from tess_ui.shipped import shipped_rules, shipped_views


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.n = Signal(3)


def opened(tmp_path, body, **kwargs):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        "---\nTDL: 0.2\nName: main\n---\nContainer {\n  Name: main\n  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 300, Height: 200, Padding: 20 }\n"
        "  Children {\n" + body + "  }\n}\n")
    app = App(root=tmp_path, **kwargs)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    return view


def mark(view, name="b"):
    return view.node(f"root.{name}.mark")


def role(view, name):
    return (view._scheme or tokens.BASELINE)[name]


def test_the_badge_is_shipped_with_its_look():
    assert "Badge" in shipped_views() and any(rule.widget == "Badge" for sheet in shipped_rules() for rule in sheet.rules)


def test_with_no_value_it_is_a_six_pixel_error_dot(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b }\n")
    m = mark(view)
    assert (m.get("layout_width"), m.get("layout_height")) == (6.0, 6.0) and m.get("corner_radius") == 3.0 and m.get("fill") == role(view, "error")
    assert "root.b.mark.label" not in view._built.specs


@pytest.mark.parametrize("value, text, width", [(3, "3", 16.0), (9, "9", 16.0), (42, "42", 20.0), (123, "123", 26.0), ("New", "New", 26.0)])
def test_a_value_is_a_sixteen_pixel_pill_at_least_sixteen_wide(tmp_path, value, text, width):
    view = opened(tmp_path, f"    Badge {{ Name: b, Value: {value!r} }}\n".replace("'", '"'))
    m = mark(view)
    assert m.get("layout_height") == 16.0 and m.get("layout_width") == width and m.get("corner_radius") == 8.0
    label = view.node("root.b.mark.label")
    assert label.get("text") == text and label.get("fill") == role(view, "on_error") and label.get("font_size") == 11.0


def test_a_count_over_the_max_is_capped(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b, Value: 1500 }\n    Badge { Name: c, Value: 12, Limit: 9 }\n")
    assert view.node("root.b.mark.label").get("text") == "999+" and view.node("root.c.mark.label").get("text") == "9+"


def test_a_count_follows_a_signal(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b, Value: <| n |> }\n")
    assert view.node("root.b.mark.label").get("text") == "3"
    view.handle.viewmodel.n.set(1200)
    view.window.advance(16)
    assert view.node("root.b.mark.label").get("text") == "999+"


def test_show_false_takes_it_away(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b, Value: <| n |>, Show: <| n > 0 |> }\n")
    assert "root.b.mark" in view._built.specs
    view.handle.viewmodel.n.set(0)
    view.window.advance(16)
    assert "root.b.mark" not in view._built.specs


def test_the_mark_is_hidden_from_a_screen_reader(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b, Value: 3 }\n")
    assert mark(view).get("a11y_hidden") is True


HOST = "Style { Width: 24, Height: 24, Background: primary }"


def test_anchored_it_sits_over_the_top_right_corner_of_its_host(tmp_path):
    view = opened(tmp_path, f"    Badge {{ Name: b, Anchored: true, Children {{ Container {{ Name: icon, {HOST} }} }} }}\n")
    icon, m = view.node("root.b.icon"), mark(view)
    right, top = icon.get("layout_x") + icon.get("layout_width"), icon.get("layout_y")
    assert m.get("layout_x") == right - 4 and m.get("layout_y") == top  # a dot overlaps the corner by 4
    assert view.node("root.b").get("layout_width") == 24.0  # the badge does not widen the host's place


def test_a_pill_starts_twelve_in_and_four_above_the_corner(tmp_path):
    view = opened(tmp_path, f"    Badge {{ Name: b, Anchored: true, Value: 3, Children {{ Container {{ Name: icon, {HOST} }} }} }}\n")
    icon, m = view.node("root.b.icon"), mark(view)
    assert m.get("layout_x") == icon.get("layout_x") + 24 - 12 and m.get("layout_y") == icon.get("layout_y") - 4


def test_not_anchored_it_takes_its_own_place_in_the_flow(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b, Value: 3 }\n    Container { Name: after, Style { Width: 10, Height: 10 } }\n")
    assert view.node("root.after").get("layout_y") == mark(view).get("layout_y") + 16.0


def test_a_project_can_restyle_it(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b, Value: 3 }\n", stylesheet_spec={"styles": [{"widget": "Badge", "part": "mark", "style": {"background": "#00FF00"}}]})
    assert mark(view).get("fill") == (0, 255, 0, 255)


def test_a_count_at_the_limit_shows_and_one_over_is_capped(tmp_path):
    view = opened(tmp_path, "    Badge { Name: b, Value: 999 }\n    Badge { Name: c, Value: 1000 }\n")
    assert view.node("root.b.mark.label").get("text") == "999" and view.node("root.c.mark.label").get("text") == "999+"
