"""State layers on the Material components (UX spec ADR-0009, ADR-0013; AC-STL): hover 8 percent, keyboard focus 10, none for pointer focus, none when disabled, one layer at a time (focus beats hover), with the opacities from one token table."""

import pytest

from tess_ui import App, ViewModel, tokens
from tess_ui import interaction

#: component call -> a name
COMPONENTS = {
    "button": "Button { Name: c, Label: Go }",
    "icon_button": "IconButton { Name: c, Icon: home, Label: Home }",
    "chip": "Chip { Name: c, Label: Tag }",
    "list_item": "ListItem { Name: c, Headline: One }",
    "menu_item": "MenuItem { Name: c, Label: Open, Handlers { On_Click: noop } }",
    "fab": "Fab { Name: c, Icon: home, Handlers { On_Click: noop } }",
    "tree_node": "TreeNode { Name: c, Label: Node, Handlers { On_Click: noop } }",
}


class VM(ViewModel):
    views = "main"

    def noop(self):
        pass


def opened(tmp_path, call, disabled=False):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    if disabled:
        call = call[: -len(" }")] + ", Disabled: true }"
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 300 }}
  Children {{
    {call}
  }}
}}
""")
    app = App(root=tmp_path, width=400, height=300, dark=False)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(4):
        view.window.advance(16)
    return view


def layer(view):
    found = view._interactions.get("root.c")
    return found


def run(view, ms=48):
    for _ in range(ms // 16 + 1):
        view.window.advance(16)


def centre(view):
    node = view._built.outer["root.c"]
    return node.get("layout_x") + node.get("layout_width") / 2, node.get("layout_y") + node.get("layout_height") / 2


def test_the_opacities_are_one_table_the_modules_read():
    assert tokens.STATE_LAYER == {"hover": 0.08, "focus": 0.10, "pressed": 0.10, "dragged": 0.16}
    assert (interaction.HOVERED, interaction.FOCUSED, interaction.PRESSED, interaction.DRAGGED) == tuple(tokens.STATE_LAYER.values())


@pytest.mark.parametrize("name", COMPONENTS)
def test_hover_is_8_percent_and_leaving_removes_it_AC_STL(tmp_path, name):
    view = opened(tmp_path, COMPONENTS[name])
    it = layer(view)
    assert it is not None, f"{name} has no interaction"
    x, y = centre(view)
    view.window.simulate("pointer_move", x=x, y=y)
    run(view)
    assert it.layer.get("opacity") == pytest.approx(tokens.STATE_LAYER["hover"])
    view.window.simulate("pointer_move", x=395, y=295)
    run(view)
    assert it.layer.get("opacity") == 0.0


@pytest.mark.parametrize("name", COMPONENTS)
def test_keyboard_focus_is_10_percent_and_beats_hover_AC_STL(tmp_path, name):
    view = opened(tmp_path, COMPONENTS[name])
    it = layer(view)
    view.window.simulate("key_down", key="tab")
    run(view)
    assert it.layer.get("opacity") == pytest.approx(tokens.STATE_LAYER["focus"])
    x, y = centre(view)
    view.window.simulate("pointer_move", x=x, y=y)
    run(view)
    assert it.layer.get("opacity") == pytest.approx(tokens.STATE_LAYER["focus"])  # one layer at a time: focus over hover


@pytest.mark.parametrize("name", [n for n in COMPONENTS if n != "tree_node"])
def test_a_disabled_component_shows_no_layer_AC_STL(tmp_path, name):
    view = opened(tmp_path, COMPONENTS[name], disabled=True)
    it = layer(view)
    x, y = centre(view)
    view.window.simulate("pointer_move", x=x, y=y)
    run(view)
    assert it is None or it.layer.get("opacity") == 0.0
