"""The window's density and fit: dense trees, the folder path inside its pane, single-line fields centred (the owner's feedback on the live demo)."""

import shutil

import pytest
from test_shell_config_form_window import FormWindow
from test_shell_config_window import CONFIG


@pytest.fixture
def w(tmp_path, schema):
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    window = FormWindow(folder, tmp_path, schema)
    window.open()
    window.select("Bar  Top_Bar")
    window.open_all_groups()
    return window


def named(w, name):
    view = w.built.view
    return [(inst, view.node(inst.id)) for inst in view.handle.composition.walk() if inst.name == name]


def test_tree_rows_are_dense_four_pixels_in_and_sixteen_per_level(w):
    view = w.built.view
    pads = sorted({view._built.outer[inst.id].get("padding_left") for inst, _ in named(w, "row") if "structure_tree" in inst.id})
    assert pads[0] == 8, f"a root row is 8 px in at the compact density (the toolkit default is 16): {pads}"
    assert {b - a for a, b in zip(pads, pads[1:])} == {16}, f"16 px per level (the default is 24): {pads}"


def test_the_folder_path_stays_inside_the_files_pane_and_says_the_whole_path_in_a_tooltip(w):
    (inst, text), = named(w, "folder_text")
    pane = w.built.view.node("root.panes.files_pane")
    assert text.get("layout_x") + text.get("layout_width") <= pane.get("layout_x") + pane.get("layout_width") - 8 + 0.5
    assert inst.tooltip and str(w.vm.folder.get()) in str(inst.tooltip["text"].get())


def test_text_in_a_single_line_field_is_centred_vertically(w):
    """tre 0.6.11 centres a single-line text input by itself (`vertical_align` 'center' is its default); the window no longer pads 7 above and below to fake it."""
    view = w.built.view
    inputs = [view.node(inst.id) for inst, _ in named(w, "field") if inst.widget == "TextInput"]
    assert inputs
    for node in inputs:
        assert node.get("vertical_align") in (None, "center")  # unset: the engine default is centred, and nothing here opts out with "start"


def test_a_wrapped_doc_text_is_as_tall_as_its_lines_and_no_row_is_laid_over_it(tmp_path, schema):
    """The owner's overlap: the doc paragraph under the focused row was laid out one line tall (the toolkit measured a `Width: 100%` text with nothing to wrap at) and painted
    wrapped, so the rows below sat on top of it. Its height is its wrapped lines, and the next row starts below it."""
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    w = FormWindow(folder, tmp_path, schema, width=900, height=800)  # the owner's narrow window: the Form pane is about 210 px wide
    w.open()
    w.select("Monitor  Primary")
    w.open_all_groups()
    view = w.built.view
    rows = [item for item in w.vm.form_items.get() if item["type"] == "row" and item.get("doc") and any(c.get("ui") == "field" for c in item["cells"])]
    longest = max(rows, key=lambda item: len(item["doc"]))
    key = longest["id"]
    field = next(i for i in view.handle.composition.walk() if f"form_item[{key}#" in i.id and i.id.endswith(".field_box.field") and f"cell[{key}|" in i.id)
    view.node(field.id).focus()
    w.settle(8)
    (inst, doc), = [(i, n) for i, n in named(w, "doc_line") if f"form_item[{key}#" in i.id]
    line = 16.0  # body_small: 12 px at 1.33
    lines = doc.get("layout_height") / line
    assert lines >= 2, f"the doc ({len(longest['doc'])} characters, {doc.get('layout_width')} px wide) is {lines} line(s) tall"
    below = min(n.get("layout_y") for _, n in named(w, "form_item") if n.get("layout_y") > doc.get("layout_y"))
    assert below >= doc.get("layout_y") + doc.get("layout_height") - 0.5, "the next row starts below the doc text"
