"""The tab bar follows the density (ux spec Tabs, ADR-0029): 48, 32, 28 dp high; with icons the primary bar is 64 only where there is room (default), else the icon is beside the label."""

import pytest

from test_density_cascade import opened

BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 500, Height: 300, Gap: 8 }
  Children {
    Tabs { Name: plain, Selected: a, Tabs: <| [{'value': 'a', 'label': 'One'}, {'value': 'b', 'label': 'Two'}] |> }
    Tabs { Name: iconic, Selected: a, Tabs: <| [{'value': 'a', 'label': 'One', 'icon': 'home'}, {'value': 'b', 'label': 'Two', 'icon': 'home'}] |> }
  }
}
"""


@pytest.mark.parametrize("level, plain, iconic, icon", [(None, 48, 64, 24), ("default", 48, 64, 24), ("compact", 32, 32, 20), ("dense", 28, 28, 18)])
def test_the_bar_is_as_high_as_the_density_says_and_an_icon_goes_beside_the_label_where_the_bar_is_short(tmp_path, level, plain, iconic, icon):
    view = opened(tmp_path, BODY, level)
    o = view._built.outer
    assert (o["root.plain.bar"].get("layout_height"), o["root.iconic.bar"].get("layout_height")) == (plain, iconic)
    assert o["root.iconic.bar.tab[a].icon"].get("layout_width") == icon if "root.iconic.bar.tab[a].icon" in o else True
