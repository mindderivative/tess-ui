"""Behavior events (`tess_ui.behavior`): a user's change of a widget's state is asked about (`before_change`, vetoable) and reported (`change`), with
a reason and a detail; a write nothing caused is `api` and is made at once; a controlled widget writes only what its host accepts."""

import tess_re

from tess_ui.widgets import search_bar


def _bar(**options):
    window = tess_re.Window(width=600, height=200)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start")
    bar = search_bar(window, "Search", 360, **options)
    window.advance(16)
    return window, bar


def _field(window, bar):
    bar.part("field").focus()
    window.advance(16)


def _record(bar):
    heard = []
    bar.on_before_change(lambda e: heard.append(("before", e.reason, e.detail, e.previous, e.value)))
    bar.on_change(lambda e: heard.append(("change", e.reason, e.detail, e.previous, e.value)))
    return heard


def test_typing_is_a_keyboard_change_with_detail_typing():
    window, bar = _bar()
    heard = _record(bar)
    _field(window, bar)
    window.simulate("input", text="a")
    window.advance(32)
    assert heard == [("before", "keyboard", "typing", "", "a"), ("change", "keyboard", "typing", "", "a")] and bar.query.get() == "a"


def test_clear_by_pointer_and_by_keyboard_and_escape_say_who_and_what():
    window, bar = _bar()
    _field(window, bar)
    window.simulate("input", text="ab")
    window.advance(32)
    heard = _record(bar)
    window.simulate("click", node=bar.part("clear"))
    window.advance(32)
    window.simulate("input", text="cd")
    window.advance(32)
    bar.part("clear").focus()
    window.simulate("key_down", key="enter")
    window.advance(32)
    window.simulate("input", text="ef")
    window.advance(32)
    window.simulate("key_down", key="escape")
    window.advance(32)
    kinds = [(h[0], h[1], h[2]) for h in heard if h[0] == "change"]
    assert kinds == [("change", "pointer", "clear"), ("change", "keyboard", "typing"), ("change", "keyboard", "clear"),
                     ("change", "keyboard", "typing"), ("change", "keyboard", "escape")]


def test_a_vetoed_change_leaves_the_query_and_puts_the_field_back():
    window, bar = _bar()
    _field(window, bar)
    bar.on_before_change(lambda e: e.cancel())
    window.simulate("input", text="a")
    window.advance(32)
    assert bar.query.get() == "" and bar.part("field").get("text") == ""


def test_a_write_nothing_caused_is_api_and_is_never_asked_about():
    window, bar = _bar()
    heard = _record(bar)
    bar.on_before_change(lambda e: e.cancel())
    bar.query.set("x")
    window.advance(32)
    assert bar.query.get() == "x" and heard == [] and bar.part("field").get("text") == "x"


def test_a_controlled_bar_writes_only_what_its_host_accepts():
    window, bar = _bar(controlled=True)
    _field(window, bar)
    window.simulate("input", text="a")
    window.advance(32)
    assert bar.query.get() == ""  # nobody answered: that is a refusal
    bar.on_before_change(lambda e: e.accept())
    window.simulate("input", text="a")
    window.advance(32)
    assert bar.query.get() == "a"
    bar.query.set("zz")  # the host's own write is its to make
    assert bar.query.get() == "zz"


def test_a_bar_with_no_listener_and_not_controlled_is_as_it_was():
    window, bar = _bar()
    _field(window, bar)
    window.simulate("input", text="ab")
    window.advance(32)
    assert bar.query.get() == "ab" and not bar.query.gate.active


def _selectable(start=None):
    from tess_ui.widgets import list_, list_item

    window = tess_re.Window(width=600, height=400)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start", flex_direction="vertical")
    rows = [list_item(window, text) for text in ("A", "B", "C")]
    box = list_(window, rows, selectable="single", selected=start)
    window.advance(32)
    return window, box, rows


def test_a_selectable_list_is_a_listbox_of_options_with_one_roving_tab_stop_and_the_arrows_move_it():
    window, box, rows = _selectable(1)
    assert box.node.get("role") == "listbox" and [r.node.get("role") for r in rows] == ["option"] * 3
    assert [r.node.get("tab_index") for r in rows] == [-1, 0, -1] and [r.node.get("selected") for r in rows] == [False, True, False]
    rows[1].node.focus()
    for key, want in (("arrow_down", 2), ("arrow_down", 2), ("home", 0), ("end", 2), ("arrow_up", 1)):
        window.simulate("key_down", key=key)
        window.advance(16)
        assert [r.node.get("focused") for r in rows].index(True) == want, key
        assert [r.node.get("tab_index") for r in rows][want] == 0 and sorted(r.node.get("tab_index") for r in rows) == [-1, -1, 0]


def test_a_click_enter_or_space_selects_a_row_with_reason_and_detail_and_only_one_is_selected():
    window, box, rows = _selectable()
    heard = []
    box.on_change(lambda e: heard.append((e.reason, e.detail, e.previous, e.value)))
    window.simulate("click", node=rows[2].node)
    window.advance(16)
    rows[0].node.focus()
    window.simulate("key_down", key="enter")
    window.advance(16)
    rows[1].node.focus()
    window.simulate("key_down", key="space")
    window.advance(16)
    assert heard == [("pointer", "select", None, 2), ("keyboard", "select", 2, 0), ("keyboard", "select", 0, 1)]
    assert box.selected.get() == 1 and [r.selected.get() for r in rows] == [False, True, False]
    assert [r.node.get("selected") for r in rows] == [False, True, False]


def test_a_listener_can_refuse_a_selection_and_the_host_can_set_it_without_being_asked():
    window, box, rows = _selectable(0)
    box.on_before_change(lambda e: e.cancel())
    window.simulate("click", node=rows[2].node)
    window.advance(16)
    assert box.selected.get() == 0 and not rows[2].selected.get()
    box.selected.set(2)  # the host's own write: api, made at once
    window.advance(16)
    assert box.selected.get() == 2 and rows[2].selected.get() and not rows[0].selected.get()


def test_typing_the_start_of_a_rows_name_moves_to_it_in_a_selectable_list_and_a_pause_starts_over(monkeypatch):
    from tess_ui import typeahead
    from tess_ui.widgets import list_, list_item

    window = tess_re.Window(width=600, height=400)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start", flex_direction="vertical")
    rows = [list_item(window, name) for name in ("Apple", "Banana", "Blueberry", "Cherry")]
    list_(window, rows, selectable="single")
    window.advance(32)
    focused = lambda: [r.node.get("focused") for r in rows].index(True)  # noqa: E731
    rows[0].node.focus()
    for key, want in (("b", 1), ("l", 2)):  # "b" -> Banana, "bl" -> Blueberry
        window.simulate("key_down", key=key)
        window.advance(16)
        assert focused() == want
    monkeypatch.setattr(typeahead, "RESET", 0.0)
    window.simulate("key_down", key="c")
    window.advance(16)
    assert focused() == 3
    window.simulate("key_down", key="z")  # nothing starts with it: the focus stays
    window.advance(16)
    assert focused() == 3


def _multiple(start=None, announce="{count} selected"):
    from tess_ui.widgets import list_, list_item

    window = tess_re.Window(width=600, height=400)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start", flex_direction="vertical")
    rows = [list_item(window, text) for text in ("Apple", "Banana", "Blueberry", "Cherry")]
    box = list_(window, rows, selectable="multiple", selected=start, announce=announce)
    window.advance(32)
    heard = []
    box.on_change(lambda e: heard.append((e.reason, e.detail, e.previous, e.value)))
    return window, box, rows, heard


def test_a_multiple_selection_list_is_the_engines_click_ctrl_shift_space_and_select_all_AC_SLT():
    window, box, rows, heard = _multiple()
    window.simulate("click", node=rows[0].node)
    window.advance(16)
    assert box.selection.get() == (0,)
    window.simulate("click", node=rows[2].node, ctrl=True)  # toggles, the anchor moves
    window.advance(16)
    assert box.selection.get() == (0, 2)
    window.simulate("click", node=rows[3].node, shift=True)  # a range from the anchor (row 2), replacing the set
    window.advance(16)
    assert box.selection.get() == (2, 3)
    rows[1].node.focus()
    window.advance(16)
    window.simulate("key_down", key="space")
    window.advance(16)
    assert box.selection.get() == (1, 2, 3)
    window.simulate("key_down", key="a", ctrl=True)
    window.advance(16)
    assert box.selection.get() == (0, 1, 2, 3)
    assert [r.selected.get() for r in rows] == [True] * 4 and [r.node.get("selected") for r in rows] == [True] * 4
    assert [h[0] for h in heard] == ["pointer", "pointer", "pointer", "keyboard", "keyboard"]
    assert [h[1] for h in heard] == ["select", "toggle", "range", "toggle", "all"]  # the Selection pattern's names for what the input did


def test_the_arrows_home_and_end_move_the_focus_between_the_rows_of_a_multiple_selection_list_and_shift_extends_the_range():
    window, box, rows, _ = _multiple()
    focused = lambda: [i for i, r in enumerate(rows) if r.node.get("focused")]  # noqa: E731

    def press(key, **modifiers):
        window.simulate("key_down", key=key, **modifiers)
        window.advance(32)

    rows[1].node.focus()
    window.advance(16)
    press("arrow_down")
    assert focused() == [2] and box.selection.get() == ()
    press("arrow_down", shift=True)  # the focus goes on one, and the range from the anchor reaches the row it lands on
    assert focused() == [3] and box.selection.get() == (2, 3)
    press("home")
    assert focused() == [0] and box.selection.get() == (2, 3)
    press("end")
    assert focused() == [3]
    press("arrow_down")  # at the end nothing moves
    assert focused() == [3]


def test_a_click_on_the_empty_part_clears_and_a_write_from_code_is_a_select():
    window, box, rows, heard = _multiple(start=[1, 2])
    box.node.set(min_height=400.0)  # room below the four rows
    window.advance(16)
    window.simulate("click", node=box.node, x=10.0, y=380.0)
    window.advance(16)
    assert box.selection.get() == () and heard[-1][1] == "clear"
    box.selection.set((0,))
    window.advance(16)
    assert heard[-1][:2] == ("api", "select")


def test_the_rows_show_the_selection_and_a_write_from_code_chooses_rows_and_is_reported_as_api():
    window, box, rows, heard = _multiple(start=[1, 3])
    assert box.selection.get() == (1, 3) and [r.selected.get() for r in rows] == [False, True, False, True]
    box.selection.set((0, 2))
    window.advance(16)
    assert [r.selected.get() for r in rows] == [True, False, True, False] and heard[-1] == ("api", "select", (1, 3), (0, 2))
    assert [row.node.get("role") for row in rows] == ["option"] * 4


def test_a_multiple_selection_list_keeps_the_roving_tab_stop_and_the_type_ahead_and_has_the_announce_text():
    window, box, rows, _ = _multiple()
    assert box.node.get("selection_announce") == "{count} selected" and box.node.get("selection_mode") == "multiple"
    assert sorted(r.node.get("tab_index") for r in rows) == [-1, -1, -1, 0]
    rows[0].node.focus()
    window.advance(16)
    window.simulate("key_down", key="b")
    window.advance(16)
    assert rows[1].node.get("focused") and sorted(r.node.get("tab_index") for r in rows) == [-1, -1, -1, 0] and rows[1].node.get("tab_index") == 0
    window2, box2, *_ = _multiple(announce=None)
    assert box2.node.get("selection_announce") is None


def _rows(selectable, disabled=(), unselectable=()):
    from tess_ui.widgets import list_, list_item

    window = tess_re.Window(width=600, height=400)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start", flex_direction="vertical")
    rows = [list_item(window, text, disabled=i in disabled) for i, text in enumerate(("Apple", "Banana", "Cherry", "Date", "Elder"))]
    box = list_(window, rows, selectable=selectable, unselectable=list(unselectable))
    window.advance(32)
    return window, box, rows


def _press(window, key, **modifiers):
    window.simulate("key_down", key=key, **modifiers)
    window.advance(32)


def test_a_disabled_row_is_skipped_by_the_arrows_and_never_chosen_in_a_multiple_list():
    window, box, rows = _rows("multiple", disabled=(2,))
    focused = lambda: [i for i, r in enumerate(rows) if r.node.get("focused")]  # noqa: E731
    window.simulate("click", node=rows[1].node)
    window.advance(16)
    _press(window, "arrow_down")
    assert focused() == [3]  # Cherry is disabled
    _press(window, "arrow_up")
    assert focused() == [1]
    window.simulate("click", node=rows[4].node, shift=True)  # a range from Banana over the disabled row
    window.advance(16)
    assert box.selection.get() == (1, 3, 4)
    _press(window, "a", ctrl=True)
    assert box.selection.get() == (0, 1, 3, 4)
    window.simulate("click", node=rows[2].node)  # a press on it does nothing
    window.advance(16)
    assert box.selection.get() == (0, 1, 3, 4)


def test_an_unselectable_row_takes_focus_but_is_never_chosen_in_a_multiple_list():
    window, box, rows = _rows("multiple", unselectable=(2,))
    focused = lambda: [i for i, r in enumerate(rows) if r.node.get("focused")]  # noqa: E731
    window.simulate("click", node=rows[1].node)
    window.advance(16)
    _press(window, "arrow_down")
    assert focused() == [2] and box.selection.get() == (1,)  # the arrow lands on it
    _press(window, "space")
    assert box.selection.get() == (1,)  # and Space chooses nothing
    window.simulate("click", node=rows[4].node, shift=True)
    window.advance(16)
    assert box.selection.get() == (1, 3, 4)  # the range passes over it
    window.simulate("click", node=rows[2].node)  # a press focuses it and changes nothing
    window.advance(16)
    assert focused() == [2] and box.selection.get() == (1, 3, 4)
    _press(window, "a", ctrl=True)
    assert box.selection.get() == (0, 1, 3, 4)
    box.selection.set((0, 2, 3))  # a write from code leaves it out
    window.advance(32)
    assert box.selection.get() == (0, 3)


def test_a_single_selection_list_skips_a_disabled_row_and_cannot_choose_an_unselectable_one():
    window, box, rows = _rows("single", disabled=(1,), unselectable=(3,))
    rows[0].node.focus()
    window.advance(16)
    _press(window, "arrow_down")
    assert rows[2].node.get("focused")  # Banana is disabled
    _press(window, "arrow_down")
    assert rows[3].node.get("focused")  # Date takes focus
    _press(window, "enter")
    assert box.selected.get() is None  # and cannot be chosen
    window.simulate("click", node=rows[2].node)
    window.advance(16)
    assert box.selected.get() == 2


def test_a_list_has_the_accessible_name_it_is_given_and_none_otherwise():
    for selectable, role in ((None, "list"), ("single", "listbox"), ("multiple", "listbox")):
        window, box, rows = _rows(selectable)
        assert box.node.get("label") is None and box.node.get("role") == role
    from tess_ui.widgets import list_, list_item

    window = tess_re.Window(width=600, height=400)
    window.root.set(padding_top=0, padding_right=0, padding_bottom=0, padding_left=0, align_items="flex_start", flex_direction="vertical")
    named = list_(window, [list_item(window, "Apple")], selectable="multiple", label="Fruit")
    assert named.node.get("label") == "Fruit" and named.node.get("role") == "listbox"
