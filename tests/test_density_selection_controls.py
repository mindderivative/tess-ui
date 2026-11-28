"""The checkbox and the radio button follow the density (ux spec Checkbox, Radio Button; ADR-0029): the hit target and the state layer are the control height of the level (40, 32, 28) and not 48 and 40, the box is
18, 16, 14 and the ring 20, 18, 16; with no density they keep their Material sizes."""

import pytest

from test_density_cascade import opened

BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 300, Gap: 8 }
  Children {
    Checkbox { Name: c, Label: Agree }
    RadioButton { Name: r, Label: Yes, Group: g }
    Container {
      Name: pane
      Density: dense
      Style { Flex_Direction: vertical, Align_Content: top_left, Gap: 8 }
      Children { Checkbox { Name: dense_c, Label: Small } }
    }
  }
}
"""


def measure(tmp_path, level):
    view = opened(tmp_path, BODY, level)
    c, r, d = (view._built.controls[f"root.{n}"] for n in ("c", "r", "pane.dense_c"))
    outer = view._built.outer
    return ((outer["root.c"].get("layout_width"), outer["root.c"].get("layout_height")), c.box.get("width"), c.surface.get("width"),
            (outer["root.r"].get("layout_width"), outer["root.r"].get("layout_height")), r.ring.get("width"), r.dot.get("width"), d.box.get("width"))


@pytest.mark.parametrize("level, hit, box, layer, ring, dense_box", [
    (None, (48, 48), 18, 40, 20, 14),
    ("default", (40, 40), 18, 40, 20, 14),
    ("compact", (32, 32), 16, 32, 18, 14),
    ("dense", (28, 28), 14, 28, 16, 14),
])
def test_the_target_the_state_layer_the_box_and_the_ring_follow_the_density(tmp_path, level, hit, box, layer, ring, dense_box):
    c_hit, c_box, c_layer, r_hit, r_ring, r_dot, d_box = measure(tmp_path, level)
    assert (c_hit, c_box, c_layer) == (hit, box, layer)
    assert (r_hit, r_ring, r_dot) == (hit, ring, ring / 2) and d_box == dense_box
