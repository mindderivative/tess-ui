"""#219: `on_move` and `on_release` with `capture()`, `release()` and `cursor(name)` in a handler: a drag that follows the pointer outside the node."""

import pytest

from tess_ui import App, Signal, ViewModel


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.x = Signal(0.0)
        self.dragging = Signal(False)


VIEW = """---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 300, Height: 200 }
  Children {
    Container {
      Name: thumb
      Style { Width: 40, Height: 40 }
      Handlers {
        On_Press {
          Set { Target: dragging, Value: <| True |> }
          Call { Action: "capture" }
          Call { Action: "cursor", Args: [<| 'grabbing' |>] }
        }
        On_Move { Set { Target: x, Value: <| event.x if dragging else x |> } }
        On_Release {
          Set { Target: dragging, Value: <| False |> }
          Call { Action: "release" }
          Call { Action: "cursor", Args: [<| None |>] }
        }
      }
    }
  }
}
"""


def opened(tmp_path, view=VIEW):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(view)
    app = App(root=tmp_path)
    app.bind(VM)
    shown = app.open_view("Main")
    app.show("main")
    shown.window.advance(16)
    return shown, app.bindings.viewmodel_for("main")


def thumb(view):
    return view.node("root.thumb")


def test_pressing_captures_the_pointer_and_sets_the_cursor(tmp_path):
    view, vm = opened(tmp_path)
    view.window.simulate("pointer_down", x=10, y=10)
    view.window.advance(16)
    assert vm.dragging.get() is True and thumb(view).get("cursor") == "grabbing"


def test_a_captured_pointer_moves_the_value_even_outside_the_node(tmp_path):
    view, vm = opened(tmp_path)
    view.window.simulate("pointer_down", x=10, y=10)
    view.window.simulate("pointer_move", x=200, y=150)  # far outside the 40 px node
    view.window.advance(16)
    assert vm.x.get() == 200.0


def test_releasing_ends_the_drag_and_clears_the_cursor(tmp_path):
    view, vm = opened(tmp_path)
    view.window.simulate("pointer_down", x=10, y=10)
    view.window.simulate("pointer_up", x=250, y=150)
    view.window.advance(16)
    assert vm.dragging.get() is False and thumb(view).get("cursor") is None


def test_without_a_capture_a_move_outside_the_node_is_not_seen(tmp_path):
    view, vm = opened(tmp_path, VIEW.replace('          Call { Action: "capture" }\n', ""))
    view.window.simulate("pointer_down", x=10, y=10)
    view.window.simulate("pointer_move", x=200, y=150)
    view.window.advance(16)
    assert vm.x.get() == 0.0


def test_a_bad_cursor_name_is_the_engines_message(tmp_path):
    view, _ = opened(tmp_path, VIEW.replace("<| 'grabbing' |>", "<| 'nope' |>"))
    inst = next(i for i in view.handle.composition.walk() if i.id == "root.thumb")
    view._firing.append(inst)  # as the wiring does while a handler runs (the engine would log the error rather than raise it)
    with pytest.raises(Exception, match=r"Main_View.tdl:13:\d+: cursor\(\) failed: ValueError: .*must be one of: default, pointer"):
        inst.fire("on_press")


def test_capture_outside_a_handler_says_so(tmp_path):
    view, _ = opened(tmp_path)
    with pytest.raises(ValueError, match="acts on the widget whose handler is running"):
        view.firing_node("capture")


def test_the_view_checks_the_new_actions_and_events(tmp_path):
    from tess_ui.spec.nodes import parse_view
    parse_view(VIEW, "Main_View.tdl")


def test_the_handler_is_not_running_once_it_has_returned(tmp_path):
    view, _ = opened(tmp_path)
    view.window.simulate("pointer_down", x=10, y=10)
    view.window.advance(16)
    assert view._firing == []
    with pytest.raises(ValueError, match="acts on the widget whose handler is running"):
        view.firing_node("cursor")


LINK = """---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 300, Height: 200 }
  Children {
    Link {
      Name: thumb
      Text: grab
      Font_Family: Roboto
      Font_Size: 14
      Style { Foreground: "#000000", Width: 40, Height: 40 }
      Handlers {
        On_Press {
          Set { Target: dragging, Value: <| True |> }
          Call { Action: "capture" }
        }
        On_Move { Set { Target: x, Value: <| event.x if dragging else x |> } }
      }
    }
  }
}
"""


def test_a_link_captures_through_its_box(tmp_path):
    view, vm = opened(tmp_path, LINK)
    view.window.simulate("pointer_down", x=10, y=10)
    view.window.simulate("pointer_move", x=220, y=150)
    view.window.advance(16)
    assert vm.dragging.get() is True and vm.x.get() == 220.0
