"""#166, #167: the Material 3 tab bar -- primary and secondary, an indicator that slides, arrows that move and choose, badges and icons."""

import pytest

from tess_ui import App, Signal, ViewModel, tokens
from tess_ui.shipped import shipped_views

TABS = """Tabs {
    Item { Value: flights, Label: Flights, Icon: home }
    Item { Value: trips, Label: Trips, Icon: search, Badge: 3 }
    Item { Value: explore, Label: Explore, Icon: menu }
  }"""
PLAIN = """Tabs {
    Item { Value: a, Label: One }
    Item { Value: b, Label: Two }
    Item { Value: c, Label: Three }
  }"""


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.tab = Signal("trips")
        self.plain = Signal("a")


def opened(tmp_path, widget, **kwargs):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        '---\nTDL: 0.2\nName: main\nTesserae: "0.6"\n---\n'
        "Container {\n  Name: main\n  Style { Flex_Direction: vertical, Align_Content: top_left, Width: 500, Height: 300 }\n  Children {\n" + widget + "\n  }\n}\n")
    app = App(root=tmp_path, **kwargs)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(3):
        view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


ICONS = f"Tabs {{ Name: t, {TABS}, Selected: <| tab |> }}"
BARE = f"Tabs {{ Name: t, {PLAIN}, Selected: <| plain |> }}"


def tab(view, value, node="t"):
    return view.node(f"root.{node}.bar.tab[{value}]")


def indicator(view, node="t"):
    return view.node(f"root.{node}.bar.indicator")


def role(view, name):
    return (view._scheme or tokens.BASELINE)[name]


def settle(view):
    for _ in range(40):
        view.window.advance(16)


def click(view, value):
    view.window.simulate("click", node=tab(view, value))
    settle(view)


def test_it_is_shipped():
    assert "Tabs" in shipped_views()


def test_a_bar_of_equal_tabs_over_a_divider(tmp_path):
    view, _ = opened(tmp_path, BARE)
    xs = [tab(view, v).get("layout_x") for v in "abc"]
    assert xs == [xs[0], xs[0] + 120, xs[0] + 240] and tab(view, "a").get("layout_width") == 120.0
    assert view.node("root.t.bar").get("layout_height") == 48.0
    assert view.node("root.t.divider").get("layout_y") == view.node("root.t.bar").get("layout_y") + 48.0
    assert view.node("root.t.bar").get("role") == "tablist"


def test_icons_make_the_bar_sixty_four_tall(tmp_path):
    view, _ = opened(tmp_path, ICONS)
    assert view.node("root.t.bar").get("layout_height") == 64.0


def test_the_selected_tab_is_primary_and_the_rest_on_surface_variant(tmp_path):
    view, _ = opened(tmp_path, BARE)
    assert view.node("root.t.bar.tab[a].label").get("fill") == role(view, "primary")
    assert view.node("root.t.bar.tab[b].label").get("fill") == role(view, "on_surface_variant")
    assert view.node("root.t.bar.tab[a].label").get("font_size") == 14.0


def test_each_tab_is_a_tab_that_knows_if_it_is_selected(tmp_path):
    view, _ = opened(tmp_path, BARE)
    assert [tab(view, v).get("role") for v in "abc"] == ["tab"] * 3
    assert [tab(view, v).get("selected") for v in "abc"] == [True, False, False]
    assert tab(view, "b").get("label") == "Two"


def test_the_primary_indicator_is_three_tall_rounded_on_top_and_under_the_selected_tab(tmp_path):
    view, _ = opened(tmp_path, BARE)
    ind = indicator(view)
    assert ind.get("layout_height") == 3.0 and ind.get("fill") == role(view, "primary")
    assert ind.get("corner_radius") == (3.0, 3.0, 0.0, 0.0)
    assert ind.get("layout_x") == tab(view, "a").get("layout_x") + 12 and ind.get("layout_width") == 96.0
    assert ind.get("layout_y") == view.node("root.t.bar").get("layout_y") + 46


def test_the_secondary_indicator_is_two_tall_across_the_whole_tab(tmp_path):
    view, _ = opened(tmp_path, BARE.replace("Name: t,", "Name: t, Variant: secondary,"))
    ind = indicator(view)
    assert ind.get("layout_height") == 2.0 and ind.get("layout_width") == 120.0 and ind.get("layout_x") == tab(view, "a").get("layout_x")
    assert ind.get("corner_radius") == 0.0


def test_pressing_a_tab_chooses_it_and_the_indicator_slides_there(tmp_path):
    view, vm = opened(tmp_path, BARE)
    start = indicator(view).get("layout_x")
    view.window.simulate("click", node=tab(view, "c"))
    for _ in range(6):
        view.window.advance(16)
    assert vm.plain.get() == "c" and start < indicator(view).get("layout_x") < start + 240  # on its way
    settle(view)
    assert indicator(view).get("layout_x") == start + 240 and view.node("root.t.bar.tab[c].label").get("fill") == role(view, "primary")


def test_the_indicator_follows_a_signal_too(tmp_path):
    view, vm = opened(tmp_path, BARE)
    vm.plain.set("b")
    settle(view)
    assert indicator(view).get("layout_x") == tab(view, "b").get("layout_x") + 12


def test_a_value_that_is_no_tab_puts_the_indicator_on_the_first(tmp_path):
    view, vm = opened(tmp_path, BARE)
    vm.plain.set("nope")
    settle(view)
    assert indicator(view).get("layout_x") == tab(view, "a").get("layout_x") + 12


def test_the_arrows_move_the_focus_along_the_bar_and_choose_the_tab(tmp_path):
    view, vm = opened(tmp_path, BARE)
    assert [tab(view, v).get("tab_index") for v in "abc"] == [0, -1, -1]
    tab(view, "a").focus()
    view.window.simulate("key_down", key="arrow_right")
    settle(view)
    assert vm.plain.get() == "b"
    view.window.simulate("key_down", key="end")
    settle(view)
    assert vm.plain.get() == "c"
    view.window.simulate("key_down", key="home")
    settle(view)
    assert vm.plain.get() == "a"


def test_an_icon_and_a_badge_sit_in_the_tab(tmp_path):
    view, _ = opened(tmp_path, ICONS)
    assert view.node("root.t.bar.tab[flights].icon").get("fill") == role(view, "on_surface_variant")
    assert view.node("root.t.bar.tab[trips].badged.mark.label").get("text") == "3"
    assert view.node("root.t.bar.tab[trips].badged.badged_icon").get("fill") == role(view, "primary")
    assert "root.t.bar.tab[trips].icon" not in view._built.specs


def test_a_tab_width_sets_every_tab(tmp_path):
    view, _ = opened(tmp_path, BARE.replace("Name: t,", "Name: t, Tab_Width: 90,"))
    assert tab(view, "b").get("layout_width") == 90.0 and indicator(view).get("layout_width") == 66.0


def test_tabs_can_change(tmp_path):
    class Dynamic(ViewModel):
        views = "main"

        def __init__(self):
            super().__init__()
            self.tabs = Signal([{"value": "a", "label": "A"}, {"value": "b", "label": "B"}])

    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        '---\nTDL: 0.2\nName: main\nTesserae: "0.6"\n---\n'
        "Container {\n  Name: main\n  Style { Width: 500, Height: 200 }\n  Children {\n    Tabs { Name: t, Tabs: <| tabs |>, Selected: b }\n  }\n}\n")
    app = App(root=tmp_path)
    app.bind(Dynamic)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(16)
    app.bindings.viewmodel_for("main").tabs.set([{"value": "a", "label": "A"}, {"value": "b", "label": "B"}, {"value": "c", "label": "C"}])
    settle(view)
    assert tab(view, "c").get("layout_x") == tab(view, "a").get("layout_x") + 240


def test_a_panel_is_the_viewers_to_switch(tmp_path):
    view, vm = opened(tmp_path, BARE + "\nIf <| plain == 'a' |> { Container { Name: pa, Style { Width: 10, Height: 10 } } }"
                                       "\nIf <| plain == 'b' |> { Container { Name: pb, Style { Width: 10, Height: 10 } } }")
    assert "root.pa" in view._built.specs and "root.pb" not in view._built.specs
    click(view, "b")
    assert "root.pb" in view._built.specs and "root.pa" not in view._built.specs
