"""The desktop icon toolbar (ux spec Toolbar, ADR-0029: AC-TLB-14 to 18): 40 and 32 dp bars with 32 and 28 dp buttons at compact and dense, group dividers that no arrow stops at, toggles that show `pressed`,
tooltips that read "Name (Shortcut)", role `toolbar`."""

import pytest

from tess_ui import App, Signal, ViewModel

ITEMS = (
    "Items: <| [{'value': 'save', 'icon': 'content_save', 'label': 'Save', 'shortcut': 'Ctrl+S'}, {'value': 'undo', 'icon': 'undo', 'label': 'Undo', 'shortcut': 'Ctrl+Z'}, {'divider': True}, "
    "{'value': 'fmt', 'icon': 'format_align_left', 'label': 'Format file'}, {'divider': True}, "
    "{'value': 'apply', 'icon': 'sync', 'label': 'Apply as I edit', 'toggle': True, 'pressed': apply_on}] |>"
)


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.chosen = Signal("")
        self.apply_on = Signal(False)


def opened(tmp_path, density="compact", width=600):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Width: {width}, Height: 300, Align_Content: top_left, Flex_Direction: vertical }}
  Children {{
    Toolbar {{
      Name: tb
      {ITEMS}
      Chosen: <| chosen |>
    }}
  }}
}}
""")
    app = App(root=tmp_path, width=width, height=300, density=density)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(6):
        view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


def settle(view, n=8):
    for _ in range(n):
        view.window.advance(16)


def item(view, value):
    return view.node(f"root.tb.group.entry[{value}].item")


@pytest.mark.parametrize("level, bar, button, icon", [(None, 64, 40, 24), ("default", 64, 40, 24), ("compact", 40, 32, 20), ("dense", 32, 28, 18)])
def test_the_bar_and_its_buttons_have_the_size_of_the_density_AC_TLB_14(tmp_path, level, bar, button, icon):
    view, _ = opened(tmp_path, level)
    assert view.node("root.tb").get("layout_height") == bar
    for value in ("save", "undo", "fmt", "apply"):
        assert item(view, value).get("layout_height") == item(view, value).get("layout_width") == (button if level else 40)
    top = view.node("root.tb").get("layout_y")
    mid = lambda n: n.get("layout_y") + n.get("layout_height") / 2 - top  # noqa: E731
    assert abs(mid(item(view, "save")) - bar / 2) <= 0.5


def test_the_role_is_toolbar_and_a_press_chooses_the_value(tmp_path):
    view, vm = opened(tmp_path)
    assert view.node("root.tb").get("role") == "toolbar"
    view.window.simulate("click", node=item(view, "undo"))
    settle(view)
    assert vm.chosen.get() == "undo"


def test_a_divider_is_a_thin_line_between_the_groups_and_no_arrow_stops_at_it_AC_TLB_18(tmp_path):
    view, _ = opened(tmp_path)
    dividers = [k for k in view._built.specs if k.endswith(".divider")]
    assert len(dividers) == 2
    for key in dividers:
        node = view._built.nodes[key]
        assert node.get("layout_width") == 1 and node.get("layout_height") < 32 and view._built.specs[key]["a11y"]["role"] == "separator"
    item(view, "undo").focus()
    settle(view, 2)
    focus = lambda: [i for i, n in view._built.nodes.items() if n.get("focused") is True]  # noqa: E731
    view.window.simulate("key_down", key="arrow_right")
    settle(view, 2)
    assert focus() == ["root.tb.group.entry[fmt].item"]


def test_a_toggle_shows_pressed_and_follows_the_callers_value_AC_TLB_17(tmp_path):
    view, vm = opened(tmp_path)
    assert item(view, "apply").get("pressed") is False and item(view, "save").get("pressed") in (None, False)
    view.window.simulate("click", node=item(view, "apply"))
    settle(view)
    assert vm.chosen.get() == "apply"
    vm.apply_on.set(True)
    settle(view)
    assert item(view, "apply").get("pressed") is True


def test_the_tooltip_reads_the_name_and_the_shortcut_and_the_name_stays_the_accessible_name_AC_TLB_15_AC_TLB_16(tmp_path):
    view, _ = opened(tmp_path)
    assert item(view, "save").get("label") == "Save"
    def tips():
        return [t.get("text") for layer in view._tips.values() for t in layer[0].children()]

    view.window.simulate("key_down", key="tab")
    settle(view, 3)
    assert tips() == ["Save (Ctrl+S)"]
    view.window.simulate("key_down", key="arrow_right")
    view.window.simulate("key_down", key="arrow_right")
    settle(view, 3)
    assert tips() == ["Format file"]  # no shortcut: the name only
