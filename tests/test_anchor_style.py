"""#280, step 2: `style: {anchor: name, placement: ..., offset: [dx, dy]}` places a node against another node of the view, in the tree (tre 0.5.7): it follows its anchor,
stays clipped by its parent, and is looked for, checked and cleaned up by Tesserae."""

import pytest

from tess_ui import App, Signal, ViewModel
from tess_ui.spec.nodes import LoadError


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.show = Signal(True)
        self.x = Signal(150)
        self.place = Signal("top_end")
        self.rows = Signal([1, 2])


def doc(body, size="Width: 400, Height: 300"):
    """A TDL view: a root container holding the TDL nodes in `body`."""
    return f"---\nTDL: 0.2\nName: main\n---\nContainer {{\n  Name: main\n  Style {{ {size}, Background: surface }}\n  Children {{\n{body}  }}\n}}\n"


def opened(tmp_path, body, files=None, size="Width: 400, Height: 300"):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(doc(body, size))
    for name, text in (files or {}).items():
        (tmp_path / "Views" / name).write_text(text)
    app = App(root=tmp_path, width=400, height=300)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(50)
    return app, view, app.bindings.viewmodel_for("main")


PLAIN_TARGET = "    Rect { Name: target, Style { Position: absolute, X: <| x |>, Y: 120, Width: 60, Height: 40, Background: primary } }\n"
TARGET = "    If <| show |> { " + PLAIN_TARGET.strip() + " }\n"
DOT = "    Rect { Name: dot, Style { Anchor: target, Placement: top_end, %s Width: 12, Height: 12, Background: error } }\n"


def where(view, path="root.dot"):
    node = view.node(path)
    return node.get("layout_x"), node.get("layout_y")


def test_a_node_sits_on_the_corner_of_another(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + DOT % "")
    assert where(view) == (204.0, 114.0)  # its centre on the target's top-right corner (210, 120)


def test_an_offset_moves_it(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + DOT % "Offset: [2, -2],")
    assert where(view) == (206.0, 112.0)


@pytest.mark.parametrize("placement, expected", [("below", (150.0, 160.0)), ("above", (150.0, 108.0)), ("start", (138.0, 120.0)), ("end", (210.0, 120.0)),
                                                 ("center", (174.0, 134.0)), ("bottom_start", (144.0, 154.0))])
def test_the_placements(tmp_path, placement, expected):
    app, view, vm = opened(tmp_path, TARGET + (DOT % "").replace("top_end", placement))
    assert where(view) == expected


def test_it_leaves_the_flow_by_itself(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + DOT % "")
    assert view.node("root.dot").get("position") == "absolute"


def test_it_follows_its_anchor_with_no_lag(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + DOT % "")
    vm.x.set(200)
    view.window.advance(16)
    assert where(view) == (254.0, 114.0)


def test_a_placement_that_is_an_expression_follows_it(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + (DOT % "").replace("Placement: top_end", "Placement: <| place |>"))
    assert where(view) == (204.0, 114.0)
    vm.place.set("center")
    view.window.advance(16)
    assert where(view) == (174.0, 134.0)


def test_when_the_anchor_goes_the_node_is_hidden_and_when_it_is_back_it_is_shown(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + DOT % "")
    vm.show.set(False)
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is False
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is True and where(view) == (204.0, 114.0)


def test_a_node_that_says_visible_false_stays_hidden_when_its_anchor_returns(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + "    Rect { Name: dot, Visible: false, Style { Anchor: target, Placement: top_end, Width: 12, Height: 12, Background: error } }\n")
    vm.show.set(False)
    view.window.advance(16)
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is False


def test_the_anchor_may_be_the_parent(tmp_path):
    app, view, vm = opened(tmp_path, "    Container {\n      Name: host\n      Style { Position: absolute, X: 100, Y: 100, Width: 80, Height: 40 }\n      Children {\n"
                                      "        Rect { Name: dot, Style { Anchor: parent, Placement: top_end, Width: 12, Height: 12, Background: error } }\n      }\n    }\n")
    assert where(view, "root.host.dot") == (174.0, 94.0)  # the host's top-right corner is (180, 100)


def test_in_a_for_each_row_the_name_means_its_own_rows_node(tmp_path):
    body = ("    For n In <| rows |> Key <| n |> {\n      Container {\n        Name: row\n        Style { Position: absolute, X: 20, Y: <| n * 100 |>, Width: 100, Height: 40 }\n        Children {\n"
            "          Rect { Name: field, Style { Width: 100, Height: 40, Background: primary } }\n"
            "          Rect { Name: badge, Style { Anchor: field, Placement: top_end, Width: 10, Height: 10, Background: error } }\n        }\n      }\n    }\n")
    app, view, vm = opened(tmp_path, body)
    first, second = where(view, "root.row[1].badge"), where(view, "root.row[2].badge")
    assert first[1] < 100 and second[1] > 150  # each on its own row's field, not both on the first


def test_the_anchor_is_found_in_the_view_that_called_this_one(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + "    Marker { Name: m }\n", {"Marker_View.tdl":
                           "---\nTDL: 0.2\nName: Marker\n---\nContainer {\n  Children {\n    Rect { Name: dot, Style { Anchor: target, Placement: top_end, Width: 12, Height: 12, Background: error } }\n  }\n}\n"})
    assert where(view, "root.m.dot") == (204.0, 114.0)


def test_a_node_in_a_clipped_parent_is_clipped_like_any_child(tmp_path):
    body = ("    Container {\n      Name: box\n      Style { Position: absolute, X: 250, Y: 10, Width: 100, Height: 50, Clip_Children: true }\n      Children {\n"
            "        Rect { Name: host, Style { Position: absolute, X: 80, Y: 5, Width: 40, Height: 30, Background: primary } }\n"
            "        Rect { Name: dot, Style { Anchor: host, Placement: top_end, Width: 12, Height: 12, Background: error } }\n      }\n    }\n")
    app, view, vm = opened(tmp_path, body)
    x = where(view, "root.box.dot")[0]
    assert x > 350 and view.node("root.box").get("clip_children") is True  # it sits past the box's right edge (350), and the box cuts it off


def test_a_stylesheet_rule_can_give_the_placement(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        doc(PLAIN_TARGET + "    Rect { Name: dot, Classes: [badge], Style { Width: 12, Height: 12, Background: error } }\n"))
    app = App(root=tmp_path, width=400, height=300, stylesheet_spec={"styles": [{"classes": ["badge"], "widget": "Rect", "style": {"anchor": "target", "placement": "top_end"}}]})
    app.bind(VM)
    view = app.open_view("Main")
    view.window.advance(50)
    assert where(view) == (204.0, 114.0)


def test_when_the_style_stops_saying_it_the_node_goes_back_to_the_flow(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + DOT % "")
    node = view.node("root.dot")
    assert node.get("position") == "absolute"
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        doc(TARGET + "    Rect { Name: dot, Style { Width: 12, Height: 12, Background: error } }\n"))
    from tess_ui.spec.watch import ComposedWatcher
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    import os
    stat = view.source.stat()
    os.utime(view.source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert watcher.poll() is True
    view.window.advance(50)
    assert view.node("root.dot").get("position") == "relative" and where(view)[0] < 100


@pytest.mark.parametrize("style, fragment", [
    ("Anchor: \"\"", "style.anchor is the name of the node"),
    ("Anchor: target, Placement: above_end", "style.placement is one of"),
    ("Anchor: target, Offset: [1]", "style.offset is a pair of pixels"),
    ("Anchor: target, Offset: 3", "style.offset is a pair of pixels"),
])
def test_a_mistake_in_the_fields_is_found_at_load_with_its_position(tmp_path, style, fragment):
    with pytest.raises(LoadError) as caught:
        opened(tmp_path, TARGET + f"    Rect {{ Name: dot, Style {{ {style}, Width: 12, Height: 12, Background: error }} }}\n")
    assert fragment in str(caught.value) and "Main_View.tdl:" in str(caught.value)


def test_an_anchor_no_node_has_is_named_with_the_nearest_name(tmp_path):
    with pytest.raises(ValueError) as caught:
        opened(tmp_path, TARGET + "    Rect { Name: dot, Style { Anchor: tarbet, Placement: top_end, Width: 12, Height: 12, Background: error } }\n")
    assert "anchor 'tarbet' is no node by that name" in str(caught.value) and "did you mean 'target'" in str(caught.value)


def test_a_placement_worked_out_to_something_wrong_is_named(tmp_path):
    with pytest.raises(ValueError, match="style.placement is one of"):
        opened(tmp_path, TARGET + (DOT % "").replace("Placement: top_end", "Placement: <| 'sideways' |>"))


def test_an_overlay_in_a_row_sits_against_its_own_rows_node(tmp_path):
    """The lookup an Overlay's `anchor` uses prefers the node nearest it, so each row's popover opens by its own button."""
    body = ("    For n In <| rows |> Key <| n |> {\n      Container {\n        Name: row\n        Style { Position: absolute, X: 20, Y: <| n * 100 |>, Width: 100, Height: 40 }\n        Children {\n"
            "          Rect { Name: field, Style { Width: 100, Height: 40, Background: primary } }\n"
            "          Overlay {\n            Name: pop\n            Anchor: field\n            Placement: end\n            Open: true\n            Dismissible: false\n            Children {\n"
            "              Rect { Name: dot, Style { Width: 10, Height: 10, Background: error } }\n            }\n          }\n        }\n      }\n    }\n")
    app, view, vm = opened(tmp_path, body)
    first, second = where(view, "root.row[1].pop.dot"), where(view, "root.row[2].pop.dot")
    assert second[1] - first[1] == 100.0 and first[0] == second[0] == 120.0  # one row apart, each beside its own field


# -- #282: an anchor that is hidden hides the node anchored to it (tess_re leaves the node at the window's corner, drawn and pressable) ------------------

SHOWN = "    Rect { Name: target, Visible: <| show |>, Style { Position: absolute, X: 150, Y: 120, Width: 60, Height: 40, Background: primary } }\n"


def test_an_anchor_hidden_at_load_hides_the_node(tmp_path):
    body = "    Rect { Name: target, Visible: false, Style { Position: absolute, X: 150, Y: 120, Width: 60, Height: 40, Background: primary } }\n" + DOT % ""
    app, view, vm = opened(tmp_path, body)
    assert view.node("root.dot").get("visible") is False


def test_hiding_the_anchor_hides_the_node_at_once_and_showing_it_puts_it_back(tmp_path):
    app, view, vm = opened(tmp_path, SHOWN + DOT % "")
    assert view.node("root.dot").get("visible") is True and where(view) == (204.0, 114.0)
    vm.show.set(False)
    assert view.node("root.dot").get("visible") is False  # in the same step, before any frame can draw it at the corner
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is True and where(view) == (204.0, 114.0)


def test_an_anchor_in_a_hidden_container_hides_the_node(tmp_path):
    body = ("    Container {\n      Name: box\n      Visible: <| show |>\n      Style { Position: absolute, X: 150, Y: 120 }\n      Children {\n"
            "        Rect { Name: target, Style { Width: 60, Height: 40, Background: primary } }\n      }\n    }\n" + DOT % "")
    app, view, vm = opened(tmp_path, body)
    assert view.node("root.dot").get("visible") is True
    vm.show.set(False)
    assert view.node("root.dot").get("visible") is False
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is True and where(view) == (204.0, 114.0)


def test_the_nodes_own_visible_false_wins_when_the_anchor_is_shown_again(tmp_path):
    body = SHOWN + "    Rect { Name: dot, Visible: false, Style { Anchor: target, Placement: top_end, Width: 12, Height: 12, Background: error } }\n"
    app, view, vm = opened(tmp_path, body)
    vm.show.set(False)
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is False


def test_a_node_whose_own_visible_comes_while_the_anchor_is_hidden_stays_hidden(tmp_path):
    body = SHOWN + "    Rect { Name: dot, Visible: <| x > 100 |>, Style { Anchor: target, Placement: top_end, Width: 12, Height: 12, Background: error } }\n"
    app, view, vm = opened(tmp_path, body)
    vm.show.set(False)
    vm.x.set(50)
    vm.x.set(150)  # its own `visible:` goes false and true again while the anchor is hidden
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is False
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.dot").get("visible") is True


def test_a_labelled_control_as_the_anchor_is_hidden_with_its_row(tmp_path):
    body = "    Checkbox { Name: target, Label: ok, Visible: <| show |>, Style { Position: absolute, X: 150, Y: 120 } }\n" + DOT % ""
    app, view, vm = opened(tmp_path, body)
    assert view.node("root.dot").get("visible") is True
    vm.show.set(False)
    assert view.node("root.dot").get("visible") is False


def test_the_node_is_shown_again_when_its_style_stops_saying_anchor_while_the_anchor_is_hidden(tmp_path):
    app, view, vm = opened(tmp_path, SHOWN + DOT % "")
    vm.show.set(False)
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        doc(SHOWN + "    Rect { Name: dot, Style { Width: 12, Height: 12, Background: error } }\n"))
    from tess_ui.spec.watch import ComposedWatcher
    import os
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    stat = view.source.stat()
    os.utime(view.source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    assert watcher.poll() is True
    view.window.advance(50)
    assert view.node("root.dot").get("visible") is True


def test_the_anchor_may_be_in_the_view_that_called_this_one_and_hidden_there(tmp_path):
    files = {"Tag_View.tdl": "---\nTDL: 0.2\nName: Tag\n---\nRect { Style { Anchor: target, Placement: top_end, Width: 12, Height: 12, Background: error } }\n"}
    app, view, vm = opened(tmp_path, SHOWN + "    Tag { Name: tag }\n", files)
    assert view.node("root.tag").get("visible") is True
    vm.show.set(False)
    assert view.node("root.tag").get("visible") is False


# #289: placement or offset with no anchor does nothing, so it is an error at the node (checked on the merged style, where rules and the node meet)

def opened_with_rule(tmp_path, node, rule):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(doc(PLAIN_TARGET + f"    {node}\n"))
    app = App(root=tmp_path, width=400, height=300, stylesheet_spec={"styles": [rule]})
    app.bind(VM)
    view = app.open_view("Main")
    view.window.advance(50)
    return view


DOT_NODE = "Rect { Name: dot, Classes: [badge], Style { %s Width: 12, Height: 12, Background: error } }"


@pytest.mark.parametrize("fields, said", [
    ("Placement: top_end,", "style.placement"),
    ("Offset: [3, 3],", "style.offset"),
    ("Placement: above, Offset: [3, 3],", "style.placement and style.offset"),
])
def test_placement_or_offset_without_an_anchor_is_an_error_naming_the_node(tmp_path, fields, said):
    with pytest.raises(ValueError) as caught:
        opened(tmp_path, TARGET + "    " + (DOT_NODE % fields) + "\n")
    message = str(caught.value)
    assert "root.dot" in message and f"{said} does nothing without style.anchor" in message


def test_a_rule_that_gives_only_the_placement_to_a_node_with_no_anchor_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="does nothing without style.anchor"):
        opened_with_rule(tmp_path, DOT_NODE % "", {"classes": ["badge"], "widget": "Rect", "style": {"placement": "top_end"}})


def test_a_rule_that_gives_only_the_placement_still_works_for_a_node_that_gives_the_anchor(tmp_path):
    view = opened_with_rule(tmp_path, DOT_NODE % "Anchor: target,", {"classes": ["badge"], "widget": "Rect", "style": {"placement": "top_end"}})
    assert where(view) == (204.0, 114.0)


def test_a_node_that_gives_the_placement_still_works_when_a_rule_gives_the_anchor(tmp_path):
    view = opened_with_rule(tmp_path, DOT_NODE % "Placement: top_end,", {"classes": ["badge"], "widget": "Rect", "style": {"anchor": "target"}})
    assert where(view) == (204.0, 114.0)


def test_an_anchor_expression_that_works_out_to_nothing_leaves_the_node_in_the_flow(tmp_path):
    app, view, vm = opened(tmp_path, TARGET + "    " + (DOT_NODE % "Anchor: <| 'target' if show else '' |>, Placement: top_end,") + "\n")
    assert where(view) == (204.0, 114.0)
    vm.show.set(False)
    view.window.advance(50)
    assert view.node("root.dot").get("position") == "relative"
