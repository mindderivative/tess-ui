"""ChoicePicker (ux spec Choice Picker, the plain popup form): an outlined button of the density's height that opens a Menu of the options under it; keys, hints, hug width."""

import pytest

from test_density_cascade import opened

BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 600, Height: 400, Gap: 8 }
  Children {
    TextField { Name: before, Label: Before }
    ChoicePicker { Name: p, Label: Edge, Value: top, Options: <| OPTIONS |> }
    ChoicePicker { Name: u, Hug: true, Label: Unit, Value: px, Options: <| [{'value': 'px', 'label': 'px'}, {'value': 'pct', 'label': '%'}] |> }
  }
}
"""
OPTIONS = "[{'value': 'top', 'label': 'TOP', 'hint': 'The top edge of the screen'}, {'value': 'left', 'label': 'LEFT', 'disabled': True}, {'value': 'bottom', 'label': 'BOTTOM'}]"


class Rig:
    def __init__(self, tmp_path, density="compact"):
        self.view = opened(tmp_path, BODY.replace("OPTIONS", OPTIONS), density)
        self.settle()

    def settle(self, n=8):
        for _ in range(n):
            self.view.window.advance(16)

    def node(self, i):
        return self.view.node(i)

    def key(self, key):
        self.view.window.simulate("key_down", key=key)
        self.settle()

    def focused(self):
        return [i for i, n in self.view._built.nodes.items() if n.get("focused") is True]

    def layers(self):
        return sorted(self.view._shown_layers)

    def value(self, name="p"):
        return next(i for i in self.view.handle.composition.walk() if i.id == f"root.{name}").identities[-1].get("value")


@pytest.fixture
def rig(tmp_path):
    return Rig(tmp_path)


@pytest.mark.parametrize("level, height", [("default", 40), ("compact", 32), ("dense", 28)])
def test_the_button_is_as_high_as_a_control_of_the_density_AC_CHO_14(tmp_path, level, height):
    r = Rig(tmp_path, level)
    assert r.node("root.p.button").get("layout_height") == height and r.node("root.u.button").get("layout_height") == height


def test_a_hugging_button_is_as_wide_as_its_label_and_at_least_56_wide_and_the_other_fills_its_place_AC_CHO_14(rig):
    assert rig.node("root.u.button").get("layout_width") >= 56 and rig.node("root.u.button").get("layout_width") < 100
    assert rig.node("root.p.button").get("layout_width") == 600


def test_the_button_shows_the_current_label_is_named_for_the_key_and_says_whether_it_is_open(rig):
    assert rig.node("root.p.button.shown").get("text") == "TOP"
    assert rig.node("root.p.button").get("label") == "Edge" and rig.node("root.p.button").get("expanded") is False
    rig.view.window.simulate("click", node=rig.node("root.p.button"))
    rig.settle()
    assert rig.layers() == ["root.p.button.menu"] and rig.node("root.p.button").get("expanded") is True


def test_down_opens_the_menu_with_the_first_row_in_focus_and_escape_gives_the_focus_back(rig):
    rig.node("root.p.button").focus()
    rig.settle(2)
    rig.key("arrow_down")
    assert rig.layers() == ["root.p.button.menu"] and rig.focused() == ["root.p.button.menu.surface.row[0].item"]
    rig.key("escape")
    assert rig.layers() == [] and rig.focused() == ["root.p.button"]


def test_enter_on_a_row_chooses_it_closes_the_menu_and_a_disabled_row_is_skipped(rig):
    rig.node("root.p.button").focus()
    rig.settle(2)
    rig.key("arrow_down")
    rig.key("arrow_down")  # LEFT is disabled: the next row is BOTTOM
    assert rig.focused() == ["root.p.button.menu.surface.row[2].item"]
    rig.key("enter")
    assert rig.layers() == [] and rig.value() == "bottom" and rig.node("root.p.button.shown").get("text") == "BOTTOM"


def test_the_row_of_the_current_value_is_checked_and_a_hint_is_under_its_label(rig):
    rig.view.window.simulate("click", node=rig.node("root.p.button"))
    rig.settle()
    first, last = rig.node("root.p.button.menu.surface.row[0].item"), rig.node("root.p.button.menu.surface.row[2].item")
    assert first.get("checked") is True and last.get("checked") is False
    assert first.get("layout_height") > last.get("layout_height")  # the hint line makes the row taller
    assert "The top edge" in rig.node("root.p.button.menu.surface.row[0].item.label").get("text")


def test_the_popup_is_at_least_as_wide_as_the_button_and_at_least_160(rig):
    rig.view.window.simulate("click", node=rig.node("root.u.button"))
    rig.settle()
    assert rig.node("root.u.button.menu.surface").get("layout_width") >= 160
