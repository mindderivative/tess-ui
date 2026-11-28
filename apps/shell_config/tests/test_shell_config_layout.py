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
    pane = w.built.view.node("root.dock.files_panel.files_pane")
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


def test_the_fields_of_the_properties_fill_the_dock_and_line_up_in_one_column(w):  # (a Monitor: its rows are short, so the widest row does not size the content)
    """A value field is as wide as the dock leaves it, the same for every row; before, the content of a two-way scroller was only as wide as its widest row, so short rows had tiny fields."""
    w.select("Monitor  Primary")
    w.open_all_groups()
    view = w.built.view
    scroll = view._built.outer["root.dock.form_panel.form_pane.form_scroll"]
    boxes = [(n.get("layout_x"), n.get("layout_width")) for inst, n in named(w, "field_box")]
    assert boxes and len({round(x) for x, _ in boxes}) == 1, f"one column: {boxes}"
    assert min(width for _, width in boxes) >= scroll.get("layout_width") - 120 - 32 - 8 * 4 - 8, "wide enough to use the dock"


def test_a_long_file_name_ends_in_an_ellipsis_inside_the_files_dock_and_nothing_scrolls_sideways(tmp_path, schema):
    """The Tree spec (Layout and overflow): labels truncate with an ellipsis and the tree makes no horizontal overflow from labels. The name was cut at the pane edge and a bar scrolled it."""
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    (folder / "Modules" / "A_Very_Long_Module_Name_That_Cannot_Fit_The_Dock").mkdir()
    (folder / "Modules" / "A_Very_Long_Module_Name_That_Cannot_Fit_The_Dock" / "A_Very_Long_Module_Name_That_Cannot_Fit_The_Dock_Module.tdl").write_text(
        (folder / "Modules" / "Hello" / "Hello_Module.tdl").read_text())
    w = FormWindow(folder, tmp_path, schema)
    w.settle(6)
    tree = w.built.view.node("root.dock.files_panel.files_pane.files_scroll.files_tree")
    right = tree.get("layout_x") + tree.get("layout_width")
    labels = [n for inst, n in named(w, "label") if "files_tree.row[f:Modules/A_Very_Long" in inst.id]
    assert labels, "the long file is listed"
    assert all(n.get("layout_x") + n.get("layout_width") <= right + 0.5 for n in labels), "the label ends inside the row"
    assert all(n.get("wrap") == "none" and n.get("overflow") == "ellipsis" for n in labels)
    assert w.built.view._built.outer["root.dock.files_panel.files_pane.files_scroll"].get("orientation") == "vertical"


def test_a_marker_under_a_label_wraps_inside_the_label_column_and_never_runs_under_the_field(w):
    """The owner's fb06: the second line under a label ("written in a module's file, not here") was one long line, laid over the field and clipped by it. It wraps in the label column."""
    w.select("Text")
    w.open_all_groups()
    markers = [(inst, node) for inst, node in named(w, "marker_text")]
    assert markers, "a Text block has a row with a marker"
    for inst, marker in markers:
        label_box = w.built.view.node(inst.id.rsplit(".", 1)[0])
        cells = w.built.view.node(label_box and inst.id.rsplit(".", 2)[0] + ".cells")
        assert marker.get("layout_x") + marker.get("layout_width") <= cells.get("layout_x") + 0.5, "the marker ends before the cells begin"
        assert marker.get("layout_width") <= label_box.get("layout_width") + 0.5
