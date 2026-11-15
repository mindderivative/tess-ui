"""#277: what a view may write back, and what it keeps. The four questions of the issue, each answered by running the code:

1. which names a handler may assign (`state:` and a `model: true` param, never a plain param, a loop variable or a ViewModel's Computed or attribute);
2. what a model property does when it is not given one bare reference to a writable Signal (one-way: the user's edit stays on screen until the value next changes);
3. what a `state:` keeps across a recomposition (the user's value, over an edited starting value), against a ViewModel Signal (untouched);
4. which of these the pages say (`tests/test_docs_two_way.py` is not needed: the pages are read by `test_docs_no_history` and the build).
"""

import pytest

from tess_ui import Computed, Signal, ViewModel
from tess_ui.composed import open_composed
from tess_ui.spec.compose import Composer
from tess_ui.spec.nodes import LoadError, parse_view
from tess_ui.spec.tdl import load_marked_tdl
from tess_ui.spec.tdl_theme import plain
from tess_ui.spec.widgets import WidgetDecl, decl_from_params
from tess_ui.viewmodel import Bindings

from test_compose import VM

SEED = (103, 80, 164, 255)
STYLE = 'Style { Width: 24, Height: 24, Background: "#6750A4" }'
#: A view `V` with a model param `m` and a plain param `p`; its text node runs `%s` when clicked.
CALL = ("Container {\n  Params {\n    M { Type: int, Default: 0, Model: true }\n    P { Type: int, Default: 0 }\n  }\n  Children {\n"
        "    Text { Name: t, Text: <| m |>, Handlers { On_Click { %s } } }\n  }\n}\n")
SET_M_9 = "Set { Target: m, Value: <| 9 |> }"


def tdl(root, name="Main"):
    """The file text of the view `name` whose root block is `root`."""
    return f"---\nTDL: 0.2\nName: {name}\n---\n{root}"


def container(*children, state="", name=None):
    """A Container (TDL text) holding `children`, one block each; `state` is the body of its `State { }` (`N: 1`)."""
    lines = (f"  Name: {name}\n" if name else "") + (f"  State {{ {state} }}\n" if state else "")
    return "Container {\n" + lines + "  Children {\n" + "".join(f"    {child}\n" for child in children) + "  }\n}\n"


def click(*steps, name="t", text="x", wrap=None):
    """A Text node that runs `steps` (the TDL of `Set` or `Call` blocks) on a click, inside `wrap` (a `For` head) when there is one."""
    node = f"Text {{ Name: {name}, Text: {text}, Handlers {{ On_Click {{ {' '.join(steps)} }} }} }}"
    return f"{wrap} {{ {node} }}" if wrap else node


def set_(target, value):
    return f"Set {{ Target: {target}, Value: <| {value} |> }}"


FOR_ROWS = "For r In <| rows |> Key <| r.id |>"


def make(views=None, main="Container { }", viewmodel=None, **kw):
    """Parses `views` (name -> TDL root block) and `main`, composes `main`; returns (composition, viewmodel, composer)."""
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


class Flags(ViewModel):
    views = "demo"

    def __init__(self):
        super().__init__()
        self.done = Signal(False)
        self.inverse = Computed(lambda: not self.done.get())
        self.plain = False
        self.rows = Signal([1, 2])


# -- 1. what a handler may assign -------------------------------------------------------------------------------------------------------


def test_a_handler_writes_a_state_name():
    comp, _, _ = make(None, container(click(set_("s", 2)), state="S: 1"))
    comp.find("root.t").fire("on_click")
    assert comp.root.state["s"].get() == 2


@pytest.mark.parametrize("setup", ["P: 3", "P: <| count |>"])
def test_a_handler_cannot_write_a_plain_param_and_is_told_where_at_load(setup):
    with pytest.raises(LoadError, match="V_View.tdl:11:\\d+: error: 'p' is not writable here"):
        make({"V": CALL % set_("p", 9)}, container(f"V {{ Name: v, {setup} }}"))


def test_a_handler_cannot_write_a_loop_variable():
    with pytest.raises(LoadError, match="Main_View.tdl:7:\\d+: error: 'r' is not writable here"):
        make(None, container(click(set_("r", 1), wrap=FOR_ROWS)))


def test_a_handler_cannot_write_a_viewmodel_attribute_that_is_not_a_signal():
    vm = VM()
    vm.plain = 3
    with pytest.raises(LoadError, match="'plain' is not writable here"):
        make(None, container(click(set_("plain", 4))), viewmodel=vm)


def test_a_handler_cannot_write_a_computed():
    vm = VM()
    vm.shown = Computed(lambda: vm.count.get() + 1)
    with pytest.raises(LoadError, match="'shown' is not writable here"):
        make(None, container(click(set_("shown", 4))), viewmodel=vm)


def test_a_misspelt_name_is_found_at_load_and_the_writable_names_are_offered():
    with pytest.raises(LoadError, match="'cuont' is not writable here.*count"):
        make(None, container(click(set_("cuont", "cuont + 1"))))


def test_a_model_param_is_writable_by_the_view_that_declares_it():
    comp, vm, _ = make({"V": CALL % SET_M_9}, container("V { Name: v, M: 3 }"))
    comp.find("root.v.t").fire("on_click")
    assert comp.find("root.v.t").value("text") == "9"


# -- 2. a model param, by what the caller gives it -----------------------------------------------------------------------------------------


def test_a_bare_viewmodel_signal_is_shared_so_the_views_write_reaches_the_caller():
    comp, vm, _ = make({"V": CALL % SET_M_9}, container("V { Name: v, M: <| count |> }"))
    comp.find("root.v.t").fire("on_click")
    assert vm.count.get() == 9


def test_a_bare_state_name_is_shared_the_same_way():
    comp, vm, _ = make({"V": CALL % SET_M_9}, container("V { Name: v, M: <| s |> }", state="S: 5"))
    comp.find("root.v.t").fire("on_click")
    assert comp.root.state["s"].get() == 9


def test_the_signal_passes_through_a_view_that_passes_it_on():
    out = "Container {\n  Params { Q { Type: int, Default: 0, Model: true } }\n  Children {\n    V { Name: inner, M: <| q |> }\n  }\n}\n"
    comp, vm, _ = make({"V": CALL % SET_M_9, "Out": out}, container("Out { Name: o, Q: <| count |> }"))
    comp.find("root.o.inner.t").fire("on_click")
    assert vm.count.get() == 9


def test_an_expression_gives_the_view_a_copy_that_holds_its_write_until_the_expression_changes():
    comp, vm, _ = make({"V": CALL % SET_M_9}, container("V { Name: v, M: <| count + 1 |> }"))
    text = lambda: comp.find("root.v.t").value("text")  # noqa: E731
    assert text() == "1"
    comp.find("root.v.t").fire("on_click")
    assert text() == "9" and vm.count.get() == 0  # the caller's value was not written
    vm.count.set(5)
    assert text() == "6"  # the expression changed, so the copy follows it again


def test_a_write_stays_when_the_expression_is_set_to_the_value_it_has():
    comp, vm, _ = make({"V": CALL % SET_M_9}, container("V { Name: v, M: <| count + 1 |> }"))
    comp.find("root.v.t").fire("on_click")
    vm.count.set(0)  # no change
    assert comp.find("root.v.t").value("text") == "9"


def test_a_literal_or_nothing_gives_the_view_its_own_value():
    for call in ("V { Name: v, M: 3 }", "V { Name: v }"):
        comp, vm, _ = make({"V": CALL % SET_M_9}, container(call))
        comp.find("root.v.t").fire("on_click")
        assert comp.find("root.v.t").value("text") == "9" and vm.count.get() == 0


def test_a_param_that_is_not_a_model_follows_its_expression_and_is_not_written():
    view = "Text {\n  Params { P { Type: int, Default: 0 } }\n  Text: <| p |>\n}\n"
    comp, vm, _ = make({"V": view}, container("V { Name: v, P: <| count |> }"))
    vm.count.set(4)
    assert comp.find("root.v").value("text") == "4"


# -- 2b. a built-in model property, by what it is given ---------------------------------------------------------------------------------

BASE = "Container {\n  Name: demo\n  Style { Flex_Direction: vertical, Width: 300, Height: 300 }\n  Children {\n"


def render(children, vmcls=Flags):
    doc = parse_view(tdl(BASE + "".join(f"    {child}\n" for child in children) + "  }\n}\n", "demo"), "Demo_View.tdl")
    bindings = Bindings()
    bindings.bind(vmcls)
    view = open_composed(doc, bindings, None, theme_seed=SEED)
    return view, view.handle.viewmodel, bindings


def _checkbox(expr, vmcls=Flags):
    view, vm, _ = render([f"Checkbox {{ Name: c, Checked: {expr}, {STYLE} }}"], vmcls=vmcls)
    return view, vm, view.control("root.c")


def _click(view):
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.c"))


def test_a_bare_signal_is_two_way():
    view, vm, control = _checkbox("<| done |>")
    assert view.handle.node("c").models.keys() == {"checked"}
    _click(view)
    assert vm.done.get() is True and control.checked.get() is True


@pytest.mark.parametrize("expr", ["<| not done |>", "<| inverse |>", "<| plain |>"])
def test_anything_else_is_one_way_and_the_users_edit_is_not_written_back(expr):
    view, vm, control = _checkbox(expr)
    assert view.handle.node("c").models == {}
    _click(view)
    assert vm.done.get() is False  # nothing written


def test_the_users_edit_of_a_one_way_property_stays_until_the_value_next_changes():
    view, vm, control = _checkbox("<| not done |>")
    assert control.checked.get() is True
    _click(view)
    assert control.checked.get() is False  # the control shows the edit; the expression still says True
    vm.done.set(True)
    assert control.checked.get() is False  # the expression is False now
    vm.done.set(False)
    assert control.checked.get() is True  # and follows it again


def test_a_plain_attribute_is_never_set_again_by_the_view():
    view, vm, control = _checkbox("<| plain |>")
    _click(view)
    assert control.checked.get() is True and vm.plain is False  # a plain attribute does not notify: the edit stays


def test_a_literal_is_one_way():
    view, vm, _ = render([f"Checkbox {{ Name: c, Checked: true, {STYLE} }}"])
    assert view.handle.node("c").models == {}


def test_a_read_only_param_is_one_way_even_when_it_holds_a_signal():
    view = "Checkbox {\n  Params { P { Type: bool, Default: true } }\n  Checked: <| p |>\n}\n"
    comp, vm, _ = make({"V": view}, container("V { Name: v, P: <| show |> }"))
    assert comp.find("root.v").models == {}


# -- 3. what a state keeps -------------------------------------------------------------------------------------------------------------


def _source(state="N: 1", target="n", shown="n"):
    return container(click(set_(target, f"{target} + 1"), set_("count", "count + 1"), text=f"<| {shown} |> <| count |>"), state=state)


SOURCE = _source()


def _again(comp, vm, source):
    return Composer({}, vm, previous=comp).compose(parse_view(tdl(source), "Main_View.tdl"))


def test_a_state_keeps_the_users_value_over_an_edited_starting_value():
    comp, vm, _ = make(None, SOURCE)
    comp.find("root.t").fire("on_click")
    assert _again(comp, vm, _source(state="N: 100")).find("root.t").value("text") == "2 1"


def test_a_state_that_is_renamed_starts_again_and_the_viewmodel_keeps_its_value():
    comp, vm, _ = make(None, SOURCE)
    comp.find("root.t").fire("on_click")
    assert _again(comp, vm, _source(state="K: 7", target="k", shown="k")).find("root.t").value("text") == "7 1"


def test_a_state_of_a_node_that_is_renamed_starts_again():
    def source(name):
        return container(container(click(set_("n", "n + 1"), text="<| n |>"), state="N: 1", name=name).replace("\n", "\n    ").rstrip(" "))

    comp, vm, _ = make(None, source("box"))
    comp.find("root.box.t").fire("on_click")
    assert _again(comp, vm, source("box")).find("root.box.t").value("text") == "2"
    assert _again(comp, vm, source("crate")).find("root.crate.t").value("text") == "1"


def test_the_state_of_a_row_follows_its_key_when_the_rows_are_reordered():
    row = f"Container {{ Name: row, State {{ Open: false }}, Children {{ {click(set_('open', 'True'), text='<| r.t |> <| open |>')} }} }}"
    source = container(f"{FOR_ROWS} {{ {row} }}")
    comp, vm, _ = make(None, source)
    comp.find("root.row[1].t").fire("on_click")
    vm.rows.set(list(reversed(vm.rows.get())))
    again = _again(comp, vm, source)
    assert again.find("root.row[1].t").value("text") == "a True" and again.find("root.row[2].t").value("text") == "b False"


# -- #283: the same for the text of an `after(...)` or `every(...)` ---------------------------------------------------------------------------


@pytest.mark.parametrize("timer", ["after", "every"])
def test_a_timer_text_that_assigns_what_cannot_be_written_is_a_load_error(timer):
    with pytest.raises(LoadError, match="'r' is not writable here"):
        make(None, container(click(f'Call {{ Action: "{timer}", Args: [<| 10 |>, <| "r = 1" |>] }}', wrap=FOR_ROWS)))


def test_a_timer_text_that_assigns_state_loads():
    comp, _, _ = make(None, container(click('Call { Action: "after", Args: [<| 10 |>, <| "s = 2" |>] }'), state="S: 1"))
    assert comp.root.state["s"].get() == 1
