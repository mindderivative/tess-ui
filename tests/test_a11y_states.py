"""#210: the accessibility states tess_re already has -- `expanded`, `selected`, `checked`, `value`, `value_min`, `value_max`, `value_step` -- as `a11y:` fields:
fixed or bound, in a view written either way, cleared with `null`, and refused where a control sets its own."""

import pytest

from tess_ui import Signal, View, ViewModel, a11y
from tess_ui.composed import open_composed
from tess_ui.spec.build import SpecBuildError
from tess_ui.spec.nodes import LoadError, parse_view
from tess_ui.viewmodel import Bindings

SEED = (103, 80, 164, 255)
STATES = ("expanded", "selected", "checked")
NUMBERS = ("value", "value_min", "value_max", "value_step")


def old(a11y_fields, kind="Rect", **extra):
    node = {"id": "n", "kind": kind, "a11y": a11y_fields, "style": {"width": 40, "height": 20, "background": "#112233"}, **extra}
    return View({"id": "root", "kind": "Container", "style": {"width": 100, "height": 100}, "children": [node]}, theme_seed=SEED)


# -- the checker -----------------------------------------------------------------------------------------------------------


def test_the_states_and_numbers_are_checked_and_may_be_cleared():
    assert a11y.check({"expanded": True, "selected": False, "checked": True, "value": 3, "value_min": 0, "value_max": 10, "value_step": 1}) == {
        "expanded": True, "selected": False, "checked": True, "value": 3.0, "value_min": 0.0, "value_max": 10.0, "value_step": 1.0}
    assert a11y.check({"expanded": None, "checked": None, "value": None}) == {"expanded": None, "checked": None, "value": None}
    for name in STATES:
        with pytest.raises(ValueError, match=f"a11y {name} must be true or false"):
            a11y.check({name: "yes"})
    for name in NUMBERS:
        with pytest.raises(ValueError, match=f"a11y {name} must be a number"):
            a11y.check({name: "x"})
        with pytest.raises(ValueError, match=f"a11y {name} must be a number"):
            a11y.check({name: True})
    with pytest.raises(ValueError, match="a11y hidden must be true or false"):
        a11y.check({"hidden": None})  # hidden is one or the other


def test_every_state_is_bindable_and_the_fixed_ones_are_not():
    assert {"checked", "selected", "expanded", "value", "value_min", "value_max", "value_step", "label", "hidden", "level", "set_size", "pos_in_set",
            "pressed", "invalid", "description", "current", "value_now", "value_text", "busy", "focusable"} == set(a11y.BINDABLE)  # the relations name nodes: fixed
    assert "role" not in a11y.BINDABLE and "live" not in a11y.BINDABLE


# -- the old syntax ------------------------------------------------------------------------------------------------------------


def test_a_node_in_the_old_syntax_takes_the_states():
    node = old({"role": "button", "expanded": False, "selected": True, "checked": True, "value": 2, "value_min": 0, "value_max": 5, "value_step": 1}).node("n")
    assert (node.get("expanded"), node.get("selected"), node.get("checked")) == (False, True, True)
    assert (node.get("value"), node.get("value_min"), node.get("value_max"), node.get("value_step")) == (2.0, 0.0, 5.0, 1.0)


def test_a_control_sets_its_own_state_and_says_so():
    with pytest.raises(SpecBuildError, match='widget "n": a Checkbox sets its own checked; `a11y:` can\'t'):
        old({"checked": True}, kind="Checkbox")
    with pytest.raises(SpecBuildError, match="a Slider sets its own value"):
        old({"value": 1}, kind="Slider")


def test_a_bad_state_names_the_widget_and_the_field():
    with pytest.raises(SpecBuildError, match='widget "n": a11y expanded must be true or false'):
        old({"expanded": "open"})
    with pytest.raises(SpecBuildError, match="unknown a11y field.*did you mean"):
        old({"expandd": True})


def test_a_bound_state_follows_its_signal_in_the_old_syntax():
    class VM(ViewModel):
        def __init__(self, view):
            self.open = Signal(False)
            self.pos = Signal(1)
            super().__init__(view)

    view = old({"expanded": "{{ open.get() }}", "value": "{{ pos.get() }}", "value_max": 9})
    vm = VM(view)
    node = view.node("n")
    assert node.get("expanded") is False and node.get("value") == 1.0 and node.get("value_max") == 9.0
    vm.open.set(True)
    vm.pos.set(4)
    assert node.get("expanded") is True and node.get("value") == 4.0
    with pytest.raises(ValueError, match="a11y expanded must be true or false"):
        vm.open.set("maybe")


def test_a_field_dropped_in_a_reload_goes_back_to_unset():
    view = old({"expanded": True, "selected": True, "value": 3})
    node = view.node("n")
    spec = {"id": "root", "kind": "Container", "style": {"width": 100, "height": 100}, "children": [
        {"id": "n", "kind": "Rect", "a11y": {"label": "x"}, "style": {"width": 40, "height": 20, "background": "#112233"}}]}
    view.reconcile(spec)
    assert (node.get("expanded"), node.get("selected"), node.get("value")) == (None, None, None)


# -- the new syntax -----------------------------------------------------------------------------------------------------------


def test_the_loader_takes_the_states_fixed_or_bound_and_names_a_wrong_one():
    node = parse_view("---\nTDL: 0.2\nName: T\n---\nRect { A11y { Expanded: true, Selected: <| on |>, Value: 3, Value_Max: <| top |> } }\n", "T_View.tdl").root
    assert node.a11y["expanded"] is True and node.a11y["value"] == 3
    with pytest.raises(LoadError, match="a11y expanded must be true or false"):
        parse_view("---\nTDL: 0.2\nName: T\n---\nRect { A11y { Expanded: open } }\n", "T_View.tdl")
    parse_view("---\nTDL: 0.2\nName: T\n---\nRect { A11y { Role: <| x |> } }\n", "T_View.tdl")  # a role may be worked out from a view's params (see test_segmented_button)


def test_a_composed_view_keeps_the_states_up_to_date():
    class VM(ViewModel):
        views = "v"

        def __init__(self):
            super().__init__()
            self.open = Signal(False)
            self.pos = Signal(0)

    bindings = Bindings()
    bindings.bind(VM)
    doc = parse_view("---\nTDL: 0.2\nName: T\n---\nRect {\n  Name: v\n  Style { Width: 40, Height: 20, Background: \"#112233\" }\n"
                     "  A11y { Role: button, Expanded: <| open |>, Value: <| pos |>, Value_Min: 0, Value_Max: 10 }\n}\n", "V_View.tdl")
    view = open_composed(doc, bindings, theme_seed=SEED)
    node, vm = view.node("root"), view.handle.viewmodel
    assert (node.get("expanded"), node.get("value"), node.get("value_min"), node.get("value_max")) == (False, 0.0, 0.0, 10.0)
    vm.open.set(True)
    vm.pos.set(7)
    assert node.get("expanded") is True and node.get("value") == 7.0


def test_set_size_and_pos_in_set_are_positive_whole_numbers_a_row_can_bind():
    assert a11y.check({"set_size": 7, "pos_in_set": 3}) == {"set_size": 7, "pos_in_set": 3}
    assert a11y.check({"set_size": None}) == {"set_size": None}
    for bad in (0, -1, 2.5, True):
        with pytest.raises(ValueError, match="positive whole number"):
            a11y.check({"pos_in_set": bad})
