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


@pytest.mark.parametrize("level, height", [("", 48), ("default", 48), ("compact", 40), ("dense", 32)])
def test_the_dock_tab_height_follows_the_density_AC_DKP_1(level, height):
    assert tabs_at(level)[0] == height


def test_the_dock_tab_is_narrower_with_less_padding_AC_DKP_1():
    default, dense = tabs_at("default")[1], tabs_at("dense")[1]
    assert default - dense == 2 * (16 - 8)


@pytest.mark.parametrize("level, height, start, gap", [("", 40, 12, 8), ("default", 40, 12, 8), ("compact", 32, 8, 8), ("dense", 28, 4, 4)])
def test_the_title_bar_follows_the_density_AC_TTB_1(level, height, start, gap):
    tel._app_density.set(level)
    assert (title_bar._bar_height(), title_bar._start_padding(), title_bar._gap()) == (height, start, gap)
