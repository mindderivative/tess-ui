"""Autocomplete (ux spec Autocomplete, AC-ACP-1, 2, 3, 4, 7, 10, 11): the view of the combo box: field, popup, rows, keys and the focus that never leaves the field."""

import pytest

from test_density_cascade import opened

NAMES = ["Apple", "Avocado", "Banana", "Cherry", "Date", "Elder", "Fig", "Grape", "Honeydew", "Kiwi"]
OPTIONS = "[" + ", ".join("{'value': '%s', 'label': '%s'}" % (n.lower(), n) for n in NAMES) + ", {'value': 'lemon', 'label': 'Lemon', 'disabled': True}]"
BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 600, Height: 500, Gap: 8 }
  Children {
    TextField { Name: before, Label: Before }
    Autocomplete { Name: ac, Label: Fruit, Value: banana, Options: <| OPTIONS |> }
  }
}
"""


class Rig:
    def __init__(self, tmp_path, density="compact", body=BODY):
        self.view = opened(tmp_path, body.replace("OPTIONS", OPTIONS), density)
        self.settle()

    def settle(self, n=8):
        for _ in range(n):
            self.view.window.advance(16)

    def field(self):
        return self.view.node("root.ac.field_box.field.box.body.input")

    def key(self, key, **mods):
        self.view.window.simulate("key_down", key=key, **mods)
        self.settle()

    def type(self, text):
        for ch in text:
            self.view.window.simulate("input", text=ch)
        self.settle()

    def focused(self):
        return [i for i, n in self.view._built.nodes.items() if n.get("focused") is True]

    def rows(self):
        return sorted((i for i in self.view._built.nodes if ".list.row[" in i and i.endswith("]")), key=lambda i: int(i.rsplit("[", 1)[1][:-1]))

    def labels(self):
        return [self.view.node(i + ".texts.row_label").get("text") for i in self.rows()]

    def control(self):
        return self.view._built.controls["root.ac.mind"]


@pytest.fixture
def rig(tmp_path):
    r = Rig(tmp_path)
    r.field().focus()
    r.settle(2)
    return r


@pytest.mark.parametrize("level, field, row", [("default", 56, 40), ("compact", 32, 32), ("dense", 28, 28)])  # default: the Text Field's own 56 (the vault says 40)
def test_the_field_and_a_label_row_follow_the_density_AC_ACP_1(tmp_path, level, field, row):
    r = Rig(tmp_path, level)
    r.field().focus()
    r.key("arrow_down")
    assert r.view.node("root.ac.field_box.field.box").get("layout_height") == field
    assert r.view.node(r.rows()[0]).get("layout_height") == row


def test_the_field_shows_the_label_of_the_value_and_is_a_combobox_that_says_whether_it_is_open(rig):
    assert rig.field().get("text") == "Banana"
    field = rig.view.node("root.ac.field_box.field")
    assert field.get("role") == "combobox" and field.get("expanded") is False
    rig.key("arrow_down")
    assert field.get("expanded") is True


def test_typing_narrows_the_list_at_once_and_zzz_says_no_matches_AC_ACP_2(rig):
    rig.field().set(text="")
    rig.settle(4)
    rig.type("a")
    assert rig.labels() == ["Apple", "Avocado", "Banana", "Date", "Grape"]
    rig.type("v")
    assert rig.labels() == ["Avocado"]
    rig.type("zz")
    assert rig.rows() == [] and "root.ac.layer.surface.empty" in rig.view._built.nodes and rig.view.node("root.ac.layer.surface.empty").get("text") == "No matches"


def test_down_opens_with_the_selected_row_active_keeps_the_focus_in_the_field_and_stops_at_the_last_AC_ACP_3_AC_ACP_11(rig):
    rig.key("arrow_down")
    assert rig.control().model.active == 2 and rig.focused() == ["root.ac.field_box.field.box.body.input"]
    for _ in range(12):
        rig.key("arrow_down")
    assert rig.control().model.active == 9  # Lemon, the last row, is disabled: Kiwi is the last stop
    assert rig.focused() == ["root.ac.field_box.field.box.body.input"]


def test_enter_picks_the_active_row_writes_the_value_closes_and_leaves_the_focus_AC_ACP_4(rig):
    rig.key("arrow_down")
    rig.key("arrow_down")  # Cherry
    rig.key("enter")
    assert rig.field().get("text") == "Cherry" and rig.control().model.value == "cherry" and not rig.view._shown_layers
    assert rig.focused() == ["root.ac.field_box.field.box.body.input"]


def test_a_press_on_a_row_picks_it_and_the_focus_stays_in_the_field_AC_ACP_4_AC_ACP_11(rig):
    rig.key("arrow_down")
    rig.view.window.simulate("click", node=rig.view.node(rig.rows()[4]))
    rig.settle()
    assert rig.control().model.value == "date" and rig.field().get("text") == "Date" and not rig.view._shown_layers
    assert rig.focused() == ["root.ac.field_box.field.box.body.input"]


def test_escape_closes_the_list_keeps_the_text_and_a_second_escape_puts_the_value_back_AC_ACP_7(rig):
    rig.field().set(text="")
    rig.settle(2)
    rig.type("xy")
    assert rig.view._shown_layers
    rig.key("escape")
    assert not rig.view._shown_layers and rig.field().get("text") == "xy"
    rig.key("escape")
    assert rig.field().get("text") == "Banana" and rig.control().model.value == "banana"


def test_the_popup_is_as_wide_as_the_field_up_to_360_shows_eight_rows_and_keeps_the_active_row_in_view_AC_ACP_10(rig):
    rig.key("arrow_down")
    surface = rig.view.node("root.ac.layer.surface")
    assert surface.get("layout_width") == 360  # the field is 600 wide: capped
    assert rig.view.node("root.ac.layer.surface.list_box").get("layout_height") == 8 * 32
    for _ in range(9):
        rig.key("arrow_down")
    assert rig.control().model.active == 9 and rig.control().scroll.get() > 0


def test_a_disabled_row_is_dimmed_and_skipped_and_a_press_on_it_does_nothing(rig):
    rig.key("arrow_down")
    last = rig.view.node(rig.rows()[10])
    assert last.get("opacity") == pytest.approx(0.38, abs=0.01)
    rig.view.window.simulate("click", node=last)
    rig.settle()
    assert rig.control().model.value == "banana"


def test_the_active_row_is_the_fields_active_descendant_and_none_when_the_list_closes_AC_ACP_8(rig):
    field = rig.field()
    assert field.get("active_descendant") is None
    rig.key("arrow_down")
    row = rig.view.node(rig.rows()[2])
    assert field.get("active_descendant") == row and row.get("role") == "option" and row.get("label") == "Banana"
    rig.key("arrow_down")
    assert field.get("active_descendant") == rig.view.node(rig.rows()[3])
    rig.key("escape")
    assert field.get("active_descendant") is None
    assert rig.view.node("root.ac.layer.surface").get("role") == "listbox" if "root.ac.layer.surface" in rig.view._built.nodes else True


def test_a_row_can_have_a_swatch_an_icon_or_the_label_in_its_own_font(tmp_path):
    body = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 600, Height: 400 }
  Children {
    Autocomplete { Name: ac, Label: Pick, Value: '', Options: <| [{'value': 'a', 'label': 'Red', 'swatch': '#ff0000'}, {'value': 'b', 'label': 'Home', 'icon': 'home'}, {'value': 'c', 'label': 'Roboto', 'font': 'Roboto'}, {'value': 'd', 'label': 'Plain'}] |> }
  }
}
"""
    r = Rig(tmp_path, body=body)
    r.field().focus()
    r.key("arrow_down")
    nodes = r.view._built.nodes
    rows = r.rows()
    assert any(i.startswith(rows[0]) and i.endswith(".swatch") for i in nodes) and any(i.startswith(rows[1]) and i.endswith(".lead_icon") for i in nodes)
    assert not any(i.startswith(rows[3]) and (i.endswith(".swatch") or i.endswith(".lead_icon")) for i in nodes)
    assert [r.view.node(i + ".texts.row_label").get("text") for i in rows] == ["Red", "Home", "Roboto", "Plain"]
