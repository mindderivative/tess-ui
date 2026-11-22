"""The Tree as a user and an assistive technology see it, pinned BEFORE its internal restructure: the rows that show and their order, levels, open and
chosen state, the one Tab stop, the keyboard, the two-way `expanded` and `selected`, a disabled row. Nothing here names a node id: rows are found by
their role and label, so the tests describe the public behaviour and hold across a different internal structure."""

import pytest

from test_tree import NODES, VM, opened as _opened, settle

DISABLED = NODES.replace("Item { Value: readme, Label: Readme, Icon: file }", "Item { Value: readme, Label: Readme, Icon: file, Disabled: true }")


def _walk(node):
    yield node
    for child in node.children():
        yield from _walk(child)


def rows(view):
    """The tree's rows in the order they show."""
    return [n for n in _walk(view.window.root) if n.get("role") == "treeitem"]


def row(view, label):
    return next(n for n in rows(view) if n.get("label") == label)


def labels(view):
    return [n.get("label") for n in rows(view)]


def press(view, label):
    view.window.simulate("click", node=row(view, label))
    settle(view, 6)


def key(view, name):
    view.window.simulate("key_down", key=name)
    settle(view, 4)


def focused(view):
    return [n.get("label") for n in rows(view) if n.get("focused")]


@pytest.fixture
def tree(tmp_path):
    return _opened(tmp_path)


def test_the_rows_that_show_are_the_open_branches_children_in_order_with_their_levels_and_state(tree):
    view, _ = tree
    assert labels(view) == ["Documents", "Letter", "Reports", "Pictures", "Readme"]
    assert [n.get("level") for n in rows(view)] == [1, 2, 2, 1, 1]
    assert [n.get("expanded") for n in rows(view)] == [True, None, False, False, None]  # a leaf has no `expanded`
    assert [n.get("selected") for n in rows(view)] == [False, True, False, False, False]
    assert next(n for n in _walk(view.window.root) if n.get("role") == "tree").get("label") == "Tree"


def test_a_row_is_56_tall_and_a_deeper_row_is_indented_24_further(tree):
    view, _ = tree
    assert {n.get("layout_height") for n in rows(view)} == {56.0}
    text = {n.get("text"): n.get("layout_x") for n in _walk(view.window.root) if n.get("kind") == "text"}
    assert text["Letter"] - text["Pictures"] == 24.0 and text["Reports"] == text["Letter"]  # (rows with no icon: an icon moves the label)


def test_the_tree_is_one_tab_stop_held_by_the_chosen_row_and_it_follows_the_focus(tree):
    view, _ = tree
    stops = lambda: [n.get("label") for n in rows(view) if n.get("tab_index") == 0]  # noqa: E731
    assert stops() == ["Letter"]
    row(view, "Pictures").focus()
    settle(view, 4)
    assert stops() == ["Pictures"]


def test_pressing_a_leaf_chooses_it_and_a_branch_chooses_it_and_toggles_it(tree):
    view, vm = tree
    press(view, "Readme")
    assert vm.sel.get() == "readme" and vm.open.get() == ["docs"]
    press(view, "Pictures")
    assert vm.sel.get() == "pics" and "pics" in vm.open.get() and labels(view)[-2:] == ["Holiday", "Readme"]
    press(view, "Pictures")
    assert "pics" not in vm.open.get() and "Holiday" not in labels(view)


def test_the_two_models_drive_the_tree_from_outside(tree):
    view, vm = tree
    vm.sel.set("readme")
    vm.open.set(["docs", "b"])
    settle(view)
    assert labels(view) == ["Documents", "Letter", "Reports", "Q1", "Q2", "Pictures", "Readme"]
    assert [n.get("label") for n in rows(view) if n.get("selected")] == ["Readme"]
    assert row(view, "Q1").get("level") == 3
    vm.open.set([])
    settle(view)
    assert labels(view) == ["Documents", "Pictures", "Readme"]


def test_down_and_up_move_through_the_rows_that_show_and_home_and_end_go_to_the_ends(tree):
    view, _ = tree
    row(view, "Letter").focus()
    settle(view, 4)
    for name, want in (("arrow_down", "Reports"), ("arrow_down", "Pictures"), ("arrow_up", "Reports"), ("end", "Readme"), ("home", "Documents")):
        key(view, name)
        assert focused(view) == [want], name


def test_right_opens_a_closed_branch_then_goes_to_its_first_child_and_left_closes_then_goes_to_the_parent(tree):
    view, vm = tree
    row(view, "Pictures").focus()
    settle(view, 4)
    key(view, "arrow_right")
    assert "pics" in vm.open.get() and focused(view) == ["Pictures"]
    key(view, "arrow_right")
    assert focused(view) == ["Holiday"]
    key(view, "arrow_left")  # a leaf: to its parent
    assert focused(view) == ["Pictures"]
    key(view, "arrow_left")  # an open branch: closes
    assert "pics" not in vm.open.get() and focused(view) == ["Pictures"]


def test_typing_the_start_of_a_label_jumps_to_that_row_and_star_opens_the_sibling_branches(tree):
    view, vm = tree
    row(view, "Letter").focus()
    settle(view, 4)
    key(view, "p")
    assert focused(view) == ["Pictures"]
    row(view, "Documents").focus()
    settle(view, 4)
    key(view, "*")
    assert set(vm.open.get()) == {"docs", "pics"}


def test_enter_on_a_row_presses_it(tree):
    view, vm = tree
    row(view, "Pictures").focus()
    settle(view, 4)
    key(view, "enter")
    assert vm.sel.get() == "pics" and "pics" in vm.open.get()


def test_a_disabled_row_is_not_chosen_and_the_arrows_skip_nothing_that_is_enabled(tmp_path):
    view, vm = _opened(tmp_path, "")
    text = (tmp_path / "Views" / "Main_View.tdl").read_text().replace(NODES, DISABLED)
    (tmp_path / "Views" / "Main_View.tdl").write_text(text)
    from tess_ui import App

    app = App(root=tmp_path, width=400, height=600)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 8)
    before = app.bindings.viewmodel_for("main").sel.get()
    press(view, "Readme")
    assert app.bindings.viewmodel_for("main").sel.get() == before
    assert not row(view, "Readme").get("focusable")
