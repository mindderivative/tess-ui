"""#280, step 1: an `Overlay` takes the corner and centre placements, an `offset` and `flip` (tre 0.5.7), and a tooltip takes the corner placements."""

import pytest

from tess_ui import App, Signal, ViewModel
from tess_ui.spec.nodes import LoadError


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.shown = Signal(True)


def opened(tmp_path, overlay_lines, anchor="X: 150, Y: 120, Width: 60, Height: 40"):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Width: 400, Height: 300, Background: surface }}
  Children {{
    Rect {{
      Name: target
      Style {{ Position: absolute, {anchor}, Background: primary }}
    }}
    Overlay {{
      Name: badge
      Anchor: target
      Open: <| shown |>
      Dismissible: false
{overlay_lines}      Children {{
        Rect {{
          Name: dot
          Style {{ Width: 12, Height: 12, Background: error }}
        }}
      }}
    }}
  }}
}}
""")
    app = App(root=tmp_path, width=400, height=300)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(50)
    return view


TOOLTIP = """---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Width: 400, Height: 300, Background: surface }}
  Children {{
    Rect {{
      Name: target
      Style {{ Width: 60, Height: 40, Background: primary }}
      Tooltip {{ Text: hi, Placement: {placement} }}
    }}
  }}
}}
"""


def dot(view):
    node = view.node("root.badge.dot")
    return node.get("layout_x"), node.get("layout_y")


@pytest.mark.parametrize("placement, expected", [("top_start", (144.0, 114.0)), ("top_end", (204.0, 114.0)), ("bottom_start", (144.0, 154.0)),
                                                 ("bottom_end", (204.0, 154.0)), ("center", (174.0, 134.0))])
def test_a_corner_or_the_centre_puts_the_overlays_centre_on_that_point_of_the_anchor(tmp_path, placement, expected):
    assert dot(opened(tmp_path, f"      Placement: {placement}\n")) == expected


def test_an_offset_moves_the_point(tmp_path):
    assert dot(opened(tmp_path, "      Placement: top_end\n      Offset: [2, -2]\n")) == (206.0, 112.0)


def test_a_side_placement_is_as_it_was(tmp_path):
    assert dot(opened(tmp_path, "      Placement: below\n")) == (150.0, 160.0)


def test_a_side_flips_at_the_window_edge_and_flip_false_keeps_it_there(tmp_path):
    near_top = "X: 150, Y: 4, Width: 60, Height: 40"
    flipped = dot(opened(tmp_path / "a", "      Placement: above\n", anchor=near_top))
    kept = dot(opened(tmp_path / "b", "      Placement: above\n      Flip: false\n", anchor=near_top))
    assert flipped[1] > 40 and kept[1] < 0  # flipped below the anchor, or left above it and off the window


def test_a_corner_is_never_moved_to_fit(tmp_path):
    assert dot(opened(tmp_path, "      Placement: top_end\n", anchor="X: 394, Y: 2, Width: 6, Height: 6")) == (394.0, -4.0)


def test_the_overlay_follows_its_anchor(tmp_path):
    view = opened(tmp_path, "      Placement: top_end\n")
    view.window.advance(16)
    assert dot(view) == (204.0, 114.0)


@pytest.mark.parametrize("offset", ["5", "[1]", "[1, 2, 3]", "[a, b]", "[true, 1]"])
def test_an_offset_that_is_not_a_pair_of_numbers_is_named(tmp_path, offset):
    with pytest.raises(Exception) as caught:
        opened(tmp_path, f"      Offset: {offset}\n")
    text = str(caught.value)
    assert "offset is a pair of pixels" in text or ("'offset' takes a list" in text and "Main_View.tdl:" in text)  # a number is refused at load; a wrong list when it is shown


def test_a_placement_that_is_not_one_is_refused_with_the_choices(tmp_path):
    with pytest.raises(LoadError) as caught:
        opened(tmp_path, "      Placement: above_end\n")
    assert "top_start" in str(caught.value) and "center" in str(caught.value) and "Main_View.tdl" in str(caught.value)


def test_a_tooltip_may_use_a_corner(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(TOOLTIP.format(placement="top_end"))
    app = App(root=tmp_path, width=400, height=300)
    app.bind(VM)
    view = app.open_view("Main")
    assert view.node("root.target") is not None
    with pytest.raises(LoadError, match="tooltip placement is one of"):
        (tmp_path / "Views" / "Main_View.tdl").write_text(TOOLTIP.format(placement="sideways"))
        App(root=tmp_path).open_view("Main")
