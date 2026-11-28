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


def test_the_window_stylesheet_boxes_its_own_inputs_not_the_input_inside_a_text_field(tmp_path):
    """The owner's fb01: the token search (a TextField) showed a dark pill of its own inside its outlined frame, over the frame: the window stylesheet's rule for every TextInput also matched the input a
    TextField holds. The dark box is for the inputs the window writes itself (class `boxed`)."""
    from tess_ui import App

    from tess_shell_config.app import ROOT

    (tmp_path / "Views").mkdir()
    shutil.copy(ROOT / "Views" / "Main_Stylesheet.tdl", tmp_path / "Views" / "Main_Stylesheet.tdl")
    (tmp_path / "Views" / "Main_View.tdl").write_text("""---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 400, Height: 200, Gap: 8 }
  Children {
    TextField { Name: field, Variant: outlined, Label: "Search tokens", Leading: search, Style { Width: 360 } }
    TextInput { Name: bare, Classes: [boxed], Text: "x", Typography_Role: body_medium, Style { Width: 200 } }
  }
}
""")
    app = App(root=tmp_path, width=400, height=200, dark=True, theme_seed=(0x67, 0x50, 0xA4, 0xFF), stylesheet=tmp_path / "Views" / "Main_Stylesheet.tdl")
    view = app.open_view("Main")
    app.show("main")
    for _ in range(8):
        view.window.advance(16)
    window = view.window
    try:
        pixels, width, _ = window.snapshot()
    except RuntimeError as error:
        pytest.skip(f"no GPU to render with: {error}")
    field = view.node("root.field")
    inner = next(n for i in view.handle.composition.walk() if i.id.startswith("root.field.") for n in [view._built.nodes.get(i.id)] if n is not None and n.get("kind") == "text_input")

    def pixel(x, y):
        at = (int(y) * width + int(x)) * 4
        return tuple(pixels[at : at + 3])

    frame_inside = pixel(field.get("layout_x") + 5, field.get("layout_y") + field.get("layout_height") / 2 - 6)  # inside the frame, left of the icon
    over_input = pixel(inner.get("layout_x") + inner.get("layout_width") - 20, inner.get("layout_y") + inner.get("layout_height") / 2 + 6)  # where the dark pill was
    assert max(abs(a - b) for a, b in zip(frame_inside, over_input)) < 12, f"the input paints no box of its own: {frame_inside} vs {over_input}"
    bare = view.node("root.bare")
    box = pixel(bare.get("layout_x") + bare.get("layout_width") - 6, bare.get("layout_y") + bare.get("layout_height") / 2)
    assert max(abs(a - b) for a, b in zip(frame_inside, box)) > 12, "the window's own input keeps its box"
