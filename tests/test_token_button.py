"""T-034 (5): the token button -- `tess_ui.token_controls` (the tokens as rows, the search, the cursor), the `TokenList` control and the `TokenButton` view with its popup, driven by key and pointer events on a
headless window. Nothing here reads outside `tmp_path`."""

import pytest

from tess_ui import App, Signal, ViewModel, tokens
from tess_ui.shipped import shipped_views
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.widgets import lookup
from tess_ui.token_controls import TokenList, rows_of

TOKENS = [
    {"name": "color.primary", "ref": "$color.primary", "kind": "colour", "value": "#6750A4", "doc": "The brand colour"},
    {"name": "color.on_primary", "ref": "$color.on_primary", "kind": "colour", "value": "#ffffff", "doc": "Text and icons on primary"},
    {"name": "color.error", "ref": "$color.error", "kind": "color", "value": "#b3261e80", "doc": "Errors"},
    {"name": "space.md", "ref": "$space.md", "kind": "dimension", "value": 16, "doc": "A medium gap"},
    {"name": "radius.card", "ref": "$radius.card", "kind": "dimension", "value": "12px", "doc": "Corners of a card"},
    {"name": "font.body", "ref": "$font.body", "kind": "font", "value": "Inter", "doc": "Body text"},
]

# -- the rows ------------------------------------------------------------------------------------------------------------------------------


def test_a_token_is_a_row_with_its_ref_value_text_and_a_swatch_only_for_a_colour():
    rows = {r["name"]: r for r in rows_of(TOKENS)}
    primary = rows["color.primary"]
    assert (primary["ref"], primary["swatch"], primary["shown"], primary["detail"], primary["label"]) == ("$color.primary", "#6750a4", "#6750A4", "The brand colour", "color.primary: #6750A4")
    assert rows["color.error"]["swatch"] == "#b3261e80"  # `color` is a colour kind too
    assert rows["space.md"]["swatch"] == "" and rows["space.md"]["shown"] == "16" and rows["space.md"]["value"] == 16
    assert rows["font.body"]["swatch"] == "" and rows["font.body"]["shown"] == "Inter"


def test_the_ref_is_a_dollar_and_the_name_when_it_is_left_out_and_a_token_with_no_name_or_a_repeated_ref_is_left_out():
    rows = rows_of([{"name": "a.b"}, {"name": "  "}, {"ref": "$x"}, "text", None, {"name": "again", "ref": "$a.b"}, {"name": "c", "ref": "$c", "value": None}])
    assert [(r["name"], r["ref"]) for r in rows] == [("a.b", "$a.b"), ("c", "$c")]
    assert rows[1]["shown"] == "" and rows[1]["label"] == "c" and rows[1]["value"] is None


def test_a_colour_kind_with_a_value_that_is_not_a_colour_has_no_swatch_and_shows_its_text():
    row = rows_of([{"name": "x", "kind": "colour", "value": "primary"}, {"name": "y", "kind": "colour", "value": 5}])
    assert [r["swatch"] for r in row] == ["", ""] and [r["shown"] for r in row] == ["primary", "5"]


def test_groups_follow_the_tokens_and_each_row_says_its_group_before_its_doc():
    rows = rows_of([{"name": "loose"}], groups=[{"name": "Colour", "tokens": [{"name": "c1", "doc": "one"}, {"name": "c2"}]}, {"title": "Space", "tokens": [{"name": "s1"}]}, {"tokens": [{"name": "s2"}]}, "bad", {"name": "Empty"}])
    assert [(r["name"], r["group"], r["detail"]) for r in rows] == [("loose", "", ""), ("c1", "Colour", "Colour · one"), ("c2", "Colour", "Colour"), ("s1", "Space", "Space"), ("s2", "", "")]


def test_preferred_names_or_refs_come_first_in_their_order_and_the_rest_keep_theirs():
    names = [r["name"] for r in rows_of(TOKENS, preferred=["font.body", "$color.error", "nothing", "color.primary"])]
    assert names == ["font.body", "color.error", "color.primary", "color.on_primary", "space.md", "radius.card"]


def test_things_that_are_not_lists_are_nothing():
    assert rows_of("x", {"a": 1}, 5) == [] and rows_of(None, None, None) == []


# -- the model --------------------------------------------------------------------------------------------------------------------------


def names(model):
    return [r["name"] for r in model.results]


def test_the_search_keeps_the_tokens_with_every_word_in_name_ref_group_or_doc_in_any_case_and_order():
    model = TokenList(TOKENS, groups=[{"name": "Fonts", "tokens": [{"name": "font.mono", "doc": "Code"}]}])
    model.set_query("PRIMARY")
    assert names(model) == ["color.primary", "color.on_primary"]
    model.set_query("on primary")  # the words are in the name and in the doc, in any order
    assert names(model) == ["color.on_primary"]
    model.set_query("card corners")
    assert names(model) == ["radius.card"]
    model.set_query("fonts")  # the group
    assert names(model) == ["font.mono"]
    model.set_query("$space")  # the ref
    assert names(model) == ["space.md"]
    model.set_query("zzz")
    assert names(model) == [] and model.cursor == -1 and model.picked is None
    model.set_query("")
    assert len(model.results) == 7 and model.cursor == 0


def test_a_name_that_starts_with_the_first_word_comes_first_and_the_preferred_stay_first_inside_it():
    model = TokenList(TOKENS, preferred=["color.on_primary"])
    model.set_query("primary")  # neither name starts with it: the preferred one stays first
    assert names(model) == ["color.on_primary", "color.primary"]
    model = TokenList([{"name": "x.error"}, {"name": "error.main"}, {"name": "error.alt"}], preferred=["error.alt", "x.error"])
    model.set_query("error")
    assert names(model) == ["error.alt", "error.main", "x.error"]  # the two that start with it first, the preferred of them first


def test_the_cursor_moves_inside_the_results_and_keys_pick():
    model = TokenList(TOKENS, page_rows=3)
    assert model.press("arrow_down") is None and model.cursor == 1
    model.press("page_down")
    assert model.cursor == 4
    model.press("end")
    assert model.cursor == 5
    model.press("arrow_down")
    assert model.cursor == 5
    model.press("home")
    model.press("arrow_up")
    assert model.cursor == 0
    assert model.press("enter") == "pick" and model.picked["name"] == "color.primary"
    assert model.press("Enter") == "pick" and model.press("space") == "pick" and model.press(" ") == "pick"
    assert model.press("a") is None


def test_in_the_search_field_only_the_arrows_and_the_pages_act_and_enter_picks():
    model = TokenList(TOKENS, page_rows=3)
    model.press("arrow_down", in_field=True)
    model.press("end", in_field=True)
    model.press("home", in_field=True)
    assert model.cursor == 1 and model.press("space", in_field=True) is None and model.press(" ", in_field=True) is None
    assert model.press("enter", in_field=True) == "pick"


def test_a_press_picks_the_row_it_is_on_and_a_place_that_is_not_there_picks_nothing():
    model = TokenList(TOKENS)
    assert model.click(3) == "pick" and model.picked["name"] == "space.md" and model.click(-1) is None and model.click(99) is None
    assert model.index_of("$font.body") == 5 and model.index_of("$nothing") == -1 and model.row_of("$font.body")["name"] == "font.body" and model.row_of("x") is None


def test_the_scroll_offset_keeps_the_cursor_in_the_window():
    model = TokenList(TOKENS, page_rows=3)
    model.move(4)
    assert model.reveal(0, 56) == 2 * 56
    model.move(0)
    assert model.reveal(112, 56) == 0
    model.move(3)
    assert model.reveal(112, 56) == 112
    assert TokenList([]).reveal(5, 56) == 5


# -- the view -----------------------------------------------------------------------------------------------------------------------------


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.tokens = Signal(list(TOKENS))
        self.ref = Signal("$color.primary")
        self.pop = Signal(False)
        self.log = []

    def picked(self):
        self.log.append(self.ref.get())


CALL = '{widget: TokenButton, name: tb, tokens: "{{ tokens }}", value: "{{ ref }}", open: "{{ pop }}", on_pick: picked%s}'


def opened(tmp_path, call=CALL, options="", ref=None, size=(560, 700), dark=False):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.yaml").write_text(f"""tesserae: 0.6
name: main
widget: Container
style: {{flex_direction: vertical, gap: 16, padding: 16, width: {size[0]}, height: {size[1]}}}
children:
  - {call % options}
  - {{widget: Rect, name: elsewhere, style: {{width: 80, height: 40, background: surface_variant}}}}
""")
    app = App(root=tmp_path, width=size[0], height=size[1], theme_seed=(0x67, 0x50, 0xA4, 0xFF), dark=dark)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 4)
    vm = app.bindings.viewmodel_for("main")
    if ref is not None:
        vm.ref.set(ref)
        settle(view, 6)
    return view, vm


def settle(view, n=6):
    for _ in range(n):
        view.window.advance(16)


def ctl(view):
    return view._built.controls["root.tb.mind"]


def nodes(view, path):
    return view._built.nodes[f"root.tb.{path}"]


def trigger(view):
    return nodes(view, "field.trigger")


def search(view):
    return view._built.nodes["root.tb.layer.surface.search.box.body.input"]


def list_box(view):
    return nodes(view, "layer.surface.list_box")


def row(view, ref):
    return nodes(view, f"layer.surface.list_box.list.row[{ref}]")


def row_part(view, ref, part):
    inside = "texts." if part in ("row_name", "row_detail") else ""
    return nodes(view, f"layer.surface.list_box.list.row[{ref}].{inside}{part}")


def shown(view):
    prefix = "root.tb.layer.surface.list_box.list.row["
    keys = [k for k in view._built.nodes if k.startswith(prefix) and k.endswith("]")]
    return [k[len(prefix):-1] for k in sorted(keys, key=lambda k: view._built.nodes[k].get("layout_y"))]


def press(view, target, n=4):
    view.window.simulate("pointer_down", node=target)
    view.window.simulate("pointer_up", node=target)
    settle(view, n)


def open_it(view):
    press(view, trigger(view))
    assert view._shown_layers


def type_in_search(view, text):
    box = search(view)
    box.focus()
    box.set(text=text[:-1] if text else "x")
    view.window.simulate("key_down", key="end")
    if text:
        view.window.simulate("input", text=text[-1])
    else:
        view.window.simulate("key_down", key="backspace")
    settle(view, 4)


def key_in_list(view, name, n=3):
    box = list_box(view)
    if not box.get("focused"):
        box.focus()
    view.window.simulate("key_down", key=name)
    settle(view, n)


def key_in_field(view, name, n=3):
    search(view).focus()
    view.window.simulate("key_down", key=name)
    settle(view, n)


def test_the_button_and_its_mind_are_shipped_and_declared():
    assert "TokenButton" in set(shipped_views())
    declared = lookup("TokenList")
    assert declared is not None and declared.properties["value"].model and declared.properties["current"].model and declared.properties["tokens"] is not None


def test_closed_it_shows_the_ref_with_a_swatch_of_the_token_and_lists_nothing(tmp_path):
    view, vm = opened(tmp_path)
    assert view.handle.viewmodel is vm
    assert nodes(view, "field.trigger_text").get("text") == "$color.primary"
    swatch = nodes(view, "field.current_swatch")
    assert swatch.get("fill") == (0x67, 0x50, 0xA4, 255) and (swatch.get("layout_width"), swatch.get("layout_height")) == (24.0, 24.0)
    assert not view._shown_layers and vm.pop.get() is False and ctl(view).entries.get() == [] and ctl(view).current.get()["known"] is True


def test_a_token_that_is_not_a_colour_has_no_swatch_on_the_button_and_a_ref_that_is_none_is_shown_as_it_is(tmp_path):
    view, vm = opened(tmp_path, ref="$space.md")
    assert nodes(view, "field.trigger_text").get("text") == "$space.md" and "root.tb.field.current_swatch" not in view._built.nodes
    vm.ref.set("$gone.token")
    settle(view, 6)
    assert nodes(view, "field.trigger_text").get("text") == "$gone.token" and ctl(view).current.get()["known"] is False and vm.log == []
    assert "root.tb.field.current_swatch" not in view._built.nodes


def test_with_no_ref_it_says_what_to_do(tmp_path):
    view, vm = opened(tmp_path, ref="")
    assert nodes(view, "field.trigger_text").get("text") == "Choose a token" and trigger(view).get("label") == "Token"


def test_pressing_the_button_opens_the_list_with_a_row_for_each_token_and_the_value_picked(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    assert vm.pop.get() is True and trigger(view).get("expanded") is True
    assert ctl(view).count.get() == 6 and shown(view) == [t["ref"] for t in TOKENS]
    assert row(view, "$color.primary").get("fill") == (view._scheme or tokens.BASELINE)["secondary_container"]
    assert row(view, "$color.primary").get("selected") is True and row(view, "$space.md").get("selected") is False
    assert nodes(view, "layer.surface").get("corner_radius") == 12.0


def test_a_colour_row_has_a_swatch_and_any_other_the_value_as_text_and_a_line_with_the_doc(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    assert row_part(view, "$color.on_primary", "swatch").get("fill") == (255, 255, 255, 255)
    assert row_part(view, "$color.error", "swatch").get("fill") == (0xb3, 0x26, 0x1e, 0x80)
    assert "root.tb.layer.surface.list_box.list.row[$color.primary].row_value" not in view._built.nodes
    assert row_part(view, "$space.md", "row_value").get("text") == "16" and row_part(view, "$font.body", "row_value").get("text") == "Inter"
    assert "root.tb.layer.surface.list_box.list.row[$space.md].swatch" not in view._built.nodes
    assert row_part(view, "$radius.card", "row_name").get("text") == "radius.card" and row_part(view, "$radius.card", "row_detail").get("text") == "Corners of a card"
    assert row(view, "$space.md").get("label") == "space.md: 16"


def test_a_press_on_a_row_writes_its_ref_calls_on_pick_and_closes(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    press(view, row(view, "$space.md"))
    assert vm.ref.get() == "$space.md" and vm.log == ["$space.md"] and vm.pop.get() is False and not view._shown_layers
    assert nodes(view, "field.trigger_text").get("text") == "$space.md" and "root.tb.field.current_swatch" not in view._built.nodes
    open_it(view)
    press(view, row(view, "$color.error"))
    assert vm.ref.get() == "$color.error" and nodes(view, "field.current_swatch").get("fill") == (0xb3, 0x26, 0x1e, 0x80)


def test_close_on_pick_false_keeps_the_list_open(tmp_path):
    view, vm = opened(tmp_path, options=", close_on_pick: false")
    open_it(view)
    press(view, row(view, "$space.md"))
    assert vm.ref.get() == "$space.md" and vm.pop.get() is True and view._shown_layers
    assert row(view, "$space.md").get("selected") is True and row(view, "$color.primary").get("selected") is False


def test_picking_the_ref_that_is_already_there_calls_on_pick_again(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    press(view, row(view, "$color.primary"))
    assert vm.log == ["$color.primary"] and vm.pop.get() is False


# -- search -------------------------------------------------------------------------------------------------------------------------------


def test_typing_in_the_search_narrows_the_rows_by_name_and_doc(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    type_in_search(view, "primary")
    assert shown(view) == ["$color.primary", "$color.on_primary"] and ctl(view).count.get() == 2
    type_in_search(view, "corner")  # doc
    assert shown(view) == ["$radius.card"]
    type_in_search(view, "nothing at all")
    assert shown(view) == [] and nodes(view, "layer.surface.empty").get("text") == "No token matches"
    type_in_search(view, "")
    assert len(shown(view)) == 6 and "root.tb.layer.surface.empty" not in view._built.nodes


def test_the_search_field_has_the_focus_when_the_list_opens_and_is_labelled(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    assert search(view).get("focused") and search(view).get("label") == "Search tokens"


def test_up_down_and_enter_in_the_search_field_move_the_cursor_and_pick(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    type_in_search(view, "color")
    assert ctl(view).cursor_ref.get() == "$color.primary"
    key_in_field(view, "arrow_down")
    assert ctl(view).cursor_ref.get() == "$color.on_primary"
    assert row(view, "$color.on_primary").get("fill") == (view._scheme or tokens.BASELINE)["surface_container_highest"]
    key_in_field(view, "arrow_down")
    key_in_field(view, "arrow_up")
    assert ctl(view).cursor_ref.get() == "$color.on_primary"
    search(view).focus()
    view.window.simulate("key_down", key="Enter")
    settle(view, 6)
    assert vm.ref.get() == "$color.on_primary" and vm.log == ["$color.on_primary"] and vm.pop.get() is False


def test_the_list_has_the_arrows_pages_home_end_enter_and_space(tmp_path):
    view, vm = opened(tmp_path, options=", rows: 3")
    open_it(view)
    key_in_list(view, "end")
    assert ctl(view).cursor_ref.get() == "$font.body" and ctl(view).scroll.get() == 3 * 56
    key_in_list(view, "home")
    assert ctl(view).cursor_ref.get() == "$color.primary" and ctl(view).scroll.get() == 0
    key_in_list(view, "page_down")
    assert ctl(view).cursor_ref.get() == "$space.md"
    key_in_list(view, "arrow_up")
    key_in_list(view, "enter")
    assert vm.ref.get() == "$color.error" and vm.pop.get() is False
    open_it(view)
    key_in_list(view, "arrow_down")
    key_in_list(view, " ")
    assert vm.ref.get() == "$space.md"


def test_the_list_opens_scrolled_so_that_the_value_shows_with_the_cursor_on_it(tmp_path):
    view, vm = opened(tmp_path, options=", rows: 3", ref="$font.body")
    open_it(view)
    assert ctl(view).cursor_ref.get() == "$font.body" and ctl(view).scroll.get() == 3 * 56


def test_many_tokens_build_only_the_rows_in_view(tmp_path):
    view, vm = opened(tmp_path)
    vm.tokens.set([{"name": f"color.c{i}", "kind": "colour", "value": "#112233"} for i in range(600)])
    settle(view, 6)
    open_it(view)
    assert ctl(view).count.get() == 600 and 0 < len(shown(view)) <= 7 + 2 * 3 + 1


# -- data ---------------------------------------------------------------------------------------------------------------------------------


def test_groups_and_preferred_names_reach_the_list(tmp_path):
    view, vm = opened(tmp_path, call='{widget: TokenButton, name: tb, tokens: "{{ tokens }}", groups: [{name: Motion, tokens: [{name: motion.fast, ref: "$motion.fast", value: 100, doc: Short}]}], preferred: ["$font.body"], value: "{{ ref }}", open: "{{ pop }}"%s}')
    open_it(view)
    assert shown(view)[:2] == ["$font.body", "$color.primary"] and shown(view)[-1] == "$motion.fast"
    assert row_part(view, "$motion.fast", "row_detail").get("text") == "Motion · Short"


def test_tokens_changed_by_the_app_while_the_list_is_open_are_listed_and_the_search_is_kept(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    type_in_search(view, "space")
    assert shown(view) == ["$space.md"]
    vm.tokens.set([*TOKENS, {"name": "space.lg", "value": 24, "doc": "A large gap"}])
    settle(view, 6)
    assert shown(view) == ["$space.md", "$space.lg"] and view.window and ctl(view).entries.get()[1]["name"] == "space.lg"


def test_a_ref_set_by_the_app_while_the_list_is_open_moves_the_selection_and_the_cursor(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    vm.ref.set("$font.body")
    settle(view, 6)
    assert row(view, "$font.body").get("selected") is True and ctl(view).cursor_ref.get() == "$font.body" and vm.log == []


def test_the_list_is_empty_when_no_tokens_are_given_and_says_so(tmp_path):
    view, vm = opened(tmp_path, call='{widget: TokenButton, name: tb, value: "{{ ref }}", open: "{{ pop }}"%s}')
    open_it(view)
    assert ctl(view).count.get() == 0 and nodes(view, "layer.surface.empty").get("text") == "No token matches"


# -- the popup: Escape, outside, the keyboard, disabled -------------------------------------------------------------------------------------


def test_escape_closes_the_list_from_the_field_and_from_the_list_and_writes_false_back(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers and vm.ref.get() == "$color.primary" and vm.log == []
    open_it(view)
    list_box(view).focus()
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers
    open_it(view)  # and it opens again
    assert vm.pop.get() is True


def test_the_list_opens_from_the_keyboard_and_escape_gives_the_focus_back_to_the_button(tmp_path):
    view, vm = opened(tmp_path)
    button = trigger(view)
    button.focus()
    view.window.simulate("key_down", key="enter")
    settle(view, 6)
    assert vm.pop.get() is True and search(view).get("focused")
    view.window.simulate("key_down", key="escape")
    settle(view, 8)
    assert vm.pop.get() is False and button.get("focused")


def test_enter_and_arrow_down_on_the_button_open_it_and_the_other_keys_do_not(tmp_path):
    view, vm = opened(tmp_path)
    button = trigger(view)
    button.focus()
    for name in ("arrow_up", "a", "tab"):
        view.window.simulate("key_down", key=name)
        settle(view, 3)
        button.focus()
    assert vm.pop.get() is False
    view.window.simulate("key_down", key="arrow_down")
    settle(view, 6)
    assert vm.pop.get() is True and search(view).get("focused")
    view.window.simulate("key_down", key="escape")
    settle(view, 8)
    assert button.get("focused")
    view.window.simulate("key_down", key="enter")
    settle(view, 6)
    assert vm.pop.get() is True


def test_a_press_outside_closes_the_list_and_the_button_closes_it_too(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    view.window.simulate("pointer_down", x=500, y=660)
    view.window.simulate("pointer_up", x=500, y=660)
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers
    open_it(view)
    view.window.advance(1000)
    x, y = trigger(view).get("layout_x") + 30, trigger(view).get("layout_y") + 24
    view.window.simulate("pointer_down", x=x, y=y)
    view.window.simulate("pointer_up", x=x, y=y)
    settle(view, 4)
    assert vm.pop.get() is False and not view._shown_layers


def test_a_disabled_button_does_not_open_and_the_list_can_be_opened_from_the_viewmodel(tmp_path):
    view, vm = opened(tmp_path / "a", options=", disabled: true")
    press(view, trigger(view))
    key = view.window.simulate
    trigger(view).focus()
    key("key_down", key="arrow_down")
    settle(view, 4)
    assert vm.pop.get() is False and not view._shown_layers and ctl(view).disabled.get()
    view, vm = opened(tmp_path / "b")
    vm.pop.set(True)
    settle(view, 6)
    assert view._shown_layers and len(shown(view)) == 6
    vm.pop.set(False)
    settle(view, 6)
    assert not view._shown_layers


def test_the_names_a_screen_reader_hears(tmp_path):
    view, vm = opened(tmp_path, options=", label: Accent")
    assert trigger(view).get("role") == "button" and trigger(view).get("label") == "Accent: $color.primary" and trigger(view).get("expanded") is False
    assert trigger(view).get("focusable")
    open_it(view)
    assert trigger(view).get("expanded") is True
    assert nodes(view, "layer.surface").get("role") == "group" and nodes(view, "layer.surface").get("label") == "Accent"
    assert list_box(view).get("role") == "list" and list_box(view).get("label") == "Accent tokens"
    assert row(view, "$color.primary").get("role") == "listitem" and row(view, "$color.primary").get("label") == "color.primary: #6750A4"
    assert search(view).get("focusable") and list_box(view).get("focusable")


def test_an_unknown_property_of_the_button_is_named(tmp_path):
    with pytest.raises(LoadError, match="colour"):
        opened(tmp_path, call="{widget: TokenButton, name: tb, colour: red%s}")


def test_the_search_is_empty_each_time_the_list_opens(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    type_in_search(view, "space")
    assert shown(view) == ["$space.md"]
    view.window.simulate("key_down", key="escape")
    settle(view, 10)
    assert not view._shown_layers
    open_it(view)
    assert search(view).get("text") == "" and len(shown(view)) == 6 and ctl(view).query.get() == ""


def test_after_a_pick_the_focus_is_on_the_button_again(tmp_path):
    view, vm = opened(tmp_path)
    open_it(view)
    press(view, row(view, "$space.md"))
    settle(view, 8)
    assert vm.pop.get() is False and trigger(view).get("focused")
