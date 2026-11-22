"""State layers on the Material components (UX spec ADR-0009, ADR-0013; AC-STL): hover 8 percent, keyboard focus 10, none for pointer focus, none when disabled, one layer at a time (focus beats hover), with the opacities from one token table."""

from layers import layer_of
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
    assert layer_of(it).get("opacity") == pytest.approx(tokens.STATE_LAYER["hover"], abs=0.005)
    view.window.simulate("pointer_move", x=395, y=295)
    run(view)
    assert layer_of(it).get("opacity") == 0.0


@pytest.mark.parametrize("name", COMPONENTS)
def test_keyboard_focus_is_10_percent_and_beats_hover_AC_STL(tmp_path, name):
    view = opened(tmp_path, COMPONENTS[name])
    it = layer(view)
    view.window.simulate("key_down", key="tab")
    run(view)
    assert layer_of(it).get("opacity") == pytest.approx(tokens.STATE_LAYER["focus"], abs=0.005)
    x, y = centre(view)
    view.window.simulate("pointer_move", x=x, y=y)
    run(view)
    assert layer_of(it).get("opacity") == pytest.approx(tokens.STATE_LAYER["focus"], abs=0.005)  # one layer at a time: focus over hover


@pytest.mark.parametrize("name", [n for n in COMPONENTS if n != "tree_node"])
def test_a_disabled_component_shows_no_layer_AC_STL(tmp_path, name):
    view = opened(tmp_path, COMPONENTS[name], disabled=True)
    it = layer(view)
    x, y = centre(view)
    view.window.simulate("pointer_move", x=x, y=y)
    run(view)
    assert it is None or layer_of(it).get("opacity") == 0.0


def test_the_engine_paints_hover_and_focus_over_the_fill_in_the_scheme_colour_AC_STL(tmp_path):
    """The layers are the engine's `hover_layer` and `focus_layer`: the pixels of a button change by the table's percentages and come back."""
    view = opened(tmp_path, COMPONENTS["button"])
    node = view._built.outer["root.c"]

    def pixel():
        rgba, width, _ = view.window.snapshot()
        x, y = int(node.get("layout_x") + 6), int(node.get("layout_y") + node.get("layout_height") / 2)
        return tuple(rgba[(y * width + x) * 4:][:3])

    rest = pixel()
    x, y = centre(view)
    view.window.simulate("pointer_move", x=x, y=y)
    run(view, 200)
    hovered = pixel()
    assert hovered != rest
    view.window.simulate("pointer_move", x=395, y=295)
    run(view, 200)
    assert pixel() == rest
    view.window.simulate("key_down", key="tab")
    run(view, 200)
    focused = pixel()
    assert focused != rest and focused != hovered


def test_the_engine_draws_the_focus_outline_on_keyboard_focus_only_AC_FOC(tmp_path):
    """The ring is `focus_outline_*`: 3 px wide, 2 px off the node, in the scheme's ring colour, on keyboard focus and not on a click."""
    view = opened(tmp_path, COMPONENTS["button"])
    node = view._built.outer["root.c"]
    rgba_of = lambda: view.window.snapshot()  # noqa: E731
    run(view, 100)
    right = int(node.get("layout_x") + node.get("layout_width"))
    y = int(node.get("layout_y") + node.get("layout_height") / 2)

    def row():
        rgba, width, _ = rgba_of()
        return [tuple(rgba[(y * width + x) * 4:][:3]) for x in range(right, right + 7)]

    before = row()
    assert before[2] == before[3] == before[4]  # nothing drawn beside the node
    view.window.simulate("key_down", key="tab")
    run(view, 100)
    after = row()
    assert after[0] == before[0]  # the 2 px gap (a fractional node edge antialiases pixel 1)
    assert after[2] == after[3] == after[4] != before[2]  # the 3 px ring, one colour
    assert after[5] == before[5]
