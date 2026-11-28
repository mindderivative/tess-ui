"""MenuBar (ux spec Menu Bar, AC-MBR-1 to 15 as far as headless input reaches): titles, one Tab stop with arrows, open from the keyboard and the pointer, hover switching, Left and Right between menus,
Alt, F10 and mnemonics, the density of the bar, the roles."""

import pytest

from test_density_cascade import opened

MENUS = (
    "[{'label': '&File', 'items': [{'value': 'new', 'label': 'New', 'shortcut': 'Ctrl+N'}, {'value': 'save', 'label': 'Save'}, "
    "{'value': 'more', 'label': 'More', 'submenu': [{'value': 'deep', 'label': 'Deep'}]}]}, "
    "{'label': '&Edit', 'disabled': True, 'items': [{'value': 'undo', 'label': 'Undo'}]}, "
    "{'label': '&View', 'items': [{'value': 'a', 'label': 'A'}, {'value': 'b', 'label': 'B'}]}]"
)
BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 600, Height: 400 }
  Children {
    TextField { Name: field, Label: Name }
    MenuBar {
      Name: bar
      Menus: <| MENUS |>
    }
  }
}
"""


class Rig:
    def __init__(self, tmp_path, density="compact"):
        self.view = opened(tmp_path, BODY.replace('MENUS', MENUS), density)
        self.settle()

    def settle(self, n=8):
        for _ in range(n):
            self.view.window.advance(16)

    def title(self, i):
        return self.view.node(f"root.bar.strip.title[{i}]")

    def key(self, key, **mods):
        self.view.window.simulate("key_down", key=key, **mods)
        self.settle()

    def tap(self, key):
        self.view.window.simulate("key_down", key=key)
        self.view.window.simulate("key_up", key=key)
        self.settle()

    def focused(self):
        return [i for i, n in self.view._built.nodes.items() if n.get("focused") is True]

    def open_menus(self):
        return sorted(self.view._shown_layers)

    def state(self):
        bar = next(i for i in self.view.handle.composition.walk() if i.id == "root.bar")
        return {k: s.get() for k, s in bar.state.items()}


def menu_row(i, row=0):
    return f"root.bar.strip.title[{i}].menu.surface.row[{row}].item"


@pytest.fixture
def rig(tmp_path):
    return Rig(tmp_path)


@pytest.mark.parametrize("level, height", [("default", 40), ("compact", 32), ("dense", 28)])
def test_the_bar_and_its_titles_are_as_high_as_a_control_of_the_density_AC_MBR_1(tmp_path, level, height):
    rig = Rig(tmp_path, level)
    assert rig.title(0).get("layout_height") == rig.title(2).get("layout_height") == height
    assert rig.title(0).get("layout_y") == rig.view.node("root.bar").get("layout_y")


def test_the_titles_have_the_roles_of_a_menu_bar_and_the_names_without_the_mnemonic_mark_AC_MBR_2(rig):
    assert [rig.title(i).get("role") for i in range(3)] == ["menuitem"] * 3
    assert [rig.title(i).get("label") for i in range(3)] == ["File", "Edit", "View"]
    assert rig.view.node("root.bar").get("label") == "Menu bar"
    assert [rig.title(i).get("expanded") for i in range(3)] == [False] * 3
    rig.view.window.simulate("click", node=rig.title(0))
    rig.settle()
    assert rig.title(0).get("expanded") is True and rig.title(2).get("expanded") is False


def test_arrows_move_between_the_titles_and_skip_a_disabled_one_and_wrap_AC_MBR_4(rig):
    rig.title(0).focus()
    rig.settle(2)
    rig.key("arrow_right")
    assert rig.focused() == ["root.bar.strip.title[2]"]
    rig.key("arrow_right")
    assert rig.focused() == ["root.bar.strip.title[0]"]
    rig.key("arrow_left")
    assert rig.focused() == ["root.bar.strip.title[2]"]
    rig.key("home")
    assert rig.focused() == ["root.bar.strip.title[0]"]
    rig.key("end")
    assert rig.focused() == ["root.bar.strip.title[2]"]


@pytest.mark.parametrize("key", ["arrow_down", "arrow_up", "enter"])
def test_down_up_and_enter_open_the_menu_with_its_first_row_in_focus_AC_MBR_5(rig, key):
    rig.title(0).focus()
    rig.settle(2)
    rig.key(key)
    assert rig.open_menus() == ["root.bar.strip.title[0].menu"] and rig.focused() == [menu_row(0)]
    assert rig.title(0).get("expanded") is True


def test_escape_closes_the_menu_and_the_focus_is_its_title_AC_MBR_7(rig):
    rig.title(2).focus()
    rig.settle(2)
    rig.key("arrow_down")
    rig.key("escape")
    assert rig.open_menus() == [] and rig.focused() == ["root.bar.strip.title[2]"]


def test_right_and_left_in_an_open_menu_open_the_next_and_the_previous_menu_and_skip_a_disabled_title_AC_MBR_6(rig):
    rig.title(0).focus()
    rig.settle(2)
    rig.key("arrow_down")
    rig.key("arrow_right")
    assert rig.open_menus() == ["root.bar.strip.title[2].menu"] and rig.focused() == [menu_row(2)]
    rig.key("arrow_right")  # wraps
    assert rig.open_menus() == ["root.bar.strip.title[0].menu"] and rig.focused() == [menu_row(0)]
    rig.key("arrow_left")
    assert rig.open_menus() == ["root.bar.strip.title[2].menu"]


def test_right_on_a_row_with_a_submenu_opens_the_submenu_and_not_the_next_menu_AC_MBR_6(rig):
    rig.title(0).focus()
    rig.settle(2)
    rig.key("arrow_down")
    rig.key("arrow_down")
    rig.key("arrow_down")
    assert rig.focused() == ["root.bar.strip.title[0].menu.surface.row[2].parent_item"]
    rig.key("arrow_right")
    assert "root.bar.strip.title[0].menu" in rig.open_menus() and "root.bar.strip.title[2].menu" not in rig.open_menus()


def test_a_press_opens_a_menu_and_a_second_press_closes_it_and_hover_switches_only_while_one_is_open_AC_MBR_11(rig):
    rig.view.window.simulate("pointer_move", node=rig.title(2))
    rig.settle()
    assert rig.open_menus() == []  # nothing is open: hover only highlights
    rig.view.window.simulate("pointer_move", node=rig.title(0))
    rig.view.window.simulate("click", node=rig.title(0))
    rig.settle()
    assert rig.open_menus() == ["root.bar.strip.title[0].menu"] and rig.focused() != [menu_row(0)]  # by pointer: no row is in focus
    rig.view.window.simulate("pointer_move", node=rig.title(2))
    rig.settle()
    assert rig.open_menus() == ["root.bar.strip.title[2].menu"]
    rig.view.window.simulate("click", node=rig.title(2))
    rig.settle()
    assert rig.open_menus() == []


def test_a_menu_that_escape_closed_opens_again_with_one_press(rig):
    rig.view.window.simulate("click", node=rig.title(0))
    rig.settle()
    rig.key("escape")
    rig.view.window.simulate("click", node=rig.title(0))
    rig.settle()
    assert rig.open_menus() == ["root.bar.strip.title[0].menu"]


def test_choosing_a_row_closes_the_menu_and_sets_chosen(rig):
    rig.view.window.simulate("click", node=rig.title(0))
    rig.settle()
    rig.view.window.simulate("click", node=rig.view.node(menu_row(0, 1)))
    rig.settle()
    assert rig.open_menus() == [] and rig.state() == {"open_menu": -1, "keyed": False, "active": False}


def test_f10_and_a_bare_alt_focus_the_first_title_and_the_same_again_gives_the_focus_back_AC_MBR_8(rig):
    for press in (lambda: rig.key("f10"), lambda: rig.tap("alt")):
        rig.view.node("root.field").focus()
        rig.settle(2)
        press()
        assert rig.focused() == ["root.bar.strip.title[0]"] and rig.state()["active"] is True
        press()
        assert rig.focused() == ["root.field"] and rig.state()["active"] is False


def test_alt_with_another_key_does_not_activate_the_bar_AC_MBR_8(rig):
    rig.view.node("root.field").focus()
    rig.settle(2)
    rig.view.window.simulate("key_down", key="alt")
    rig.view.window.simulate("key_down", key="arrow_left", alt=True)
    rig.view.window.simulate("key_up", key="alt")
    rig.settle()
    assert rig.focused() == ["root.field"] and rig.state()["active"] is False


def test_escape_on_an_active_bar_with_no_menu_gives_the_focus_back_AC_MBR_7(rig):
    rig.view.node("root.field").focus()
    rig.settle(2)
    rig.key("f10")
    rig.key("escape")
    assert rig.focused() == ["root.field"] and rig.state()["active"] is False


def test_alt_and_the_mnemonic_open_the_menu_from_anywhere_and_a_disabled_title_ignores_it_AC_MBR_9(rig):
    rig.view.node("root.field").focus()
    rig.settle(2)
    rig.key("v", alt=True)
    assert rig.open_menus() == ["root.bar.strip.title[2].menu"] and rig.focused() == [menu_row(2)]
    rig.key("escape")
    rig.key("e", alt=True)
    assert rig.open_menus() == []


def test_the_mnemonic_letter_is_underlined_only_while_the_bar_is_active():
    from tess_ui import tokens

    assert tokens.mnemonic_runs("&File", False) == ["File"]
    assert tokens.mnemonic_runs("&File", True) == [{"text": "F", "underline": True}, "ile"]
    assert tokens.mnemonic_runs("Sa&ve as", True) == ["Sa", {"text": "v", "underline": True}, "e as"]
    assert tokens.mnemonic_runs("Fish && Chips", True) == ["Fish & Chips"] and tokens.mnemonic_of("&File") == "f" and tokens.mnemonic_of("None") == ""


def test_a_letter_moves_to_the_title_that_starts_with_it_and_an_unknown_one_changes_nothing_AC_MBR_10(rig):
    rig.title(0).focus()
    rig.settle(2)
    rig.key("v")
    assert rig.focused() == ["root.bar.strip.title[2]"]
    rig.key("z")
    assert rig.focused() == ["root.bar.strip.title[2]"]
