"""The chip follows the density (ux spec Chip, ADR-0029): 32, 28 and 24 dp high, the icon, avatar and close icon scale with it."""

import pytest

from test_density_cascade import opened

BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 300, Gap: 8 }
  Children {
    Chip { Name: plain, Label: Share, Variant: assist }
    Chip { Name: iconic, Label: Share, Variant: assist, Icon: home }
    Chip { Name: closing, Label: Tag, Variant: input, Removable: true }
  }
}
"""


def sizes(tmp_path, level):
    view = opened(tmp_path, BODY, level)
    n = view._built.outer
    return (n["root.plain"].get("layout_height"), n["root.iconic.icon"].get("layout_width"), n["root.closing.close"].get("layout_width"),
            n["root.plain.label"].get("layout_x") - n["root.plain"].get("layout_x"), n["root.iconic.icon"].get("layout_x") - n["root.iconic"].get("layout_x"))


@pytest.mark.parametrize("level, height, icon, close, pad, pad_icon", [(None, 32, 18, 18, 16, 8), ("default", 32, 18, 18, 16, 8), ("compact", 28, 16, 16, 12, 8), ("dense", 24, 14, 14, 8, 4)])
def test_the_chip_icon_close_and_padding_follow_the_density(tmp_path, level, height, icon, close, pad, pad_icon):
    assert sizes(tmp_path, level) == (height, icon, close, pad, pad_icon)
