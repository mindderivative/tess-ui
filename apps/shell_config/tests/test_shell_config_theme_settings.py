"""Theme, settings and popup pages: the Add menu of a theme (token groups, Modes, a mode column), of settings.tdl (its sections), the token columns with a swatch for each mode, the default popups' values."""

import difflib
import shutil

import pytest
from test_shell_config_form_window import FormWindow
from test_shell_config_window import CONFIG, _rows

from tess_shell_config.blocks import MODES, children_of, mode_names
from tess_shell_config.form import Form
from tess_shell_config.model import DocumentModel

THEME = """---
TDL: 0.1
Name: Mine
---

Theme {
    Color {
        Surface: "#101418"
        Primary: "#5B97C9"   # steel blue
    }

    Modes {
        Light {
            Color { Surface: "#F4F7FA" }
        }
    }
}
"""


@pytest.fixture
def folder(tmp_path):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    (target / "Themes" / "Mine_Theme.tdl").write_text(THEME)
    return target


@pytest.fixture
def w(folder, tmp_path, schema):
    window = FormWindow(folder, tmp_path, schema)
    window.open("Themes/Mine_Theme.tdl")
    return window


def offered(w):
    """What the Add list of the selected block offers, by calling the action and reading the picker."""
    w.vm.structure_add()
    w.settle()
    return [o["value"] for o in w.vm.picker_items.get()]


def test_a_theme_offers_its_token_groups_and_modes_once_each(schema):
    found = [c.type for c in children_of(schema, "Theme")]
    assert found == [g.capitalize() for g in schema.tokens] + ["Modes"] and all(c.unique for c in children_of(schema, "Theme"))
    assert [c.type for c in children_of(schema, "Modes")] == list(mode_names(schema)) and mode_names(schema)[:4] == MODES
    assert [c.type for c in children_of(schema, "Light")] == [g.capitalize() for g in schema.tokens]
    assert children_of(schema, "Color") == []


def test_settings_offers_its_sections_from_the_schema_and_shortcuts_when_the_schema_has_them(schema, schema_data):
    assert [c.type for c in children_of(schema, "Settings")] == [s for s in schema.settings if s != "Settings"]
    more = dict(schema_data, settings={**schema_data["settings"], "Shortcuts": {"Open": {"kind": "key_chord", "doc": "x", "group": "Shortcuts"}}})
    from tess_shell_config.schema import Schema

    assert "Shortcuts" in [c.type for c in children_of(Schema.from_data(more), "Settings")]


def test_the_theme_add_list_leaves_out_what_the_file_has_and_adding_a_mode_adds_a_column(w, schema):
    w.select("Theme")
    groups = offered(w)
    assert "Color" not in groups and "Type" in groups and "Modes" not in groups  # Color and Modes are there already
    w.vm.pick_option("Type")
    w.settle()
    assert "Type { }" in w.session.model.text
    w.select("Modes")
    modes = offered(w)
    assert modes == ["Dark", "High_Contrast", "Reduced_Motion"]
    before = w.session.model.text
    w.vm.pick_option("Dark")
    w.settle()
    assert [line[0] + line[2:].strip() for line in difflib.ndiff(before.splitlines(), w.session.model.text.splitlines()) if line[0] in "+-"] == ["+Dark { }"]
    w.select("Color")  # the group under the theme
    rows = [i for i in w.vm.form_items.get() if i["type"] == "row"]
    assert [c["column"] for c in rows[0]["cells"]] == ["base", "Light", "Dark"]


def test_a_colour_token_has_a_swatch_in_every_mode_column_and_the_values_are_each_modes(w):
    w.select("Color")
    rows = {i["id"]: i for i in w.vm.form_items.get() if i["type"] == "row"}
    cells = {c["column"]: c for c in rows["t:surface"]["cells"]}
    assert set(cells) == {"base", "Light"} and all(c["ui"] == "colour" for c in cells.values())
    assert (cells["base"]["colour"], cells["Light"]["colour"]) == ("#101418", "#f4f7fa")
    assert cells["base"]["present"] and cells["Light"]["present"]
    # a token the Light mode does not override has an empty Light cell (its placeholder is the schema's default)
    primary = {c["column"]: c for c in rows["t:primary"]["cells"]}
    assert primary["base"]["present"] and not primary["Light"]["present"]


def test_removing_a_mode_removes_its_column_and_undo_brings_it_back(w):
    before = w.session.model.text
    w.select("Light")
    assert w.vm.can_remove.get()
    w.vm.structure_remove()
    w.settle()
    assert "Light" not in w.session.model.text
    w.select("Color")
    rows = [i for i in w.vm.form_items.get() if i["type"] == "row"]
    assert [c["column"] for c in rows[0]["cells"]] == ["base"]
    w.vm.undo()
    assert w.session.model.text == before


def test_a_mode_group_edits_that_modes_tokens_in_one_column(w):
    w.select("Modes")
    w.vm.structure_add()
    w.settle()
    w.vm.pick_option("Dark")
    w.settle()
    w.select("Dark")
    w.vm.structure_add()
    w.settle()
    w.vm.pick_option("Color")
    w.settle()
    labels = [r["label"] for r in _rows(w.vm.structure_nodes.get())]
    assert labels.count("Color") == 3
    assert "Color { }" in w.session.model.text


def test_a_settings_section_is_a_page_and_a_missing_section_is_added_from_the_add_list(folder, tmp_path, schema):
    w = FormWindow(folder, tmp_path, schema)
    w.open("settings.tdl")
    w.select("Settings")
    sections = offered(w)
    assert "Logging" not in sections and "Validation" not in sections  # the file has them
    assert {"Directories", "Appearance", "Debug"} <= set(sections)
    w.vm.pick_option("Appearance")
    w.settle()
    assert "Appearance { }" in w.session.model.text
    w.select("Appearance")
    keys = [i["id"] for i in w.vm.form_items.get() if i["type"] == "row"]
    assert keys and all(k.startswith("k:") for k in keys) and "k:Theme" in keys
    w.select("Logging")
    assert w.vm.form_title.get() == "Logging" and "k:Level" in [i["id"] for i in w.vm.form_items.get() if i["type"] == "row"]


def test_every_settings_section_of_the_schema_has_a_page(schema):
    text = "---\nTDL: 0.1\nName: S\n---\nSettings {\n" + "".join(f"    {s} {{ }}\n" for s in schema.settings if s != "Settings") + "}\n"
    model = DocumentModel.from_bytes(text.encode())
    form = Form(schema)
    for entry in model.document.root.entries:
        if getattr(entry, "type", ""):
            model.select(tuple(entry.index_path))
            assert form.build(model).rows, entry.type
    model.select(())
    assert any(r.key is not None and r.key.name == "Main_Shell" for r in form.build(model).rows)


POPUPS = """---
TDL: 0.1
Name: Pop
---

Shell {
    Monitor {
        Name: Main, Index: default
        Popup { Name: Tray_Menu, Gap: 9 }
        Popup { Name: Mine }
    }
}
"""


def test_a_popup_with_the_name_of_a_default_popup_shows_that_popups_values_and_says_it_replaces_it(schema):
    model = DocumentModel.from_bytes(POPUPS.encode())
    form = Form(schema)
    popups = [e for e in next(e for e in model.document.root.entries if getattr(e, "type", "") == "Monitor").entries if getattr(e, "type", "") == "Popup"]
    model.select(tuple(popups[0].index_path))
    view = form.build(model)
    default = schema.popups["Tray_Menu"]
    assert any("default Tray_Menu popup of the Tray module" in n and "replaces it whole" in n for n in view.notes)
    assert view.cell("Attach").widget.default == "BOTTOM" and view.cell("Alignment").widget.default == "START"
    assert view.cell("Gap").widget.default == "4" and view.cell("Gap").text == "9"  # the file's own value is shown, the default is the placeholder
    assert view.cell("Max_Height").widget.default == "60%" and default.values["max_height"]["unit"] == "%"
    model.select(tuple(popups[1].index_path))
    view = form.build(model)
    assert any(n.startswith("The popups the modules open by default: Tray_Menu (Tray)") for n in view.notes)
    assert view.cell("Attach").widget.default == (schema.roots["Popup"].keys["Attach"].default or "")
