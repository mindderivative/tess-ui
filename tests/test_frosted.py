"""Frosted navigation, search and menus (step 72): `frosted: true` makes the surface 72% of its colour with a 20 pixel backdrop blur."""

import pytest

from tess_ui import App, tokens

ITEMS = "Items { Item { Value: a, Label: Alpha, Icon: home } Item { Value: b, Label: Beta, Icon: search } }"
ROWS = "Items { Item { Value: a, Label: Alpha } Item { Value: b, Label: Beta } }"

# (widget line, the node holding the surface, the colour role it has)
CASES = {
    "rail": (f"NavigationRail {{ Name: w, {ITEMS}%s }}", "root.w", "surface"),
    "drawer": (f"NavigationDrawer {{ Name: w, {ITEMS}%s }}", "root.w", "surface"),
    "bar": ("SearchBar { Name: w%s }", "root.w", "surface_container_high"),
    "top": ("TopAppBar { Name: w, Title: Notes%s }", "root.w", "surface"),
    "menu": (f"Menu {{ Name: w, Open: <| o |>, {ROWS}%s }}", "root.w.surface", "surface_container"),
    "search": ("SearchView { Name: w, Open: <| o |>%s }", "root.w.panel", "surface_container_high"),
    "modal": (f"NavigationDrawerModal {{ Name: w, Open: <| o |>, {ITEMS}%s }}", "root.w.sheet", "surface_container_low"),
}


def opened(tmp_path, case, frosted):
    line, node_id, role = CASES[case]
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        """---
TDL: 0.2
Name: main
---
Container {
  Name: main
  State { O: true }
  Style { Width: 500, Height: 400, Align_Content: top_left }
  Children {
    """ + line % (", Frosted: true" if frosted else "") + """
  }
}
""")
    app = App(root=tmp_path, width=500, height=400)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(8):
        view.window.advance(16)
    return view, node_id, role


@pytest.mark.parametrize("case", sorted(CASES))
def test_frosted_is_a_translucent_surface_with_a_backdrop_blur(tmp_path, case):
    view, node_id, role = opened(tmp_path, case, True)
    node = view.node(node_id)
    colour = (view._scheme or tokens.BASELINE)[role]
    assert node.get("fill")[:3] == colour[:3] and node.get("fill")[3] == round(0.72 * 255)
    assert node.get("backdrop_blur") == 20.0


@pytest.mark.parametrize("case", sorted(CASES))
def test_the_default_is_solid_with_no_blur(tmp_path, case):
    view, node_id, role = opened(tmp_path, case, False)
    node = view.node(node_id)
    assert node.get("fill") == (view._scheme or tokens.BASELINE)[role] and node.get("backdrop_blur") == 0.0


def test_a_top_app_bar_keeps_its_scrolled_colour_when_frosted(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        """---
TDL: 0.2
Name: main
---
Container {
  Name: main
  Style { Width: 500, Height: 300 }
  Children {
    TopAppBar { Name: w, Title: T, Scrolled: true, Frosted: true }
  }
}
""")
    app = App(root=tmp_path, width=500, height=300)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(8):
        view.window.advance(16)
    fill = view.node("root.w").get("fill")
    assert fill[:3] == (view._scheme or tokens.BASELINE)["surface_container"][:3] and fill[3] == round(0.72 * 255)
