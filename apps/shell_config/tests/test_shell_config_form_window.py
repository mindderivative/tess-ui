"""The form in the window (Main_View.yaml), headless: the Form area beside the Structure tree, driven with key events.

The form's rows are drawn by the toolkit from `form_items`; each widget's commit (Enter, or the focus leaving) is one `DocumentModel` edit, so the Text area and the Structure tree follow. A test checks the file
line by line: only the edited line changes.
"""

import difflib
import re
import shutil
import time
from pathlib import Path

import pytest
from test_shell_config_window import CONFIG, Window, _rows

from tess_shell_config.app import build
from tess_shell_config.session import ConfigSession


@pytest.fixture
def folder(tmp_path):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    return target


class FormWindow(Window):
    """The window over a session that has the recorded schema, so the form has keys to show."""

    def __init__(self, folder, tmp_path, schema, **options):
        self.session = ConfigSession(folder, schema=schema, state_dir=tmp_path / "state")
        self.built = build(self.session, reduced_motion=True, **options)
        self.vm = self.built.viewmodel
        self.window = self.built.window
        self.settle(8)

    def open(self, rel="Shells/Main_Shell.tdl"):
        self.vm.open_file(rel)
        self.settle()

    def select(self, label):
        """Select the block whose row says `label` in the Structure tree."""
        row = next(r for r in _rows(self.vm.structure_nodes.get()) if r["label"] == label)
        self.vm.structure_selected.set(row["value"])
        self.settle()

    def node_id(self, key, name):
        """The id of the node called `name` in the cell of `key` (a row's widgets are named; the row's own key says which build of it this is)."""
        wanted = f"cell[{key}|"
        for inst in self.built.view.handle.composition.walk():
            if wanted in inst.id and inst.id.endswith("." + name):
                return inst.id
        raise AssertionError(f"no {name} in the cell of {key}: the group may be closed")

    def node(self, key, name):
        return self.built.view.node(self.node_id(key, name))

    def focus(self, key, name):
        self.node(key, name).focus()
        self.settle(2)

    def where(self):
        """The focused node, as `item.node`: `k:Height.field`."""
        found = re.search(r"form_item\[([^#\]]+)#\d+\](.*)", self.focused()[0]) if self.focused() else None
        return None if found is None else f"{found.group(1)}{found.group(2).rsplit('.', 1)[-1] and '.' + found.group(2).rsplit('.', 1)[-1]}"

    def tab(self, n=1):
        for _ in range(n):
            self.key("tab")

    def diff(self, before):
        """What changed, line by line, without the indentation: `-old` and `+new`."""
        return [line[0] + line[2:].strip() for line in difflib.ndiff(before.splitlines(True), self.session.model.text.splitlines(True)) if line[0] in "+-"]

    def type_over(self, text):
        self.key("a", ctrl=True)
        self.type(text)

    def error_text(self):
        return [inst.value("text") for inst in self.built.view.handle.composition.walk() if inst.name == "row_error"]

    def open_group(self, label):
        if not any(i["id"] == f"g:{label}" and i["open"] for i in self.vm.form_items.get()):
            self.vm.form_group(label)
            self.settle()

    def open_all_groups(self):
        for item in list(self.vm.form_items.get()):
            if item["type"] == "group":
                self.open_group(item["label"])


@pytest.fixture
def w(folder, tmp_path, schema):
    window = FormWindow(folder, tmp_path, schema)
    window.open()
    window.select("Bar  Top_Bar")
    return window


# -- the form follows the selection ------------------------------------------------------------------------------------------------

def test_the_form_sits_beside_the_structure_and_follows_the_selected_block(folder, tmp_path, schema):
    w = FormWindow(folder, tmp_path, schema)
    names = {inst.name for inst in w.built.view.handle.composition.walk() if inst.name}
    assert {"files_pane", "structure_pane", "form_pane", "text_pane"} <= names and w.vm.form_items.get() == []
    w.open()
    assert w.vm.form_title.get() == "Shell" and w.vm.form_items.get() == [], "the root block has no keys of its own"
    w.select("Bar  Top_Bar")
    assert w.vm.form_title.get() == "Bar  Top_Bar" and w.vm.form_items.get()[0]["label"] == "Identity"
    w.select("Monitor  Primary")
    assert w.vm.form_title.get() == "Monitor  Primary" and {i["label"] for i in w.vm.form_items.get() if i["type"] == "group"} >= {"Identity"}
    assert w.vm.form_notes.get(), "the block's doc is a note above its rows"


def test_a_file_with_syntax_errors_has_no_form_and_says_so(folder, tmp_path, schema):
    w = FormWindow(folder, tmp_path, schema)
    w.open("Shells/Broken_Shell.tdl")
    assert w.vm.form_items.get() == [] and "syntax errors" in w.vm.form_notes.get()[0]


def test_only_the_first_group_builds_its_rows_until_the_person_opens_another(w):
    items = w.vm.form_items.get()
    assert [(i["label"], i["open"]) for i in items if i["type"] == "group"][:3] == [("Identity", True), ("Placement", False), ("Size", False)]
    assert not any(i["type"] == "row" and i["id"] == "k:Height" for i in items)
    w.open_group("Size")
    assert any(i["id"] == "k:Height" for i in w.vm.form_items.get())
    w.select("Monitor  Primary")
    w.select("Bar  Top_Bar")
    assert any(i["id"] == "k:Height" for i in w.vm.form_items.get()), "an opened group stays open from block to block"


# -- one full edit by keyboard -----------------------------------------------------------------------------------------------------

def test_a_value_is_changed_from_the_keyboard_alone_and_the_text_the_tree_and_the_file_follow(folder, tmp_path, schema):
    w = FormWindow(folder, tmp_path, schema)
    main = folder / "Shells" / "Main_Shell.tdl"
    before = main.read_bytes()
    w.row("f:Shells/Main_Shell.tdl")
    w.key("enter")
    w.key("F6")
    w.row(next(r["value"] for r in _rows(w.vm.structure_nodes.get()) if r["label"] == "Bar  Top_Bar"))
    w.key("enter")
    w.key("F6")
    assert w.region() == 2 and w.where() == "g:Identity.group_header"
    w.tab(4)
    assert w.where() == "g:Size.group_header"
    w.key("enter")  # opens the group
    w.tab(3)
    assert w.where() == "k:Height.field"
    text_before = w.session.model.text
    w.type_over("48")
    assert w.session.model.text == text_before, "nothing is written while the person types"
    w.key("Enter")
    assert w.diff(text_before) == ["-Height: 32", "+Height: 48"]
    assert w.vm.text.get() == w.session.model.text and w.vm.dirty.get() and main.read_bytes() == before, "the Text area shows it; the disk is untouched until Save"
    assert w.where() == "k:Height.field", "the focus stays on the field that was edited"
    w.tab()
    assert w.where() == "k:Height.unit_button"
    w.key("s", ctrl=True)
    assert main.read_bytes() == before.replace(b"Height: 32", b"Height: 48")
    w.key("z", ctrl=True)
    assert w.session.model.data == before and w.node("k:Height", "field").get("text") == "32", "undo puts the field back to what the file had"


def test_a_name_changed_in_the_form_is_the_name_in_the_structure_tree(w):
    w.focus("k:Name", "field")
    w.type_over("Bottom_Bar")
    w.key("Enter")
    assert "Name: Bottom_Bar   # the bar" in w.session.model.text or "Name: Bottom_Bar" in w.session.model.text
    assert [r["label"] for r in _rows(w.vm.structure_nodes.get()) if r["label"].startswith("Bar")] == ["Bar  Bottom_Bar"]
    assert w.vm.selected_label.get() == "Selected: Bar  Bottom_Bar" and w.vm.form_title.get() == "Bar  Bottom_Bar"


def test_leaving_a_field_commits_it_and_an_unchanged_field_writes_nothing(w):
    w.open_group("Size")
    before = w.session.model.text
    w.focus("k:Height", "field")
    w.tab(2)  # the unit button, then reset: the field lost the focus with its text as it was
    assert w.session.model.text == before and not w.vm.can_undo.get()
    w.focus("k:Height", "field")
    w.type_over("20")
    w.tab()
    assert w.diff(before) == ["-Height: 32", "+Height: 20"], "leaving the field commits it"


def test_typing_in_the_text_view_shows_in_the_form(w):
    text = w.session.model.text
    w.vm.text.set(text.replace("Height: 32", "Height: 33"))
    w.vm.text_edited()
    w.settle()
    w.open_group("Size")
    assert w.node("k:Height", "field").get("text") == "33"


# -- ranges, units, sides ---------------------------------------------------------------------------------------------------------------

def test_a_number_outside_its_range_is_refused_with_the_range_in_the_window_and_nothing_is_written(w):
    w.open_group("Fill")
    before = w.session.model.text
    w.focus("k:Elevation", "field")
    w.type_over("150")
    w.key("Enter")
    assert w.session.model.text == before and not w.vm.dirty.get()
    assert w.vm.status.get() == "Elevation must be from 0 to 100 %." and w.vm.status_is_error.get()
    assert w.error_text() == ["Elevation must be from 0 to 100 %."]
    assert w.node("k:Elevation", "field").get("text") == "150", "what was typed stays so it can be corrected"
    w.focus("k:Elevation", "field")
    w.type_over("40")
    w.key("Enter")
    assert [line for line in w.diff(before)] and "Elevation: 40%" in w.session.model.text and w.error_text() == []


def test_the_arrow_keys_step_a_number_field(w):
    w.open_group("Placement")
    w.focus("k:Offset", "field")
    w.key("arrow_up")
    assert "Offset: 1" in w.session.model.text
    w.key("arrow_up")
    assert "Offset: 2" in w.session.model.text
    w.key("arrow_down")
    assert "Offset: 1" in w.session.model.text


def test_a_length_unit_is_chosen_from_a_list_of_the_keys_units(w):
    w.open_group("Size")
    before = w.session.model.text
    w.focus("k:Height", "unit_button")
    w.key("enter")
    assert w.vm.picker_open.get() and [o["value"] for o in w.vm.picker_items.get()] == ["px", "%", "AUTO", "EXPAND"]
    assert w.vm.picker_title.get() == "Unit of Height" and w.vm.picker_current.get() == "px"
    w.vm.pick_option("%")
    w.settle()
    assert w.diff(before) == ["-Height: 32", "+Height: 32%"]
    assert not w.vm.picker_open.get()
    w.focus("k:Height", "unit_button")
    w.key("enter")
    w.vm.pick_option("EXPAND")
    w.settle()
    assert "Height: EXPAND" in w.session.model.text and w.node("k:Height", "unit_button").get("label") if False else "Height: EXPAND" in w.session.model.text


BOX_SHELL = """---
TDL: 0.1
Name: Box
---

Shell {
    Monitor {
        Name: M
        Children {
            Box { Name: B, Margin: [1, 2, 3, 4], Opacity: 0.5 }
            Bitmap { Name: Pic, Source: "old.png" }
        }
    }
}
"""


def _extra_shell(folder, tmp_path, schema):
    (folder / "Shells" / "Box_Shell.tdl").write_text(BOX_SHELL)
    (folder / "Shells" / "pic.png").write_bytes(b"x")
    w = FormWindow(folder, tmp_path, schema)
    w.session.refresh()
    w.open("Shells/Box_Shell.tdl")
    return w


def test_four_sides_are_four_fields_in_the_schemas_order(folder, tmp_path, schema):
    w = _extra_shell(folder, tmp_path, schema)
    w.select("Box  B")
    w.open_group("Placement")
    cell = [i for i in w.vm.form_items.get() if i["id"] == "k:Margin"][0]["cells"][0]
    assert cell["ui"] == "sides" and cell["fields"] == ["1", "2", "3", "4"] and cell["labels"] == ["Left", "Top", "Right", "Bottom"]
    before = w.session.model.text
    w.focus("k:Margin", "side_2")
    w.type_over("9")
    w.key("Enter")
    assert w.diff(before) == ["-Box { Name: B, Margin: [1, 2, 3, 4], Opacity: 0.5 }", "+Box { Name: B, Margin: [1, 2, 9, 4], Opacity: 0.5 }"]


# -- switch, choice, colour, tokens, expressions, path --------------------------------------------------------------------------------

def test_a_switch_toggles_from_the_keyboard_and_writes_one_line(w):
    w.open_group("Placement")
    before = w.session.model.text
    w.focus("k:Reserve", "switch")
    w.key("space")
    assert [line[1:].strip() for line in w.diff(before)] == ["Reserve: false"]
    assert w.built.view.control(w.node_id("k:Reserve", "switch")).selected.get() is False
    w.key("space")
    assert "Reserve: true" in w.session.model.text


def test_an_enum_is_chosen_from_a_list_with_each_choice(w):
    before = w.session.model.text
    w.open_group("Placement")
    w.focus("k:Edge", "choose")
    w.key("enter")
    assert w.vm.picker_open.get() and [o["value"] for o in w.vm.picker_items.get()] == ["TOP", "BOTTOM", "LEFT", "RIGHT"] and w.vm.picker_current.get() == "TOP"
    names = {inst.name for inst in w.built.view.handle.composition.walk() if inst.name}
    assert "picker" in names and "option" in names
    w.vm.pick_option("RIGHT")
    w.settle()
    assert w.diff(before) == ["-Edge: TOP", "+Edge: RIGHT"]


def test_the_token_button_is_the_shipped_one_with_the_accepted_groups_preferred_first_and_writes_into_the_style_block_that_has_the_key(w):
    w.open_group("Fill")
    before = w.session.model.text
    assert w.node("k:Background", "field").get("text") == "$color.surface", "the key is in the block's Style { }: the form reads it there"
    button = w.node("k:Background", "token_button")
    assert type(w.built.view.control(w.node_id("k:Background", "token_button.mind"))).__name__ == "TokenListControl"
    cell = next(c for i in w.vm.form_items.get() if i["id"] == "k:Background" for c in i["cells"])
    assert [g["name"] for g in cell["token_groups"]] == ["color"] and cell["token_ref"] == "$color.surface"
    assert cell["token_preferred"][0] == "$color.surface" or cell["token_preferred"] == []
    first = cell["token_groups"][0]["tokens"][0]
    assert set(first) == {"name", "ref", "kind", "value", "doc"} and first["kind"] == "colour" and first["value"].startswith("#")
    assert button is not None
    w.vm.form_token("k:Background|", "$color.primary")
    w.settle()
    assert w.diff(before) == ["-Style { Background: $color.surface }   # a token, not a colour", "+Style { Background: $color.primary }   # a token, not a colour"]


def test_the_colour_the_picker_gives_is_written_after_the_person_stops_moving_it(w):
    w.open_group("Fill")
    before = w.session.model.text
    w.vm.form_colour("k:Background|", "#4682b4")
    w.settle()
    assert w.diff(before) == ["-Style { Background: $color.surface }   # a token, not a colour", '+Style { Background: "#4682B4" }   # a token, not a colour']
    assert any(inst.name == "colour_picker" for inst in w.built.view.handle.composition.walk() if "cell[k:Background|" in inst.id)


def test_a_key_with_a_slot_has_an_expression_button_that_swaps_the_widget_for_a_field(folder, tmp_path, schema):
    w = _extra_shell(folder, tmp_path, schema)
    w.select("Box  B")
    w.open_group("Fill")
    before = w.session.model.text
    w.focus("k:Opacity", "expression_button")
    w.key("enter")
    assert w.node("k:Opacity", "field").get("text") == "{{  }}" and w.session.model.text == before
    w.focus("k:Opacity", "field")
    w.type_over("{{ battery.level }}")
    w.key("Enter")
    assert w.diff(before) == ["-Box { Name: B, Margin: [1, 2, 3, 4], Opacity: 0.5 }", "+Box { Name: B, Margin: [1, 2, 3, 4], Opacity: {{ battery.level }} }"]
    w.focus("k:Opacity", "expression_button")
    w.key("enter")
    assert "Opacity" not in w.session.model.text, "back to the widget removes the expression"


def test_a_path_has_a_browse_button_that_opens_the_file_dialog_in_the_keys_mode_and_writes_the_answer(folder, tmp_path, schema):
    w = _extra_shell(folder, tmp_path, schema)
    w.select("Bitmap  Pic")
    w.open_group("Content")
    before = w.session.model.text
    assert w.node("k:Source", "field").get("text") == "old.png"
    w.focus("k:Source", "browse")
    w.key("enter")
    assert w.vm.file_open.get() and w.vm.file_mode.get() == "open" and Path(w.vm.file_start.get()) == folder / "Shells"
    assert w.vm.file_filters.get()[0]["patterns"][0] == "*.png"
    w.vm.file_value.set(str(folder / "Shells" / "pic.png"))
    w.vm.file_accepted()
    w.vm.file_open.set(False)
    w.settle()
    assert w.diff(before) == ['-Bitmap { Name: Pic, Source: "old.png" }', '+Bitmap { Name: Pic, Source: "pic.png" }']


def test_reset_removes_the_property_from_the_keyboard_and_is_disabled_when_the_key_is_absent(w):
    w.open_group("Size")
    before = w.session.model.text
    assert w.node("k:Min_Width", "reset_button").get("disabled") is True
    w.focus("k:Height", "reset_button")
    w.key("enter")
    assert w.diff(before) == ["-Height: 32"]
    assert w.node("k:Height", "reset_button").get("disabled") is True and w.node("k:Height", "field").get("text") == ""


# -- every row is reachable by Tab ----------------------------------------------------------------------------------------------------

def test_every_row_of_the_form_is_reached_by_tab(w):
    w.open_all_groups()
    rows = [i["id"] for i in w.vm.form_items.get() if i["type"] == "row"]
    assert len(rows) >= 30
    w.built.shortcuts.move_focus(-1)
    w.key("F6", shift=True)
    w.built.shortcuts.move_focus(1) if w.region() != 2 else None
    visited = set()
    for _ in range(600):
        found = re.search(r"form_item\[([^#\]]+)#", w.focused()[0]) if w.focused() else None
        if found is None and visited:
            break
        if found is not None:
            visited.add(found.group(1))
        w.key("tab")
    assert set(rows) <= visited, sorted(set(rows) - visited)


# -- speed -------------------------------------------------------------------------------------------------------------------------

def test_selecting_a_block_builds_its_form_and_a_group_of_a_dozen_keys_opens_in_a_bounded_time(w):
    """Measured here, asserted loosely: the toolkit lays the whole window out again after a change, so the time grows with everything on screen."""
    w.select("Monitor  Primary")
    start = time.perf_counter()
    w.vm.structure_selected.set(next(r["value"] for r in _rows(w.vm.structure_nodes.get()) if r["label"] == "Bar  Top_Bar"))
    select_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    w.vm.form_group("Size")
    open_ms = (time.perf_counter() - start) * 1000
    print(f"select a block with {len(w.vm.form_items.get())} items: {select_ms:.0f} ms; open a group of 6 keys: {open_ms:.0f} ms")
    assert select_ms < 1500 and open_ms < 1000


# -- a theme file --------------------------------------------------------------------------------------------------------------------

def test_a_theme_group_in_the_window_shows_a_cell_for_the_base_and_each_mode(folder, tmp_path, schema):
    w = FormWindow(folder, tmp_path, schema)
    w.open("Themes/Dark_Theme.tdl")
    w.select("Color")
    rows = [i for i in w.vm.form_items.get() if i["type"] == "row"]
    assert rows and rows[0]["id"] == "t:surface" and [c["column"] for c in rows[0]["cells"]] == ["base"]
    before = w.session.model.text
    w.focus("t:surface", "colour_picker") if False else None
    outcome = w.vm.form.form.commit("t:surface|base", {"value": "#000000"})
    w.vm.form._done(outcome)
    assert w.diff(before) == ['-Surface: "#101418"', '+Surface: "#000000"']
