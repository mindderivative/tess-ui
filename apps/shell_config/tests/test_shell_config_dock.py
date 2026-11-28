"""The window's panels are docked: Files and Structure are tabs of the left zone, the Editor and the View tabs of the centre, the Properties are the right zone and the Problems the bottom
one, between the left and right zones (the owner's layout). The panes keep their behaviour inside the docks; the tabs, the shortcuts that show them and the remembered arrangement are here."""

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
    return window


def dock(w):
    return w.built.view.dock_host("root.dock")


def box(w, panel):
    node = w.built.view.node(f"root.dock.{panel}")
    return node.get("layout_x"), node.get("layout_y"), node.get("layout_width"), node.get("layout_height")


def test_the_panels_are_in_the_zones_of_the_layout_and_the_tabs_are_named(w):
    d = dock(w).dock
    assert d.titles("left") == ["Files", "Structure"] and d.titles("center") == ["Editor", "View"]
    assert d.titles("right") == ["Properties"] and d.titles("bottom") == ["Problems"]
    assert d.shown_title("left") == "Files" and d.shown_title("center") == "Editor"


def test_the_left_and_right_zones_run_the_full_height_and_the_bottom_one_is_between_them(w):
    left, right, bottom = box(w, "files_panel"), box(w, "form_panel"), box(w, "problems_panel")
    centre = box(w, "text_panel")
    assert left[1] == right[1] and abs((left[1] + left[3]) - (right[1] + right[3])) < 1, "both side docks have the same top and bottom"
    assert bottom[0] >= left[0] + left[2] - 0.5 and bottom[0] + bottom[2] <= right[0] + 0.5, "the bottom zone is only as wide as the centre"
    assert bottom[1] >= centre[1] + centre[3] - 0.5, "and it is under the centre"
    assert left[3] > bottom[3] * 2


def test_f6_shows_the_tab_that_holds_the_area_it_goes_to(w):
    d = dock(w).dock
    w.key("F6")
    assert w.region() == 1 and d.shown_title("left") == "Structure"
    w.key("F6", shift=True)
    assert w.region() == 0 and d.shown_title("left") == "Files"


def test_a_tab_that_is_not_showing_is_shown_before_it_takes_the_focus_from_code(w):
    d = dock(w).dock
    d.show(d.panel("View"))
    w.settle()
    assert d.shown_title("center") == "View"
    w.built.shortcuts._focus("editor")
    w.settle()
    assert d.shown_title("center") == "Editor" and w.region() == 2


def test_the_arrangement_is_remembered_and_put_back_at_the_next_start(tmp_path, schema):
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    first = FormWindow(folder, tmp_path, schema)
    d = first.built.view.dock_host("root.dock")
    d.set_size("right", 400)
    d.set_size("bottom", 220)
    first.settle()
    first.built.close()
    second = FormWindow(folder, tmp_path, schema)
    again = second.built.view.dock_host("root.dock")
    assert again.size("right") == 400 and again.size("bottom") == 220
    assert again.dock.shown_title("left") == "Files", "a start always has the focus in the Files area, so its tab shows"
