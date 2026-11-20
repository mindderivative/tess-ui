"""`View._validate` builds on the side only what changed. Whatever it skips, a sync must accept and refuse the same specs, with the same message,
as trying the whole new spec (`View.validate_everything`), and a refused one leaves the window as it was."""

import copy

import pytest

from tess_ui.view import View

SEED = (0x67, 0x50, 0xA4, 0xFF)


def _rect(node_id, color="#112233", **extra):
    return {"id": node_id, "kind": "Rect", "style": {"width": 40, "height": 20, "background": color}, **extra}


def _text(node_id, content="hi"):
    return {"id": node_id, "kind": "Text", "text": {"content": content, "font_family": "Roboto", "font_size": 14},
            "style": {"foreground": "#000000", "width": 100, "height": 20}}


def _tree():
    return {"id": "root", "kind": "Container", "style": {"flex_direction": "vertical"},
            "children": [_rect("a"), _text("t"),
                         {"id": "box", "kind": "Container", "style": {"flex_direction": "horizontal"}, "children": [_rect("b"), _rect("c")]}]}


def _edit(spec, change):
    spec = copy.deepcopy(spec)
    change(spec)
    return spec


def _find(spec, node_id):
    if spec["id"] == node_id:
        return spec
    for child in spec.get("children") or []:
        found = _find(child, node_id)
        if found is not None:
            return found
    return None


EDITS = {
    "nothing": lambda s: None,
    "colour": lambda s: _find(s, "b")["style"].update(background="#abcdef", width=44),
    "bad colour": lambda s: _find(s, "c")["style"].update(background="not-a-colour"),
    "bad colour deep, a sibling also changed": lambda s: (_find(s, "b")["style"].update(width=77), _find(s, "c")["style"].update(background="nope")),
    "bad kind added": lambda s: _find(s, "box")["children"].append({"id": "x", "kind": "NoSuchKind"}),
    "node added": lambda s: _find(s, "box")["children"].append(_rect("d")),
    "node removed": lambda s: _find(s, "box")["children"].pop(),
    "reordered": lambda s: _find(s, "box")["children"].reverse(),
    "text changed": lambda s: _find(s, "t")["text"].update(content="bye"),
    "layout of a parent changed": lambda s: _find(s, "box")["style"].update(flex_direction="vertical"),
    "bad layout value": lambda s: _find(s, "box")["style"].update(flex_direction="diagonal"),
    "kind changed": lambda s: _find(s, "a").update(kind="Container", children=[]),
}


def _widths(view):
    out = []
    for node_id in ("a", "b", "c"):
        try:
            out.append(view.node(node_id).get("width"))
        except ValueError:  # the edit removed it
            out.append(None)
    return out


def _outcome(view, spec):
    try:
        view.reconcile(spec)
    except Exception as error:  # noqa: BLE001 - the type and text are what is compared
        return type(error).__name__, str(error)
    return "ok", None


@pytest.mark.parametrize("name", EDITS)
def test_validating_only_what_changed_agrees_with_trying_the_whole_spec(name):
    start = _tree()
    changed = _edit(start, EDITS[name])
    partial, full = View(copy.deepcopy(start), theme_seed=SEED), View(copy.deepcopy(start), theme_seed=SEED)
    full.validate_everything = True
    first = _outcome(partial, copy.deepcopy(changed))
    assert first == _outcome(full, copy.deepcopy(changed))
    if first[0] != "ok":  # refused: nothing of the edit, not even the part before the bad node, is on the screen
        assert _widths(partial) == _widths(View(copy.deepcopy(start), theme_seed=SEED))
    assert _widths(partial) == _widths(full)
    # a second edit on top of whatever the first left
    again = _edit(changed, lambda s: _find(s, "a")["style"].update(width=50))
    assert _outcome(partial, copy.deepcopy(again)) == _outcome(full, copy.deepcopy(again))


def test_a_refused_spec_leaves_the_tree_as_it_was():
    start = _tree()
    view = View(copy.deepcopy(start), theme_seed=SEED)
    before = _widths(view)
    status, _ = _outcome(view, _edit(start, EDITS["bad colour deep, a sibling also changed"]))
    assert status != "ok"
    assert _widths(view) == before
    assert _outcome(view, _edit(start, EDITS["colour"])) == ("ok", None)
