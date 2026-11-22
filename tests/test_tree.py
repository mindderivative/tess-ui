"""#157, #158: a tree -- branches that open to show their children, and leaves; selection, the keyboard, and levels."""

import pytest

from tess_ui import App, Signal, ViewModel, tokens
from tess_ui.shipped import shipped_views

NODES = """Nodes {
  Item {
    Value: docs
    Label: Documents
    Icon: folder
    Children {
      Item { Value: a, Label: Letter }
      Item { Value: b, Label: Reports, Children { Item { Value: q, Label: Q1 } Item { Value: r, Label: Q2 } } }
    }
  }
  Item { Value: pics, Label: Pictures, Children { Item { Value: p, Label: Holiday } } }
  Item { Value: readme, Label: Readme, Icon: file }
}"""


class VM(ViewModel):
    views = "main"

    def heard(self, *told):
        self.log.append(told)

    def __init__(self):
        super().__init__()
        self.open = Signal(["docs"])
        self.sel = Signal("a")
        self.picked = Signal([])
        self.log = []


def opened(tmp_path, props=""):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 600 }}
  Children {{
    Tree {{
      Name: t
      {NODES}
      Expanded: <| open |>
      Selected: <| sel |>
      {props}
    }}
  }}
}}
""")
    app = App(root=tmp_path, width=400, height=600)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(8):
        view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


def role(view, name):
    return (view._scheme or tokens.BASELINE)[name]


def settle(view, n=20):
    for _ in range(n):
        view.window.advance(16)


def row(view, *path):
    """The row at `path` of values: ('docs', 'b') is Reports inside Documents."""
    return view.node(f"root.t.row[{path[-1]}]")


def test_they_are_shipped():
    assert {"Tree", "TreeNode"} <= set(shipped_views())


def test_the_tree_is_a_tree_and_its_rows_are_tree_items_at_their_levels(tmp_path):
    view, _ = opened(tmp_path)
    assert view.node("root.t").get("role") == "tree"
    assert [row(view, *p).get("role") for p in (("docs",), ("docs", "a"), ("readme",))] == ["treeitem"] * 3
    assert [row(view, *p).get("level") for p in (("docs",), ("docs", "a"), ("docs", "b"))] == [1, 2, 2]


def test_open_branches_show_their_children_one_level_in_and_closed_ones_do_not(tmp_path):
    view, _ = opened(tmp_path)
    assert row(view, "docs").get("expanded") is True and row(view, "pics").get("expanded") is False
    assert "root.t.row[a]" in view._built.specs and "root.t.row[p]" not in view._built.specs
    assert "root.t.row[q]" not in view._built.specs  # Reports is closed
    assert row(view, "docs", "a").get("layout_x") == row(view, "docs").get("layout_x") and row(view, "docs", "a").get("layout_y") == row(view, "docs").get("layout_y") + 56


def test_a_row_is_56_tall_indented_16_plus_24_a_level_with_the_chevron_and_the_label(tmp_path):
    view, _ = opened(tmp_path)
    top, inner = row(view, "docs"), row(view, "docs", "a")
    assert top.get("layout_height") == 56.0
    assert view.node("root.t.row[pics].chevron").get("layout_x") == 16.0  # (a turned one reports its box from the turn)
    assert view.node("root.t.row[a].label").get("layout_x") == 16 + 24 + 24 + 8
    assert view.node("root.t.row[docs].label").get("layout_x") == 16 + 24 + 8 + 24 + 8  # a folder icon after the chevron
    assert view.node("root.t.row[docs].label").get("font_size") == 16.0


def test_a_leaf_has_no_chevron_and_a_branch_has_one(tmp_path):
    view, _ = opened(tmp_path)
    assert "root.t.row[docs].chevron" in view._built.specs and "root.t.row[readme].chevron" not in view._built.specs
    assert "root.t.row[readme].chevron_space" in view._built.specs


def test_the_chevron_turns_a_quarter_when_a_branch_is_open(tmp_path):
    view, _ = opened(tmp_path)
    settle(view)
    assert view.node("root.t.row[docs].chevron").get("rotation_deg") == 90.0
    assert view.node("root.t.row[pics].chevron").get("rotation_deg") == 0.0


def test_the_chosen_row_is_secondary_container(tmp_path):
    view, _ = opened(tmp_path)
    assert row(view, "docs", "a").get("fill") == role(view, "secondary_container") and row(view, "docs", "a").get("selected") is True
    assert row(view, "docs").get("fill")[3] == 0


def test_pressing_a_leaf_chooses_it(tmp_path):
    view, vm = opened(tmp_path)
    view.window.simulate("click", node=row(view, "readme"))
    settle(view, 30)
    assert vm.sel.get() == "readme" and vm.open.get() == ["docs"]


def test_pressing_a_branch_chooses_it_and_opens_or_closes_it(tmp_path):
    view, vm = opened(tmp_path)
    view.window.simulate("click", node=row(view, "pics"))
    settle(view, 6)
    assert vm.sel.get() == "pics" and vm.open.get() == ["docs", "pics"] and "root.t.row[p]" in view._built.specs
    view.window.simulate("click", node=row(view, "docs"))
    settle(view, 6)
    assert vm.open.get() == ["pics"] and "root.t.row[a]" not in view._built.specs


def test_a_nested_branch_opens_inside_its_parent_and_deeper_rows_are_deeper(tmp_path):
    view, vm = opened(tmp_path)
    view.window.simulate("click", node=row(view, "docs", "b"))
    settle(view, 6)
    assert vm.open.get() == ["docs", "b"]
    q = row(view, "docs", "b", "q")
    assert q.get("level") == 3 and q.get("layout_y") == row(view, "docs", "b").get("layout_y") + 56


def test_the_arrows_move_through_the_rows_that_show_across_levels(tmp_path):
    view, _ = opened(tmp_path)
    row(view, "docs").focus()
    settle(view, 2)
    for expected in (("docs", "a"), ("docs", "b"), ("pics",)):
        view.window.simulate("key_down", key="arrow_down")
        settle(view, 3)
        assert row(view, *expected).get("focused") is True


def test_right_opens_a_branch_and_left_closes_it(tmp_path):
    view, vm = opened(tmp_path)
    row(view, "pics").focus()
    settle(view, 2)
    view.window.simulate("key_down", key="arrow_right")
    settle(view, 6)
    assert vm.open.get() == ["docs", "pics"]
    view.window.simulate("key_down", key="arrow_left")
    settle(view, 6)
    assert vm.open.get() == ["docs"]
    view.window.simulate("key_down", key="arrow_left")  # already closed: nothing
    settle(view, 4)
    assert vm.open.get() == ["docs"]


def test_a_compact_tree_has_40_pixel_rows(tmp_path):
    view, _ = opened(tmp_path, "Compact: true")
    assert row(view, "docs").get("layout_height") == 40.0 and row(view, "docs", "a").get("layout_y") == row(view, "docs").get("layout_y") + 40


def test_a_disabled_row_does_not_respond(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text("""---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Width: 300, Height: 300 }
  Children {
    Tree {
      Name: t
      Nodes { Item { Value: x, Label: X, Disabled: true } Item { Value: y, Label: Y } }
      Selected: <| sel |>
    }
  }
}
""")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 6)
    view.window.simulate("click", node=view.node("root.t.row[x]"))
    settle(view, 6)
    assert app.bindings.viewmodel_for("main").sel.get() == "a"


def test_a_tree_with_nothing_bound_still_opens_and_chooses(tmp_path):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Width: 400, Height: 500 }}
  Children {{
    Tree {{
      Name: t
      {NODES}
    }}
  }}
}}
""")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 6)
    view.window.simulate("click", node=row(view, "pics"))
    settle(view, 6)
    assert "root.t.row[p]" in view._built.specs and row(view, "pics").get("selected") is True


def focused_label(view):
    return next(r for r in ("docs", "pics", "readme") if row(view, r).get("focused"))


def test_right_on_an_open_branch_focuses_its_first_child_AC_TRE_04(tmp_path):
    view, vm = opened(tmp_path)  # docs is open: its children are Letter (a) and Reports (b)
    row(view, "docs").focus()
    settle(view, 2)
    view.window.simulate("key_down", key="arrow_right")
    settle(view, 6)
    assert vm.open.get() == ["docs"] and row(view, "docs", "a").get("focused") and not row(view, "docs").get("focused")
    view.window.simulate("key_down", key="arrow_right")  # a leaf: nothing
    settle(view, 4)
    assert row(view, "docs", "a").get("focused")


def test_left_on_a_leaf_or_a_closed_child_branch_focuses_its_parent_AC_TRE_05(tmp_path):
    view, vm = opened(tmp_path)
    row(view, "docs", "a").focus()
    settle(view, 2)
    view.window.simulate("key_down", key="arrow_left")
    settle(view, 6)
    assert row(view, "docs").get("focused") and vm.open.get() == ["docs"]
    view.window.simulate("key_down", key="arrow_left")  # docs is open at the root: it closes, focus stays
    settle(view, 6)
    assert vm.open.get() == [] and row(view, "docs").get("focused")
    view.window.simulate("key_down", key="arrow_left")  # a closed root: nothing
    settle(view, 4)
    assert row(view, "docs").get("focused") and vm.open.get() == []


def test_star_opens_every_closed_sibling_branch_and_no_others_AC_TRE_08(tmp_path):
    view, vm = opened(tmp_path)
    vm.open.set([])
    settle(view, 6)
    row(view, "docs").focus()
    settle(view, 2)
    view.window.simulate("key_down", key="*")
    settle(view, 6)
    assert sorted(vm.open.get()) == ["docs", "pics"]  # the two root branches; readme is a leaf and b (a deeper branch) is not a sibling


def test_the_tree_is_named_by_what_it_is_and_its_rows_are_one_flat_list_AC_TRE_01_AC_TRE_10(tmp_path):
    view, _ = opened(tmp_path, "Label: Files")
    assert view.node("root.t").get("role") == "tree" and view.node("root.t").get("label") == "Files"
    tree = view.node("root.t")
    assert all(n.get("role") != "group" for n in tree.children())  # the flat AT form: no group around an open branch's children
    assert [n.get("role") for n in tree.children()] == ["treeitem"] * 5 and [n.get("level") for n in tree.children()] == [1, 2, 2, 1, 1]
    assert view.node("root.t").get("label") != "Tree"


def opened_at(tmp_path, density, props=""):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 600 }}
  Children {{
    Tree {{
      Name: t
      {NODES}
      Expanded: <| open |>
      Selected: <| sel |>
      {props}
    }}
  }}
}}
""")
    app = App(root=tmp_path, width=400, height=600, density=density)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(8):
        view.window.advance(16)
    return view, app


@pytest.mark.parametrize("level, height, pad, indent, box", [("default", 40, 12, 20, 24), ("compact", 32, 8, 16, 20), ("dense", 24, 4, 12, 16)])
def test_the_tree_follows_the_density_table_AC_TRN_01_to_06(tmp_path, level, height, pad, indent, box):
    view, _ = opened_at(tmp_path, level)
    docs, a, b_ = row(view, "docs"), row(view, "docs", "a"), row(view, "docs", "b")
    assert docs.get("layout_height") == height == a.get("layout_height")  # all rows alike (AC-TRN-02)
    d0 = view._built.outer["root.t.row[docs]"].get("padding_left")
    d1 = view._built.outer["root.t.row[a]"].get("padding_left")
    assert d0 == pad and d1 - d0 == indent  # AC-TRN-03, AC-TRN-04
    chevron = view._built.outer["root.t.row[docs].chevron"]
    spacer = view._built.outer["root.t.row[a].chevron_space"]
    assert (chevron.get("width"), chevron.get("height"), spacer.get("width")) == (box, box, box)  # AC-TRN-06


def test_an_app_with_no_density_keeps_the_material_tree(tmp_path):
    view, app = opened_at(tmp_path, None)
    assert app.density.get() == "" and row(view, "docs").get("layout_height") == 56
    assert view._built.outer["root.t.row[docs]"].get("padding_left") == 16


def test_a_density_change_reaches_a_tree_that_is_showing(tmp_path):
    view, app = opened_at(tmp_path, "default")
    app.set_density("dense")
    for _ in range(8):
        view.window.advance(16)
    assert row(view, "docs").get("layout_height") == 24


def test_a_tree_can_have_a_density_of_its_own(tmp_path):
    view, _ = opened_at(tmp_path, "default", "Density: compact")
    assert row(view, "docs").get("layout_height") == 32
