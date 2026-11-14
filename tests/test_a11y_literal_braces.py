"""A label or description with `{{` in it is kept (T-056): in a composed view every expression is worked out before the builder sees the spec, so a brace pair left in an `a11y:` label or description is the text
itself (a tree row's label, a param that holds braces), not a binding for the view to wire. It used to be taken for a binding: the view refused it, or on a patch left it unset."""

import pytest

import tess_ui
from tess_ui import Signal
from tess_ui.spec.compose import Composer
from tess_ui.spec.lower import lower
from tess_ui.spec.nodes import parse_view
from tess_ui.view import View

SEED = (0x67, 0x50, 0xA4, 0xFF)


class VM:
    def __init__(self):
        self.label = Signal("hi")
        self.name = Signal("Ada")


def lowered(source, vm=None):
    return lower(Composer({}, vm or VM()).compose(parse_view(source, "T_View.yaml")).root)


VIEW = "widget: Text\ntext: x\nfont_family: Roboto\nfont_size: 14\na11y: {label: '{{ label }}', description: 'note: {{ label }}'}\n"
STYLE = {"foreground": "#000000", "width": 100, "height": 20}


def at(spec):
    """The lowered node as a child of a root, with the style a bare Text needs."""
    return {"id": "root", "kind": "Container", "style": {"width": 200, "height": 100}, "children": [{**spec, "id": "t", "style": STYLE}]}


@pytest.mark.parametrize("text", ["Bar  {{ x }}", "plain {{", "}} and {{", "{{ one }} and {{ two }}", "{{}}"])
def test_a_label_and_a_description_that_hold_a_brace_pair_are_set_on_the_node(text):
    vm = VM()
    vm.label.set(text)
    spec = lowered(VIEW, vm)
    assert spec["a11y"] == {"label": text, "description": f"note: {text}"} and spec["a11y_literal"] is True
    view = View(at(spec), theme_seed=SEED)
    node = view.node("t")
    assert node.get("label") == text
    assert node.get("description") == f"note: {text}"


def test_a_label_that_mixes_text_and_an_expression_is_worked_out_and_follows_the_view_model():
    vm = VM()
    spec = lowered("widget: Text\ntext: x\nfont_family: Roboto\nfont_size: 14\na11y: {label: 'Hello {{ name }}, {{ label }}'}\n", vm)
    assert spec["a11y"]["label"] == "Hello Ada, hi"
    view = View(at(spec), theme_seed=SEED)
    assert view.node("t").get("label") == "Hello Ada, hi"
    vm.name.set("Bo")
    again = lowered("widget: Text\ntext: x\nfont_family: Roboto\nfont_size: 14\na11y: {label: 'Hello {{ name }}, {{ label }}'}\n", vm)
    view.reconcile(at(again))
    assert view.node("t").get("label") == "Hello Bo, hi"


def test_a_patch_keeps_a_label_with_braces_and_changes_it():
    vm = VM()
    vm.label.set("{{ a }}")
    view = View(at(lowered(VIEW, vm)), theme_seed=SEED)
    vm.label.set("{{ b }}")
    view.reconcile(at(lowered(VIEW, vm)))
    assert view.node("t").get("label") == "{{ b }}" and view.node("t").get("description") == "note: {{ b }}"


def test_a_hand_written_spec_still_treats_a_brace_pair_as_a_binding():
    class Model(tess_ui.ViewModel):
        def __init__(self, view):
            self.title = tess_ui.Signal("Inbox")
            super().__init__(view)

    spec = ({"id": "root", "kind": "Container", "style": {"width": 200, "height": 100}, "children": [{"id": "t", "kind": "Text", "text": {"content": "x", "font_family": "Roboto", "font_size": 14}, "style": {"foreground": "#000000", "width": 100, "height": 20}, "a11y": {"label": "{{ title.get() }}"}}]})
    view = View(spec, theme_seed=SEED)
    Model(view)
    assert view.node("t").get("label") == "Inbox"
