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
    view = w.built.view
    fields = [view._built.outer[inst.id] for inst, _ in named(w, "field") if inst.widget == "TextInput"]
    assert fields
    for node in fields:
        assert node.get("padding_top") == node.get("padding_bottom") == 7
