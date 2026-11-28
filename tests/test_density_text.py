"""The body text follows the density (ADR-0029): a row label is `body_large` 16/24 at `default` and with no density, 14/20 at `compact`, 13 at `dense` (a 19 dp line: 1.43 times 13, the engine has no 13 dp role)."""

import pytest

from test_density_cascade import opened

BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 500, Height: 600 }
  Children {
    TreeNode { Name: tn, Label: Alpha }
    MenuItem { Name: mi, Label: Open }
    ListItem { Name: li, Headline: One }
    Container {
      Name: pane
      Density: dense
      Style { Flex_Direction: vertical, Align_Content: top_left, Width: 100% }
      Children { TreeNode { Name: dense_tn, Label: Beta } }
    }
  }
}
"""


def label_lines(tmp_path, density):
    view = opened(tmp_path, BODY, density)
    outer = view._built.outer
    headline = next(i for i in outer if i.startswith("root.li") and i.endswith("headline"))
    return tuple(outer[i].get("layout_height") for i in ("root.tn.label", "root.mi.label", headline, "root.pane.dense_tn.label"))


@pytest.mark.parametrize("level, tree, menu, listed, in_dense_pane", [
    (None, 24, 20, 24, 19),     # no density: the Material sizes; the dense pane is dense whatever the app says
    ("default", 24, 20, 24, 19),
    ("compact", 20, 20, 20, 19),
    ("dense", 19, 19, 19, 19),
])
def test_a_row_label_is_the_body_text_of_its_density(tmp_path, level, tree, menu, listed, in_dense_pane):
    assert label_lines(tmp_path, level) == (tree, menu, listed, in_dense_pane)
