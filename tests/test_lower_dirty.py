"""A sync costs what changed (T-056): each composition node keeps what `lower` made of it and its subtree and is marked dirty, with the nodes above it, only when something it read changes. An unchanged node is
the same dict at the next sync, so `View.reconcile`, `extract_images` and the expansion skip it by identity. What must stay true: no stale node after any edit, a view kept up to date this way equals one
lowered from nothing, and equals a window built from scratch."""

import random

import pytest

from tess_ui import Signal, ViewModel
from tess_ui.composed import open_composed
from tess_ui.spec.lower import lower
from tess_ui.spec.nodes import parse_view
from tess_ui.view import View
from tess_ui.viewmodel import Bindings

SEED = (103, 80, 164, 255)
TEXT = "typography_role: body_large\n    style: {width: 100, height: 20, foreground: '#000000'}"


class VM(ViewModel):
    views = ["demo"]

    def __init__(self):
        super().__init__()
        self.title = Signal("Hello")
        self.rows = Signal([{"id": i, "t": f"row {i}"} for i in range(6)])
        self.show = Signal(True)
        self.color = Signal("#6750A4")
        self.label = Signal("a label")


SOURCE = ("name: demo\nwidget: Container\nstyle: {flex_direction: vertical, width: 300, height: 400}\nchildren:\n"
          "  - widget: Text\n    name: head\n    text: '{{ title }}'\n    a11y: {label: '{{ label }}'}\n    " + TEXT + "\n"
          "  - widget: Rect\n    name: swatch\n    style: {width: 40, height: 20, background: '{{ color }}'}\n"
          "  - widget: Container\n    name: list\n    style: {flex_direction: vertical, width: 200, height: 200}\n    children:\n"
          "      - for: r in rows\n        key: r.id\n        widget: Text\n        name: row\n        text: '{{ r.t }}'\n        " + TEXT.replace("\n    ", "\n        ") + "\n"
          "  - if: show\n    widget: Text\n    name: extra\n    text: 'extra'\n    " + TEXT + "\n"
          "  - widget: Container\n    name: still\n    style: {width: 50, height: 50}\n    children:\n"
          "      - {widget: Text, name: s1, text: fixed, typography_role: body_large, style: {width: 40, height: 10, foreground: '#000000'}}\n")


def render():
    doc = parse_view(SOURCE, "Demo_View.yaml")
    bindings = Bindings()
    bindings.bind(VM)
    view = open_composed(doc, bindings, None, theme_seed=SEED)
    return view, view.handle.viewmodel


def everything_dirty(root):
    for inst in root.walk():
        inst._lowered = None


def find(spec, node_id):
    if spec.get("id") == node_id:
        return spec
    for child in spec.get("children") or []:
        found = find(child, node_id)
        if found is not None:
            return found
    return None


def test_an_unchanged_composition_lowers_to_the_same_dicts():
    view, vm = render()
    root = view.handle.composition.root
    assert lower(root) is lower(root)
    assert all(inst._lowered is not None for inst in root.walk())


def test_one_change_makes_dirty_the_nodes_on_the_way_to_it_and_no_others():
    view, vm = render()
    root = view.handle.composition.root
    first = lower(root)
    before = {n["id"]: n for n in _walk(first)}
    vm.color.set("#B3261E")  # the view syncs itself; take the spec it lowered
    second = lower(root)
    after = {n["id"]: n for n in _walk(second)}
    changed = {i for i in before if before[i] is not after.get(i)}
    assert changed == {"root", "root.swatch"}, changed
    assert after["root.still"] is before["root.still"] and after["root.list"] is before["root.list"] and after["root.head"] is before["root.head"]


def _walk(node):
    yield node
    for child in node.get("children") or []:
        yield from _walk(child)


def test_a_changed_signal_reaches_the_window_through_the_dirty_flag_alone():
    view, vm = render()
    vm.title.set("Bye")
    vm.label.set("another label")
    assert view.node("root.head").get("text") == "Bye" and view.node("root.head").get("label") == "another label"
    vm.rows.set([{"id": 1, "t": "one"}, {"id": 9, "t": "nine"}])
    assert [view.node(i).get("text") for i in ("root.list.row[1]", "root.list.row[9]")] == ["one", "nine"]
    vm.show.set(False)
    with pytest.raises(ValueError):
        view.node("root.extra")


EDITS = (
    lambda vm, r: vm.title.set(f"t{r.randrange(5)}"),
    lambda vm, r: vm.color.set(r.choice(["#6750A4", "#B3261E", "#006874"])),
    lambda vm, r: vm.show.set(not vm.show.get()),
    lambda vm, r: vm.label.set(f"label {r.randrange(4)} {{{{ x }}}}" if r.random() < 0.3 else f"label {r.randrange(4)}"),
    lambda vm, r: vm.rows.set([{"id": i, "t": f"r{i}-{r.randrange(3)}"} for i in r.sample(range(8), r.randrange(0, 7))]),
)


@pytest.mark.parametrize("seed", range(8))
def test_after_random_edits_the_kept_lowering_equals_one_from_nothing_and_the_window_equals_a_fresh_build(seed):
    rng = random.Random(seed)
    view, vm = render()
    root = view.handle.composition.root
    for step in range(25):
        rng.choice(EDITS)(vm, rng)
        kept = lower(root)
        snapshot = _frozen(kept)
        everything_dirty(root)
        assert _frozen(lower(root)) == snapshot, f"stale node after step {step}"
        fresh = View(view._lowered()[0], theme_seed=SEED)  # a window built from the same spec from nothing
        for node in _walk(kept):
            live, built = view.node(node["id"]), fresh.node(node["id"])
            for prop in ("text", "fill", "label", "visible", "width", "height"):
                try:
                    expected = built.get(prop)
                except ValueError:  # the property is not one this kind of node has
                    continue
                assert live.get(prop) == expected, (step, node["id"], prop)


def _frozen(node):
    """A node and its subtree as plain data to compare."""
    return {k: (_frozen_list(v) if k == "children" else v) for k, v in node.items()}


def _frozen_list(children):
    return [_frozen(c) for c in children]


def test_undo_of_an_edit_brings_the_old_value_back_not_a_kept_one():
    view, vm = render()
    vm.color.set("#B3261E")
    changed = view.node("root.swatch").get("fill")
    vm.color.set("#6750A4")
    vm.color.set("#B3261E")
    assert view.node("root.swatch").get("fill") == changed
    vm.color.set("#6750A4")
    assert view.node("root.swatch").get("fill") != changed
