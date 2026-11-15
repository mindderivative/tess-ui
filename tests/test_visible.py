"""#259 (part of #257): a node's `visible:` -- hidden and out of layout while false, kept in the tree with its state and listeners (unlike `if:`)."""

import pytest

from tess_ui import App, Signal, ViewModel


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.show = Signal(False)
        self.flag = Signal(True)
        self.clicks = []

    def on_under(self):
        self.clicks.append("under")

    def on_over(self):
        self.clicks.append("over")


META = "---\nTDL: 0.2\nName: {}\n---\n"
HEAD = META.format("main") + "Container {\n  Name: main\n  Style { Width: 300, Height: 200, Flex_Direction: vertical }\n  Children {\n"
BOX = "Style { Width: 40, Height: 40, Background: primary }"


def opened(tmp_path, body, files=None, head=HEAD):
    """`body` is the TDL of the root's children, indented four spaces; `files` are more views in `Views/` (their whole text)."""
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(head + body + "  }\n}\n")
    for name, text in (files or {}).items():
        (tmp_path / "Views" / name).write_text(text)
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    return app, view, app.bindings.viewmodel_for("main")


def test_a_node_with_visible_false_is_hidden_and_takes_no_room(tmp_path):
    app, view, vm = opened(tmp_path, f"    Rect {{ Name: a, Visible: false, {BOX} }}\n    Rect {{ Name: b, {BOX} }}\n")
    a, b = view.node("root.a"), view.node("root.b")
    assert a.get("visible") is False and (a.get("layout_width"), a.get("layout_height")) == (0.0, 0.0)
    assert b.get("layout_y") == 0.0  # it moved up into the room the hidden one would have taken


def test_visible_true_or_absent_shows_the_node(tmp_path):
    app, view, vm = opened(tmp_path, f"    Rect {{ Name: a, Visible: true, {BOX} }}\n    Rect {{ Name: b, {BOX} }}\n")
    assert view.node("root.a").get("visible") is True and view.node("root.b").get("visible") is True
    assert view.node("root.b").get("layout_y") == 40.0


def test_a_signal_hides_and_shows_it(tmp_path):
    app, view, vm = opened(tmp_path, f"    Rect {{ Name: a, Visible: <| show |>, {BOX} }}\n")
    a = view.node("root.a")
    assert a.get("visible") is False
    vm.show.set(True)
    view.window.advance(16)
    assert a.get("visible") is True and a.get("layout_width") == 40.0
    vm.show.set(False)
    view.window.advance(16)
    assert a.get("visible") is False


def test_a_hidden_node_keeps_its_state_which_an_if_would_lose(tmp_path):
    body = """    Container {
      Name: counter
      State { N: 0 }
      Visible: <| show |>
      Interaction: true
      Handlers { On_Click { Set { Target: n, Value: <| n + 1 |> } } }
      Style { Width: 100, Height: 40 }
      Children {
        Text { Name: label, Text: <| n |>, Typography_Role: body_medium, Style { Foreground: on_surface } }
      }
    }
    If <| show |> {
      Container {
        Name: rebuilt
        State { N: 0 }
        Interaction: true
        Handlers { On_Click { Set { Target: n, Value: <| n + 1 |> } } }
        Style { Width: 100, Height: 40 }
        Children {
          Text { Name: label2, Text: <| n |>, Typography_Role: body_medium, Style { Foreground: on_surface } }
        }
      }
    }
"""
    app, view, vm = opened(tmp_path, body)
    vm.show.set(True)
    view.window.advance(16)
    for name in ("counter", "rebuilt"):
        node = view.node(f"root.{name}")
        view.window.simulate("click", x=50.0, y=node.get("layout_y") + 20)
    assert view.node("root.counter.label").get("text") == "1" and view.node("root.rebuilt.label2").get("text") == "1"
    vm.show.set(False)
    view.window.advance(16)
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.counter.label").get("text") == "1"   # it was only hidden
    assert view.node("root.rebuilt.label2").get("text") == "0"  # it was taken out and built again


def test_a_hidden_node_does_not_take_the_pointer(tmp_path):
    body = """    Container {
      Name: under
      Interaction: true
      Handlers { On_Click: on_under }
      Style { Position: absolute, X: 0, Y: 0, Width: 200, Height: 100, Background: surface_container }
    }
    Container {
      Name: over
      Visible: <| show |>
      Interaction: true
      Handlers { On_Click: on_over }
      Style { Position: absolute, X: 0, Y: 0, Width: 200, Height: 100 }
    }
"""
    app, view, vm = opened(tmp_path, body)
    view.window.simulate("click", x=100.0, y=50.0)
    assert vm.clicks == ["under"]
    vm.show.set(True)
    view.window.advance(16)
    vm.clicks.clear()
    view.window.simulate("click", x=100.0, y=50.0)
    assert vm.clicks == ["over"]


def test_a_patch_leaves_a_node_hidden_by_other_code_alone_when_the_style_does_not_say_visible(tmp_path):
    """An overlay, a view's root and a binding hide nodes too; a node with no `visible:` is never set shown by a re-patch."""
    app, view, vm = opened(tmp_path, "    Rect { Name: a, Style { Width: 40, Height: 40, Background: <| 'primary' if flag else 'secondary' |> } }\n")
    a = view.node("root.a")
    a.set(visible=False)  # something else hid it
    vm.flag.set(False)    # the node is patched
    view.window.advance(16)
    assert a.get("visible") is False


def test_dropping_visible_from_a_node_shows_it_again():
    from tess_ui.spec.build import _resets, _with_visible

    assert _resets({}, frozenset({"visible"})) == {"visible": True}
    assert _with_visible({"visible": False}, {"width": 1}) == {"width": 1, "visible": False}
    assert _with_visible({"visible": True}, {}) == {"visible": True}
    assert _with_visible({}, {"width": 1}) == {"width": 1} and _with_visible({"visible": None}, {}) == {}


def test_a_widget_that_declares_a_visible_of_its_own_keeps_it(tmp_path):
    panel = META.format("Panel") + """Container {
  Params { Visible { Type: bool, Default: true } }
  Style { Width: 100, Height: 50 }
  Children {
    Text { Name: t, Text: <| 'on' if visible else 'off' |>, Typography_Role: body_medium, Style { Foreground: on_surface } }
  }
}
"""
    app, view, vm = opened(tmp_path, "    Panel { Name: p, Visible: false }\n", {"Panel_View.tdl": panel})
    assert view.node("root.p.t").get("text") == "off" and view.node("root.p").get("visible") is True  # the param, not the key


def test_visible_on_a_view_call_hides_the_whole_view(tmp_path):
    files = {"Panel_View.tdl": META.format("Panel") + "Container { Style { Width: 100, Height: 50, Background: surface_container } }\n"}
    body = f"    Panel {{ Name: p, Visible: <| show |> }}\n    Rect {{ Name: after, {BOX} }}\n"
    app, view, vm = opened(tmp_path, body, files)
    assert view.node("root.p").get("visible") is False and view.node("root.after").get("layout_y") == 0.0
    vm.show.set(True)
    view.window.advance(16)
    assert view.node("root.p").get("visible") is True and view.node("root.after").get("layout_y") == 50.0


def test_the_root_of_a_view_takes_no_visible(tmp_path):
    head = META.format("main") + "Container {\n  Name: main\n  Visible: false\n  Style { Width: 300, Height: 200 }\n  Children {\n"
    with pytest.raises(Exception, match="the root of a view takes no 'visible:'"):
        opened(tmp_path, f"    Rect {{ Name: a, {BOX} }}\n", head=head)


@pytest.mark.parametrize("value", ["maybe", "3", "[true]"])
def test_a_visible_that_is_not_true_or_false_is_refused_naming_it(tmp_path, value):
    with pytest.raises(Exception, match="'visible' takes true or false"):
        opened(tmp_path, f"    Rect {{ Name: a, Visible: {value}, {BOX} }}\n")


def test_a_control_and_a_link_can_be_hidden_too(tmp_path):
    body = ("    Slider { Name: s, Visible: false, Value: 3, Min: 0, Max: 10 }\n"
            "    Link { Name: l, Visible: false, Text: Docs, Href: \"https://example.com\", Style { Foreground: primary } }\n"
            f"    Rect {{ Name: r, {BOX} }}\n")
    app, view, vm = opened(tmp_path, body)
    assert view.node("root.s").get("visible") is False and view.node("root.l").get("visible") is False
    assert view.node("root.r").get("layout_y") == 0.0


def test_the_widget_schema_knows_the_key():
    from tess_ui.spec.widgets import json_schema
    assert "visible" in str(json_schema())


def test_a_bound_visible_whose_value_is_not_true_or_false_is_refused_naming_it(tmp_path):
    """A literal is checked when the file is read; what an expression works out is checked when it is worked out."""
    with pytest.raises(Exception, match="'visible' takes true or false"):
        opened(tmp_path, f"    Rect {{ Name: a, Visible: <| 'maybe' |>, {BOX} }}\n")
