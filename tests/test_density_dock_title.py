"""Density for the dock tabs and the title bar (UX spec: AC-DKP-1, AC-TTB-1): tab 48/40/32 with padding 16/12/8, bar 40/32/28 with start padding 12/8/4 and gap 8/8/4; no density is what they always were."""

import pytest
import tess_re

from tess_ui import tel
from tess_ui.docking import Dock
from tess_ui.spec import title_bar


@pytest.fixture(autouse=True)
def reset():
    yield
    tel._app_density.set("")


def tabs_at(level):
    tel._app_density.set(level)
    window = tess_re.Window(width=900, height=500)
    dock = Dock(window)
    window.root.add_child(dock.add_zone("left", 220))
    dock.add_panel("left", window.create("box", width=10, height=10), "Files")
    window.advance(16)
    node = dock._zones["left"].tabs[0].node
    return node.get("layout_height"), node.get("layout_width")


@pytest.mark.parametrize("level, height", [("", 48), ("default", 48), ("compact", 32), ("dense", 28)])
def test_the_dock_tab_height_follows_the_density_AC_DKP_1(level, height):
    assert tabs_at(level)[0] == height


def test_the_dock_tab_is_narrower_with_less_padding_AC_DKP_1():
    default, dense = tabs_at("default")[1], tabs_at("dense")[1]
    assert default - dense == 2 * (16 - 8)


@pytest.mark.parametrize("level, height, start, gap", [("", 40, 12, 8), ("default", 40, 12, 8), ("compact", 32, 8, 8), ("dense", 28, 4, 4)])
def test_the_title_bar_follows_the_density_AC_TTB_1(level, height, start, gap):
    tel._app_density.set(level)
    assert (title_bar._bar_height(), title_bar._start_padding(), title_bar._gap()) == (height, start, gap)


@pytest.mark.parametrize("level", ["", "default", "compact", "dense"])
def test_the_close_button_is_a_24_dp_hit_area_with_a_14_dp_centred_glyph_and_8_dp_before_it_AC_DKP_2(level):
    tel._app_density.set(level)
    window = tess_re.Window(width=900, height=500)
    dock = Dock(window)
    window.root.add_child(dock.add_zone("left", 220))
    dock.add_panel("left", window.create("box", width=10, height=10), "Files", closable=True)
    window.advance(16)
    tab = dock._zones["left"].tabs[0]
    close = next(child for child in tab.node.children() if child.get("role") == "button")
    glyph = close.children()[0]
    assert (close.get("layout_width"), close.get("layout_height")) == (24.0, 24.0)
    assert (glyph.get("layout_width"), glyph.get("layout_height")) == (14.0, 14.0)
    centre = lambda node: (node.get("layout_x") + node.get("layout_width") / 2, node.get("layout_y") + node.get("layout_height") / 2)  # noqa: E731
    assert max(abs(a - b) for a, b in zip(centre(glyph), centre(close))) <= 0.5  # the glyph is centred in the hit area
    assert close.get("layout_x") - (tab.label.get("layout_x") + tab.label.get("layout_width")) >= 8.0  # the gap, and no overlap with the label
    top = tab.node.get("layout_y")
    assert close.get("layout_y") >= top and close.get("layout_y") + 24 <= top + tab.node.get("layout_height")  # inside the tab, at every density
