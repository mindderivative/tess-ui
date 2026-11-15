"""0.3.4 (#83): a component's look lives in its stylesheet.

Every built-in fragment of `spec/fragments.py` is structure (`tree`); its look is its `sheet`, `{part id: style}`, whose values may be the component's
`{{ parameters }}`.
"""

import pytest

from tess_ui.spec import expand_components_to_spec
from tess_ui.spec.expand import _parts_of
from tess_ui.spec.fragments import FRAGMENTS

STYLED = sorted(name for name, entry in FRAGMENTS.items() if entry["sheet"])


def _node(spec, node_id):
    stack = [spec]
    while stack:
        node = stack.pop()
        if node.get("id") == node_id:
            return node
        stack.extend(node.get("children") or [])
    raise KeyError(node_id)


def _styles_in(tree):
    if isinstance(tree, dict):
        yield from (["style"] if "style" in tree else [])
        for child in tree.get("children") or []:
            yield from _styles_in(child)


def test_there_is_a_stylesheet_for_most_built_in_components():
    assert len(STYLED) >= 45


@pytest.mark.parametrize("name", STYLED)
def test_a_built_in_stylesheet_names_parts_its_component_has(name):
    assert set(FRAGMENTS[name]["sheet"]) <= _parts_of(FRAGMENTS[name]["tree"])


@pytest.mark.parametrize("name", STYLED)
def test_a_built_in_fragment_keeps_no_style_of_its_own(name):
    assert not list(_styles_in(FRAGMENTS[name]["tree"]))


def test_a_component_is_styled_by_its_stylesheet():
    spec = expand_components_to_spec({"id": "root", "kind": "Container", "children": [
        {"id": "b", "component": "ButtonFilled", "with": {"label": "Go", "width": 120, "height": 40, "corner_radius": 20}}]})
    assert _node(spec, "b")["style"]["background"] == "primary"
    assert _node(spec, "b")["style"]["width"] == 120  # a parameter, filled in the stylesheet
    assert _node(spec, "b.label")["style"]["foreground"] == "on_primary"


def test_a_conditional_in_a_stylesheet_follows_the_parameters(monkeypatch):
    monkeypatch.setitem(FRAGMENTS, "Pick", {"params": ["selected"], "tree": {"id": "root", "kind": "Container", "children": [
        {"id": "label", "kind": "Text", "text": {"content": "A"}}]},
        "sheet": {"label": {"foreground": {"if": "{{ selected }}", "then": "primary", "else": "on_surface_variant"}}}})

    def pick(selected):
        spec = expand_components_to_spec({"id": "root", "kind": "Container", "children": [
            {"id": "t", "component": "Pick", "with": {"selected": selected}}]})
        return _node(spec, "t.label")["style"]["foreground"]

    assert (pick(True), pick(False)) == ("primary", "on_surface_variant")
