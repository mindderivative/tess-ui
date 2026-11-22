"""A Tree that chooses several rows (`Multiple: true`, `Selection`): the engine's click, Ctrl, Shift, Space and Ctrl+A rules over the rows that show, and the choice kept in
the tree's keys, so a chosen row inside a closed branch stays chosen (AC-SLT-7, AC-TRE-11). Rows are found by role and label."""

import pytest

from test_tree import opened, settle
from test_tree_characterisation import key, row, rows


@pytest.fixture
def tree(tmp_path):
    view, vm = opened(tmp_path, "Multiple: true\n      Selection: <| picked |>")
    return view, vm


def click(view, label, **modifiers):
    view.window.simulate("click", node=row(view, label), **modifiers)
    settle(view, 6)


def press(view, name, **modifiers):
    view.window.simulate("key_down", key=name, **modifiers)
    settle(view, 5)


def focus(view, label):
    row(view, label).focus()
    settle(view, 3)


def chosen(vm):
    return sorted(vm.picked.get())


def test_click_chooses_one_ctrl_toggles_and_shift_chooses_a_range_from_the_anchor(tree):
    view, vm = tree
    click(view, "Letter")
    assert chosen(vm) == ["a"]
    click(view, "Pictures", ctrl=True)
    assert chosen(vm) == ["a", "pics"]
    click(view, "Readme", shift=True)  # the anchor is the row Ctrl+click chose last
    assert chosen(vm) == ["pics", "readme"]
    click(view, "Pictures", ctrl=True)
    assert chosen(vm) == ["readme"]


def test_a_plain_press_on_a_branch_opens_it_and_a_ctrl_or_shift_press_only_chooses(tree):
    view, vm = tree
    click(view, "Pictures")
    assert "pics" in vm.open.get() and chosen(vm) == ["pics"]
    click(view, "Documents", ctrl=True)
    assert "docs" in vm.open.get() and chosen(vm) == ["docs", "pics"]  # Documents was open and stays open


def test_shift_arrow_extends_the_choice_and_moves_the_focus_with_it(tree):
    view, vm = tree
    click(view, "Letter")
    focus(view, "Letter")
    press(view, "arrow_down", shift=True)
    assert chosen(vm) == ["a", "b"] and [n.get("label") for n in rows(view) if n.get("focused")] == ["Reports"]
    press(view, "arrow_down", shift=True)
    assert chosen(vm) == ["a", "b", "pics"]
    press(view, "arrow_up", shift=True)
    assert chosen(vm) == ["a", "b"]
    press(view, "arrow_down", ctrl=True)  # Ctrl+Arrow moves the focus and chooses nothing
    assert chosen(vm) == ["a", "b"] and [n.get("label") for n in rows(view) if n.get("focused")] == ["Pictures"]


def test_space_toggles_the_row_that_has_the_focus_and_ctrl_a_chooses_every_row_that_shows(tree):
    view, vm = tree
    focus(view, "Letter")
    press(view, "space")
    assert chosen(vm) == ["a"]
    press(view, "space")
    assert chosen(vm) == []
    press(view, "a", ctrl=True)
    assert chosen(vm) == ["a", "b", "docs", "pics", "readme"]  # Reports is closed: its children q and r do not show


def test_a_chosen_row_inside_a_closed_branch_stays_chosen_AC_SLT_7(tree):
    view, vm = tree
    click(view, "Letter")
    click(view, "Reports", ctrl=True)  # Reports is a closed branch: Ctrl+press does not open it
    assert chosen(vm) == ["a", "b"]
    focus(view, "Documents")
    press(view, "arrow_left")  # closes Documents: Letter and Reports are out of sight
    assert vm.open.get() == [] and chosen(vm) == ["a", "b"]
    press(view, "a", ctrl=True)  # Ctrl+A chooses the rows that show; the hidden ones keep their state
    assert chosen(vm) == ["a", "b", "docs", "pics", "readme"]
    press(view, "arrow_right")  # Documents opens again: its chosen children show as chosen
    assert [(n.get("label"), n.get("selected")) for n in rows(view)] == [
        ("Documents", True), ("Letter", True), ("Reports", True), ("Pictures", True), ("Readme", True)]


def test_a_plain_click_chooses_only_that_row_also_clearing_what_is_hidden(tree):
    view, vm = tree
    click(view, "Letter")
    focus(view, "Documents")
    press(view, "arrow_left")
    assert chosen(vm) == ["a"]
    click(view, "Readme")
    assert chosen(vm) == ["readme"]


def test_the_rows_tell_assistive_technology_whether_they_are_chosen_and_a_write_from_code_chooses_rows(tree):
    view, vm = tree
    assert view.node("root.t").get("selection_mode") == "multiple"
    vm.picked.set(["b", "readme", "q"])  # q is inside a closed branch: kept, not shown
    settle(view, 6)
    assert [(n.get("label"), n.get("selected")) for n in rows(view)] == [
        ("Documents", False), ("Letter", False), ("Reports", True), ("Pictures", False), ("Readme", True)]
    assert chosen(vm) == ["b", "q", "readme"]


def test_a_disabled_row_is_not_chosen_by_ctrl_a_a_range_or_a_press(tmp_path, monkeypatch):
    import test_tree
    from test_tree_characterisation import DISABLED

    monkeypatch.setattr(test_tree, "NODES", DISABLED)  # Readme is disabled
    view, vm = opened(tmp_path, "Multiple: true\n      Selection: <| picked |>")
    focus(view, "Letter")
    press(view, "a", ctrl=True)
    assert chosen(vm) == ["a", "b", "docs", "pics"]
    click(view, "Readme")
    assert "readme" not in chosen(vm)


def test_without_multiple_the_tree_chooses_one_row_as_before(tmp_path):
    view, vm = opened(tmp_path)
    assert view.node("root.t").get("selection_mode") in (None, "none")
    click(view, "Pictures")
    assert vm.sel.get() == "pics" and vm.picked.get() == []


def test_on_change_says_the_reason_and_the_detail_of_each_change_to_the_chosen_rows(tmp_path):
    view, vm = opened(tmp_path, "Multiple: true\n      Selection: <| picked |>\n      On_Change: \"heard(event.reason, event.detail, event.count, event.selection, event.anchor)\"")
    click(view, "Letter")
    click(view, "Pictures", ctrl=True)
    click(view, "Readme", shift=True)
    focus(view, "Letter")
    press(view, "a", ctrl=True)
    vm.picked.set(["a"])
    settle(view, 6)
    heard = vm.log
    assert [(r, d, c) for r, d, c, *_ in heard] == [
        ("pointer", "select", 1), ("pointer", "toggle", 2), ("pointer", "range", 2), ("keyboard", "all", 5), ("api", "select", 1)]
    assert heard[0][3:] == (["a"], "a") and heard[1][3:] == (["a", "pics"], "pics")


def test_ctrl_a_can_be_taken_from_a_multiple_tree(tmp_path):
    view, vm = opened(tmp_path, "Multiple: true\n      Selection: <| picked |>\n      Select_All_Key: false")
    focus(view, "Letter")
    press(view, "a", ctrl=True)
    assert chosen(vm) == []
    click(view, "Letter")
    assert chosen(vm) == ["a"]
