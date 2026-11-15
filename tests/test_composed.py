"""#209 phase 5: a composed view on screen -- bindings, handlers, `for:` and `if:` reaching real nodes, two-way edits, and the App glue."""

import pytest

from tess_ui import App, Signal, ViewModel
from tess_ui.composed import ComposedView, open_composed
from tess_ui.spec.nodes import parse_view
from tess_ui.spec.widgets import decl_from_params
from tess_ui.viewmodel import Bindings

SEED = (103, 80, 164, 255)
TEXT = 'Typography_Role: body_large, Style { Width: 100, Height: 20, Foreground: "#000000" }'


class DemoVM(ViewModel):
    views = ["demo", "other"]

    def __init__(self):
        super().__init__()
        self.title = Signal("Hello")
        self.rows = Signal([{"id": 1, "t": "a"}])
        self.show_extra = Signal(False)
        self.done = Signal(False)
        self.color = Signal("#6750A4")
        self.log = []

    def bump(self):
        self.log.append("bump")


def render(source, vmcls=DemoVM, views=None, **kw):
    doc = parse_view(source, "Demo_View.tdl", resolver=(views or {}).get)
    bindings = Bindings()
    bindings.bind(vmcls)
    callee = kw.pop("callee", None)
    view = open_composed(doc, bindings, callee, theme_seed=SEED, **kw)
    return view, view.handle.viewmodel, bindings


def tdl(body, name="Demo"):
    """A view file in TDL: the metadata block, then `body`, the root block."""
    return f"---\nTDL: 0.2\nName: {name}\n---\n{body}\n"


def page(*children):
    """The demo view: a vertical Container (300 x 300) holding the TDL blocks `children`."""
    return tdl("Container {\n  Name: demo\n  Style { Flex_Direction: vertical, Width: 300, Height: 300 }\n  Children {\n" + "".join(f"    {c}\n" for c in children) + "  }\n}")


def test_a_bound_property_reaches_the_node_and_follows_its_signal():
    view, vm, _ = render(page("Text { Name: head, Text: <| title |> <| 1 + 1 |>, " + TEXT + " }"))
    assert view.node("root.head").get("text") == "Hello 2"
    vm.title.set("Bye")
    assert view.node("root.head").get("text") == "Bye 2"


def test_a_reactive_style_value_reaches_the_node():
    view, vm, _ = render(page("Rect { Name: r, Style { Width: 40, Height: 20, Background: <| color |> } }"))
    before = view.node("root.r").get("fill")
    vm.color.set("#B3261E")
    assert view.node("root.r").get("fill") != before


def test_a_click_runs_the_handler_in_the_scope_it_was_written():
    view, vm, _ = render(page('Rect { Name: a, Style { Width: 40, Height: 20, Background: "#6750A4" }, Handlers { On_Click: bump } }',
                       'Rect { Name: b, State { N: 0 }, Style { Width: 40, Height: 20, Background: "#6750A4" }, '
                       'Handlers { On_Click { Set { Target: n, Value: <| n + 1 |> } } } }',
                       'Text { Name: t, Text: "x", ' + TEXT + " }"))
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.a"))
    assert vm.log == ["bump"]
    view.window.simulate("click", node=view.node("root.b"))
    view.window.simulate("click", node=view.node("root.b"))
    assert view.handle.node("b").state["n"].get() == 2


def test_for_adds_and_removes_real_nodes_and_keeps_the_ones_that_stay():
    view, vm, _ = render(page("For r In <| rows |> Key <| r.id |> { Text { Name: row, Text: <| r.t |>, " + TEXT + " } }"))
    first = view.node("root.row[1]")
    vm.rows.set([{"id": 1, "t": "a"}, {"id": 2, "t": "b"}])
    assert view.node("root.row[2]").get("text") == "b" and view.node("root.row[1]") == first
    vm.rows.set([{"id": 2, "t": "B"}])
    assert view.node("root.row[2]").get("text") == "B"
    with pytest.raises(ValueError, match="no widget with id 'root.row.1.'"):
        view.node("root.row[1]")


def test_if_builds_and_removes_a_real_node_and_a_handler_on_it_stays_wired():
    view, vm, _ = render(page('If <| show_extra |> { Rect { Name: extra, Style { Width: 40, Height: 20, Background: "#6750A4" }, Handlers { On_Click: bump } } }'))
    with pytest.raises(ValueError, match="no widget"):
        view.node("root.extra")
    vm.show_extra.set(True)
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.extra"))
    assert vm.log == ["bump"]
    vm.show_extra.set(False)
    with pytest.raises(ValueError, match="no widget"):
        view.node("root.extra")


def test_a_checkbox_follows_the_signal_and_the_users_click_writes_it_back():
    view, vm, _ = render(page('Checkbox { Name: c, Checked: <| done |>, Style { Width: 24, Height: 24, Background: "#6750A4" } }'))
    control = view.control("root.c")
    assert control.checked.get() is False
    vm.done.set(True)
    assert control.checked.get() is True
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.c"))
    assert vm.done.get() is False  # the click toggled the control and the edit went back to the Signal


def test_a_model_parameter_given_a_bare_signal_passes_the_signal_through_a_view():
    check = tdl('Checkbox { Params { On { Type: bool, Model: true } }, Checked: <| on |>, Style { Width: 24, Height: 24, Background: "#6750A4" } }', "Check")
    decls = {"Check": decl_from_params("Check", {"on": {"type": "bool", "model": True}})}
    docs = {"Check": parse_view(check, "Check_View.tdl", resolver=decls.get, view_name="Check")}
    view, vm, _ = render(page("Check { Name: c, On: <| done |> }"), views=decls, callee=docs.get)
    control = view.control("root.c")
    vm.done.set(True)
    assert control.checked.get() is True
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.c"))
    assert vm.done.get() is False


def test_a_view_call_with_slot_content_renders_in_one_tree_and_a_handler_at_the_call_runs_in_the_callers_scope():
    card = tdl("Container { Params: [title], Style { Flex_Direction: vertical, Width: 200, Height: 100 }, Children { "
               "Text { Name: head, Text: <| title |>, " + TEXT + " } Slot { } } }", "Card")
    decls = {"Card": decl_from_params("Card", ["title"])}
    docs = {"Card": parse_view(card, "Card_View.tdl", resolver=decls.get, view_name="Card")}
    view, vm, _ = render(page("Card { Name: c, Title: <| title |>!, Handlers { On_Click: bump }, "
                       "Children { Text { Name: inside, Text: slotted, " + TEXT + " } } }"), views=decls, callee=docs.get)
    assert view.node("root.c.head").get("text") == "Hello!" and view.node("root.c.inside").get("text") == "slotted"
    vm.title.set("Yo")
    assert view.node("root.c.head").get("text") == "Yo!"
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.c"))
    assert vm.log == ["bump"]


def test_hiding_a_view_hides_its_root_and_close_stops_it_following_anything():
    view, vm, _ = render(page("Text { Name: head, Text: <| title |>, " + TEXT + " }"))
    assert view.root.get("visible") is True
    view.handle.hide()
    assert view.root.get("visible") is False
    view.handle.show()
    assert view.root.get("visible") is True
    view.close()
    vm.title.set("after")  # nothing follows it any more
    assert view.node("root.head").get("text") == "Hello"
    assert vm.title._subscribers == []


def test_two_views_of_one_viewmodel_are_rendered_at_once_and_both_follow_one_signal():
    class Pair(ViewModel):
        views = ["pie", "list"]

        def __init__(self):
            super().__init__()
            self.rows = Signal([1, 2])

    bindings = Bindings()
    bindings.bind(Pair)
    pie = open_composed(parse_view(tdl("Text { Name: pie, Text: <| len(rows) |> slices, " + TEXT + " }", "Pie"), "Pie_View.tdl"), bindings, theme_seed=SEED)
    lst = open_composed(parse_view(tdl("Container { Name: list, Style { Flex_Direction: vertical, Width: 100, Height: 100 }, Children { "
                                       "For r In <| rows |> Key <| r |> { Text { Name: row, Text: <| r |>, " + TEXT + " } } } }", "List"), "List_View.tdl"),
                        bindings, theme_seed=SEED)
    vm = pie.handle.viewmodel
    assert vm is lst.handle.viewmodel and pie.root.get("text") == "2 slices"
    vm.rows.set([1, 2, 3])
    assert pie.root.get("text") == "3 slices" and lst.node("root.row[3]").get("text") == "3"
    assert vm.views["pie"].closed is False and vm.views["list"] is lst.handle


def test_an_image_frame_that_is_not_a_frame_is_named_not_dropped():
    with pytest.raises(ValueError, match="a frame is .rgba bytes, width, height."):
        render(page("Image { Name: i, Frame: <| title |>, Style { Width: 10, Height: 10 } }"))


# -- the App ---------------------------------------------------------------------------------------------------------------


def project(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(tdl("""Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 300, Height: 200 }
  Children {
    Banner { Name: banner, Text: <| title |> }
    Rect { Name: go, Style { Width: 40, Height: 20, Background: "#6750A4" }, Handlers { On_Click: bump } }
  }
}""", "Main"))
    (tmp_path / "Views" / "Banner_View.tdl").write_text(tdl(
        "Text { Params: [text], Text: <| text |>, " + TEXT + " }", "Banner"))
    return tmp_path


def test_the_app_binds_opens_shows_and_checks_a_view_written_in_the_new_syntax(tmp_path):
    root = project(tmp_path)
    class MainVM(DemoVM):
        views = ["main", "other"]

    app = App(root=root)
    app.bind(MainVM)
    opened = app.open_view("Main")
    assert isinstance(opened, ComposedView) and opened.node("root.banner").get("text") == "Hello"
    vm = opened.handle.viewmodel
    vm.title.set("Changed")
    assert opened.node("root.banner").get("text") == "Changed"
    window = app.show("main")
    assert window is app._window
    opened.window.advance(16)
    opened.window.simulate("click", node=opened.node("root.go"))
    assert vm.log == ["bump"]
    assert app.check() == ["MainVM serves the view 'other', but no view has that name"]


def test_the_app_reports_a_view_that_needs_a_name_its_viewmodel_lacks(tmp_path):
    root = project(tmp_path)
    (root / "Views" / "Main_View.tdl").write_text(tdl(
        'Rect { Name: main, Style { Width: 10, Height: 10, Background: "#6750A4" }, Handlers { On_Click: nope_missing } }', "Main"))

    class Small(ViewModel):
        views = "main"

    app = App(root=root)
    app.bind(Small)
    app.open_view("Main")
    problems = app.check()
    assert len(problems) == 1 and "'nope_missing' is not a method of Small" in problems[0] and "Main_View.tdl:5:1" in problems[0].replace(str(root) + "/Views/", "")


def test_a_name_no_view_or_binding_serves_is_still_an_error_at_open(tmp_path):
    root = project(tmp_path)
    app = App(root=root)
    with pytest.raises(Exception, match="'title' is not defined"):
        app.open_view("Main")  # the view reads `title`, and no ViewModel is bound to give it


# -- rules the mutation check found no test for -----------------------------------------------------------------------------


def test_a_disabled_nodes_handlers_do_not_run():
    view, vm, _ = render(page('TextInput { Name: f, Disabled: <| not show_extra |>, Typography_Role: body_large, '
                       'Style { Width: 100, Height: 30, Background: "#FFFFFF" }, Handlers { On_Click: bump } }'))
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.f"))
    assert vm.log == []
    vm.show_extra.set(True)  # enabled: the handler runs
    view.window.simulate("click", node=view.node("root.f"))
    assert vm.log == ["bump"]


def test_a_click_on_a_child_is_handled_there_and_does_not_also_run_the_parents_handler():
    class Outer(DemoVM):  # a ViewModel method is there when the view loads (#251 finds a name that is not)
        def log_outer(self):
            self.log.append("outer")

    view, vm, _ = render(page('Rect { Name: outer, Style { Width: 80, Height: 40, Background: "#6750A4" }, Handlers { On_Click { Call { Action: log_outer } } }, '
                       'Children { Rect { Name: inner, Style { Width: 30, Height: 20, Background: "#B3261E" }, Handlers { On_Click: bump } } } }'),
                       vmcls=Outer)
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.outer.inner"))
    assert vm.log == ["bump"]


def test_a_loop_variable_given_to_a_model_property_is_not_two_way():
    class Flags(ViewModel):
        views = "demo"

        def __init__(self):
            super().__init__()
            self.flags = Signal([True, False])

    view, vm, _ = render(page('For f In <| flags |> Key <| f |> { Checkbox { Name: c, Checked: <| f |>, Style { Width: 24, Height: 24, Background: "#6750A4" } } }'),
                       vmcls=Flags)
    assert view.handle.node("c").models == {}
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.c[True]"))  # the control toggles; nothing is written back and nothing fails
    assert vm.flags.get() == [True, False]


def test_the_built_in_actions_exist_without_an_app_and_do_nothing_there():
    view, vm, _ = render(page('Rect { Name: w, Style { Width: 40, Height: 20, Background: "#6750A4" }, Handlers { On_Click: window.close } }',
                       'Rect { Name: n, Style { Width: 40, Height: 20, Background: "#6750A4" }, Handlers { On_Click: navigate.back } }'))
    view.window.advance(16)
    view.window.simulate("click", node=view.node("root.w"))
    view.window.simulate("click", node=view.node("root.n"))


def test_after_close_showing_and_hiding_the_view_no_longer_changes_its_nodes():
    view, vm, _ = render(page("Text { Name: head, Text: x, " + TEXT + " }"))
    view.close()
    view.handle.hide()
    assert view.root.get("visible") is True


def test_the_built_in_actions_resolve_for_a_view_and_nothing_else_does():
    from tess_ui.composed import builtin_actions

    class Stub:
        window = None

        def node(self, name):
            return None

    resolve = builtin_actions(lambda: Stub())
    for path in ("window.close", "window.minimize", "navigate.back", "navigate.forward", "navigate.Settings", "navigate_to", "surface.dismiss"):
        assert callable(resolve(path)), path
    for path in ("window.bogus", "surface.explode", "navigate", "save", "window"):
        assert resolve(path) is None, path
    assert resolve("window.close")() is None and resolve("navigate.back")() is None and resolve("navigate_to")("Home") is None  # no App: nothing to do
