"""A press that leaves its widget before it ends is cancelled: the pressed state (the pressed shape of a round Button, a rule `State: pressed`) does not stay on. The engine does not capture a
press, so a release after the pointer left goes to whatever is under it and the widget never hears `pointer_up` (owner round 2, fb04: the button stayed morphed)."""

import pathlib

from tess_ui import App

VIEW = """---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Flex_Direction: vertical, Width: 400, Height: 300, Gap: 40 }
  Children {
    Button { Name: b, Label: "Press", Shape: round }
    Container { Name: other, Style { Width: 100, Height: 40, Background: primary } }
  }
}
"""


def _view(tmp_path: pathlib.Path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(VIEW)
    app = App(root=tmp_path, width=400, height=300, reduced_motion=True)
    view = app.open_view("Main")
    app.show("main")
    return view


def _settle(view, n=8):
    for _ in range(n):
        view.window.advance(16)


def _radius(view):
    return view._built.outer["root.b"].get("corner_radius")


def test_a_press_dragged_off_the_button_and_released_elsewhere_gives_the_shape_back(tmp_path):
    view = _view(tmp_path)
    button, other = view.node("root.b"), view.node("root.other")
    _settle(view)
    rest = _radius(view)
    view.window.simulate("pointer_move", node=button)
    _settle(view)
    view.window.simulate("pointer_down", node=button)
    _settle(view)
    assert _radius(view) != rest, "pressed: the shape is less round"
    view.window.simulate("pointer_move", node=other)
    _settle(view)
    assert _radius(view) == rest, "the press left the button: it is cancelled, the shape is back"
    view.window.simulate("pointer_up", node=other)
    _settle(view)
    assert _radius(view) == rest


def test_a_press_and_release_on_the_button_still_morphs_and_gives_the_shape_back(tmp_path):
    view = _view(tmp_path)
    button = view.node("root.b")
    _settle(view)
    rest = _radius(view)
    view.window.simulate("pointer_down", node=button)
    _settle(view)
    assert _radius(view) != rest
    view.window.simulate("pointer_up", node=button)
    _settle(view)
    assert _radius(view) == rest
