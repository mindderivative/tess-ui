"""The form's tooltips: a row's doc is the tooltip of its LABEL only (not of the row, which also holds the control and the reset button), one tooltip shows at a time, and
it goes when the pointer leaves."""

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


def row_parts(w):
    """(row id, row doc, label node, the focusable control node) for each form row that has a doc."""
    view = w.built.view
    found = {}
    for inst in view.handle.composition.walk():
        if ".form_item[" in inst.id:
            key = inst.id.split(".form_item[")[1].split("#")[0]
            found.setdefault(key, {}).setdefault(inst.name, inst)
    docs = {item["id"]: item["doc"] for item in w.vm.form_items.get() if item["type"] == "row"}
    for key, parts in found.items():
        if docs.get(key) and "label" in parts and "row" in parts:
            yield key, docs[key], parts


def point(view, inst):
    node = view.node(inst.id)
    return node.get("layout_x") + 4, node.get("layout_y") + 4


def run(view, ms):
    for _ in range(ms // 16 + 1):
        view.window.advance(16)


def tip_texts(view):
    return [t.get("text") for layer, _ in view._tips.values() for t in layer.children()]


def test_the_label_shows_its_keys_doc_and_nothing_else_does(w):
    view = w.built.view
    rows = list(row_parts(w))
    assert len(rows) >= 3
    key, doc, parts = rows[0]
    assert not parts["row"].tooltip, "the row itself must not carry the doc: it covers the control and the reset button"
    x, y = point(view, parts["label"])
    view.window.simulate("pointer_move", x=x, y=y)
    run(view, 700)
    assert tip_texts(view) == [doc]
    # onto another row's label: the first tooltip is gone, the second is shown, never both
    key2, doc2, parts2 = rows[1]
    x, y = point(view, parts2["label"])
    view.window.simulate("pointer_move", x=x, y=y)
    run(view, 700)
    assert tip_texts(view) == [doc2]
    # off every row: nothing stays
    view.window.simulate("pointer_move", x=2, y=2)
    run(view, 1000)
    assert tip_texts(view) == []
