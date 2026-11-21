"""Density for List item, Accordion header and Menu item (UX spec ADR-0002: AC-LSI-02, AC-ACC-01, AC-MEN-1): the row heights of the table at three levels, and the Material sizes when no density is asked."""

import pytest

from tess_ui import App, ViewModel

BODY = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 500 }
  Children {
    ListItem { Name: li, Headline: One }
    ListItem { Name: li2, Headline: Two, Supporting: More }
    Accordion { Name: ac, Title: Details, Expanded: false }
    MenuItem { Name: mi, Label: Open }
  }
}
"""


class VM(ViewModel):
    views = "main"


def opened(tmp_path, density):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text("---\nTDL: 0.2\nName: main\n---\n" + BODY)
    app = App(root=tmp_path, width=400, height=500, density=density)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(6):
        view.window.advance(16)
    return view


def heights(view):
    return tuple(view._built.outer[i].get("layout_height") for i in ("root.li", "root.li2", "root.ac.header", "root.mi"))


@pytest.mark.parametrize("level, row, header, item", [("default", 40, 40, 40), ("compact", 32, 32, 32), ("dense", 24, 24, 28)])
def test_rows_follow_the_density_table_AC_LSI_02_AC_ACC_01_AC_MEN_1(tmp_path, level, row, header, item):
    li, li2, ac, mi = heights(opened(tmp_path, level))
    assert (li, ac, mi) == (row, header, item)
    assert li2 == row + 20  # a second line adds one body line, 20 dp


def test_no_density_is_the_material_sizes(tmp_path):
    assert heights(opened(tmp_path, None)) == (56, 72, 56, 48)


CONTROLS = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 500 }
  Children {
    Button { Name: b, Label: Go }
    IconButton { Name: ib, Icon: home, Label: Home }
  }
}
"""


def controls_at(tmp_path, density):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text("---\nTDL: 0.2\nName: main\n---\n" + CONTROLS)
    app = App(root=tmp_path, width=400, height=500, density=density)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(6):
        view.window.advance(16)
    outer = view._built.outer
    return outer["root.b"].get("layout_height"), outer["root.ib"].get("layout_height"), outer["root.ib"].get("layout_width")


@pytest.mark.parametrize("level, size", [("default", 40), ("compact", 32), ("dense", 28)])
def test_button_and_icon_button_follow_the_density_table_AC_BTN_1_AC_ICB_1(tmp_path, level, size):
    assert controls_at(tmp_path, level) == (size, size, size)


def test_no_density_keeps_the_buttons_as_they_were(tmp_path):
    assert controls_at(tmp_path, None) == (40, 40, 40)


def test_making_an_app_does_not_run_the_effects_of_views_that_are_still_alive(tmp_path):
    """A reactive density made every view of a finished test run its effect again when the next App was made (a video player's old frame then raised in the next test)."""
    from tess_ui import Effect, tel

    runs = []
    keep = Effect(lambda: runs.append(tel.HOST_FUNCTIONS["app_density"]()))
    before = len(runs)
    App(root=tmp_path, density="compact")
    App(root=tmp_path)
    assert len(runs) == before
    keep.dispose()
FIELD = """Container {
  Name: main
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 500 }
  Children {
    TextField { Name: f, Label: Name, Variant: outlined }
  }
}
"""


def field_at(tmp_path, density):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text("---\nTDL: 0.2\nName: main\n---\n" + FIELD)
    app = App(root=tmp_path, width=400, height=500, density=density)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(6):
        view.window.advance(16)
    return view


@pytest.mark.parametrize("level, height, gap", [("compact", 32, 4), ("dense", 28, 2)])
def test_a_compact_or_dense_field_has_its_label_above_the_container_AC_TXF_3_AC_TXF_17(tmp_path, level, height, gap):
    view = field_at(tmp_path, level)
    box, label = view._built.outer["root.f.box"], view._built.outer["root.f.external_label"]
    assert box.get("layout_height") == height  # the container height is the table's, the label is outside it
    assert label.get("layout_y") + label.get("layout_height") + gap == pytest.approx(box.get("layout_y"), abs=0.6)
    assert "root.f.box.label_box" not in view._built.outer


@pytest.mark.parametrize("density", [None, "default"])
def test_the_default_keeps_the_floating_label_in_a_56_container_AC_TXF_19(tmp_path, density):
    view = field_at(tmp_path, density)
    assert view._built.outer["root.f.box"].get("layout_height") >= 56
    assert "root.f.box.label_box" in view._built.outer and "root.f.external_label" not in view._built.outer
