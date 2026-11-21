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
