"""A ScrollView with `orientation: horizontal` scrolls sideways (tre 0.5.6): a row of children, an offset along x, and `right`/`left` for the way it went."""

import pytest

from tess_ui import App, Signal, ViewModel
from tess_ui.spec.build import SpecBuildError


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.x = Signal(0.0)
        self.start = Signal(True)
        self.end = Signal(False)
        self.way = Signal("none")


def opened(tmp_path, props="Orientation: horizontal"):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 300, Height: 200 }}
  Children {{
    ScrollView {{
      Name: strip
      {props}
      Scroll_Offset: <| x |>
      At_Top: <| start |>
      At_End: <| end |>
      Scroll_Direction: <| way |>
      Style {{ Width: 100, Height: 60 }}
      Children {{
        Container {{ Name: a, Style {{ Width: 150, Height: 40, Background: primary }} }}
        Container {{ Name: b, Style {{ Width: 150, Height: 40, Background: secondary }} }}
        Container {{ Name: c, Style {{ Width: 150, Height: 40, Background: tertiary }} }}
      }}
    }}
  }}
}}
""")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(3):
        view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


def test_the_children_are_a_row_and_the_view_scrolls_sideways(tmp_path):
    view, vm = opened(tmp_path)
    strip = view._built.outer["root.strip"]
    assert strip.get("orientation") == "horizontal"
    assert view.node("root.strip.b").get("layout_x") == view.node("root.strip.a").get("layout_x") + 150
    strip.set(scroll_offset=150.0)
    view.window.advance(16)
    assert strip.get("scroll_offset") == 150.0


def test_a_wheel_to_the_side_moves_it_and_the_outputs_follow(tmp_path):
    view, vm = opened(tmp_path)
    strip = view._built.outer["root.strip"]
    view.window.simulate("wheel", node=strip, delta_x=60.0, delta_y=0.0)
    view.window.advance(16)
    assert vm.x.get() == 60.0 and vm.way.get() == "right" and vm.start.get() is False and vm.end.get() is False
    view.window.simulate("wheel", node=strip, delta_x=-20.0, delta_y=0.0)
    view.window.advance(16)
    assert vm.way.get() == "left"
    strip.set(scroll_offset=350.0)
    view.window.advance(16)
    assert vm.end.get() is True


def test_a_bound_offset_moves_the_view(tmp_path):
    view, vm = opened(tmp_path)
    vm.x.set(90.0)
    view.window.advance(16)
    assert view._built.outer["root.strip"].get("scroll_offset") == 90.0


def test_vertical_is_still_the_default(tmp_path):
    view, vm = opened(tmp_path, props="")
    assert view._built.outer["root.strip"].get("orientation") == "vertical"


def test_another_orientation_is_refused(tmp_path):
    with pytest.raises((SpecBuildError, ValueError, Exception), match="vertical or horizontal|orientation"):
        opened(tmp_path, props="Orientation: diagonal")


def test_a_scroll_view_with_a_max_size_and_none_of_its_own_is_as_long_as_its_content_up_to_that(tmp_path):
    view, _ = opened(tmp_path, props="Orientation: horizontal")
    strip = view._built.outer["root.strip"]
    assert strip.get("layout_width") == 100.0  # its own width
    (tmp_path / "Views" / "Main_View.tdl").write_text("""---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 300, Height: 300 }
  Children {
    ScrollView {
      Name: short
      Style { Max_Height: 100 }
      Children { Container { Name: a, Style { Width: 50, Height: 40 } } }
    }
    ScrollView {
      Name: tall
      Style { Max_Height: 100 }
      Children { Container { Name: b, Style { Width: 50, Height: 400 } } }
    }
    ScrollView {
      Name: wide
      Orientation: horizontal
      Style { Max_Width: 120, Height: 30 }
      Children { Container { Name: c, Style { Width: 500, Height: 20 } } }
    }
  }
}
""")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(4):
        view.window.advance(16)
    assert view._built.outer["root.short"].get("layout_height") == 40.0
    assert view._built.outer["root.tall"].get("layout_height") == 100.0
    assert view._built.outer["root.wide"].get("layout_width") == 120.0


def test_snap_and_snap_align_make_it_settle_on_a_child_and_a_wrong_alignment_is_refused(tmp_path):
    (tmp_path / "Views").mkdir(exist_ok=True)

    def view_with(snap, align):
        (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Width: 300, Height: 100, Align_Content: top_left }}
  Children {{
    ScrollView {{
      Name: s
      Orientation: horizontal
      Snap: {snap}
      Style {{ Width: 100, Height: 60 }}
      Children {{
        Container {{ Name: a, Style {{ Width: 150, Height: 40, Snap_Align: {align} }} }}
        Container {{ Name: b, Style {{ Width: 150, Height: 40, Snap_Align: {align} }} }}
      }}
    }}
  }}
}}
""")
        app = App(root=tmp_path)
        app.bind(VM)
        view = app.open_view("Main")
        app.show("main")
        for _ in range(4):
            view.window.advance(16)
        return view

    view = view_with("start", "start")
    strip = view._built.outer["root.s"]
    assert strip.get("scroll_snap") == "start" and view.node("root.s.a").get("snap_align") == "start"
    view.window.simulate("wheel", node=strip, delta_x=100.0, delta_y=0.0)
    for _ in range(60):
        view.window.advance(16)
    assert strip.get("scroll_offset") == 150.0
    with pytest.raises(Exception, match="snap_align"):
        view_with("start", "middle")
