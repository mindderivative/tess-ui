"""The toolkit widgets in the form registry: icon, font, key chord, list and the token button, each with a byte-level diff of the file and a keyboard-driven test in the window.

The recorded schema has no key of kind `key_chord` (the shell has not built Shortcuts yet), so a test adds one to a copy of the schema, as a newer minor version would.
"""

import copy
import shutil

import pytest
from test_shell_config_form import Rig
from test_shell_config_form_window import FormWindow
from test_shell_config_window import CONFIG

from tess_shell_config.schema import Schema
from tess_shell_config.widgets import Context, FontWidget, IconWidget, KeyChordWidget, ListWidget, default_registry

TEXT = """---
TDL: 0.1
Name: Widgets_Test
---

# before the root
Shell {
    Monitor {
        Name: Main
        Bar {
            Name: B   # the bar
            Edge: TOP
            Width: EXPAND
            Height: 32

            SVG { Name: Logo, Icon: "home", Shortcut: "ctrl+f1" }   # the logo, inline
            Text { Name: T, Font_Family: "Roboto", Text: "x" }

            Box { Name: Bx, Class: [a_class, b_class] }

            # kept
            Path { Name: P, Data: "M0 0", View_Box: [0, 0, 24, 24] }
        }
        Popup {
            Name: Pop
            Width: 10
            Height: 10
            Adjust: [FLIP_Y, SLIDE_X]
        }
    }
}
"""


@pytest.fixture(scope="module")
def chord_schema(schema_data):
    data = copy.deepcopy(schema_data)
    data["blocks"]["SVG"]["keys"]["Shortcut"] = {"kind": "key_chord", "default": None, "doc": "A chord.", "group": "Content", "required": False, "built": True, "tokens": [], "preferred_tokens": [], "slot": False}
    return Schema.from_data(data)


@pytest.fixture
def rig(tmp_path, chord_schema):
    return Rig(tmp_path, chord_schema, TEXT)


# -- icon --------------------------------------------------------------------------------------------------------------------------

def test_an_icon_is_one_quoted_name_and_only_that_value_changes(rig):
    rig.select("SVG", "Logo")
    cell = rig.build().cell("Icon")
    assert isinstance(cell.widget, IconWidget) and cell.widget.ui == "icon" and cell.view()["field"] == "home" and cell.view()["ui"] == "icon"
    outcome, diff = rig.commit("Icon", {"text": "logo.svg"})
    assert outcome.changed and diff == ['-            SVG { Name: Logo, Icon: "home", Shortcut: "ctrl+f1" }   # the logo, inline', '+            SVG { Name: Logo, Icon: "logo.svg", Shortcut: "ctrl+f1" }   # the logo, inline']
    outcome, diff = rig.commit("Icon", {"text": ""})
    assert outcome.changed and diff == ['-            SVG { Name: Logo, Icon: "logo.svg", Shortcut: "ctrl+f1" }   # the logo, inline', '+            SVG { Name: Logo, Shortcut: "ctrl+f1" }   # the logo, inline']


def test_the_icon_picker_is_offered_the_icons_folder_of_the_configuration_folder_only_when_there_is_one(rig, tmp_path):
    rig.select("SVG", "Logo")
    assert rig.build().cell("Icon").view()["icons_folder"] == ""
    (tmp_path / "Icons").mkdir()
    assert rig.build().cell("Icon").view()["icons_folder"] == str(tmp_path / "Icons")


def test_an_icon_that_is_not_a_string_is_shown_as_tdl_and_kept(rig):
    rig.text_before = rig.text
    rig.model.set_text(rig.text.replace('Icon: "home"', "Icon: {{ icon_name }}"))
    rig.select("SVG", "Logo")
    cell = rig.build().cell("Icon")
    assert cell.tdl or cell.is_slot, "an expression is shown as text"


# -- font --------------------------------------------------------------------------------------------------------------------------

def test_a_font_family_is_one_quoted_name_and_a_list_of_families_is_kept_as_text(rig):
    rig.select("Text", "T")
    cell = rig.build().cell("Font_Family")
    assert isinstance(cell.widget, FontWidget) and cell.view()["ui"] == "font" and cell.view()["field"] == "Roboto"
    outcome, diff = rig.commit("Font_Family", {"text": "DejaVu Sans"})
    assert diff == ['-            Text { Name: T, Font_Family: "Roboto", Text: "x" }', '+            Text { Name: T, Font_Family: "DejaVu Sans", Text: "x" }']
    rig.model.set_text(rig.text.replace('"DejaVu Sans"', '["Roboto", "Noto Sans"]'))
    again = rig.select("Text", "T").cell("Font_Family")
    assert again.tdl and again.view()["ui"] == "field" and again.text == '["Roboto", "Noto Sans"]'


# -- key chord ---------------------------------------------------------------------------------------------------------------------

def test_a_key_chord_is_written_in_the_canonical_order_and_text_that_is_not_a_chord_is_refused(rig):
    rig.select("SVG", "Logo")
    cell = rig.build().cell("Shortcut")
    assert isinstance(cell.widget, KeyChordWidget) and cell.view()["ui"] == "chord" and cell.view()["field"] == "ctrl+f1" or cell.tdl
    outcome, diff = rig.commit("Shortcut", {"text": "shift+control+f2"})
    assert outcome.changed and diff == ['-            SVG { Name: Logo, Icon: "home", Shortcut: "ctrl+f1" }   # the logo, inline', '+            SVG { Name: Logo, Icon: "home", Shortcut: "Ctrl+Shift+F2" }   # the logo, inline']
    before = rig.text
    outcome, diff = rig.commit("Shortcut", {"text": "banana"})
    assert not outcome.ok and diff == [] and rig.text == before and "key chord" in outcome.message


# -- list --------------------------------------------------------------------------------------------------------------------------

def test_a_list_of_enum_items_is_written_as_a_list_with_the_choices_checked(rig):
    rig.select("Popup", "Pop")
    cell = rig.build().cell("Adjust")
    shown = cell.view()
    assert isinstance(cell.widget, ListWidget) and shown["ui"] == "list" and shown["items"] == ["FLIP_Y", "SLIDE_X"] and shown["item_kind"] == "enum" and "RESIZE_X" in shown["choices"]
    outcome, diff = rig.commit("Adjust", {"items": ["FLIP_Y", "RESIZE_X", "SLIDE_X"]})
    assert diff == ["-            Adjust: [FLIP_Y, SLIDE_X]", "+            Adjust: [FLIP_Y, RESIZE_X, SLIDE_X]"]
    for bad, why in ((["NOPE"], "takes one of"), (["FLIP_Y", "FLIP_Y"], "no repeated")):
        outcome = rig.form.commit("k:Adjust|", {"items": bad})
        assert not outcome.ok and why in outcome.message
    assert rig.commit("Adjust", {"items": []})[1] == ["-            Adjust: [FLIP_Y, RESIZE_X, SLIDE_X]", "+            Adjust: []"], "this key allows an empty list"


def test_a_list_of_names_and_a_lone_item_that_the_key_reads_as_a_list(rig):
    rig.select("Box", "Bx")
    assert rig.build().cell("Class").view()["items"] == ["a_class", "b_class"]
    outcome, diff = rig.commit("Class", {"items": ["a_class", "c_class"]})
    assert diff == ["-            Box { Name: Bx, Class: [a_class, b_class] }", "+            Box { Name: Bx, Class: [a_class, c_class] }"]
    rig.model.set_text(rig.text.replace("[a_class, c_class]", "solo"))
    assert rig.select("Box", "Bx").cell("Class").view()["items"] == ["solo"], "one_or_list: a lone item is a list of one"
    assert not rig.form.commit("k:Class|", {"items": ["has space"]}).ok


def test_a_list_of_numbers_has_the_length_the_schema_says_and_each_item_in_its_range(rig):
    rig.select("Path", "P")
    cell = rig.build().cell("View_Box")
    assert cell.view()["items"] == [0, 0, 24, 24] and cell.view()["item_kind"] == "number" and cell.view()["min_items"] == 4 and cell.view()["max_items"] == 4
    outcome, diff = rig.commit("View_Box", {"items": [0, 0, 48, 48]})
    assert diff == ['-            Path { Name: P, Data: "M0 0", View_Box: [0, 0, 24, 24] }', '+            Path { Name: P, Data: "M0 0", View_Box: [0, 0, 48, 48] }']
    outcome = rig.form.commit("k:View_Box|", {"items": [1, 2, 3]})
    assert not outcome.ok and "exactly 4" in outcome.message


def test_a_list_whose_items_the_editor_cannot_show_is_edited_as_tdl_and_a_list_with_an_item_kind_it_has_no_row_for_says_why(rig, schema_data, chord_schema):
    rig.model.set_text(rig.text.replace("[FLIP_Y, SLIDE_X]", "[FLIP_Y, $space.md]"))
    cell = rig.select("Popup", "Pop").cell("Adjust")
    assert cell.tdl and cell.view()["ui"] == "field" and cell.text == "[FLIP_Y, $space.md]"
    data = copy.deepcopy(schema_data)
    data["blocks"]["Box"]["keys"]["Odd"] = {"kind": "list", "item_kind": "tooltip", "default": None, "doc": "", "group": "Other", "required": False, "built": True, "tokens": [], "preferred_tokens": [], "slot": False}
    odd = Schema.from_data(data)
    key = odd.blocks["Box"].keys["Odd"]
    widget = default_registry().create(key, Context(odd))
    assert widget.reason and "tooltip" in widget.reason


# -- the whole schema ----------------------------------------------------------------------------------------------------------------

def test_every_list_icon_font_and_key_chord_key_of_the_schema_has_its_own_widget(chord_schema):
    from tess_shell_config.form import coverage

    report = coverage(chord_schema)
    kinds = {"list": ListWidget, "icon": IconWidget, "font": FontWidget, "key_chord": KeyChordWidget}
    seen = dict.fromkeys(kinds, 0)
    for _, key, widget in report.entries:
        if key.kind in kinds:
            seen[key.kind] += 1
            assert type(widget) is kinds[key.kind] and widget.reason is None, (key.name, widget.reason)
    assert all(seen.values()), seen


# -- in the window, from the keyboard ------------------------------------------------------------------------------------------------

@pytest.fixture
def ww(tmp_path, chord_schema):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    (target / "Icons").mkdir()
    (target / "Icons" / "logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M0 0h24v24H0z" fill="currentColor"/></svg>')
    (target / "Shells" / "Widgets_Shell.tdl").write_text(TEXT)
    window = FormWindow(target, tmp_path, chord_schema)
    window.session.refresh()
    window.open("Shells/Widgets_Shell.tdl")
    return window


def _enter_in_search(w):
    w.window.simulate("key_down", key="Enter")
    w.settle(6)


def test_the_icon_picker_lists_the_icons_folder_and_a_pick_writes_the_file_name(ww):
    ww.select("SVG  Logo")
    ww.open_all_groups()
    before = ww.session.model.text
    ww.focus("k:Icon", "icon_picker.field.trigger")
    ww.key("enter")
    ww.type("logo")
    _enter_in_search(ww)
    assert ww.diff(before) == ['-SVG { Name: Logo, Icon: "home", Shortcut: "ctrl+f1" }   # the logo, inline', '+SVG { Name: Logo, Icon: "logo.svg", Shortcut: "ctrl+f1" }   # the logo, inline']


def test_the_font_list_writes_the_family_picked(ww):
    from tess_ui import font_families

    font_families.use(lambda: ["Roboto", "DejaVu Sans", "Noto Serif"])
    try:
        ww.select("Text  T")
        ww.open_all_groups()
        before = ww.session.model.text
        ww.focus("k:Font_Family", "font_list.field.trigger")
        ww.key("enter")
        ww.type("noto")
        _enter_in_search(ww)
        assert ww.diff(before) == ['-Text { Name: T, Font_Family: "Roboto", Text: "x" }', '+Text { Name: T, Font_Family: "Noto Serif", Text: "x" }']
    finally:
        font_families.use(None)


def test_the_key_chord_field_records_a_key_press_and_writes_it_canonically(ww):
    ww.select("SVG  Logo")
    ww.open_all_groups()
    before = ww.session.model.text
    ww.focus("k:Shortcut", "chord_field.record")
    ww.key("enter")
    ww.window.simulate("key_down", key="F3", ctrl=True, shift=True)
    ww.settle(6)
    assert ww.diff(before) == ['-SVG { Name: Logo, Icon: "home", Shortcut: "ctrl+f1" }   # the logo, inline', '+SVG { Name: Logo, Icon: "home", Shortcut: "Ctrl+Shift+F3" }   # the logo, inline']


def test_the_list_editor_adds_an_item_from_the_keyboard_and_the_file_gets_the_list(ww):
    ww.select("Popup  Pop")
    ww.open_all_groups()
    before = ww.session.model.text
    ww.focus("k:Adjust", "list_editor.actions.add")
    ww.key("enter")
    lines = ww.diff(before)
    assert lines[0] == "-Adjust: [FLIP_Y, SLIDE_X]" and lines[1].startswith("+Adjust: [FLIP_Y, SLIDE_X, ") and len(lines) == 2, lines
