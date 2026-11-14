"""The Structure area's actions in the window (Main_View.yaml), headless and driven with key events only: Add, Remove, Move up and down, Move to, Duplicate, the menu, Undo and Redo.

Each edit is checked in the file's text line by line, in the tree and in the selection, and the whole flow once from the keyboard alone (open, select, change a value, add a block, move it,
duplicate it, undo, redo, save).
"""

import re

import pytest
from test_shell_config_form_window import FormWindow, folder  # noqa: F401  (the fixture)
from test_shell_config_window import _rows


@pytest.fixture
def w(folder, tmp_path, schema):  # noqa: F811
    window = FormWindow(folder, tmp_path, schema)
    window.open()
    return window


def can(w):
    return {n: getattr(w.vm, f"can_{n}").get() for n in ("add", "remove", "move_up", "move_down", "move_to", "duplicate")}


def value_of(w, label):
    return next(r["value"] for r in _rows(w.vm.structure_nodes.get()) if r["label"] == label)


def pick(w, value):
    """Tab through the open choice list to the row `value` and press Enter on it."""
    assert w.vm.picker_open.get()
    for _ in range(80):
        if any(re.search(rf"option\[{re.escape(value)}\]$", f) for f in w.focused()):
            w.key("enter")
            return
        w.key("tab")
    raise AssertionError(f"no {value} in the list: {[o['value'] for o in w.vm.picker_items.get()]}")


def node_named(w, name):
    return next(inst.id for inst in w.built.view.handle.composition.walk() if inst.name == name)


def selected(w):
    return w.session.model.selected


# -- the actions' states ------------------------------------------------------------------------------------------------------------

def test_each_action_is_enabled_only_where_it_can_be_done(w):
    assert can(w) == {"add": True, "remove": False, "move_up": False, "move_down": False, "move_to": False, "duplicate": False}, "the root block can only take a child"
    w.select("Monitor  Primary")
    assert can(w) == {"add": True, "remove": True, "move_up": False, "move_down": False, "move_to": True, "duplicate": True}
    w.select("Bar  Top_Bar")
    assert can(w)["move_up"] is False and can(w)["move_down"] is True, "the bar is the first block of its monitor, the popup comes after it"
    w.select("Popup  Calendar_Popup")
    assert can(w)["move_up"] is True and can(w)["move_down"] is False and can(w)["add"] is True
    w.select("Clock  Clock")
    assert can(w)["add"] is False, "a block the schema says holds nothing has nothing to add"
    w.select("Battery")
    assert can(w) == {"add": False, "remove": False, "move_up": False, "move_down": False, "move_to": False, "duplicate": False}, "a block inside an If is edited in the text view"


def test_the_buttons_and_the_menu_show_the_states(w):
    w.select("Bar  Top_Bar")
    names = {inst.name: inst for inst in w.built.view.handle.composition.walk() if inst.name}
    assert {"add_button", "remove_button", "up_button", "down_button", "move_button", "duplicate_button", "menu_button"} <= set(names)
    assert w.built.view.node(node_named(w, "up_button")).get("disabled") is True and w.built.view.node(node_named(w, "down_button")).get("disabled") is False
    items = w.vm.menu_items.get()
    assert [i.get("label") for i in items if "label" in i] == ["Add child...", "Remove", "Move up", "Move down", "Move to...", "Duplicate"]
    assert [i["shortcut"] for i in items if "shortcut" in i] == ["Ctrl+Shift+N", "Delete", "Alt+Up", "Alt+Down", "Ctrl+Shift+M", "Ctrl+Shift+D"]
    assert [i["disabled"] for i in items if "label" in i] == [False, False, True, False, False, False]


# -- add ---------------------------------------------------------------------------------------------------------------------------

def test_add_lists_the_allowed_children_and_writes_the_new_block_with_its_required_keys_only(w, schema):
    w.select("Monitor  Primary")
    before = w.session.model.text
    w.key("n", ctrl=True, shift=True)
    assert [o["value"] for o in w.vm.picker_items.get()] == ["Bar", "Panel", "Popup", "Frame"] and w.vm.picker_title.get() == "Add to Monitor  Primary"
    pick(w, "Frame")
    assert [line[1:].strip() for line in w.diff(before)] == ["Children {", "Frame {", "Name: Frame_1", "Thickness: 4", "}", "}"], "a Monitor keeps its blocks in a Children block, made with the first (the real checker refuses them in the Monitor)"
    assert w.session.model.selected.name == "Primary", "the selection stays on the block the person was on"
    assert "Frame  Frame_1" in [r["label"] for r in _rows(w.vm.structure_nodes.get())] and "Added Frame" in w.vm.status.get()


def test_a_second_block_of_a_type_gets_the_next_name(w):
    w.select("Monitor  Primary")
    for _ in range(2):
        w.key("n", ctrl=True, shift=True)
        pick(w, "Panel")
    assert "Name: Panel_1" in w.session.model.text and "Name: Panel_2" in w.session.model.text


# -- remove ------------------------------------------------------------------------------------------------------------------------

def test_delete_in_the_structure_tree_removes_the_block_and_selects_its_parent(w):
    w.select("Popup  Calendar_Popup")
    w.vm.structure_selected.set(value_of(w, "Popup  Calendar_Popup"))
    before = w.session.model.text
    w.built.shortcuts.move_focus(1)
    w.built.shortcuts.move_focus(1)
    w.built.shortcuts.move_focus(-1)
    assert w.region() == 1
    w.key("delete")
    assert [line[1:].strip() for line in w.diff(before)] == ["Popup {", "Name: Calendar_Popup", "Width: 280", "Height: 240", "}"] and all(line[0] == "-" for line in w.diff(before))
    assert "Calendar_Popup" not in w.session.model.text and "# the popup the clock opens" in w.session.model.text, "the comment above it stays"
    assert selected(w).name == "Primary" and w.vm.status.get() == "Removed Popup  Calendar_Popup"


def test_a_block_inside_an_if_is_refused_with_a_message_and_the_window_stays_as_it_was(w):
    w.select("Battery")
    before = w.session.model.text
    for keys in (dict(key="delete", ctrl=True, shift=True), dict(key="d", ctrl=True, shift=True), dict(key="arrow_down", alt=True)):
        w.key(keys.pop("key"), **keys)
        assert w.vm.status_is_error.get() and "If or For" in w.vm.status.get(), w.vm.status.get()
    assert w.session.model.text == before and not w.vm.can_undo.get()


# -- move --------------------------------------------------------------------------------------------------------------------------

def test_alt_up_and_alt_down_move_the_block_past_its_neighbour_and_the_selection_and_focus_follow_it(w):
    w.select("Bar  Top_Bar")
    w.built.shortcuts.move_focus(1)
    assert w.region() == 1
    before = w.session.model.text
    w.key("arrow_down", alt=True)
    assert w.session.model.text.index("Popup {") < w.session.model.text.index("Bar {") and selected(w).name == "Top_Bar"
    labels = [r["label"] for r in _rows(w.vm.structure_nodes.get())]
    assert labels.index("Popup  Calendar_Popup") < labels.index("Bar  Top_Bar") and w.vm.structure_selected.get() == value_of(w, "Bar  Top_Bar")
    assert any(value_of(w, "Bar  Top_Bar") in f for f in w.focused()), "the focus follows the block, so the next Alt+Down moves the same one"
    assert can(w)["move_down"] is False and can(w)["move_up"] is True
    w.key("arrow_up", alt=True)
    labels = [r["label"] for r in _rows(w.vm.structure_nodes.get())]
    assert labels.index("Bar  Top_Bar") < labels.index("Popup  Calendar_Popup") and selected(w).name == "Top_Bar"
    for _ in range(2):  # a comment above a block stays where it is when the block moves (tess_dl), so moving back is not the same bytes: undo is
        w.key("z", ctrl=True)
    assert w.session.model.text == before and selected(w).name == "Top_Bar"


def test_move_to_lists_the_blocks_that_may_hold_it_and_moves_it_last_into_the_one_picked(w):
    w.select("Text")
    before = w.session.model.text
    w.key("m", ctrl=True, shift=True)
    options = [o["label"] for o in w.vm.picker_items.get()]
    assert all(o.startswith("Shell › ") for o in options) and any(o.endswith("Popup  Calendar_Popup") for o in options) and not any(o.endswith("Bar  Top_Bar") for o in options), "a Bar that has its Children block is offered as that block"
    pick(w, value_of(w, "Popup  Calendar_Popup"))
    assert selected(w).type == "Text"
    parent = w.session.model.node_at(w.session.model.selection[:-1])
    assert parent.type == "Children" and w.session.model.node_at(w.session.model.selection[:-2]).type == "Popup" and "Moved Text into" in w.vm.status.get()
    assert w.session.model.undo() and w.session.model.text == before


def test_move_to_says_so_when_no_block_can_take_it(w):
    w.select("Monitor  Primary")
    w.key("m", ctrl=True, shift=True)
    assert w.vm.status_is_error.get() and "no other block" in w.vm.status.get() and not w.vm.picker_open.get()


# -- duplicate ---------------------------------------------------------------------------------------------------------------------

def test_duplicate_copies_the_block_after_it_with_a_name_no_other_block_has(w):
    w.select("Popup  Calendar_Popup")
    before = w.session.model.text
    w.key("d", ctrl=True, shift=True)
    added = [line[1:].strip() for line in w.diff(before)]
    assert added == ["Popup {", "Name: Calendar_Popup_Copy", "Width: 280", "Height: 240", "}"]
    assert selected(w).name == "Calendar_Popup" and w.vm.status.get() == "Duplicated Popup  Calendar_Popup as Popup  Calendar_Popup_Copy"


# -- undo and redo -----------------------------------------------------------------------------------------------------------------

def test_undo_and_redo_after_each_structure_edit_restore_the_bytes_the_selection_and_the_toolbar(w):
    w.select("Bar  Top_Bar")
    start = w.session.model.text
    assert not w.vm.can_undo.get() and not w.vm.can_redo.get()
    stages = []
    w.key("d", ctrl=True, shift=True)
    stages.append(w.session.model.text)
    w.key("arrow_down", alt=True)
    stages.append(w.session.model.text)
    w.key("n", ctrl=True, shift=True)
    pick(w, "Box")
    stages.append(w.session.model.text)
    w.key("delete", ctrl=True, shift=True)
    assert selected(w).type == "Monitor", "removing the selected block selects its parent"
    assert w.vm.can_undo.get() and not w.vm.can_redo.get()
    for earlier in (stages[2], stages[1], stages[0], start):
        w.key("z", ctrl=True)
        assert w.session.model.text == earlier and w.vm.text.get() == earlier
        assert selected(w).name == "Top_Bar", "the selection returns to what it was before the edit"
    assert selected(w).name == "Top_Bar" and not w.vm.can_undo.get() and w.vm.can_redo.get()
    for later in (stages[0], stages[1], stages[2]):
        w.key("y", ctrl=True)
        assert w.session.model.text == later and selected(w).name == "Top_Bar"


# -- the menu ----------------------------------------------------------------------------------------------------------------------

def test_a_right_click_in_the_structure_area_and_the_menu_key_open_the_menu_and_a_choice_runs_the_action(w):
    w.select("Popup  Calendar_Popup")
    x = 216 + 20
    w.window.simulate("secondary_click", x=x, y=300)
    w.settle()
    assert w.vm.menu_open.get() and any("structure_menu" in f for f in w.focused())
    w.key("escape")
    assert not w.vm.menu_open.get()
    w.key("f10", shift=True)
    assert w.vm.menu_open.get()
    w.key("escape")
    w.key("context_menu")
    assert w.vm.menu_open.get()
    before = w.session.model.text
    for _ in range(2):  # Add, Remove, Move up: the dividers and the disabled rows are skipped
        w.key("arrow_down")
    w.key("enter")
    assert not w.vm.menu_open.get() and w.vm.status.get() == "Moved Popup  Calendar_Popup up" and w.session.model.text != before


def test_a_disabled_menu_item_does_nothing(w):
    w.select("Clock  Clock")
    w.vm.structure_command("add")
    assert not w.vm.picker_open.get() and w.vm.status_is_error.get() and "nothing to add" in w.vm.status.get()


# -- one full edit from the keyboard alone ------------------------------------------------------------------------------------------

def test_open_select_change_a_value_add_a_block_move_it_duplicate_undo_redo_and_save_from_the_keyboard_alone(folder, tmp_path, schema):  # noqa: F811
    w = FormWindow(folder, tmp_path, schema)
    main = folder / "Shells" / "Main_Shell.tdl"
    original = main.read_bytes()
    w.row("f:Shells/Main_Shell.tdl")
    w.key("enter")  # open
    w.key("F6")
    w.row(value_of(w, "Bar  Top_Bar"))
    w.key("enter")  # select
    w.key("F6")
    w.tab(4)
    w.key("enter")
    w.tab(3)
    assert w.where() == "k:Height.field"
    w.type_over("48")
    w.key("Enter")  # change a value
    changed = w.session.model.text
    assert w.diff(original.decode()) == ["-Height: 32", "+Height: 48"]
    w.key("F6")
    w.key("F6", shift=True)
    w.key("F6", shift=True)
    assert w.region() == 1
    w.key("n", ctrl=True, shift=True)
    pick(w, "Box")  # add a block
    added = w.session.model.text
    assert added.count("Box { }") == 1 and selected(w).name == "Top_Bar"
    w.key("arrow_down", alt=True)  # move the bar below the popup
    moved = w.session.model.text
    assert moved.index("Popup {") < moved.index("Bar {") and selected(w).name == "Top_Bar"
    w.key("d", ctrl=True, shift=True)  # duplicate
    duplicated = w.session.model.text
    assert duplicated.count("Name: Top_Bar_Copy") == 1 and selected(w).name == "Top_Bar"
    for earlier in (moved, added, changed):
        w.key("z", ctrl=True)
        assert w.session.model.text == earlier and selected(w).name == "Top_Bar"
    w.key("y", ctrl=True)
    assert w.session.model.text == added
    w.key("y", ctrl=True)
    assert w.session.model.text == moved and main.read_bytes() == original, "nothing reaches the disk before the save"
    w.key("s", ctrl=True)
    assert main.read_bytes() == moved.encode() and not w.vm.dirty.get()
    assert (tmp_path / "state").exists() and list((tmp_path / "state").rglob("Main_Shell*")), "the first save kept the old file"


def test_a_form_edit_a_structure_edit_and_a_text_edit_each_undo_as_one_step_and_the_selection_returns(w):
    w.select("Bar  Top_Bar")
    start = w.session.model.text
    w.open_group("Size")
    w.focus("k:Height", "field")
    w.type_over("48")
    w.key("Enter")  # a form edit
    after_form = w.session.model.text
    w.key("d", ctrl=True, shift=True)  # a structure edit
    after_structure = w.session.model.text
    for part in ("1", "2", "3"):  # a run of typing in the text view
        w.vm.text.set(w.session.model.text.replace("Width: 280", f"Width: 28{part}"))
        w.vm.text_edited()
    after_text = w.session.model.text
    assert after_text != after_structure and selected(w).name == "Top_Bar"
    for earlier in (after_structure, after_form, start):
        w.key("z", ctrl=True)
        assert w.session.model.text == earlier and selected(w).name == "Top_Bar" and w.vm.text.get() == earlier
    w.key("y", ctrl=True)
    w.key("y", ctrl=True)
    w.key("y", ctrl=True)
    assert w.session.model.text == after_text and selected(w).name == "Top_Bar"


def test_delete_outside_the_structure_tree_is_the_fields_own_and_removes_no_block(w):
    w.select("Popup  Calendar_Popup")
    before = w.session.model.text
    w.built.shortcuts.move_focus(-1)  # the Text area
    assert w.region() == 3
    w.key("delete")
    w.built.shortcuts.move_focus(-1)  # the Form area
    w.key("delete")
    assert w.session.model.text == before and not w.vm.can_undo.get()
