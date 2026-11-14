"""A sync costs what changed (perf, T-036 C5): `View.reconcile` builds on the side, to keep the window as it was if the new spec is bad, only the nodes that
changed or are new, not the whole window; a bad change still leaves the window exactly as it was."""

import copy

import pytest

import tess_ui.view as view_module
from tess_ui.spec.build import SpecBuildError
from tess_ui.view import View, _copy_spec

SEED = (0x67, 0x50, 0xA4, 0xFF)


def _text(node_id, content="x", **style):
    return {"id": node_id, "kind": "Text", "text": {"content": content, "font_family": "Roboto", "font_size": 14},
            "style": {"foreground": "#000000", "width": 100, "height": 20, **style}}


def _spec(n=30, **changes):
    """A root with a column of `n` boxes, each holding a Text; `changes` maps a text's id to its content."""
    boxes = [{"id": f"box{i}", "kind": "Container", "style": {"width": 100, "height": 20},
              "children": [_text(f"t{i}", changes.get(f"t{i}", "x"))]} for i in range(n)]
    return {"id": "root", "kind": "Container", "style": {"flex_direction": "vertical"},
            "children": [{"id": "list", "kind": "Container", "style": {"flex_direction": "vertical"}, "children": boxes}]}


@pytest.fixture
def builds(monkeypatch):
    """What `build_with` is asked to build: a list of (id, number of children) as it goes."""
    calls = []
    real = view_module.build_with

    def spy(window, node, **kw):
        calls.append((node.get("id"), len(node.get("children") or [])))
        return real(window, node, **kw)

    monkeypatch.setattr(view_module, "build_with", spy)
    return calls


def test_a_sync_with_nothing_changed_builds_nothing(builds):
    view = View(_spec(), theme_seed=SEED)
    builds.clear()
    view.reconcile(_spec())
    assert builds == []


def test_one_changed_node_is_the_only_one_built_on_the_side(builds):
    view = View(_spec(), theme_seed=SEED)
    builds.clear()
    view.reconcile(_spec(t7="changed"))
    assert builds == [("t7", 0)]
    assert view.node("t7").get("text") == "changed"
    assert view.node("t8").get("text") == "x"


def test_a_new_subtree_is_built_on_the_side_whole_and_then_for_real(builds):
    view = View(_spec(2), theme_seed=SEED)
    builds.clear()
    spec = _spec(2)
    spec["children"][0]["children"].append({"id": "extra", "kind": "Container", "children": [_text("extra_text")]})
    view.reconcile(spec)
    assert builds == [("extra", 1), ("extra", 1)]  # the trial, then the node
    assert view.node("extra_text").get("text") == "x"


def test_a_changed_parent_that_lays_its_children_out_as_before_does_not_build_them(builds):
    view = View(_spec(5), theme_seed=SEED)
    builds.clear()
    spec = _spec(5)
    spec["children"][0]["style"]["background"] = "#ff0000"
    view.reconcile(spec)
    assert builds == [("list", 0)]


def test_a_changed_parent_that_lays_its_children_out_differently_builds_them_in_the_new_layout(builds):
    view = View(_spec(5), theme_seed=SEED)
    builds.clear()
    spec = _spec(5)
    spec["children"][0]["style"]["flex_direction"] = "horizontal"
    view.reconcile(spec)
    assert builds == [("list", 0)] + [(f"box{i}", 0) for i in range(5)]


def test_a_node_of_a_kind_that_changed_is_rebuilt_and_checked_whole(builds):
    view = View(_spec(2), theme_seed=SEED)
    builds.clear()
    spec = _spec(2)
    text = spec["children"][0]["children"][1]["children"][0]
    text["kind"] = "Rect"
    text.pop("text")
    text["style"]["background"] = "#ff0000"
    view.reconcile(spec)
    assert ("t1", 0) in builds and view._built.specs["t1"]["kind"] == "Rect"


def _count(node):
    return 1 + sum(_count(child) for child in node.children())


def _snapshot(view):
    return (copy.deepcopy(view._spec), {k: v.get("text") for k, v in view._built.nodes.items() if view._built.specs[k].get("kind") == "Text"},
            sorted(view._built.nodes), _count(view.window.root))


def test_a_bad_change_in_a_changed_node_leaves_the_window_as_it_was():
    view = View(_spec(), theme_seed=SEED)
    before = _snapshot(view)
    spec = _spec(t1="fine")
    spec["children"][0]["children"][20]["children"][0]["style"]["foreground"] = "not a colour"
    with pytest.raises(SpecBuildError, match="invalid style.foreground"):
        view.reconcile(spec)
    assert _snapshot(view) == before  # t1 came first, was fine, and is not applied either


def test_a_bad_new_node_deep_in_a_new_subtree_leaves_the_window_as_it_was():
    view = View(_spec(3), theme_seed=SEED)
    before = _snapshot(view)
    spec = _spec(3)
    spec["children"][0]["children"].append(
        {"id": "extra", "kind": "Container", "children": [{"id": "inner", "kind": "Container", "children": [{"id": "bad", "kind": "NoSuchKind"}]}]})
    with pytest.raises(SpecBuildError, match="unknown kind"):
        view.reconcile(spec)
    assert _snapshot(view) == before
    assert "extra" not in view._built.nodes and "bad" not in view._built.nodes


def test_a_node_without_an_id_is_an_error_and_leaves_the_window_as_it_was():
    view = View(_spec(3), theme_seed=SEED)
    before = _snapshot(view)
    spec = _spec(3)
    spec["children"][0]["children"].append({"kind": "Container"})
    with pytest.raises(SpecBuildError, match="needs an `id:`"):
        view.reconcile(spec)
    assert _snapshot(view) == before


def test_a_changed_node_that_is_bad_among_unchanged_ones_is_found_and_the_next_good_sync_applies():
    view = View(_spec(), theme_seed=SEED)
    bad = _spec()
    bad["children"][0]["children"][5]["children"][0]["style"]["background"] = "nonsense"
    with pytest.raises(SpecBuildError):
        view.reconcile(bad)
    view.reconcile(_spec(t5="now"))
    assert view.node("t5").get("text") == "now"


def test_the_trial_leaves_no_node_behind(monkeypatch):
    view = View(_spec(), theme_seed=SEED)
    trial_roots = []
    real = view_module.build_with

    def spy(window, node, **kw):
        built = real(window, node, **kw)
        if kw["into"] is not view._built:
            trial_roots.append(built)
        return built

    monkeypatch.setattr(view_module, "build_with", spy)
    spec = _spec(t3="a")
    spec["children"][0]["children"].append({"id": "extra", "kind": "Container", "children": [_text("extra_text")]})
    view.reconcile(spec)
    assert len(trial_roots) == 2  # the changed text, and the new box
    assert not any(view_module._alive(node) for node in trial_roots)


def test_the_spec_copy_is_the_deep_copy_it_replaces():
    shared = {"a": [1, 2]}
    original = {"x": shared, "y": shared, "z": [shared, (1, [2])], "n": None, "s": "t", "f": 1.5, "b": True}
    clone = _copy_spec(original, {})
    assert clone == original
    assert clone["x"] is clone["y"] is clone["z"][0] and clone["x"] is not shared  # aliasing survives, nothing is shared with the original
    assert clone["z"][1] == (1, [2]) and clone["z"][1][1] is not original["z"][1][1]


def test_walk_visits_parts_then_children_in_order_like_the_recursion_it_replaces():
    from test_composed import BASE, TEXT, render  # the same composed view the other tests build

    view, vm, _ = render(BASE + "  - widget: Container\n    name: row\n    for: r in rows\n    key: r.id\n    children:\n      - widget: Text\n        name: t\n        text: '{{ r.t }}'\n        typography_role: body_large\n        style: {width: 100, height: 20, foreground: '#000000'}\n"
                         "  - widget: Text\n    name: last\n    text: 'z'\n    " + TEXT + "\n")
    vm.rows.set([{"id": 1, "t": "a"}, {"id": 2, "t": "b"}, {"id": 3, "t": "c"}])

    def reference(inst):
        yield inst
        for sub in inst.parts.values():
            for item in sub:
                yield from reference(item)
        for child in inst.children:
            yield from reference(child)

    root = view.handle.composition.root
    walked = [inst.id for inst in root.walk()]
    assert walked == [inst.id for inst in reference(root)]
    assert len(walked) == len(set(walked)) > 7
