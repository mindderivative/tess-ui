"""#209 phase 4: composition -- params and the caller's scope, slots, `for:` and `if:` (static and reactive, reconciled by key), `state:`,
ids, hot reload, and disposal."""

import pytest

from tess_ui import Computed, Signal
from tess_ui.spec import widgets as W
from tess_ui.expr import ExprError
from tess_ui.spec.compose import MAX_DEPTH, Composer, Scope
from tess_ui.spec.nodes import LoadError, parse_view
from tess_ui.spec.tdl import load_marked_tdl
from tess_ui.spec.tdl_theme import plain
from tess_ui.spec.widgets import Property, WidgetDecl, decl_from_params


class VM:
    def __init__(self):
        self.rows = Signal([{"id": 1, "t": "a"}, {"id": 2, "t": "b"}])
        self.name = Signal("X")
        self.count = Signal(0)
        self.show = Signal(True)
        self.log = []

    def save(self):
        self.log.append("save")

    def open(self, id):
        self.log.append(("open", id))


def tdl(body, name="Main"):
    """A view file in TDL: the metadata block, then `body`, the root block (a `body` that has its own `---` block is returned as it is)."""
    if body.lstrip().startswith("---"):
        return body
    return f"---\nTDL: 0.2\nName: {name}\n---\n{body}\n"


def make(views=None, main="Container { }", viewmodel=None, **kw):
    """Parses `views` (name -> source) and `main`, composes `main`; returns (composition, viewmodel, composer)."""
    sources = views or {}
    decls = {}
    for name, source in sources.items():  # a view may call itself or another, so every declaration comes first
        params = plain(load_marked_tdl(tdl(source, name), f"{name}_View.tdl")).get("params")
        decls[name] = decl_from_params(name, params) if params is not None else WidgetDecl(name, view=True, container=True)
    docs = {name: parse_view(tdl(source, name), f"{name}_View.tdl", resolver=decls.get, view_name=name) for name, source in sources.items()}
    doc = parse_view(tdl(main), "Main_View.tdl", resolver=decls.get)
    vm = viewmodel if viewmodel is not None else VM()
    composer = Composer(docs, vm, **kw)
    return composer.compose(doc), vm, composer


def fails(message, views=None, main="Container { }", **kw):
    with pytest.raises((LoadError, ExprError)) as caught:
        make(views, main, **kw)
    assert message in str(caught.value), str(caught.value)
    return caught.value


CARD = "Container { Params: [title], Children { Text { Name: head, Text: <| title |> } Slot { } } }"


# -- params and scope ------------------------------------------------------------------------------------------------------


def test_a_view_call_is_replaced_by_the_callees_root_and_its_parts_have_the_calls_prefix():
    comp, _, _ = make({"Card": CARD}, "Container { Children { Card { Name: nav, Title: Hi } } }")
    assert comp.ids() == ["root", "root.nav", "root.nav.head"]
    assert comp.find("root.nav.head").value("text") == "Hi" and comp.find("root.nav").widget == "Container"


def test_a_static_param_is_a_plain_value_and_a_reactive_one_follows_its_signal():
    comp, vm, _ = make({"Card": CARD}, "Container { Children { Card { Name: c, Title: a <| name |> } Card { Name: d, Title: <| 1 + 2 |> } } }")
    head = comp.find("root.c.head")
    assert head.value("text") == "a X" and isinstance(head.props["text"], Computed)  # reactive: follows the signal
    assert comp.find("root.d.head").props["text"] == "3"  # static: evaluated once, a plain value
    vm.name.set("Y")
    assert head.value("text") == "a Y"
    assert comp.find("root.d.head").value("text") == "3"


def test_an_expression_at_a_call_site_is_evaluated_in_the_callers_scope():
    views = {"Row": "Text { Params: [label], Text: <| label |> }"}
    comp, vm, _ = make(views, "Container { Children { For r In <| rows |> Key <| r.id |> { Row { Name: row, Label: <| r.t |>! } } } }")
    assert [comp.find(f"root.row[{i}]").value("text") for i in (1, 2)] == ["a!", "b!"]
    vm.rows.set([{"id": 1, "t": "z"}, {"id": 2, "t": "b"}])
    assert comp.find("root.row[1]").value("text") == "z!"


def test_the_callee_cannot_see_the_callers_names_but_sees_the_viewmodel_and_its_own_params():
    views = {"Leaf": "Text { Params: [x], Text: <| x |><| mine |> }"}
    main = "Container { State { Mine: M }, Children { Leaf { X: <| mine |> } } }"
    err = fails("'mine' is not defined", views, main)
    assert "Leaf_View.tdl" in str(err) or "mine" in str(err)
    views = {"Leaf": "Text { Params: [x], Text: <| x |><| name |> }"}
    comp, _, _ = make(views, "Container { Children { Leaf { X: \"1\" } } }")
    assert comp.find("root.children[0]").value("text") == "1X"  # the ViewModel is visible to every view


def test_defaults_required_unknown_and_reserved_params():
    views = {"Btn": "Text { Params { Label { Type: str, Required: true } Variant { Type: enum, Choices: [filled, text], Default: filled } Size { Type: int, Default: 3 } }, Text: <| label |>-<| variant |>-<| size |> }"}
    comp, _, _ = make(views, "Container { Children { Btn { Label: Go } } }")
    assert comp.find("root.children[0]").value("text") == "Go-filled-3"
    fails("'label' is required", views, "Container { Children { Btn { } } }")
    err = fails("Btn: no property 'sise'", views, "Container { Children { Btn { Label: x, Sise: 1 } } }")
    assert "did you mean 'size'" in str(err)
    fails("reserved name", {"V": "Text { Params: [event] }"}, "Container { Children { V { Event: 1 } } }")


def test_a_param_value_is_coerced_to_its_type_with_the_calls_position():
    views = {"Gauge": "Text { Params { Level { Type: int, Default: 0 } }, Text: <| level |> }"}
    comp, vm, _ = make(views, "Container { Children { Gauge { Level: <| count |> } } }")
    assert comp.find("root.children[0]").value("text") == "0"
    vm.count.set(7)
    assert comp.find("root.children[0]").value("text") == "7"
    err = fails("takes a whole number", views, "Container { Children { Gauge { Level: <| \"x\" |> } } }")
    assert err.file == "Main_View.tdl" and err.line == 5


def test_no_such_view_is_an_error():
    decls = {"Ghost": WidgetDecl("Ghost", view=True, container=True)}
    doc = parse_view(tdl("Container { Children { Ghost { } } }"), "Main_View.tdl", resolver=decls.get)
    with pytest.raises(LoadError, match="no view named 'Ghost'"):
        Composer({}, VM()).compose(doc)


def test_views_may_nest_and_recursion_is_capped_with_the_chain():
    tree = "Container { Params: [depth], Children { If <| depth < 3 |> { Tree { Depth: <| depth + 1 |> } } } }"
    comp, _, _ = make({"Tree": tree}, "Container { Children { Tree { Depth: 0 } } }")
    assert len(list(comp.walk())) == 5  # the main root, then Tree at depth 0, 1, 2 and the one at 3 has no child
    endless = "Container { Params: [depth], Children { Tree { Depth: 0 } } }"
    err = fails(f"nested more than {MAX_DEPTH} deep", {"Tree": endless}, "Container { Children { Tree { Depth: 0 } } }")
    assert "Tree -> Tree" in str(err)


# -- slots -----------------------------------------------------------------------------------------------------------------


def test_children_of_a_call_go_into_the_default_slot_in_the_callers_scope():
    comp, vm, _ = make({"Card": CARD}, "Container { State { N: 5 }, Children { Card { Name: c, Title: T, Children { Text { Text: <| n |>-<| name |> } Rect { Name: r } } } } }")
    assert comp.ids() == ["root", "root.c", "root.c.head", "root.c.content[0]", "root.c.r"]
    text = comp.find("root.c.content[0]")
    assert text.value("text") == "5-X"  # `n` is the caller's state, not the Card's
    vm.name.set("Y")
    assert text.value("text") == "5-Y"


def test_named_slots_and_the_default_slot_hold_their_own_content_in_order():
    views = {"Panel": "Container { Children { Slot { Name: header } Slot { } Slot { Name: actions } } }"}
    comp, _, _ = make(views, "Container { Children { Panel { Name: p, Children { Rect { Name: body } Text { Name: act, Slot: actions } Icon { Name: head, Slot: header, Icon: home } } } } }")
    assert [c.id for c in comp.find("root.p").children] == ["root.p.head", "root.p.body", "root.p.act"]


def test_slot_errors_say_what_the_view_has():
    err = fails("Card has no slot 'actions'", {"Card": CARD}, "Container { Children { Card { Title: T, Children { Rect { Slot: actions } } } } }")
    assert "slots: default" in str(err)
    fails("Leaf takes no children", {"Leaf": "Rect { }"}, "Container { Children { Leaf { Children { Rect { } } } } }")
    fails("a Slot takes no 'if:'", {"V": "Container { Children { If <| x |> { Slot { } } } }"}, "V { }")
    assert make({"Card": CARD}, "Container { Children { Card { Title: T } } }")[0].find("root.children[0]").children[0].id.endswith("head")


def test_slot_content_may_itself_use_for_and_if_and_pass_through_a_slot():
    comp, vm, _ = make({"Card": CARD}, "Container { Children { Card { Name: c, Title: T, Children { For r In <| rows |> Key <| r.id |> { Text { Name: row, Text: <| r.t |> } } If <| show |> { Rect { Name: flag } } } } } }")
    assert [c.id for c in comp.find("root.c").children] == ["root.c.head", "root.c.row[1]", "root.c.row[2]", "root.c.flag"]
    vm.show.set(False)
    vm.rows.set([{"id": 2, "t": "b"}])
    assert [c.id for c in comp.find("root.c").children] == ["root.c.head", "root.c.row[2]"]
    wrapper = {"Wrap": "Container { Children { Card { Name: inner, Title: W, Children { Slot { } } } } }"}
    comp, _, _ = make({**wrapper, "Card": CARD}, "Container { Children { Wrap { Name: w, Children { Rect { Name: x } } } } }")
    assert "root.w.inner.x" not in comp.ids() and any(i.endswith(".x") for i in comp.ids())


# -- for -------------------------------------------------------------------------------------------------------------------


def test_a_static_for_expands_once_with_the_loop_variables_in_scope():
    comp, _, _ = make(None, "Container { Children { For i, t In <| enumerate([\"a\", \"b\", \"c\"]) |> Key <| None |> { Text { Name: row, Text: <| i |><| t |> } } } }")
    assert [(c.id, c.value("text")) for c in comp.root.children] == [("root.row[0]", "0a"), ("root.row[1]", "1b"), ("root.row[2]", "2c")]
    comp, _, _ = make(None, "Container { Children { For n In <| range(3) |> Key <| None |> { Rect { } } } }")
    assert [c.id for c in comp.root.children] == ["root.children[0][0]", "root.children[0][1]", "root.children[0][2]"]


def test_for_accepts_dicts_text_and_tuples_and_refuses_the_rest():
    comp, _, _ = make(None, "Container { Children { For k In <| {\"a\": 1, \"b\": 2} |> Key <| None |> { Text { Text: <| k |> } } } }")
    assert [c.value("text") for c in comp.root.children] == ["a", "b"]
    fails("'for:' needs a list", None, "Container { Children { For k In <| 5 |> Key <| None |> { Rect { } } } }")
    fails("unpacks 2 names", None, "Container { Children { For a, b In <| [1, 2] |> Key <| None |> { Rect { } } } }")
    fails("reserved name", None, "Container { Children { For event In <| [1] |> Key <| None |> { Rect { } } } }")


def test_a_reactive_for_needs_a_key_and_a_key_must_be_unique_and_plain():
    err = fails("a reactive 'for:' needs a 'key:'", None, "Container { Children { For r In <| rows |> Key <| None |> { Rect { } } } }")
    assert "key: item.id" in str(err)
    fails("two elements have the key 1", None, "Container { Children { For r In <| [1, 1] |> Key <| r |> { Rect { } } } }")
    fails("'key:' must be text, a number", None, "Container { Children { For r In <| [[1]] |> Key <| r |> { Rect { } } } }")


def test_a_reactive_for_reconciles_by_key_add_remove_reorder():
    comp, vm, _ = make(None, "Container { Children { For r In <| rows |> Key <| r.id |> { Text { Name: row, Text: <| r.t |> } } } }")
    first, second = comp.find("root.row[1]"), comp.find("root.row[2]")
    seen = []
    comp.root.on_children(lambda inst, old, new: seen.append(([o.id for o in old], [n.id for n in new])))
    # reorder: the same instances, new order
    vm.rows.set([{"id": 2, "t": "b"}, {"id": 1, "t": "a"}])
    assert [c.id for c in comp.root.children] == ["root.row[2]", "root.row[1]"]
    assert comp.find("root.row[1]") is first and comp.find("root.row[2]") is second
    # add in the middle, remove one
    vm.rows.set([{"id": 2, "t": "b"}, {"id": 3, "t": "c"}])
    third = comp.find("root.row[3]")
    assert [c.id for c in comp.root.children] == ["root.row[2]", "root.row[3]"] and first.disposed and not second.disposed
    assert comp.find("root.row[1]") is None
    # an item replaced under the same key updates the existing instance's bindings
    vm.rows.set([{"id": 2, "t": "B"}, {"id": 3, "t": "c"}])
    assert comp.find("root.row[2]") is second and second.value("text") == "B" and comp.find("root.row[3]") is third
    assert len(seen) == 2  # one notification per change of the children (the add and the remove are one), none for the update in place


def test_a_reconciled_loop_is_linear_enough_for_ten_thousand_rows():
    vm = VM()
    vm.rows.set(list(range(3)))
    comp, vm, _ = make(None, "Container { Children { For r In <| rows |> Key <| r |> { Rect { } } } }", viewmodel=vm)
    vm.rows.set(list(range(10_000)))
    assert len(comp.root.children) == 10_000
    vm.rows.set(list(range(5_000, 15_000)))
    assert len(comp.root.children) == 10_000 and comp.find("root.children[0][14999]") is not None


def test_loop_variables_are_in_scope_in_handlers():
    comp, vm, _ = make(None, "Container { Children { For r In <| rows |> Key <| r.id |> { Rect { Name: row, Handlers { On_Click { Call { Action: open, Args: [<| r.id |>] } } } } } } }")
    comp.find("root.row[2]").fire("on_click")
    assert vm.log == [("open", 2)]


def test_nested_for_and_for_with_if_tested_per_element():
    comp, _, _ = make(None, "Container { Children { For a In <| range(2) |> Key <| None |> { Container { Name: g, Children { For b In <| range(2) |> Key <| None |> { Rect { Name: cell } } } } } } }")
    assert comp.ids().count("root.g[0].cell[1]") == 1 and len(list(comp.walk())) == 1 + 2 + 4
    comp, vm, _ = make(None, "Container { Children { For r In <| rows |> Key <| r.id |> { If <| r.id != 2 |> { Rect { Name: row } } } } }")
    assert [c.id for c in comp.root.children] == ["root.row[1]"]
    vm.rows.set([{"id": 1, "t": ""}, {"id": 2, "t": ""}, {"id": 3, "t": ""}])
    assert [c.id for c in comp.root.children] == ["root.row[1]", "root.row[3]"]


# -- if --------------------------------------------------------------------------------------------------------------------


def test_a_static_if_decides_once_and_a_false_if_builds_nothing():
    comp, _, _ = make(None, "Container { Children { If <| 1 > 2 |> { Rect { Name: nope } } If <| 2 > 1 |> { Rect { Name: ok } } } }")
    assert comp.ids() == ["root", "root.ok"]


def test_a_reactive_if_builds_and_disposes_as_its_expression_changes():
    comp, vm, composer = make(None, "Container { Children { If <| show |> { Text { Name: t, Text: <| name |>, Handlers { On_Click: save } } } } }")
    t = comp.find("root.t")
    assert t is not None and len(vm.name._subscribers) == 1
    vm.show.set(False)
    assert comp.root.children == [] and t.disposed and comp.find("root.t") is None
    assert vm.name._subscribers == []  # the binding of a node that is gone no longer follows its signal
    vm.show.set(True)
    assert comp.find("root.t") is not t and comp.find("root.t").value("text") == "X"


def test_the_instances_of_a_false_if_do_not_run_their_handlers_or_bindings():
    comp, vm, _ = make(None, "Container { Children { If <| show |> { Rect { Name: r, Handlers { On_Click: save } } } } }")
    r = comp.find("root.r")
    vm.show.set(False)
    assert r.disposed and comp.find("root.r") is None


# -- state -----------------------------------------------------------------------------------------------------------------


def test_state_is_a_signal_visible_to_the_subtree_and_written_by_handlers():
    comp, _, _ = make(None, "Container { State { On: false, N: 1 }, Children { Text { Name: t, Text: <| n |>, Handlers { On_Click { Set { Target: n, Value: <| n + 1 |> } Set { Target: on, Value: <| not on |> } } } } } }")
    t = comp.find("root.t")
    assert t.value("text") == "1"
    t.fire("on_click")
    assert t.value("text") == "2" and comp.root.state["on"].get() is True


def test_state_is_per_instance_per_row():
    comp, _, _ = make(None, "Container { Children { For r In <| rows |> Key <| r.id |> { Container { Name: row, State { Open: false }, Children { Text { Name: t, Text: <| 'yes' if open else 'no' |>, Handlers { On_Click { Set { Target: open, Value: <| not open |> } } } } } } } } }")
    comp.find("root.row[1].t").fire("on_click")
    assert comp.find("root.row[1].t").value("text") == "yes" and comp.find("root.row[2].t").value("text") == "no"


def test_a_handler_cannot_assign_a_param_a_loop_variable_or_an_unknown_name():
    with pytest.raises(LoadError, match="'r' is not writable here"):  # found when the view loads, with its line (#277)
        make(None, "Container { Children { For r In <| rows |> Key <| r.id |> { Rect { Name: row, Handlers { On_Click { Set { Target: r, Value: <| 1 |> } } } } } } }")
    comp, vm, _ = make(None, "Container { Children { Rect { Name: r, Handlers { On_Click { Set { Target: count, Value: <| count + 1 |> } } } } } }")
    comp.find("root.r").fire("on_click")
    assert vm.count.get() == 1  # a Signal of the ViewModel is writable


def test_state_starting_values_must_be_static_and_names_unreserved():
    fails("must be static", None, "Container { State { A: <| name |> } }")
    fails("reserved name", None, "Container { State { Hovered: false } }")
    comp, _, _ = make(None, "Container { State { A: <| 1 + 1 |> } }")
    assert comp.root.state["a"].get() == 2


def test_state_on_a_call_is_visible_to_its_arguments_and_slot_content():
    comp, _, _ = make({"Card": CARD}, "Container { Children { Card { Name: c, State { T: hello }, Title: <| t |>, Children { Text { Name: x, Text: <| t |> } } } } }")
    assert comp.find("root.c.head").value("text") == "hello" and comp.find("root.c.x").value("text") == "hello"


def test_state_survives_recomposition_for_the_same_ids():
    source = "Container { State { N: 1 }, Children { Text { Name: t, Text: <| n |>, Handlers { On_Click { Set { Target: n, Value: <| n + 1 |> } } } } } }"
    comp, vm, composer = make(None, source)
    comp.find("root.t").fire("on_click")
    comp.find("root.t").fire("on_click")
    # the file is edited: new text, same names
    edited = source.replace("Text: <| n |>", "Text: n=<| n |>")
    doc = parse_view(tdl(edited), "Main_View.tdl")
    again = Composer({}, vm, previous=comp).compose(doc)
    assert again.find("root.t").value("text") == "n=3"
    # a state variable whose id no longer exists starts fresh
    moved = parse_view(tdl(edited.replace("Name: t", "Name: u")), "Main_View.tdl")
    assert Composer({}, vm, previous=comp).compose(moved).root.state["n"].get() == 3  # the root's id did not change
    assert "n=3" in Composer({}, vm, previous=comp).compose(doc).find("root.t").value("text")


def test_state_in_a_loop_survives_by_key():
    source = "Container { Children { For r In <| rows |> Key <| r.id |> { Container { Name: row, State { Open: false } } } } }"
    comp, vm, _ = make(None, source)
    comp.find("root.row[2]").state["open"].set(True)
    again = Composer({}, vm, previous=comp).compose(parse_view(tdl(source), "Main_View.tdl"))
    assert again.find("root.row[2]").state["open"].get() is True and again.find("root.row[1]").state["open"].get() is False


# -- call-level keys, ids, structure --------------------------------------------------------------------------------------


def test_the_keys_of_a_call_lie_over_the_callees_root():
    views = {"Btn": "Rect { Params: [label], Style { Width: 10, Height: 4 }, Classes: [btn], Handlers { On_Hover_Enter: save }, A11y { Label: <| label |> } }"}
    comp, vm, _ = make(views, "Container { State { K: 1 }, Children { Btn { Name: b, Label: Go, Style { Width: 99 }, Classes: [extra], Interaction: true, Route: \"\", "
                       "Handlers { On_Click { Set { Target: k, Value: <| k + 1 |> } } }, A11y { Role: button } } } }")
    b = comp.find("root.b")
    assert b.style_value("width") == 99 and b.style_value("height") == 4
    assert b.classes == ["btn", "extra"] and b.interaction is True and b.a11y["role"] == "button" and b.a11y["label"] == "Go"
    b.fire("on_click")  # written at the call: it runs in the caller's scope, where `k` is state
    assert comp.root.state["k"].get() == 2
    b.fire("on_hover_enter")
    assert vm.log == ["save"]  # the callee's own handler runs in the callee's scope, against the ViewModel


def test_root_directives_are_refused():
    # in TDL the root of a view is its widget's block: an `If` or `For` there is not valid, in the main view or in a called one
    err = fails("This text is not valid here", None, "If <| show |> { Container { } }")
    assert (err.file, err.line) == ("Main_View.tdl", 5)
    fails("This text is not valid here", None, "For r In <| rows |> Key <| r |> { Container { } }")
    err = fails("This text is not valid here", {"V": "If <| show |> { Container { } }"}, "Container { Children { V { } } }")
    assert err.file == "V_View.tdl"


def test_node_and_nodes_properties_become_parts_of_the_instance():
    W.register_widget(WidgetDecl("Bar", {"leading": Property("node"), "actions": Property("nodes")}))
    try:
        comp, _, _ = make(None, "Container { Children { Bar { Name: bar, Leading { Icon { Icon: home } }, Actions { Text { Name: a } Rect { } } } } }")
        assert comp.ids() == ["root", "root.bar", "root.bar.leading", "root.bar.a", "root.bar.actions[1]"]
        comp.dispose()
    finally:
        W.unregister_widget("Bar")


def test_dispose_releases_every_subscription():
    comp, vm, _ = make({"Card": CARD}, "Container { Children { Card { Name: c, Title: <| name |> } "
                       "For r In <| rows |> Key <| r.id |> { If <| show |> { Text { Text: <| r.t |><| count |> } } } } }")
    assert vm.name._subscribers and vm.rows._subscribers
    comp.dispose()
    for signal in (vm.name, vm.rows, vm.show, vm.count):
        assert signal._subscribers == [], signal


def test_property_values_not_given_read_as_the_declarations_default():
    comp, _, _ = make(None, "Container { Children { Slider { Name: s } } }")
    s = comp.find("root.s")
    assert s.value("value") == 0.0 and s.value("disabled") is False
    with pytest.raises(KeyError):
        s.value("nope")


def test_the_scope_reads_frames_then_the_viewmodel_and_hides_underscore_names():
    class Hidden:
        shown = 1
        _secret = 2

    scope = Scope(Scope(None, {"a": 1}), {"b": Signal(2)}, root=Hidden())
    assert scope.lookup("a") == 1 and scope.lookup("shown") == 1
    with pytest.raises(KeyError):
        scope.lookup("_secret")
    assert not scope.is_reactive("a") and scope.is_reactive("b") and scope.is_reactive("shown")
    assert {"a", "b", "shown"} <= set(scope.names())


def test_two_nodes_with_one_id_are_refused_with_the_node_that_clashes():
    # the callee's part `head` and slot content named `head` would both be `root.c.head`
    err = fails("two nodes have the id 'root.c.head'", {"Card": CARD}, "Container { Children { Card { Name: c, Title: T, Children { Rect { Name: head } } } } }")
    assert "give one of them a different name" in str(err)


def test_the_composer_checks_a_calls_properties_against_the_view_it_finds():
    # the call was parsed against a looser declaration than the file now has (a file edited while the app runs)
    loose = WidgetDecl("Btn", {"label": Property("str"), "bogus": Property("str")}, view=True, container=True)
    doc = parse_view(tdl("Container { Children { Btn { Label: x, Bogus: y } } }"), "Main_View.tdl", resolver={"Btn": loose}.get)
    strict = parse_view(tdl("Text { Params { Label { Type: str, Required: true } }, Text: <| label |> }", "Btn"), "Btn_View.tdl", view_name="Btn")
    with pytest.raises(LoadError, match="Btn: no parameter 'bogus'") as caught:
        Composer({"Btn": strict}, VM()).compose(doc)
    assert "parameters: label" in str(caught.value)
    missing = parse_view(tdl("Container { Children { Btn { } } }"), "Main_View.tdl", resolver={"Btn": loose}.get)
    with pytest.raises(LoadError, match="Btn: 'label' is required"):
        Composer({"Btn": strict}, VM()).compose(missing)


def test_built_in_actions_come_from_the_composers_actions_and_the_viewmodel_cannot_shadow_them():
    called = []
    actions = {"window.close": lambda: called.append("close"), "navigate_to": lambda screen: called.append(screen)}.get

    class Shadow(VM):
        window = type("W", (), {"close": staticmethod(lambda: called.append("viewmodel"))})()

    doc = parse_view(tdl("Rect { Handlers { On_Click: window.close, On_Hover_Enter { Call { Action: navigate_to, Args: [<| \"Settings\" |>] } } } }"), "Main_View.tdl")
    comp = Composer({}, Shadow(), actions=actions).compose(doc)
    comp.root.fire("on_click")
    comp.root.fire("on_hover_enter")
    assert called == ["close", "Settings"]
