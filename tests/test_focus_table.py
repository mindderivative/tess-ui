"""The default Focus mode by role (the behavior standard, SPEC 2.3a) on tess-ui's real widgets: `tab` roles are one Tab stop each, `roving` roles are
one Tab stop for the whole group (arrows move inside), `none` roles take none. The table is pinned here for the widgets that follow it; the one
that does not is pinned as it is in `DISAGREEMENTS`, so fixing it fails its test until the entry is removed."""

import pytest
import tess_re

from tess_ui import controls, widgets as W

TABLE = {
    **dict.fromkeys(("button", "checkbox", "switch", "slider", "textbox", "searchbox"), "tab"),
    **dict.fromkeys(("radio", "tab", "menuitem", "option"), "roving"),
    **dict.fromkeys(("tablist", "tabpanel", "menu", "listbox", "group", "dialog", "status", "tooltip", "none"), "none"),
}


def _window():
    window = tess_re.Window(width=800, height=600)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start", flex_direction="vertical")
    return window


def _nodes(node):
    yield node
    for child in node.children():
        yield from _nodes(child)


def _stops(root, role):
    """How many nodes of `role` under `root` are Tab stops."""
    return sum(1 for node in _nodes(root) if node.get("role") == role and node.get("focusable"))


def test_the_table_is_the_standards_roles_with_tab_roving_or_none():
    assert set(TABLE.values()) == {"tab", "roving", "none"} and TABLE["radio"] == "roving" and TABLE["button"] == "tab"


@pytest.mark.parametrize("role,make", [
    ("button", lambda w: W.button(w, "OK", 100, 40)),
    ("checkbox", lambda w: W.checkbox(w, (255, 255, 255, 255), 40, 40)),
    ("slider", lambda w: W.slider(w, (255, 255, 255, 255), 200, 40)),
])
def test_a_tab_role_is_one_tab_stop(role, make):
    window = _window()
    make(window)
    window.advance(32)
    assert TABLE[role] == "tab" and _stops(window.root, role) == 1


def test_a_page_of_buttons_is_a_tab_stop_each():
    window = _window()
    W.pagination(window, 5, 1)
    window.advance(32)
    assert TABLE["button"] == "tab" and _stops(window.root, "button") == 7  # five pages and the two arrows


@pytest.mark.parametrize("role,make", [
    ("radio", lambda w: _radios(w)),
    ("tab", lambda w: W.tabs(w, ["A", "B", "C"], selected=0, width=300)),
    ("radio", lambda w: W.segmented_button(w, ["A", "B", "C"], selected=0, width=300)),
    ("tab", lambda w: W.navigation_rail(w, ["A", "B", "C"], ["home", "star", "settings"], selected=0)),
])
def test_a_roving_role_is_one_tab_stop_for_the_group(role, make):
    window = _window()
    make(window)
    window.advance(32)
    assert TABLE[role] == "roving" and _stops(window.root, role) == 1


def _radios(window):
    group = controls.RadioGroup()
    return [W.radio_button(window, 48.0, selected=i == 0, group=group) for i in range(3)]


#: What the widgets do that the table says otherwise: name -> (how many Tab stops there are, how many the table wants, why).
DISAGREEMENTS = {
    "list items": (2, 0, "a list's items have the role listitem, which is not a role of the standard, and each is a Tab stop"),
}


def test_a_menus_items_are_one_tab_stop_for_the_menu_and_the_stop_follows_the_focus():
    window = _window()
    button = W.button(window, "Open", 100, 40)
    window.advance(16)
    menu = W.menu(window, [("A", None), ("B", None), ("C", None)])
    button.node.focus()
    menu.open(button.node)
    window.advance(32)
    stop = lambda: [item.get("tab_index") for item in menu.items]  # noqa: E731
    assert TABLE["menuitem"] == "roving" and stop() == [0, -1, -1]
    window.simulate("key_down", key="arrow_down")
    window.advance(16)
    assert stop() == [-1, 0, -1] and menu.items[1].get("focused")


def test_tab_leaves_a_menu_and_focus_goes_back_to_the_opener():
    window = _window()
    button = W.button(window, "Open", 100, 40)
    window.advance(16)
    menu = W.menu(window, [("A", None), ("B", None)])
    button.node.focus()
    menu.open(button.node)
    window.advance(32)
    window.simulate("key_down", key="tab")
    window.advance(32)
    assert not menu.is_open and button.node.get("focused")


def test_the_rows_of_a_selectable_list_are_options_and_one_tab_stop_for_the_list():
    window = _window()
    rows = [W.list_item(window, text) for text in ("A", "B", "C")]
    W.list_(window, rows, selectable="single")
    window.advance(32)
    assert TABLE["option"] == "roving" and TABLE["listbox"] == "none"
    assert [row.node.get("role") for row in rows] == ["option"] * 3 and sorted(row.node.get("tab_index") for row in rows) == [-1, -1, 0]


def test_a_lists_items_are_each_a_tab_stop_and_their_role_is_not_the_standards():
    window = _window()
    W.list_(window, [W.list_item(window, "A"), W.list_item(window, "B")])
    window.advance(32)
    assert "listitem" not in TABLE and _stops(window.root, "listitem") == DISAGREEMENTS["list items"][0]


def test_a_none_role_is_not_a_tab_stop_the_tooltip_layer_and_the_search_clear_button():
    from tess_ui.widgets import search_bar

    window = _window()
    bar = search_bar(window, "Search", 360)
    bar.query.set("ab")
    window.advance(32)
    assert bar.part("clear").get("focusable") is False  # Focus none, by `a11y: focusable: false`
    assert TABLE["tooltip"] == TABLE["none"] == "none" and TABLE["menu"] == "none"
    menu = W.menu(window, [("A", None)])
    menu.open_at(10, 10)
    window.advance(32)
    assert menu.node.get("role") == "menu" and not menu.node.get("focusable")
