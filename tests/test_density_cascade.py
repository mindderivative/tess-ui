"""Density on every node (ADR-0029): `Density` on a node or a stylesheet rule cascades to what is inside; a number written on a node beats it."""

import pytest

from tess_ui import App, ViewModel
from tess_ui.spec.nodes import LoadError

HEADER = "---\nTDL: 0.2\nName: {name}\n---\n"


class VM(ViewModel):
    views = "main"


def opened(tmp_path, body, density="compact", sheet=None):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(HEADER.format(name="main") + body)
    options = {}
    if sheet is not None:
        (tmp_path / "app_Stylesheet.tdl").write_text("---\nTDL: 0.2\nName: app\n---\n" + sheet)
        options["stylesheet"] = tmp_path / "app_Stylesheet.tdl"
    app = App(root=tmp_path, width=500, height=600, density=density, **options)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(6):
        view.window.advance(16)
    return view


def height(view, node_id):
    return view._built.outer[node_id].get("layout_height")


ROWS = """Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 500, Height: 600 }}
  Children {{
    Button {{ Name: outside, Label: Out }}
    Container {{
      Name: pane
      {pane}
      Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 100% }}
      Children {{
        Button {{ Name: inside, Label: In {own} }}
        ListItem {{ Name: row, Headline: Row }}
        Container {{
          Name: deeper
          {deeper}
          Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 100% }}
          Children {{ Button {{ Name: nested, Label: Nested }} }}
        }}
      }}
    }}
  }}
}}
"""


def rows(tmp_path, pane="", own="", deeper="", app="compact", sheet=None):
    view = opened(tmp_path, ROWS.format(pane=pane, own=own, deeper=deeper), app, sheet)
    return tuple(height(view, f"root.{n}") for n in ("outside", "pane.inside", "pane.row", "pane.deeper.nested"))


def test_a_container_that_says_dense_makes_everything_inside_it_dense_and_nothing_outside(tmp_path):
    assert rows(tmp_path, pane="Density: dense") == (32, 28, 24, 28)


def test_the_nearest_ancestor_wins(tmp_path):
    assert rows(tmp_path, pane="Density: dense", deeper="Density: default") == (32, 28, 24, 40)


def test_an_element_own_density_wins_over_its_ancestors(tmp_path):
    assert rows(tmp_path, pane="Density: dense", own=", Density: default") [1] == 40


def test_no_density_anywhere_follows_the_app(tmp_path):
    assert rows(tmp_path, app="dense") == (28, 28, 24, 28)
    assert rows(tmp_path, app="default") == (40, 40, 40, 40)


def test_a_number_written_on_the_element_beats_every_density(tmp_path):
    view = opened(tmp_path, """Container {
  Name: main
  Density: dense
  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 500, Height: 600 }
  Children {
    Button { Name: fixed, Label: Fixed, Density: default, Style { Height: 50 } }
    Button { Name: plain, Label: Plain }
  }
}
""")
    assert (height(view, "root.fixed"), height(view, "root.plain")) == (50, 28)


SHEET = """Styles {
  Rule { Classes: [tight], Density: dense }
}
"""


def test_a_stylesheet_rule_can_set_the_density_of_a_class(tmp_path):
    body = ROWS.format(pane="Classes: [tight]", own="", deeper="")
    view = opened(tmp_path, body, "compact", SHEET)
    assert tuple(height(view, f"root.{n}") for n in ("outside", "pane.inside", "pane.row", "pane.deeper.nested")) == (32, 28, 24, 28)


def test_a_nodes_own_density_is_over_the_rule(tmp_path):
    body = ROWS.format(pane="Classes: [tight]\n      Density: default", own="", deeper="")
    view = opened(tmp_path, body, "compact", SHEET)
    assert height(view, "root.pane.inside") == 40


def test_a_density_that_is_not_a_level_is_refused_where_it_is_written(tmp_path):
    with pytest.raises(LoadError) as raised:
        opened(tmp_path, ROWS.format(pane="Density: tiny", own="", deeper=""))
    assert "density is one of default, compact, dense" in str(raised.value) and "Main_View.tdl:12" in str(raised.value).replace("\\", "/")
