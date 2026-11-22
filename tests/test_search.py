"""M42 Phase 1: MD3's search bar (`tess_ui.widgets.search_bar`, built
from its fragment) and docked search view (`tess_ui.overlays.SearchView`).
"""

import pytest
import tess_re

from tess_ui import Theme, tokens
from tess_ui.overlays import SearchView
from tess_ui.widgets import search_bar, search_view

BASE = tokens.baseline_scheme()
SEED = (0x67, 0x50, 0xA4, 0xFF)


def _window():
    window = tess_re.Window(width=600, height=500)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, gap=0,
                    align_items="flex_start", flex_direction="vertical")
    return window


def _bar_and_view(results=None):
    window = _window()
    bar = search_bar(window, "Search mail", 360, trailing_icons=["settings"])
    view = search_view(window, 360, 300, bar=bar, results=results)
    window.advance(16)
    return window, bar, view


def test_the_search_bar_is_md3s():
    window, bar, _ = _bar_and_view()
    assert (bar.node.get("layout_height"), bar.node.get("corner_radius")) == (56.0, 28.0)
    assert bar.node.get("fill") == BASE["surface_container_high"]
    assert bar.part("leading.icon").get("fill") == BASE["on_surface"]
    trailing = bar.part("trailing0")
    assert (trailing.get("role"), trailing.get("label"), trailing.get("layout_width")) == ("button", "settings", 48.0)
    assert bar.part("trailing0.icon").get("fill") == BASE["on_surface_variant"]


def test_the_placeholder_is_hint_text_not_the_fields_text():
    """`tess_re`'s search bar (and the fragment) filled the field with it."""
    window, bar, _ = _bar_and_view()
    field = bar.part("field")
    assert field.get("text") == "" and field.get("placeholder") == "Search mail"
    assert field.get("placeholder_fill") == BASE["on_surface_variant"] and field.get("fill") == BASE["on_surface"]
    assert (field.get("role"), field.get("label")) == ("textbox", "Search mail")


def test_typing_updates_the_query():
    window, bar, _ = _bar_and_view()
    heard = []
    bar.on_query(heard.append)
    bar.part("field").focus()
    window.simulate("input", text="ali")
    assert bar.query.get() == "ali" and heard == ["ali"]


def test_the_view_opens_below_the_bar_on_focus_and_is_md3s():
    window, bar, view = _bar_and_view([("Alice", None), ("Bob", None)])
    assert not view.is_open
    bar.part("field").focus()
    window.advance(16)
    assert view.is_open and view.node.get("layout_y") == 56.0
    assert view.node.get("fill") == BASE["surface_container_high"] and view.node.get("corner_radius") == 28.0
    assert view.node.get("role") == "menu"
    row = view.rows[0]
    assert (row.get("layout_height"), row.get("role"), row.get("label")) == (56.0, "menuitem", "Alice")
    assert view.widget.part("row0.label").get("font_size") == 16.0  # body_large
    assert [r.parent() is not None for r in view.rows[:3]] == [True, True, False]


def test_no_results_no_view():
    window, bar, view = _bar_and_view()
    bar.part("field").focus()
    window.advance(16)
    assert not view.is_open
    view.set_results([("Alice", None)])
    window.simulate("input", text="a")
    assert view.is_open
    view.set_results([("Alice", None), ("Bob", None)])
    view.set_results([("Carol", None)])  # fewer: the rest go
    assert [r.parent() is not None for r in view.rows[:2]] == [True, False]
    view.set_results([])
    assert not view.is_open


def test_the_arrows_move_between_the_field_and_the_rows_and_enter_chooses():
    chosen = []
    window, bar, view = _bar_and_view([("Alice", lambda: chosen.append("alice")),
                                       ("Bob", lambda: chosen.append("bob"))])
    field = bar.part("field")
    field.focus()
    window.simulate("key_down", key="arrow_down")
    assert view.rows[0].get("focused")
    window.simulate("key_down", key="arrow_down")
    assert view.rows[1].get("focused")
    window.simulate("key_down", key="arrow_down")
    assert view.rows[0].get("focused")  # wraps
    window.simulate("key_down", key="arrow_up")
    assert field.get("focused")  # up from the first row: back to the field
    window.simulate("key_down", key="arrow_down")
    window.simulate("key_down", key="arrow_down")
    window.simulate("key_down", key="enter")
    window.advance(16)
    assert chosen == ["bob"] and not view.is_open


def test_a_click_chooses_and_escape_or_an_outside_press_closes():
    chosen = []
    window, bar, view = _bar_and_view([("Alice", lambda: chosen.append("alice"))])
    bar.part("field").focus()
    window.advance(16)
    window.simulate("click", node=view.rows[0])
    assert chosen == ["alice"] and not view.is_open
    window.simulate("input", text="x")
    window.simulate("key_down", key="escape")
    window.advance(16)
    assert not view.is_open
    window.simulate("input", text="y")
    window.simulate("pointer_down", x=590, y=490)
    window.simulate("pointer_up", x=590, y=490)
    window.advance(16)
    assert not view.is_open


def test_a_view_without_a_bar_opens_where_its_told():
    window = _window()
    anchor = window.create("box", width=100, height=30)
    window.root.add_child(anchor)
    view = SearchView(window, results=[("One", None)])
    view.open(anchor)
    window.advance(16)
    assert view.is_open and view.node.get("layout_y") == 30.0
    with pytest.raises(ValueError, match="through its bar"):
        view.on_query(print)


def test_search_follows_the_theme():
    window = _window()
    light, dark = Theme.resolve(theme_seed=SEED), Theme.resolve(theme_seed=SEED, dark=True)
    bar = search_bar(window, "Find", 300, theme=light)
    bar.set_theme(dark)
    assert bar.node.get("fill") == dark.role("surface_container_high")
    assert bar.part("field").get("placeholder_fill") == dark.role("on_surface_variant")


def _typed(with_view):
    window = _window()
    bar = search_bar(window, "Search mail", 360)
    view = search_view(window, 360, 300, bar=bar, results=[("Alice", None)]) if with_view else None
    window.advance(16)
    bar.part("field").focus()
    window.advance(16)
    window.simulate("input", text="ab")
    window.advance(32)
    return window, bar, view


def _escape(window):
    window.simulate("key_down", key="escape")
    window.advance(48)


def test_escape_closes_the_open_view_and_keeps_the_query_then_clears_it_AC_SRB_5():
    window, bar, view = _typed(True)
    assert view.is_open and bar.query.get() == "ab"
    _escape(window)
    assert not view.is_open and bar.query.get() == "ab"
    _escape(window)
    assert bar.query.get() == "" and bar.part("field").get("text") == ""


def test_escape_clears_a_typed_query_when_there_is_no_view_and_does_nothing_when_it_is_empty_AC_SRB_5():
    window, bar, _ = _typed(False)
    _escape(window)
    assert bar.query.get() == ""
    _escape(window)
    assert bar.query.get() == "" and bar.part("field").get("focused")


def test_pressing_clear_empties_the_query_and_the_field_takes_the_focus_AC_SRB_4():
    for how in ("pointer", "keyboard"):
        window, bar, _ = _typed(False)
        clear = bar.part("clear")
        if how == "pointer":
            window.simulate("click", node=clear)
        else:
            clear.focus()
            window.simulate("key_down", key="enter")
        window.advance(48)
        assert bar.query.get() == "" and bar.part("field").get("focused"), how
        with pytest.raises(ValueError):
            bar.part("clear")  # gone, and the focus did not go with it


def test_a_disabled_bar_takes_no_typing_and_shows_no_clear_button_and_clear_label_names_the_button():
    window = _window()
    bar = search_bar(window, "Search mail", 360, disabled=True)
    bar.query.set("abc")
    window.advance(32)
    field = bar.part("field")
    assert field.get("disabled") and bar.query.get() == "abc"
    with pytest.raises(ValueError):
        bar.part("clear")
    other = _window()
    named = search_bar(other, "Search mail", 360, clear_label="Erase")
    named.query.set("abc")
    other.advance(32)
    assert (named.part("clear").get("label"), named.part("clear").get("role")) == ("Erase", "button")


def test_the_clear_button_is_not_a_tab_stop_and_a_press_on_it_does_not_take_the_focus_AC_SRB_4():
    window, bar, _ = _typed(False)
    clear = bar.part("clear")
    assert clear.get("focusable") is False and clear.get("role") == "button"
    window.simulate("key_down", key="tab")
    window.advance(16)
    assert not clear.get("focused")
    bar.part("field").focus()
    window.simulate("click", node=clear)
    window.advance(48)
    assert bar.query.get() == "" and bar.part("field").get("focused")  # the press cleared it and handed the focus to the field


def test_a_third_escape_deactivates_the_bar_and_focus_goes_back_to_the_previous_control_AC_SRB_5():
    from tess_ui.widgets import button

    window = _window()
    before = button(window, "Before", 100, 40)
    bar = search_bar(window, "Search mail", 360)
    view = search_view(window, 360, 300, bar=bar, results=[("Alice", None)])
    window.advance(16)
    before.node.focus()
    window.advance(16)
    bar.part("field").focus()
    window.advance(16)
    window.simulate("click", node=bar.node)  # pressing the bar activates it
    window.simulate("input", text="ab")
    window.advance(32)
    assert bar.active.get() is True and view.is_open and bar.query.get() == "ab"
    states = []
    for _ in range(3):
        _escape(window)
        states.append((view.is_open, bar.query.get(), bar.active.get(), before.node.get("focused")))
    assert states == [(False, "ab", True, False), (False, "", True, False), (False, "", False, True)]


def test_a_third_escape_with_nothing_before_the_bar_only_deactivates_it():
    window, bar, _ = _typed(False)
    bar.active.set(True)
    _escape(window)  # clears
    _escape(window)  # deactivates, there is no control to go back to
    assert bar.active.get() is False and bar.query.get() == ""
