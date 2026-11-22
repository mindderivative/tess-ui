"""#238: `tooltip:` on any node -- plain and rich, after a hover delay or at once on keyboard focus."""

import pytest

from tess_ui import App, Signal, ViewModel, a11y, tokens
from tess_ui.spec.nodes import LoadError, parse_view


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.hint = Signal("Delete")
        self.clicks = Signal(0)


TDL = "---\nTDL: 0.2\nName: main\n---\n"
CLICK = "Handlers { On_Click { Set { Target: clicks, Value: <| clicks + 1 |> } } }"


def view_text(tooltip="Tooltip: Delete", extra=""):
    """The view's text; `tooltip` is the TDL of the `b` node's tooltip (a property or a block), `extra` more TDL lines in `b`."""
    return TDL + f"""Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Width: 300, Height: 200 }}
  Children {{
    Container {{
      Name: b
      Style {{ Width: 80, Height: 40, Background: primary }}
      {CLICK}
      {tooltip}
{extra}    }}
    Container {{ Name: other, Style {{ Width: 80, Height: 40, Background: secondary }}, {CLICK} }}
  }}
}}
"""


def opened(tmp_path, tooltip="Tooltip: Delete", extra=""):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(view_text(tooltip, extra))
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


def centre(view, name="b"):
    node = view.node(f"root.{name}")
    return node.get("layout_x") + 10, node.get("layout_y") + 10


def hover(view, name="b"):
    x, y = centre(view, name)
    view.window.simulate("pointer_move", x=x, y=y)


def run(view, ms):
    for _ in range(max(1, ms // 16)):
        view.window.advance(16)


def texts(view):
    return [t.get("text") for layer in view._tips.values() for t in layer[0].children()]


def test_a_tooltip_waits_half_a_second_after_the_pointer_arrives(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 300)
    assert not view._tips
    run(view, 300)
    assert texts(view) == ["Delete"]


def test_it_goes_when_the_pointer_leaves_and_is_cancelled_if_it_leaves_first(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 100)
    hover(view, "other")
    run(view, 800)
    assert not view._tips  # left before it showed
    hover(view)
    run(view, 800)
    assert view._tips
    far(view)
    run(view, 100)
    assert view._tips  # the 150 ms grace (ADR-0011): the pointer may be on its way onto the tooltip
    run(view, 100)
    assert not view._tips


def test_a_press_on_the_node_hides_it_and_still_clicks(tmp_path):
    view, vm = opened(tmp_path)
    hover(view)
    run(view, 800)
    assert view._tips
    x, y = centre(view)
    view.window.simulate("pointer_down", x=x, y=y)
    view.window.simulate("pointer_up", x=x, y=y)
    view.window.simulate("click", node=view.node("root.b"))
    assert not view._tips and vm.clicks.get() >= 1


def test_keyboard_focus_shows_it_at_once_and_leaving_hides_it(tmp_path):
    view, _ = opened(tmp_path)
    view.window.simulate("key_down", key="tab")  # focus arrives from the keyboard, on the first Tab stop
    view.window.advance(16)
    assert texts(view) == ["Delete"]
    view.window.simulate("key_down", key="tab")
    view.window.advance(16)
    assert not view._tips


def test_focus_that_a_mouse_gave_is_not_a_reason_to_show_it(tmp_path):
    view, _ = opened(tmp_path)
    x, y = centre(view)
    view.window.simulate("pointer_down", x=x, y=y)
    view.window.simulate("pointer_up", x=x, y=y)
    view.window.advance(16)
    assert not view._tips


def test_escape_hides_it(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 800)
    assert view._tips
    view.window.simulate("key_down", key="escape")
    assert not view._tips


def test_a_rich_tooltip_has_a_title_and_a_surface(tmp_path):
    view, _ = opened(tmp_path, "Tooltip { Text: Removes the file for good, Title: Delete }")
    hover(view)
    run(view, 800)
    layer = next(iter(view._tips.values()))[0]
    assert texts(view) == ["Delete", "Removes the file for good"]
    assert layer.get("corner_radius") == 12.0 and layer.get("fill") == (view._scheme or tokens.BASELINE)["surface_container"]


def test_a_plain_one_is_the_inverse_surface(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 800)
    layer = next(iter(view._tips.values()))[0]
    assert layer.get("fill") == (view._scheme or tokens.BASELINE)["inverse_surface"] and layer.get("corner_radius") == 4.0


def test_the_delay_is_a_property(tmp_path):
    view, _ = opened(tmp_path, "Tooltip { Text: Quick, Delay: 100 }")
    hover(view)
    run(view, 160)
    assert texts(view) == ["Quick"]


def test_the_text_can_be_an_expression_read_when_it_shows(tmp_path):
    view, vm = opened(tmp_path, "Tooltip: <| hint |>")
    vm.hint.set("Remove")
    hover(view)
    run(view, 800)
    assert texts(view) == ["Remove"]


def test_the_layer_is_hoverable_so_the_pointer_can_move_onto_it_AC_TIP_17(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 800)
    assert next(iter(view._tips.values()))[0].get("hit_testable") is True


def test_the_text_is_the_nodes_description_where_it_has_none(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(a11y, "apply_extras", lambda node, props: seen.append(props))
    opened(tmp_path)
    assert {"description": "Delete"} in seen


def test_an_a11y_description_of_its_own_is_kept(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(a11y, "apply_extras", lambda node, props: seen.append(props))
    opened(tmp_path, "Tooltip: Delete", "      A11y { Description: Mine }\n")
    assert {"description": "Delete"} not in seen


def test_closing_the_view_takes_a_showing_tooltip_with_it(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 800)
    view.close()
    assert not view._tips


@pytest.mark.parametrize("value, message", [
    ("Tooltip: 3", "takes text, or a mapping"), ("Tooltip { Title: Hi }", "needs text"), ("Tooltip { Text: Hi, Size: 3 }", "no tooltip field 'size'"),
    ("Tooltip { Text: 3 }", "tooltip text is text"), ("Tooltip { Text: Hi, Delay: -1 }", "delay is milliseconds"),
    ("Tooltip { Text: Hi, Delay: soon }", "delay is milliseconds"),
])
def test_a_wrong_tooltip_is_a_load_error(value, message):
    with pytest.raises(LoadError, match=message):
        parse_view(TDL + f"Container {{ {value} }}\n", "T_View.tdl")


def test_a_view_call_can_carry_a_tooltip_to_the_root_of_the_view(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Chip_View.tdl").write_text(TDL.replace("main", "Chip") + "Container { Style { Width: 60, Height: 30, Background: primary } }\n")
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        TDL + "Container {\n  Name: main\n  Style { Width: 300, Height: 200 }\n  Children {\n    Chip { Name: c, Tooltip: Hello }\n  }\n}\n")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    hover(view, "c")
    run(view, 800)
    assert texts(view) == ["Hello"]


def test_only_escape_hides_it(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 800)
    view.window.simulate("key_down", key="a")
    assert view._tips


def test_asking_to_show_it_twice_makes_one_layer(tmp_path):
    view, _ = opened(tmp_path)
    inst = next(i for i in view.handle.composition.walk() if i.id == "root.b")
    view._show_tip(inst)
    first = view._tips["root.b"][0]
    view._show_tip(inst)
    assert view._tips["root.b"][0] == first and len(view._tips) == 1


def test_a_click_elsewhere_while_it_shows_still_lands(tmp_path):
    view, vm = opened(tmp_path)
    hover(view)
    run(view, 800)
    assert view._tips
    view.window.simulate("pointer_move", x=290, y=190)  # off the node and off the tooltip: it goes after the grace
    run(view, 250)
    assert not view._tips
    view.window.simulate("click", node=view.node("root.other"))
    assert vm.clicks.get() == 1  # a tooltip is not a layer that eats the next press once it has gone


def test_a_node_that_leaves_the_view_takes_its_tooltip_with_it(tmp_path):
    class Gone(ViewModel):
        views = "main"

        def __init__(self):
            super().__init__()
            self.here = Signal(True)

    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        TDL + "Container {\n  Name: main\n  Style { Width: 300, Height: 200 }\n  Children {\n"
        "    If <| here |> {\n      Container { Name: b, Style { Width: 80, Height: 40, Background: primary }, Tooltip: Hi }\n    }\n  }\n}\n")
    app = App(root=tmp_path)
    app.bind(Gone)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    hover(view)
    run(view, 800)
    assert view._tips
    app.bindings.viewmodel_for("main").here.set(False)
    view.window.advance(16)
    assert not view._tips


# -- rich tooltips (#147): actions, placement, a card the pointer can enter ---------------------------------------------------

RICH = """Tooltip {
        Text: "Removes it for good"
        Title: Delete
        Actions {
          Item { Label: Undo, On_Click { Set { Target: clicks, Value: <| clicks + 10 |> } } }
          Item { Label: Close, On_Click { Set { Target: hint, Value: <| 'closed' |> } } }
        }
      }"""


def layer_of(view):
    return next(iter(view._tips.values()))[0]


def action_nodes(view):
    row = layer_of(view).children()[-1]
    return row.children()


def far(view):
    view.window.simulate("pointer_move", x=290, y=190)  # off the node and off the card


def move_to(view, node):
    view.window.simulate("pointer_move", x=node.get("layout_x") + 4, y=node.get("layout_y") + 4)


def test_a_rich_tooltip_shows_a_subhead_text_and_its_actions(tmp_path):
    view, _ = opened(tmp_path, RICH)
    hover(view)
    run(view, 800)
    layer = layer_of(view)
    assert [c.get("text") for c in layer.children()[:2]] == ["Delete", "Removes it for good"]
    assert [a.children()[0].get("text") for a in action_nodes(view)] == ["Undo", "Close"]
    assert layer.get("hit_testable") is True and layer.get("shadows")


def test_a_plain_tooltip_can_be_entered_and_the_pointer_on_it_keeps_it_AC_TIP_17(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 800)
    assert layer_of(view).get("hit_testable") is True
    move_to(view, layer_of(view))  # off the node, onto the tooltip
    run(view, 600)
    assert view._tips
    far(view)
    run(view, 250)
    assert not view._tips


def test_pressing_an_action_runs_its_handler_and_closes_the_tooltip(tmp_path):
    view, vm = opened(tmp_path, RICH)
    hover(view)
    run(view, 800)
    view.window.simulate("click", node=action_nodes(view)[0])
    assert vm.clicks.get() == 10 and not view._tips
    far(view)
    run(view, 32)
    hover(view)
    run(view, 800)
    view.window.simulate("click", node=action_nodes(view)[1])
    assert vm.hint.get() == "closed" and not view._tips


def test_a_rich_tooltip_stays_while_the_pointer_moves_onto_it_and_goes_when_it_leaves_both(tmp_path):
    view, _ = opened(tmp_path, RICH)
    hover(view)
    run(view, 800)
    move_to(view, layer_of(view))  # off the node, onto the card
    run(view, 400)
    assert view._tips
    far(view)
    run(view, 400)
    assert not view._tips


def test_a_rich_tooltip_goes_if_the_pointer_neither_returns_nor_arrives(tmp_path):
    view, _ = opened(tmp_path, RICH)
    hover(view)
    run(view, 800)
    far(view)
    run(view, 32)
    assert view._tips  # a moment's grace
    run(view, 400)
    assert not view._tips


def test_it_can_sit_above_the_node(tmp_path):
    view, _ = opened(tmp_path, "Tooltip { Text: Hi, Placement: above }")
    view.node("root.b").set(position="absolute", x=100.0, y=100.0)
    view.window.advance(16)
    hover(view)
    run(view, 800)
    assert layer_of(view).get("layout_y") < view.node("root.b").get("layout_y")


@pytest.mark.parametrize("tooltip, message", [
    ("Tooltip { Text: x, Placement: left }", "placement is one of below, above, start, end"),
    ("Tooltip { Text: x, Actions { } }", "one or two"),
    ("Tooltip { Text: x, Actions { Item { Label: A, On_Click: a } Item { Label: B, On_Click: b } Item { Label: C, On_Click: c } } }", "one or two"),
    ("Tooltip { Text: x, Actions { Item { Label: A } } }", "{label: ..., on_click: ...}"),
    ("Tooltip { Text: x, Action: [] }", "no tooltip field 'action'"),
])
def test_these_are_refused_at_load(tooltip, message):
    with pytest.raises(LoadError, match=message.replace("{", r"\{").replace("}", r"\}").replace(".", r"\.")):
        parse_view(view_text(tooltip), "Main_View.tdl")



def test_a_touch_held_in_place_shows_it(tmp_path):
    view, _ = opened(tmp_path)
    view.window.simulate("touch_start", node=view.node("root.b"), id=1)
    run(view, 100)
    assert not view._tips
    run(view, 600)
    assert texts(view) == ["Delete"]


NESTED = TDL + """Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 400, Height: 200 }
  Children {
    Container {
      Name: row
      Tooltip: The row
      Style { Flex_Direction: horizontal, Gap: 8, Width: 100%, Height: 40 }
      Children {
        Container { Name: first, Tooltip: First, Style { Width: 120, Height: 30, Background: primary } }
        Container { Name: second, Tooltip: Second, Style { Width: 30, Height: 30, Background: secondary } }
      }
    }
    Container { Name: other, Style { Width: 80, Height: 40, Background: secondary } }
  }
}
"""


def nested(tmp_path):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(NESTED)
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    return view


def move_onto(view, path):
    node = view.node(f"root.{path}")
    view.window.simulate("pointer_move", x=node.get("layout_x") + 8, y=node.get("layout_y") + 8)


def shown(view):
    return sorted(texts(view)[i] for i in range(len(texts(view))))


def test_every_node_hides_its_own_tooltip_when_the_pointer_leaves_it(tmp_path):
    """Leaving a node hid the tooltip of the LAST node that has one (a closure over the loop's last `away`), so the others stayed for ever."""
    view = nested(tmp_path)
    move_onto(view, "row.first")
    run(view, 600)
    assert shown(view) == ["First"]
    move_onto(view, "row.second")
    run(view, 600)
    assert shown(view) == ["Second"]
    move_onto(view, "other")
    run(view, 250)
    assert shown(view) == []
    run(view, 1000)
    assert shown(view) == []


def test_only_one_tooltip_is_shown_at_a_time_and_the_row_does_not_come_back(tmp_path):
    view = nested(tmp_path)
    move_onto(view, "row")  # the row's own box (its first child is the point under the pointer, so the row is entered first)
    run(view, 600)
    assert len(view._tips) <= 1
    move_onto(view, "row.first")
    run(view, 600)
    assert shown(view) == ["First"]


def test_a_press_hides_the_tooltip_and_none_is_shown_again_until_the_pointer_re_enters(tmp_path):
    view = nested(tmp_path)
    move_onto(view, "row.first")
    run(view, 600)
    node = view.node("root.row.first")
    view.window.simulate("pointer_down", x=node.get("layout_x") + 8, y=node.get("layout_y") + 8)
    view.window.simulate("pointer_up", x=node.get("layout_x") + 8, y=node.get("layout_y") + 8)
    run(view, 1000)
    assert shown(view) == []


SCROLLED = TDL + """Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 300, Height: 200 }
  Children {
    ScrollView {
      Name: pane
      Style { Width: 300, Height: 120 }
      Children {
        Container {
          Name: tall
          Style { Flex_Direction: vertical, Width: 100%, Height: 600 }
          Children {
            Container { Name: first, Tooltip: First, Style { Width: 80, Height: 40, Background: primary }, Handlers { On_Click { Set { Target: clicks, Value: <| clicks + 1 |> } } } }
          }
        }
      }
    }
  }
}
"""


def scrolled_view(tmp_path):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(SCROLLED)
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    return view


def test_a_scroll_of_an_ancestor_dismisses_the_tooltip_AC_TIP_6(tmp_path):
    view = scrolled_view(tmp_path)
    node = view.node("root.pane.tall.first")
    view.window.simulate("pointer_move", x=node.get("layout_x") + 8, y=node.get("layout_y") + 8)
    run(view, 600)
    assert len(view._tips) == 1
    view.window.simulate("wheel", node=view._built.outer["root.pane"], delta_x=0.0, delta_y=40.0)
    run(view, 32)
    assert not view._tips


def test_enter_and_space_on_the_focused_trigger_dismiss_the_tooltip_AC_TIP_7(tmp_path):
    for key in ("enter", "space"):
        view = scrolled_view(tmp_path / key)
        node = view.node("root.pane.tall.first")
        view._show_tip(next(i for i in view.handle.composition.walk() if i.id == "root.pane.tall.first"))
        assert len(view._tips) == 1
        view.window.simulate("key_down", key=key)
        run(view, 32)
        assert not view._tips, key


def _tip_pixels(tmp_path, dark):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(view_text())
    app = App(root=tmp_path, dark=dark, theme_seed=(0x67, 0x50, 0xA4, 0xFF))
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    hover(view)
    run(view, 700)
    (layer, _), = view._tips.values()
    for _ in range(4):
        view.window.advance(16)
    rgba, width, _ = view.window.snapshot()
    x, y = layer.get("layout_x"), layer.get("layout_y")
    pad = lambda dx, dy: tuple(rgba[(int(y + dy) * width + int(x + dx)) * 4:][:3])  # noqa: E731 - a pixel
    return view, pad(3, layer.get("layout_height") / 2), pad(layer.get("layout_width") / 2, 2)


def test_the_tooltip_container_is_opaque_inverse_surface_in_light_and_dark_AC_TIP_11_AC_TIP_21(tmp_path):
    """The owner saw tooltip text with no background (F9): the pixels in the container's padding, where no glyph is, are the scheme's `inverse_surface`."""
    for dark in (False, True):
        view, left, top = _tip_pixels(tmp_path / str(dark), dark)
        wanted = tuple(view._scheme["inverse_surface"][:3])
        assert left == wanted and top == wanted, (dark, left, top, wanted)


def test_losing_the_window_focus_removes_the_tooltip_AC_TIP_8(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 700)
    assert view._tips
    view.window.simulate("active", active=True)  # an event only fires on a change; a headless window starts inactive
    view.window.simulate("active", active=False)
    run(view, 32)
    assert not view._tips


def test_the_tooltip_text_follows_the_themes_type_roles_AC_TYP_3_AC_TIP_13(tmp_path):
    view, _ = opened(tmp_path)
    view._layers.typography["body_small"] = {"font_size": 21.0}
    hover(view)
    run(view, 700)
    (layer, _), = view._tips.values()
    assert layer.children()[0].get("font_size") == 21.0


def _heard(view):
    got = []
    view.on_tooltip_before_change(lambda e: got.append((e.name, e.reason, e.detail, e.previous, e.value, e.target)))
    view.on_tooltip_change(lambda e: got.append((e.name, e.reason, e.detail, e.previous, e.value, e.target)))
    return got


def test_a_tooltip_reports_opening_and_closing_with_reason_and_detail_AC_TIP_BEHAVIOR(tmp_path):
    view, _ = opened(tmp_path)
    got = _heard(view)
    hover(view)
    run(view, 600)
    view.window.simulate("pointer_move", x=290, y=190)
    run(view, 400)
    assert got == [("before_change", "pointer", "hover", False, True, "root.b"), ("change", "pointer", "hover", False, True, "root.b"),
                   ("before_change", "pointer", "grace", True, False, "root.b"), ("change", "pointer", "grace", True, False, "root.b")]


def test_a_listener_can_refuse_a_tooltip_and_a_scroll_or_window_change_is_not_asked_about(tmp_path):
    view, _ = opened(tmp_path)
    view.on_tooltip_before_change(lambda e: e.cancel())
    hover(view)
    run(view, 700)
    assert not view._tips  # refused
    (tmp_path / "b").mkdir()
    view2, _ = opened(tmp_path / "b")
    got = _heard(view2)
    hover(view2)
    run(view2, 700)
    got.clear()
    view2.on_tooltip_before_change(lambda e: e.cancel())  # would refuse anything it is asked
    view2.window.simulate("active", active=True)
    view2.window.simulate("active", active=False)
    run(view2, 32)
    assert not view2._tips and [g[:3] for g in got] == [("change", "api", "window")]


def test_coming_back_onto_the_trigger_while_the_tooltip_closes_keeps_it_open(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 600)
    view.window.simulate("pointer_move", x=290, y=190)
    run(view, 100)  # inside the 150 ms grace
    hover(view)
    run(view, 200)  # past the old grace: it did not close
    assert len(view._tips) == 1
    run(view, 1000)
    assert len(view._tips) == 1


def test_the_tip_layer_has_the_role_tooltip_and_stays_hidden_from_assistive_technology(tmp_path):
    view, _ = opened(tmp_path)
    hover(view)
    run(view, 600)
    layer = next(iter(view._tips.values()))[0]
    assert layer.get("role") == "tooltip" and layer.get("a11y_hidden") is True
