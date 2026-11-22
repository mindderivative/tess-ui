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
