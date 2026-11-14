"""The keyboard pass: every pane, control, form row and menu entry has an accessible name (and a description where the schema or the window says what it does), and Tab visits the areas in reading order."""

import re
import shutil

import pytest
from test_shell_config_form_window import FormWindow
from test_shell_config_window import CONFIG

PANES = ("toolbar", "files_pane", "files_actions", "structure_pane", "structure_actions", "form_pane", "text_pane", "problems_pane", "status_bar")
#: The form's own widgets (the shipped ones - colour picker, icon picker, font list, key recorder, list editor, token button - are named by their `label:` and are checked for a name only).
DESCRIBED = ("switch", "choose", "field", "side_0", "unit_button", "block_button", "group_header")


@pytest.fixture
def folder(tmp_path):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    return target


@pytest.fixture
def w(folder, tmp_path, schema):
    window = FormWindow(folder, tmp_path, schema)
    window.open()
    window.select("Bar  Top_Bar")
    window.open_all_groups()
    return window


def nodes(w):
    for inst in w.built.view.handle.composition.walk():
        try:
            yield inst, w.built.view.node(inst.id)
        except (KeyError, ValueError):
            continue


def test_every_pane_and_group_has_a_name_and_a_description(w):
    found = {inst.name: node for inst, node in nodes(w) if inst.name in PANES}
    assert set(found) == set(PANES)
    for name, node in found.items():
        assert node.get("role") == "group" and node.get("label") and node.get("description"), name


def test_every_control_that_takes_the_focus_has_a_name(w):
    unnamed = [inst.id for inst, node in nodes(w) if node.get("focusable") and not node.get("label")]
    assert unnamed == []


def test_the_toolbar_and_the_two_action_rows_describe_what_each_button_does(w):
    toolbar = ("save_button", "undo_button", "redo_button", "format_button", "check_button", "reload_button", "apply_switch")
    actions = ("add_button", "remove_button", "up_button", "down_button", "move_button", "duplicate_button", "menu_button", "file_new_button", "file_duplicate_button", "file_rename_button", "file_delete_button")
    found = {inst.name: node for inst, node in nodes(w) if inst.name in toolbar + actions}
    assert set(found) == set(toolbar + actions)
    assert [n for n, node in found.items() if not node.get("label") or not node.get("description")] == []


def test_every_widget_of_a_form_row_is_named_for_its_key_and_described_by_the_keys_doc(w):
    docs = {item["id"]: item["doc"] for item in w.vm.form_items.get() if item["type"] == "row"}
    labels = {item["id"]: item["label"] for item in w.vm.form_items.get() if item["type"] == "row"}
    checked = 0
    for inst, node in nodes(w):
        found = re.search(r"form_item\[([^#\]]+)#\d+\]", inst.id)
        if found is None or inst.name not in DESCRIBED or not node.get("focusable"):
            continue
        row = found.group(1)
        if inst.name == "group_header":
            assert node.get("label") and node.get("description"), inst.id
        else:
            assert labels[row] in (node.get("label") or "").replace("_", " ") and (node.get("description") == docs[row] or not docs[row]), (inst.id, node.get("label"), node.get("description"))
        checked += 1
    assert checked >= 15


def test_every_entry_of_the_structure_menu_and_the_choice_list_has_a_name(w):
    w.vm.structure_menu()
    w.settle()
    entries = [(inst.id, node.get("label")) for inst, node in nodes(w) if node.get("role") == "menuitem"]
    assert [label for _, label in entries] == ["Add child...", "Remove", "Move up", "Move down", "Move to...", "Duplicate"] and all(label for _, label in entries)
    w.vm.menu_open.set(False)
    w.settle()
    w.vm.structure_add()
    w.settle()
    options = [(inst.id, node.get("label")) for inst, node in nodes(w) if inst.name == "option"]
    assert len(options) >= 3 and all(label for _, label in options)


def test_the_trees_rows_and_the_if_and_for_nodes_have_names(w):
    w.select("Bar  Top_Bar")
    rows = [(inst.id, node.get("label")) for inst, node in nodes(w) if node.get("role") == "treeitem"]
    assert len(rows) >= 20 and [i for i, label in rows if not label] == []
    assert any(label == "If battery.present" for _, label in rows) and any(label.startswith("For item In ") for _, label in rows)


def test_a_dialog_the_prompt_and_the_problems_list_are_named(folder, tmp_path, schema):
    w = FormWindow(folder, tmp_path, schema)
    w.open("Themes/Dark_Theme.tdl")
    w.vm.file_rename()
    w.settle()
    named = {inst.name: node for inst, node in nodes(w) if inst.name in ("prompt_field", "prompt_body", "prompt_ok")}
    assert set(named) == {"prompt_field", "prompt_body", "prompt_ok"} and all(n.get("label") for n in named.values())
    assert named["prompt_field"].get("description")


def test_tab_visits_the_toolbar_then_the_files_then_the_structure_then_the_form_then_the_text_in_reading_order(w):
    w.built.shortcuts.move_focus(-1)  # the last area
    w.key("F6")  # wraps to the first
    w.vm.shortcuts.view.node(next(i.id for i, _ in nodes(w) if i.name == "save_button" or i.name == "format_button")).focus()
    w.settle()
    order = []
    for _ in range(400):
        where = w.focused()
        if where:
            panes = [p for p in ("toolbar", "files_pane", "structure_pane", "form_pane", "text_pane", "problems_pane") if f".{p}." in where[0] + "." or where[0].endswith("." + p)]
            pane = panes[0] if panes else "?"
            if not order or order[-1] != pane:
                order.append(pane)
        if order and order[-1] == "text_pane":
            break
        w.key("tab")
    assert order == ["toolbar", "files_pane", "structure_pane", "form_pane", "text_pane"], order


def test_tab_goes_through_the_form_rows_in_the_order_they_are_listed(w):
    w.built.shortcuts._focus("form_pane")
    w.settle()
    assert w.region() == 2
    rows = [i["id"] for i in w.vm.form_items.get() if i["type"] == "row"]
    seen = []
    for _ in range(500):
        found = re.search(r"form_item\[([^#\]]+)#", w.focused()[0]) if w.focused() else None
        if found is None and seen:
            break
        if found is not None and found.group(1).startswith(("k:", "t:")) and (not seen or seen[-1] != found.group(1)):
            seen.append(found.group(1))
        w.key("tab")
    assert [r for r in seen if r in rows] == [r for r in rows if r in seen] and len(seen) >= 20
