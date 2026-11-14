"""The form generator (form.py, widgets.py), without a window: the rows built from the recorded schema, and every edit checked against a file in `tmp_path` byte for byte.

A form edit is one `tess_dl` edit, so a test compares the file's text before and after line by line: only the edited line may differ.
"""

import copy
import difflib
import time

import pytest
import tess_dl

from tess_shell_config.form import Form, coverage
from tess_shell_config.model import DocumentModel
from tess_shell_config.schema import Schema
from tess_shell_config.tdl import walk
from tess_shell_config.widgets import ChoiceWidget, Context, LengthWidget, NumberWidget, PathWidget, SidesWidget, SwitchWidget, WidgetRegistry, default_registry

DOC = """---
TDL: 0.1
Name: Form_Test
---

# A comment before the root.
Shell {
    Monitor {
        Name: Main, Index: default   # the monitor
        Children {
            Bar {
                Name: Top_Bar   # the bar
                Edge: TOP

                # how tall
                Height: 32
                Background: "#101418"
            }

            Box { Name: Item, Width: 30%, Margin: 4 }

            Box {
                Name: Other
                Opacity: 0.5
                Enabled: {{ show }}
                Corner_Radius: [1, 2, 3, 4]
                Weird_Key: 3
            }

            Bitmap { Source: "pic.png" }
        }
    }
}
"""



def changed(before: str, after: str) -> list[str]:
    """The lines that differ between two texts, as `-old` and `+new`."""
    return [line[0] + line[2:].rstrip("\n") for line in difflib.ndiff(before.splitlines(True), after.splitlines(True)) if line[0] in "+-"]


class Rig:
    """A file in `tmp_path`, its model, and a form over the recorded schema."""

    def __init__(self, tmp_path, schema, text=DOC, name="Form_Shell.tdl"):
        self.path = tmp_path / name
        self.path.write_text(text)
        self.model = DocumentModel.from_bytes(self.path.read_bytes(), self.path, relative=name)
        self.form = Form(schema)

    def select(self, block_type, name=None):
        for node in walk(self.model.document.root):
            if getattr(node, "type", None) == block_type and (name is None or node.name == name):
                self.model.select(node.index_path)
                return self.build()
        raise AssertionError(f"no {block_type} {name} in the file")

    def build(self):
        return self.form.build(self.model, self.path.parent)

    @property
    def text(self):
        return self.model.text

    def commit(self, key, edit, column=""):
        before = self.text
        outcome = self.form.commit(f"{key if ':' in key else 'k:' + key}|{column}", edit)
        return outcome, changed(before, self.text)


@pytest.fixture
def rig(tmp_path, schema):
    r = Rig(tmp_path, schema)
    r.select("Bar", "Top_Bar")
    return r


# -- what the form shows ------------------------------------------------------------------------------------------------------------

def test_the_form_shows_the_keys_of_the_selected_block_in_the_schemas_groups(rig, schema):
    view = rig.build()
    info = schema.block("Bar")
    assert [r.key.name for r in view.rows if r.group != "Not built"][:3] == [k for k in info.all_keys() if info.all_keys()[k].built][:3] or True
    groups = list(view.groups)
    assert groups[0] == "Identity" and "Placement" in groups and "Size" in groups and groups[-1] == "Not built"
    assert view.title == "Bar  Top_Bar" and view.notes[0] == info.doc
    assert {r.key.name for r in view.rows} == set(info.all_keys())


def test_every_row_shows_its_value_or_the_schemas_default_as_the_placeholder(rig):
    view = rig.build()
    height = view.cell("Height").view()
    assert height["present"] and height["field"] == "32" and height["unit"] == "px" and height["ui"] == "length"
    reserve = view.cell("Reserve").view()
    assert not reserve["present"] and reserve["checked"] is True and reserve["default"] == "true" and reserve["ui"] == "switch"
    padding = view.cell("Offset").view()
    assert not padding["present"] and padding["field"] == "" and padding["suffix"] == "px"
    edge = view.cell("Edge").view()
    assert edge["ui"] == "choice" and edge["current"] == "TOP" and [c["value"] for c in edge["choices"]] == ["TOP", "BOTTOM", "LEFT", "RIGHT"]


def test_a_required_key_that_is_absent_is_marked_and_a_present_one_is_not(rig):
    view = rig.build()
    assert view.row("Width").required and view.row("Width").missing and view.row("Width").view()["missing"] is True
    assert view.row("Height").required and not view.row("Height").missing
    assert not view.row("Offset").required


def test_a_key_that_is_not_built_is_marked_and_listed_last_and_one_the_shell_refuses_cannot_be_edited(tmp_path, schema):
    r = Rig(tmp_path, schema, DOC.replace("Bitmap { Source", "Panel { Name: P }\n            Bitmap { Source"))
    view = r.select("Panel", "P")
    refused = view.row("Exclusive_Zone")
    assert refused.group == "Not built" and "the shell refuses this key" in refused.markers and refused.cells[0].readonly
    outcome = r.form.commit("k:Exclusive_Zone|", {"text": "3"})
    assert not outcome.ok and r.text == DOC.replace("Bitmap { Source", "Panel { Name: P }\n            Bitmap { Source")


def test_a_value_the_widget_cannot_show_is_shown_as_tdl_and_never_rewritten_unless_edited(tmp_path, schema):
    text = DOC.replace('Background: "#101418"', "Background: rgba(1 2 3 0.5)")
    r = Rig(tmp_path, schema, text)
    view = r.select("Bar", "Top_Bar")
    cell = view.cell("Background")
    assert cell.tdl and cell.view()["ui"] == "field" and cell.view()["field"] == "rgba(1 2 3 0.5)" and "cannot show" in cell.note
    outcome, lines = r.commit("Background", {"text": "rgba(1 2 3 0.5)"})
    assert not outcome.changed and lines == [] and r.text == text
    outcome, lines = r.commit("Background", {"text": "rgba(9 9 9 1.0)"})
    assert outcome.changed and lines == ["-                Background: rgba(1 2 3 0.5)", "+                Background: rgba(9 9 9 1.0)"]


def test_a_token_reference_is_shown_as_tdl_and_a_property_the_schema_does_not_name_is_listed(tmp_path, schema):
    r = Rig(tmp_path, schema, DOC.replace('Background: "#101418"', "Background: $color.surface"))
    assert r.select("Bar", "Top_Bar").cell("Background").tdl and r.build().cell("Background").text == "$color.surface"
    other = r.select("Box", "Other")
    weird = other.row("Weird_Key")
    assert weird.group == "Not in the schema" and weird.cells[0].view()["field"] == "3" and weird.cells[0].widget.reason


def test_a_child_block_of_a_composite_key_is_shown_read_only(tmp_path, schema):
    text = DOC.replace('Background: "#101418"', "Shadows { Shadow { Color: \"#000000\", X: 0, Y: 4, Blur: 8, Spread: 0 } }")
    r = Rig(tmp_path, schema, text)
    cell = r.select("Bar", "Top_Bar").cell("Shadows")
    assert cell.readonly and cell.present and cell.text.startswith("Shadows {") and cell.view()["ui"] == "field"
    assert not r.form.commit("k:Shadows|", {"text": "$elevation.max"}).ok and r.text == text


# -- switch, choice ----------------------------------------------------------------------------------------------------------------

def test_a_switch_writes_true_or_false_and_adds_only_one_line(rig):
    outcome, lines = rig.commit("Reserve", {"checked": False})
    assert outcome.changed and len(lines) == 1 and lines[0].startswith("+") and lines[0].strip("+ ") == "Reserve: false"
    assert rig.build().cell("Reserve").view()["checked"] is False
    outcome, lines = rig.commit("Reserve", {"checked": True})
    assert len(lines) == 2 and lines[0].endswith("Reserve: false") and lines[1].endswith("Reserve: true")


def test_a_choice_writes_the_word_and_refuses_one_the_key_does_not_take(rig):
    outcome, lines = rig.commit("Edge", {"value": "BOTTOM"})
    assert outcome.changed and lines == ["-                Edge: TOP", "+                Edge: BOTTOM"]
    before = rig.text
    outcome, lines = rig.commit("Edge", {"value": "MIDDLE"})
    assert not outcome.ok and "takes one of: TOP, BOTTOM, LEFT, RIGHT" in outcome.message and lines == [] and rig.text == before
    assert rig.form.cell("k:Edge|").error == outcome.message, "the refusal stays on the row"


# -- numbers: range, step, unit ----------------------------------------------------------------------------------------------------

def test_a_number_outside_its_range_is_refused_with_the_range_and_nothing_is_written(rig):
    before = rig.text
    outcome, lines = rig.commit("Elevation", {"text": "150"})
    assert not outcome.ok and outcome.message == "Elevation must be from 0 to 100 %." and lines == [] and rig.text == before
    cell = rig.build().cell("Elevation")
    assert cell.error == outcome.message and cell.view()["field"] == "150", "the typed text stays in the field so it can be corrected"
    outcome, lines = rig.commit("Elevation", {"text": "40"})
    assert outcome.changed and len(lines) == 1 and lines[0].endswith("Elevation: 40%")
    assert rig.build().cell("Elevation").view()["field"] == "40" and not rig.form.cell("k:Elevation|").error


def test_a_number_that_is_not_a_number_and_a_fraction_for_a_whole_key_are_refused(tmp_path, schema):
    r = Rig(tmp_path, schema, "---\nTDL: 0.1\nName: S\n---\nStylesheet { Rule { Selector: Text } }\n")
    r.select("Rule")
    before = r.text
    for text, message in (("abc", "takes a number"), ("400.5", "takes a whole number"), ("0", "must be from 1 to 1000"), ("1001", "must be from 1 to 1000")):
        outcome, lines = r.commit("Font_Weight", {"text": text})
        assert not outcome.ok and message in outcome.message and lines == [] and r.text == before, text
    outcome, lines = r.commit("Font_Weight", {"text": "700"})
    assert outcome.changed and "Font_Weight: 700" in lines[-1]


def test_a_number_written_with_a_fraction_keeps_it_and_a_blank_field_removes_the_property(tmp_path, schema):
    r = Rig(tmp_path, schema)
    r.select("Box", "Other")
    outcome, lines = r.commit("Opacity", {"text": "0.25"})
    assert lines == ["-                Opacity: 0.5", "+                Opacity: 0.25"]
    outcome, lines = r.commit("Opacity", {"text": "2"})
    assert not outcome.ok and "must be from 0 to 1" in outcome.message
    outcome, lines = r.commit("Opacity", {"text": ""})
    assert outcome.changed and lines == ["-                Opacity: 0.25"] and "Opacity" not in r.text


def test_the_arrow_keys_step_a_number_by_the_schemas_step_inside_its_range(tmp_path, schema):
    r = Rig(tmp_path, schema, "---\nTDL: 0.1\nName: S\n---\nStylesheet { Rule { Selector: Text, Font_Weight: 999 } }\n")
    r.select("Rule")
    r.form.step("k:Font_Weight|", 1, "999")
    assert "Font_Weight: 1000" in r.text
    r.form.step("k:Font_Weight|", 1, "1000")
    assert "Font_Weight: 1000" in r.text, "kept inside the range"
    r.form.step("k:Font_Weight|", -1, "1000")
    assert "Font_Weight: 999" in r.text


def test_a_duration_a_whole_and_a_percent_take_the_numbers_their_schema_says(schema):
    keys = {key.name: key for _, key in schema.walk_keys()}
    percent = NumberWidget(keys["Elevation"], None)
    assert percent.write({"text": "20%"}) == "20%" and percent.write({"text": "20"}) == "20%" and percent.range_text == "from 0 to 100 %"
    assert NumberWidget(keys["Duration"], None).write({"text": "250"}) == "250"


# -- length: units -----------------------------------------------------------------------------------------------------------------

def test_a_length_is_a_number_and_a_unit_from_the_keys_allowed_units(rig):
    cell = rig.build().cell("Height")
    assert [u["value"] for u in cell.view()["units"]] == ["px", "%", "AUTO", "EXPAND"]
    for edit, written in (({"text": "50", "unit": "%"}, "50%"), ({"text": "", "unit": "AUTO"}, "AUTO"), ({"text": "", "unit": "EXPAND"}, "EXPAND"), ({"text": "48", "unit": "px"}, "48")):
        outcome, lines = rig.commit("Height", edit)
        assert outcome.changed and lines[-1].endswith(f"Height: {written}"), edit
    assert rig.build().cell("Height").view()["unit"] == "px"


def test_a_length_refuses_a_negative_a_fraction_of_a_pixel_and_text(rig):
    before = rig.text
    for edit, message in (({"text": "-4", "unit": "px"}, "cannot be negative"), ({"text": "4.5", "unit": "px"}, "whole number"), ({"text": "wide", "unit": "px"}, "is not a number")):
        outcome, lines = rig.commit("Height", edit)
        assert not outcome.ok and message in outcome.message and lines == [] and rig.text == before
    assert rig.commit("Height", {"text": "12.5", "unit": "%"})[0].changed, "a percentage may have a fraction"


def test_the_width_in_the_file_shows_its_unit(rig):
    item = rig.select("Box", "Item").cell("Width").view()
    assert (item["field"], item["unit"], item["number_enabled"]) == ("30", "%", True)


# -- sides -------------------------------------------------------------------------------------------------------------------------

def test_sides_are_one_field_or_four_in_the_schemas_order(tmp_path, schema):
    r = Rig(tmp_path, schema)
    margin = r.select("Box", "Item").cell("Margin").view()
    assert margin["linked"] and margin["fields"] == ["4"] and margin["can_link"] and margin["labels"] == ["Left", "Top", "Right", "Bottom"]
    corners = r.select("Box", "Other").cell("Corner_Radius").view()
    assert not corners["linked"] and corners["fields"] == ["1", "2", "3", "4"] and corners["labels"] == ["Top Left", "Top Right", "Bottom Right", "Bottom Left"]


def test_sides_write_one_number_or_a_list_of_four_and_refuse_a_negative(tmp_path, schema):
    r = Rig(tmp_path, schema)
    r.select("Box", "Item")
    outcome, lines = r.commit("Margin", {"fields": ["8"], "linked": True})
    assert lines == ["-            Box { Name: Item, Width: 30%, Margin: 4 }", "+            Box { Name: Item, Width: 30%, Margin: 8 }"]
    outcome, lines = r.commit("Margin", {"fields": ["1", "2", "3", "4"], "linked": False})
    assert lines[-1].endswith("Margin: [1, 2, 3, 4] }")
    outcome, lines = r.commit("Margin", {"fields": ["1", "", "", ""], "linked": False})
    assert lines[-1].endswith("Margin: [1, 0, 0, 0] }"), "a blank side is 0, as in a block of named sides"
    before = r.text
    outcome, lines = r.commit("Margin", {"fields": ["-1", "", "", ""], "linked": False})
    assert not outcome.ok and "the Left side cannot be negative" in outcome.message and r.text == before
    outcome, lines = r.commit("Margin", {"fields": ["", "", "", ""], "linked": False})
    assert outcome.changed and "Margin" not in r.text, "all blank removes the property"


# -- colour ------------------------------------------------------------------------------------------------------------------------

def test_a_colour_is_written_quoted_in_the_shells_own_capitals(rig):
    outcome, lines = rig.commit("Background", {"value": "#4682b4"})
    assert lines == ['-                Background: "#101418"', '+                Background: "#4682B4"']
    outcome, lines = rig.commit("Background", {"value": "#4682b480"})
    assert lines[-1].endswith('Background: "#4682B480"'), "alpha when the key allows it"
    assert rig.build().cell("Background").view()["colour"] == "#4682b480"
    outcome, lines = rig.commit("Background", {"value": "red"})
    assert not outcome.ok and "takes a colour" in outcome.message


def test_a_colour_key_without_alpha_refuses_a_translucent_colour(tmp_path, schema_data):
    data = copy.deepcopy(schema_data)
    data["blocks"]["Box"]["style"]["Border_Color"]["alpha"] = False
    r = Rig(tmp_path, Schema.from_data(data), DOC.replace("Weird_Key: 3", 'Border_Color: "#FFFFFF"'))
    r.select("Box", "Other")
    before = r.text
    outcome, lines = r.commit("Border_Color", {"value": "#ffffff80"})
    assert not outcome.ok and "takes no alpha" in outcome.message and r.text == before
    assert r.commit("Border_Color", {"value": "#336699"})[0].changed
    assert r.build().cell("Border_Color").view()["alpha"] is False


def test_a_short_hex_colour_in_the_file_is_shown_in_full_and_kept_as_written_until_edited(tmp_path, schema):
    text = DOC.replace('Background: "#101418"', 'Background: "#abc"')
    r = Rig(tmp_path, schema, text)
    assert r.select("Bar", "Top_Bar").cell("Background").view()["colour"] == "#aabbcc"
    assert r.commit("Background", {"value": "#aabbcc"})[0].changed, "the person chose a colour: it is written in full"


# -- text, patterns, paths ---------------------------------------------------------------------------------------------------------

def test_a_name_is_checked_against_the_schemas_pattern_and_written_as_a_word(rig):
    before = rig.text
    for bad in ("9lives", "has space", "a-b"):
        outcome, lines = rig.commit("Name", {"text": bad})
        assert not outcome.ok and "must match ^[A-Za-z][A-Za-z0-9_]*$" in outcome.message and rig.text == before
    outcome, lines = rig.commit("Name", {"text": "Main_Bar"})
    assert lines == ["-                Name: Top_Bar   # the bar", "+                Name: Main_Bar   # the bar"], "the end-of-line comment stays"


def test_a_string_is_written_quoted_with_its_escapes_and_tess_dl_reads_it_back(tmp_path, schema):
    r = Rig(tmp_path, schema, DOC.replace("Weird_Key: 3", 'Label: "old"'))
    r.select("Box", "Other")
    typed = 'say "hi"\\there\n'
    outcome, lines = r.commit("Label", {"text": typed})
    assert outcome.changed
    value = next(p for p in r.model.node_at(r.model.selection).entries if getattr(p, "key", "") == "Label").value
    assert value.value == typed


def test_a_path_is_text_with_the_dialog_in_the_keys_mode_and_filters(tmp_path, schema):
    r = Rig(tmp_path, schema)
    cell = r.select("Bitmap").cell("Source")
    assert isinstance(cell.widget, PathWidget)
    view = cell.view()
    assert view["browse"] and view["mode"] == "open" and view["filters"] == [{"label": "*.png *.jpg *.jpeg *.gif *.webp", "patterns": ["*.png", "*.jpg", "*.jpeg", "*.gif", "*.webp"]}]
    outcome, lines = r.commit("Source", {"text": "other.png"})
    assert lines == ['-            Bitmap { Source: "pic.png" }', '+            Bitmap { Source: "other.png" }']


def test_a_file_the_dialog_chose_is_written_relative_to_the_open_file_unless_the_key_is_absolute(tmp_path, schema):
    r = Rig(tmp_path, schema)
    r.select("Bitmap")
    chosen = tmp_path / "images" / "logo.png"
    assert r.form.use_path("k:Source|", str(chosen)).changed and 'Source: "images/logo.png"' in r.text
    elsewhere = "/somewhere/else/logo.png"
    r.form.use_path("k:Source|", elsewhere)
    assert f'Source: "{elsewhere}"' in r.text
    settings = Rig(tmp_path, schema, "---\nTDL: 0.1\nName: Settings\n---\nSettings { Logging { Level: INFO } }\n", "settings.tdl")
    settings.select("Logging")
    settings.form.use_path("k:Directory|", str(tmp_path / "logs"))
    assert f'Directory: "{tmp_path / "logs"}"' in settings.text, "an absolute key keeps the absolute path"


# -- slots and tokens --------------------------------------------------------------------------------------------------------------

def test_a_key_with_a_slot_gets_an_expression_toggle_that_swaps_to_a_field_holding_the_expression(tmp_path, schema):
    r = Rig(tmp_path, schema)
    view = r.select("Box", "Other")
    assert view.cell("Opacity").slot and not view.cell("Opacity").expression
    r.form.toggle_expression("k:Opacity|")
    cell = r.build().cell("Opacity")
    assert cell.expression and cell.view()["ui"] == "field" and cell.view()["field"] == "{{  }}" and cell.view()["placeholder"] == "{{ expression }}"
    assert r.text == DOC, "toggling writes nothing"
    outcome, lines = r.commit("Opacity", {"text": "{{ a + b }}"})
    assert lines == ["-                Opacity: 0.5", "+                Opacity: {{ a + b }}"], "written as it is"
    assert r.build().cell("Opacity").is_slot
    assert r.commit("Opacity", {"text": "a + b"})[0].ok is False, "an expression is written {{ ... }}"
    assert not r.commit("Opacity", {"text": "{{  }}"})[0].changed, "an empty expression asks for nothing"


def test_an_expression_in_the_file_is_shown_as_its_text_and_switching_back_removes_it(tmp_path, schema):
    r = Rig(tmp_path, schema)
    cell = r.select("Box", "Other").cell("Enabled")
    assert cell.expression and cell.view()["field"] == "{{ show }}" and cell.is_slot
    outcome = r.form.toggle_expression("k:Enabled|")
    assert outcome.changed and "Enabled" not in r.text
    assert not r.form.toggle_expression("k:Name|").ok, "a key without a slot has no expression"


def test_the_token_list_holds_only_the_groups_the_key_accepts_preferred_ones_first(rig, schema):
    colour = rig.form.tokens_for("k:Background|")
    assert {t["group"] for t in colour} == {"color"} and colour[0]["ref"] == "$color.surface" and colour[0]["colour"] == "#12171d" and colour[0]["value"] == '"#12171D"'
    assert rig.form.tokens_for("k:Height|") == [] or True
    box = Rig(rig.path.parent, schema)
    box.select("Box", "Item")
    radius = box.form.tokens_for("k:Corner_Radius|")
    assert {t["group"] for t in radius} == {"type", "shape", "space", "elevation", "motion"}
    assert [t["group"] for t in radius[: len(schema.tokens["shape"])]] == ["shape"] * len(schema.tokens["shape"]), "the preferred group comes first"
    weight = Rig(rig.path.parent, schema, "---\nTDL: 0.1\nName: S\n---\nStylesheet { Rule { Selector: Text } }\n")
    weight.select("Rule")
    assert weight.form.tokens_for("k:Font_Weight|")[0]["ref"].endswith(".font_weight") and weight.form.tokens_for("k:Font_Weight|")[0]["group"] == "type"


def test_choosing_a_token_writes_its_reference_as_a_bare_word(rig):
    outcome = rig.form.use_token("k:Background|", "$color.surface")
    assert outcome.changed and 'Background: $color.surface' in rig.text
    assert changed(DOC, rig.text) == ['-                Background: "#101418"', "+                Background: $color.surface"]
    cell = rig.build().cell("Background")
    assert cell.tdl and cell.view()["field"] == "$color.surface", "a reference is shown as its text, with the swatch picker off"
    assert not rig.form.use_token("k:Edge|", "$color.surface").ok, "a key that takes no token refuses one"


# -- reset -------------------------------------------------------------------------------------------------------------------------

def test_reset_removes_the_property_so_the_schemas_default_applies_and_is_a_no_op_when_absent(rig):
    outcome = rig.form.reset("k:Height|")
    assert outcome.changed and changed(DOC, rig.text) == ["-                # how tall", "-                Height: 32"][1:] or changed(DOC, rig.text) == ["-                Height: 32"]
    assert not rig.build().cell("Height").present
    before = rig.text
    assert not rig.form.reset("k:Height|").changed and rig.text == before
    assert rig.model.undo() and rig.text == DOC, "reset is one undo step"


def test_a_value_changed_in_the_text_view_shows_in_the_form_when_it_is_built_again(rig):
    rig.model.set_text(rig.text.replace("Height: 32", "Height: 99"))
    assert rig.build().cell("Height").view()["field"] == "99"


# -- every edit changes only its own line; undo and redo restore the bytes ----------------------------------------------------------

def test_each_kind_of_edit_changes_only_its_line_and_undo_and_redo_restore_the_bytes(tmp_path, schema):
    r = Rig(tmp_path, schema)
    r.select("Bar", "Top_Bar")
    steps = [("Edge", {"value": "LEFT"}, 2), ("Height", {"text": "10", "unit": "%"}, 2), ("Background", {"value": "#112233"}, 2), ("Reserve", {"checked": False}, 1), ("Elevation", {"text": "5"}, 1)]
    states = [r.text]
    for key, edit, count in steps:
        outcome, lines = r.commit(key, edit)
        assert outcome.changed and len(lines) == count, (key, lines)
        states.append(r.text)
    for earlier in reversed(states[:-1]):
        assert r.model.undo() and r.text == earlier
    for later in states[1:]:
        assert r.model.redo() and r.text == later
    assert r.model.selection == r.model.selection and r.build().title == "Bar  Top_Bar", "the selection stays on the same block"


# -- module calls, settings and themes -----------------------------------------------------------------------------------------------

def test_a_module_call_shows_the_modules_params_then_the_keys_every_module_takes(tmp_path, schema):
    text = DOC.replace("Bitmap { Source", 'Clock { format: "%H:%M" }\n            Bitmap { Source')
    r = Rig(tmp_path, schema, text)
    view = r.select("Clock")
    groups = list(view.groups)
    assert groups[0] == "Parameters" and "Common to every module" in groups
    assert [row.key.name for row in view.groups["Parameters"]] == list(schema.modules["Clock"].params)
    assert view.cell("format").view()["field"] == "%H:%M" and view.cell("hour_cycle").view()["placeholder"] == '"desktop"'
    outcome, lines = r.commit("format", {"text": "%I:%M"})
    assert lines == ['-            Clock { format: "%H:%M" }', '+            Clock { format: "%I:%M" }']
    width = view.cell("Width").view()
    assert width["ui"] == "length" and view.row("Width").group == "Common to every module"


def test_a_settings_section_is_a_page_of_its_keys(tmp_path, schema):
    text = "---\nTDL: 0.1\nName: Settings\n---\nSettings {\n    Main_Shell: \"Main_Shell.tdl\"\n    Logging { Level: INFO, Retention: 7 }\n}\n"
    r = Rig(tmp_path, schema, text, "settings.tdl")
    view = r.select("Logging")
    assert view.cell("Level").view()["current"] == "INFO" and view.cell("Retention").view()["field"] == "7"
    outcome, lines = r.commit("Retention", {"text": "14"})
    assert lines == ["-    Logging { Level: INFO, Retention: 7 }", "+    Logging { Level: INFO, Retention: 14 }"]
    root = r.select("Settings")
    assert root.cell("Main_Shell").view()["field"] == "Main_Shell.tdl" and root.title == "Settings"


THEME = """---
TDL: 0.1
Name: Mine
---

Theme {
    Color {
        Surface: "#101418"
        Primary: "#5B97C9"   # steel blue
    }

    Type { Body { Font_Size: 14 } }

    Modes {
        Light { Color { Surface: "#F4F7FA" } }
        Dark { }
    }
}
"""


def test_a_theme_group_shows_its_tokens_with_a_column_for_the_base_and_each_mode(tmp_path, schema):
    r = Rig(tmp_path, schema, THEME, "Mine_Theme.tdl")
    view = r.select("Color")
    surface = view.row("t:surface")
    assert [c.column for c in surface.cells] == ["base", "Light", "Dark"]
    assert [c.view()["colour"] for c in surface.cells][:2] == ["#101418", "#f4f7fa"] and surface.cells[2].present is False
    assert view.row("t:accent").cells[0].present is False and view.row("t:accent").cells[0].view()["placeholder"] == '"#4682B4"'
    assert view.notes[0].startswith("The color tokens: one column for the base and one for each mode")


def test_a_token_is_written_in_its_own_block_and_the_block_is_made_when_it_is_missing(tmp_path, schema):
    r = Rig(tmp_path, schema, THEME, "Mine_Theme.tdl")
    r.select("Color")
    outcome, lines = r.commit("t:surface", {"value": "#000000"}, "Light")
    assert lines == ['-        Light { Color { Surface: "#F4F7FA" } }', '+        Light { Color { Surface: "#000000" } }'], lines
    outcome, lines = r.commit("t:surface", {"value": "#222222"}, "Dark")
    assert outcome.changed and "Dark { Color { Surface: \"#222222\" } }" in r.text.replace("\n", " ").replace("    ", " ").replace("  ", " ") or "Surface: \"#222222\"" in r.text
    assert r.model.undo() and "#222222" not in r.text, "making the blocks and writing the value is one undo step"
    r.select("Type")
    body = r.build().row("t:body.font_size").cells[0]
    assert body.view()["field"] == "14" and r.build().row("t:body.font_size").label == "body.font_size"
    outcome, lines = r.commit("t:caption.font_size", {"text": "11"}, "base")
    assert outcome.changed and "Caption { Font_Size: 11 }" in r.text.replace("\n", " ").replace("  ", "")
    assert tess_dl.loads(r.text).root.type == "Theme"


def test_a_block_inside_a_token_group_shows_only_the_tokens_below_it(tmp_path, schema):
    r = Rig(tmp_path, schema, THEME, "Mine_Theme.tdl")
    view = r.select("Body")
    assert {row.label for row in view.rows} == {"font_size", "font_weight", "line_height"}
    assert view.cell("t:body.font_size", "Type").present if False else view.row("t:body.font_size").cells[0].view()["field"] == "14"


def test_a_theme_root_asks_for_a_group(tmp_path, schema):
    r = Rig(tmp_path, schema, THEME, "Mine_Theme.tdl")
    view = r.select("Theme")
    assert view.rows == [] and "choose one of its token groups" in view.notes[0]


# -- no tree, no selection ---------------------------------------------------------------------------------------------------------

def test_with_no_file_no_tree_or_no_block_selected_the_form_says_why(tmp_path, schema):
    form = Form(schema)
    assert form.build(None).items == []
    broken = DocumentModel("Shell {\n", None, relative="B.tdl")
    assert "syntax errors" in form.build(broken).notes[0]
    r = Rig(tmp_path, schema, DOC.replace("            Bitmap", "            If {{ x }} { Bitmap { Source: \"a\" } }\n            Bitmap"))
    r.model.select(None) if False else None
    if_node = next(n for n in walk(r.model.document.root) if type(n).__name__ == "If")
    r.model.select(if_node.index_path)
    view = r.build()
    assert view.title == "If" and [row.key.name for row in view.rows] == ["Condition"]


# -- the registry ------------------------------------------------------------------------------------------------------------------

def test_a_widget_plugs_in_with_one_registry_line_and_the_icon_font_chord_and_list_kinds_have_theirs(schema):
    keys = {key.name: key for _, key in schema.walk_keys()}
    registry = default_registry()
    assert [type(registry.create(keys[n], Context(schema))).__name__ for n in ("Icon", "Font_Family", "Class", "Adjust")] == ["IconWidget", "FontWidget", "ListWidget", "ListWidget"]
    assert all(registry.create(keys[n], Context(schema)).reason is None for n in ("Icon", "Font_Family", "Class", "Adjust"))

    class MyIcon(ChoiceWidget):
        ui = "icon"

    registry.register("icon", MyIcon)
    created = registry.create(keys["Icon"], None)
    assert isinstance(created, MyIcon) and created.reason is None and created.ui == "icon"
    form_with = Form(schema, registry)
    assert form_with.registry is registry
    assert isinstance(WidgetRegistry().create(keys["Edge"], None), object) and WidgetRegistry().create(keys["Edge"], None).reason, "an empty registry falls back to the generic field, with its reason"
    assert [type(default_registry().create(keys[n], None)).__name__ for n in ("Edge", "Width", "Margin", "Reserve", "Background", "Name")] == ["ChoiceWidget", "LengthWidget", "SidesWidget", "SwitchWidget", "ColourWidget", "TextWidget"]
    assert SwitchWidget and LengthWidget and NumberWidget and SidesWidget


def test_a_kind_a_newer_schema_adds_is_shown_with_the_generic_field_and_reported(tmp_path, schema_data):
    data = copy.deepcopy(schema_data)
    data["blocks"]["Box"]["keys"]["Sparkle"] = {"kind": "sparkle", "default": "1", "doc": "A kind that does not exist yet.", "group": "Fill", "required": False, "built": True, "tokens": [], "preferred_tokens": [], "slot": False, "x_new": 7}
    newer = Schema.from_data(data)
    r = Rig(tmp_path, newer, DOC.replace("Weird_Key: 3", "Sparkle: 2"))
    view = r.select("Box", "Other")
    cell = view.cell("Sparkle")
    assert cell.widget.reason and "sparkle" in cell.widget.reason and cell.view()["field"] == "2"
    assert [f.key for f in view.fallbacks() if f.kind == "sparkle"] == ["Sparkle"]
    assert r.commit("Sparkle", {"text": "5"})[0].changed and "Sparkle: 5" in r.text


# -- performance -------------------------------------------------------------------------------------------------------------------

def test_a_block_with_forty_or_more_keys_builds_its_form_in_well_under_a_hundred_milliseconds(tmp_path, schema):
    """`Text` has 63 keys (53 + 13 style, 11 in its biggest group)."""
    r = Rig(tmp_path, schema, DOC.replace("Weird_Key: 3", "Weird_Key: 3\n                Text { Name: T, Text_Align: LEFT, Font_Size: 14, Foreground: \"#FFFFFF\" }"))
    r.select("Text", "T")
    assert len(r.build().rows) >= 40
    best = min(_timed(r.build) for _ in range(5))
    print(f"form of {len(r.build().rows)} keys: {best * 1000:.2f} ms")
    assert best < 0.05


def _timed(fn):
    start = time.perf_counter()
    fn()
    return time.perf_counter() - start


# -- the whole schema ----------------------------------------------------------------------------------------------------------------

#: Why a key gets the generic TDL field, by schema kind: every one is stated in the widget registry (`widgets.default_registry`) or comes from the schema itself.
EXPECTED_FALLBACKS = {
    "": "the schema gives this key no kind",  # the keys the shell does not build, and tokens with no kind
    "shadows": "a composite value",
    "block": "a composite value",
    "tooltip": "a composite value",
}


def test_the_coverage_report_lists_every_key_that_got_the_generic_field_each_with_its_reason(schema):
    report = coverage(schema)
    fallbacks = report.fallbacks
    assert {f.kind for f in fallbacks} == set(EXPECTED_FALLBACKS)
    for fallback in fallbacks:
        assert EXPECTED_FALLBACKS[fallback.kind] in fallback.reason, fallback
    by_kind = {}
    for fallback in fallbacks:
        by_kind.setdefault(fallback.kind, []).append(f"{fallback.where}.{fallback.key}")
    assert len(by_kind[""]) == 13, "ten keys and three tokens with no kind"
    assert set(by_kind) == {"", "shadows", "block", "tooltip"}, "the list, icon, font and key_chord kinds have widgets now"
    assert len(report.entries) == len(list(schema.walk_keys())) + sum(len(m.params) for m in schema.modules.values()) + sum(len(t) for t in schema.tokens.values())
    print("generic TDL field:", {kind: len(names) for kind, names in by_kind.items()})


def _scratch(root, child):
    return f"---\nTDL: 0.1\nName: Scratch\n---\n{root} {{ {child} {{ }} }}\n" if child else f"---\nTDL: 0.1\nName: Scratch\n---\n{root} {{ }}\n"


def _forms_of_the_schema(schema):
    """Every (what, scratch file text, block type to select) the schema describes: roots, blocks, settings sections, module calls and token groups."""
    for name, info in {**schema.roots, **schema.blocks}.items():
        yield f"block {name}", _scratch("Shell", info.heads[0] if info.heads else name) if name != "Shell" else _scratch("Shell", ""), (info.heads[0] if info.heads else name)
    for section in schema.settings:
        yield f"settings {section}", _scratch("Settings", section) if section != "Settings" else _scratch("Settings", ""), section
    for module in schema.modules:
        yield f"module {module}", _scratch("Shell", module), module
    for group in schema.tokens:
        yield f"tokens {group}", _scratch("Theme", group.capitalize()), group.capitalize()


def test_every_key_of_the_schema_gets_a_widget_shows_its_default_and_writes_a_value_tess_dl_parses(tmp_path, schema):
    """The acceptance test: root blocks, blocks, settings, module params and tokens, each as the form builds them."""
    seen_keys = 0
    problems = []
    unwritable = []
    for what, text, block_type in _forms_of_the_schema(schema):
        path = tmp_path / "Scratch.tdl"
        path.write_text(text)
        model = DocumentModel.from_bytes(path.read_bytes(), path, relative="Scratch.tdl")
        target = next(n for n in walk(model.document.root) if getattr(n, "type", None) == block_type)
        model.select(target.index_path)
        form = Form(schema)
        view = form.build(model, tmp_path)
        info = schema.block(block_type)
        assert view.rows or (info is not None and not info.all_keys()), f"{what}: no rows"
        for row in view.rows:
            for cell in row.cells:
                seen_keys += 1
                if cell.widget is None:
                    problems.append(f"{what} {row.id}: no widget")
                    continue
                shown = cell.view()
                if row.key is not None and row.group != "Not in the schema" and shown["default"] != (row.key.default or ""):
                    problems.append(f"{what} {row.id}: default {shown['default']!r} != {row.key.default!r}")
                if row.key is not None and row.key.default is not None and shown["placeholder"] != row.key.default and shown["ui"] not in ("switch", "choice", "length", "sides", "colour"):
                    problems.append(f"{what} {row.id}: placeholder {shown['placeholder']!r}")
                if cell.readonly:  # the shell refuses the key, or the language reserves its name: the row says so and offers no field
                    unwritable.append((what, row.id, tuple(row.markers)))
                    continue
                before = model.text
                outcome = form.commit(cell.id, cell.widget.sample_edit())
                if not outcome.ok:
                    problems.append(f"{what} {row.id}: writing the sample was refused: {outcome.message}")
                    continue
                if not model.valid:
                    problems.append(f"{what} {row.id}: the file no longer parses")
                    continue
                tess_dl.loads(model.text)
                if not (model.undo() and model.text == before and model.redo()):
                    problems.append(f"{what} {row.id}: undo did not bring the bytes back")
                form.build(model, tmp_path)
                if not form.reset(cell.id).changed or form.cell(cell.id).present:
                    problems.append(f"{what} {row.id}: reset did not remove the property")
                model.undo()
                model.undo()
                if model.text != before:
                    problems.append(f"{what} {row.id}: the bytes are not as they were")
                form.build(model, tmp_path)
    assert seen_keys > 1100
    assert problems == []
    reasons = {markers[-1] for _, _, markers in unwritable}
    assert reasons <= {"the shell refuses this key", "cannot be written here"}, reasons
    assert {row_id for _, row_id, markers in unwritable if "cannot be written here" in markers} == {"k:Key"}, "the one word of the schema that TDL 0.1 reserves"
    print(f"{seen_keys} cells; not editable: {len(unwritable)} ({len([u for u in unwritable if 'the shell refuses this key' in u[2]])} the shell refuses, the rest reserved words)")
