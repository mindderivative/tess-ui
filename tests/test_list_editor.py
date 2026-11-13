"""T-034 (4): the list editor -- `ListModel` (the items and the edits, no window), the `ListModel` control and the `ListEditor` view with a row of its own for every item kind, driven by key and
pointer events on a headless window. Nothing here reads outside `tmp_path`."""

import itertools

import pytest

from tess_ui import App, Signal, ViewModel, colour
from tess_ui.list_controls import ListModel, choices_of
from tess_ui.shipped import shipped_views
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.widgets import lookup

# -- the model ---------------------------------------------------------------------------------------------------------------------------


def test_the_model_keeps_an_identity_with_each_item_through_a_move_and_a_remove():
    model = ListModel("text", ["a", "b", "c"])
    uids = [row["uid"] for row in model.rows]
    assert len(set(uids)) == 3
    assert model.move(0, 1) and model.values == ["b", "a", "c"]
    assert [row["uid"] for row in model.rows] == [uids[1], uids[0], uids[2]]
    assert model.remove(0) and [row["uid"] for row in model.rows] == [uids[0], uids[2]]
    assert model.add() and model.values == ["a", "c", ""] and model.rows[-1]["uid"] not in uids


def test_a_move_past_either_end_and_an_edit_of_a_place_that_is_not_there_change_nothing():
    model = ListModel("text", ["a", "b"])
    assert not model.move(0, -1) and not model.move(1, 1) and not model.move(5, -1) and not model.move(0, 0)
    assert not model.set(2, "x") and not model.set(-1, "x") and not model.remove(2) and not model.remove(-1)
    assert model.values == ["a", "b"]


def test_a_setting_the_same_item_again_is_no_change():
    model = ListModel("text", ["a"])
    assert not model.set(0, "a") and model.set(0, "b") and model.values == ["b"]


@pytest.mark.parametrize("kind, text, want", [
    ("text", "hello world", "hello world"),
    ("text", "", ""),
    ("number", "3", 3),
    ("number", "3.0", 3),
    ("number", "2.5", 2.5),
    ("number", "-4", -4),
    ("bool", "true", True),
    ("bool", "False", False),
    ("colour", "#FF0000", "#ff0000"),
    ("colour", "#00ff0080", "#00ff0080"),
])
def test_a_row_sends_the_text_of_its_item_and_the_model_reads_it_as_the_kind_has_it(kind, text, want):
    model = ListModel(kind, [START[kind]])
    assert model.set(0, text)
    assert model.values == [want] and type(model.values[0]) is type(want)


START = {"text": "x", "number": 99, "bool": None, "colour": "#123456", "enum": "a"}


@pytest.mark.parametrize("kind, text", [("number", "abc"), ("number", ""), ("bool", "yes"), ("colour", "red"), ("colour", "#12"), ("enum", "zzz")])
def test_a_text_that_is_not_an_item_of_the_kind_changes_nothing(kind, text):
    model = ListModel(kind, [START[kind]], choices=["a", "b"])
    before = model.values
    assert not model.set(0, text) and model.values == before


def test_a_number_is_kept_between_least_and_most_and_whole_stays_an_int_with_a_whole_step():
    model = ListModel("number", [5], least=0, most=10, step=1)
    model.set(0, "50")
    assert model.values == [10] and isinstance(model.values[0], int)
    model.set(0, "-3")
    assert model.values == [0]
    fractional = ListModel("number", [1], least=0, most=2, step=0.5)
    fractional.set(0, "1.5")
    assert fractional.values == [1.5]
    fractional.set(0, "2")
    assert fractional.values == [2.0] and isinstance(fractional.values[0], float)


def test_an_enum_takes_one_of_its_choices_by_the_text_and_keeps_the_value_that_was_given():
    model = ListModel("enum", [1], choices=[{"value": 1, "label": "One"}, {"value": 2, "label": "Two"}, 3])
    assert choices_of([{"value": 1, "label": "One"}, 3, {"label": "no value"}]) == [(1, "One"), (3, "3")]
    assert model.set(0, "2") and model.values == [2]
    assert model.set(0, "3") and model.values == [3]
    assert model.default() == 1


@pytest.mark.parametrize("kind, kwargs, want", [
    ("text", {}, ""), ("number", {}, 0), ("number", {"least": 2}, 2), ("bool", {}, False), ("enum", {"choices": ["x", "y"]}, "x"), ("enum", {}, ""), ("colour", {}, "#000000"),
])
def test_add_makes_the_default_item_of_the_kind(kind, kwargs, want):
    model = ListModel(kind, [], **kwargs)
    model.add()
    assert model.values == [want]


def test_the_length_bounds_stop_add_and_remove():
    model = ListModel("text", ["a", "b"], min_items=2, max_items=3)
    assert not model.can_remove and not model.remove(0) and model.can_add and model.add() and not model.can_add and not model.add()
    assert model.values == ["a", "b", ""] and model.can_remove and model.remove(2)


def test_items_that_do_not_fit_the_kind_are_shown_as_its_nearest_value_and_left_alone():
    model = ListModel("number", ["x", None, True, 4])
    assert [row["value"] for row in model.rows] == [0.0, 0.0, 0.0, 4.0] and model.values == ["x", None, True, 4]
    enum = ListModel("enum", ["a", "q"], choices=["a", "b"])
    assert [row["value"] for row in enum.rows] == ["a", "a"] and enum.values == ["a", "q"]
    pale = ListModel("colour", ["#ABCDEF", "nope", 5])
    assert [row["value"] for row in pale.rows] == ["#abcdef", "#000000", "#000000"] and pale.values == ["#ABCDEF", "nope", 5]
    assert ListModel("text", [1, None]).rows[0]["value"] == "1" and ListModel("text", [1, None]).rows[1]["value"] == ""


def test_an_item_kind_that_is_not_one_is_refused_by_the_model():
    with pytest.raises(ValueError, match="item kind"):
        ListModel("date")


# -- the view -----------------------------------------------------------------------------------------------------------------------------


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.items = Signal(["alpha", "beta", "gamma"])
        self.log = []

    def changed(self):
        self.log.append(list(self.items.get()))


CALL = '{widget: ListEditor, name: le, value: "{{ items }}", on_change: changed%s}'


def opened(tmp_path, call=CALL, options="", items=None, dark=False, size=(560, 420)):
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
    if items is not None:
        vm.items.set(items)
        settle(view, 6)
    return view, vm


def settle(view, n=6):
    for _ in range(n):
        view.window.advance(16)


def ctl(view):
    return view._built.controls["root.le.model"]


def row(view, i):
    """The path of row `i`, which is keyed by the uid of its item."""
    return f"root.le.rows.item[{ctl(view).rows.get()[i]['uid']}]"


def node(view, i, part):
    return view.node(f"{row(view, i)}.{part}")


def text_box(view, i):
    return view._built.nodes[f"{row(view, i)}.cell.text.box.body.input"]


def press(view, target, n=4):
    view.window.simulate("pointer_down", node=target)
    view.window.simulate("pointer_up", node=target)
    settle(view, n)


def key(view, name, n=4, **mods):
    view.window.simulate("key_down", key=name, **mods)
    settle(view, n)


def edit(view, i, text, commit="Enter"):
    box = text_box(view, i)
    box.focus()
    box.set(text=text[:-1] if text else "x")
    view.window.simulate("key_down", key="end")
    if text:
        view.window.simulate("input", text=text[-1])
    else:
        view.window.simulate("key_down", key="backspace")
    settle(view, 3)
    if commit == "Enter":
        key(view, "Enter")
    else:  # leaving the field
        view.node("root.le.actions.add").focus()
        settle(view, 4)


def shown(view):
    return [text_box(view, i).get("text") for i in range(ctl(view).count.get())]


def test_the_editor_and_its_mind_are_shipped_and_declared():
    assert {"ListEditor", "ListEditorRow"} <= set(shipped_views())
    declared = lookup("ListModel")
    assert declared is not None and declared.properties["value"].model and declared.properties["rows"].model and declared.properties["item_kind"] is not None


# -- text rows ---------------------------------------------------------------------------------------------------------------------------


def test_it_shows_a_row_with_a_field_for_each_item_and_changes_nothing(tmp_path):
    view, vm = opened(tmp_path)
    assert view.handle.viewmodel is vm
    assert shown(view) == ["alpha", "beta", "gamma"] and ctl(view).count.get() == 3 and vm.log == []
    assert vm.items.get() == ["alpha", "beta", "gamma"]


def test_a_text_row_writes_on_enter_and_only_the_edited_item_differs(tmp_path):
    view, vm = opened(tmp_path)
    edit(view, 1, "BETA two")
    assert vm.items.get() == ["alpha", "BETA two", "gamma"] and vm.log == [["alpha", "BETA two", "gamma"]]
    assert shown(view) == ["alpha", "BETA two", "gamma"]


def test_a_text_row_writes_when_the_field_is_left(tmp_path):
    view, vm = opened(tmp_path)
    edit(view, 2, "gamma!", commit="leave")
    assert vm.items.get() == ["alpha", "beta", "gamma!"] and len(vm.log) == 1


def test_typing_writes_nothing_until_the_commit(tmp_path):
    view, vm = opened(tmp_path)
    box = text_box(view, 0)
    box.focus()
    box.set(text="alph")
    settle(view, 4)
    assert vm.items.get() == ["alpha", "beta", "gamma"] and vm.log == []


def test_committing_what_is_already_there_is_no_change(tmp_path):
    view, vm = opened(tmp_path)
    edit(view, 0, "alpha")
    assert vm.log == []


def test_a_text_that_is_empty_or_has_spaces_in_it_is_written_as_it_is(tmp_path):
    view, vm = opened(tmp_path)
    edit(view, 0, "")
    edit(view, 1, "  two  words  ")
    assert vm.items.get() == ["", "  two  words  ", "gamma"]


def test_a_list_the_app_sets_is_shown_as_it_is_with_new_rows_and_is_not_told_back(tmp_path):
    view, vm = opened(tmp_path)
    vm.items.set(["x", "y"])
    settle(view, 6)
    assert shown(view) == ["x", "y"] and vm.log == []  # the app's list is shown as it is, and not told back


# -- add, remove, move ------------------------------------------------------------------------------------------------------------------


def test_add_appends_an_empty_item_and_tells_on_change(tmp_path):
    view, vm = opened(tmp_path)
    press(view, view.node("root.le.actions.add"))
    assert vm.items.get() == ["alpha", "beta", "gamma", ""] and vm.log == [["alpha", "beta", "gamma", ""]] and len(shown(view)) == 4


def test_remove_takes_its_own_row_out_and_the_others_keep_their_rows(tmp_path):
    view, vm = opened(tmp_path)
    kept = [r["uid"] for r in ctl(view).rows.get()]
    press(view, node(view, 1, "remove"))
    assert vm.items.get() == ["alpha", "gamma"] and shown(view) == ["alpha", "gamma"]
    assert [r["uid"] for r in ctl(view).rows.get()] == [kept[0], kept[2]]


def test_move_up_and_down_move_the_row_with_its_item_and_what_was_typed_goes_with_it(tmp_path):
    view, vm = opened(tmp_path)
    uids = [r["uid"] for r in ctl(view).rows.get()]
    press(view, node(view, 1, "up"))
    assert vm.items.get() == ["beta", "alpha", "gamma"]
    assert [r["uid"] for r in ctl(view).rows.get()] == [uids[1], uids[0], uids[2]] and shown(view) == ["beta", "alpha", "gamma"]
    press(view, node(view, 1, "down"))
    assert vm.items.get() == ["beta", "gamma", "alpha"] and shown(view) == ["beta", "gamma", "alpha"]
    assert vm.log == [["beta", "alpha", "gamma"], ["beta", "gamma", "alpha"]]


def test_the_first_row_cannot_move_up_and_the_last_cannot_move_down(tmp_path):
    view, vm = opened(tmp_path)
    assert node(view, 0, "up").get("disabled") is True and node(view, 0, "down").get("disabled") is False
    assert node(view, 2, "down").get("disabled") is True and node(view, 2, "up").get("disabled") is False
    press(view, node(view, 0, "up"))
    press(view, node(view, 2, "down"))
    assert vm.items.get() == ["alpha", "beta", "gamma"] and vm.log == []
    press(view, node(view, 1, "up"))  # after a move the ends are the new ends
    assert node(view, 0, "up").get("disabled") is True and node(view, 1, "up").get("disabled") is False


def test_the_empty_list_says_so_and_add_makes_the_first_item(tmp_path):
    view, vm = opened(tmp_path, items=[])
    assert ctl(view).count.get() == 0 and view.node("root.le.empty").get("text") == "No items"
    press(view, view.node("root.le.actions.add"))
    assert vm.items.get() == [""] and "root.le.empty" not in view._built.nodes


def test_min_items_stops_remove_and_says_why_and_max_items_stops_add(tmp_path):
    view, vm = opened(tmp_path, options=", min_items: 3, max_items: 3")
    assert node(view, 0, "remove").get("disabled") is True and view.node("root.le.actions.add").get("disabled") is True
    press(view, node(view, 0, "remove"))
    press(view, view.node("root.le.actions.add"))
    assert vm.items.get() == ["alpha", "beta", "gamma"] and vm.log == []
    vm.items.set(["a", "b", "c", "d"])
    settle(view, 6)
    assert node(view, 0, "remove").get("disabled") is False and view.node("root.le.actions.add").get("disabled") is True
    vm.items.set(["a", "b", "c"])
    settle(view, 6)
    assert node(view, 0, "remove").get("disabled") is True and view.node("root.le.actions.add").get("disabled") is True


def command(view, text):
    """What the view's rows do, sent as the view sends it: a number that is new each time and the words."""
    ctl(view).follow({**ctl(view)._values, "command": f"{next(COUNTER)} {text}"})
    settle(view, 4)


COUNTER = itertools.count(900)


def test_a_remove_command_at_the_fewest_says_why(tmp_path):
    view, vm = opened(tmp_path, options=", min_items: 3")
    command(view, "remove 0")
    assert "at least 3 items" in ctl(view).message.get() and view.node("root.le.message_text").get("text") == ctl(view).message.get()
    assert vm.items.get() == ["alpha", "beta", "gamma"]


# -- the other kinds ------------------------------------------------------------------------------------------------------------------------


def test_a_number_row_has_a_spin_box_bounded_by_least_and_most_and_an_int_stays_an_int(tmp_path):
    view, vm = opened(tmp_path, options=", item_kind: number, least: 0, most: 10", items=[1, 2, 3])
    assert shown_numbers(view) == ["1", "2", "3"] and vm.log == []
    press(view, number(view, 1).increment)
    assert vm.items.get() == [1, 3, 3] and all(isinstance(x, int) for x in vm.items.get()) and vm.log == [[1, 3, 3]]
    press(view, number(view, 0).decrement)
    press(view, number(view, 0).decrement)
    assert vm.items.get() == [0, 3, 3]  # not below the least


def number(view, i):
    return view._built.controls[f"{row(view, i)}.cell.number"]


def shown_numbers(view):
    return [number(view, i).input.get("text") for i in range(ctl(view).count.get())]


def test_a_number_row_with_a_step_below_one_writes_floats(tmp_path):
    view, vm = opened(tmp_path, options=", item_kind: number, step: 0.5", items=[1.0])
    press(view, number(view, 0).increment)
    assert vm.items.get() == [1.5]


def test_a_number_typed_in_the_spin_box_is_written_on_change(tmp_path):
    view, vm = opened(tmp_path, options=", item_kind: number, least: 0, most: 100", items=[1])
    box = number(view, 0)
    box.input.focus()
    view.window.simulate("key_down", key="end")
    view.window.simulate("key_down", key="backspace")
    view.window.simulate("input", text="42")
    settle(view, 4)
    assert vm.items.get() == [42] and vm.log[-1] == [42]


def flag(view, i):
    return view._built.controls[f"{row(view, i)}.cell.flag"]


def test_a_bool_row_has_a_switch_and_writes_true_and_false(tmp_path):
    view, vm = opened(tmp_path, options=", item_kind: bool", items=[True, False])
    assert [flag(view, i).selected.get() for i in (0, 1)] == [True, False]
    press(view, flag(view, 1).node)
    assert vm.items.get() == [True, True] and vm.log == [[True, True]]
    press(view, flag(view, 0).node)
    assert vm.items.get() == [False, True] and all(type(x) is bool for x in vm.items.get())


CHOICES = ", item_kind: enum, choices: [{value: low, label: Low}, {value: mid, label: Middle}, {value: high, label: High}]"


def test_an_enum_row_is_a_button_that_shows_the_label_and_opens_a_menu_of_the_choices(tmp_path):
    view, vm = opened(tmp_path, options=CHOICES, items=["mid", "low"])
    assert [view.node(f"{row(view, i)}.cell.choice.label").get("text") for i in (0, 1)] == ["Middle", "Low"]
    press(view, view.node(f"{row(view, 0)}.cell.choice"))
    assert view._shown_layers
    assert [k for k in view._built.nodes if k.startswith(f"{row(view, 0)}.cell.choices.surface.row[") and k.endswith("].item")] == [f"{row(view, 0)}.cell.choices.surface.row[{i}].item" for i in range(3)]
    press(view, view.node(f"{row(view, 0)}.cell.choices.surface.row[2].item"))
    assert vm.items.get() == ["high", "low"] and vm.log == [["high", "low"]] and not view._shown_layers
    assert view.node(f"{row(view, 0)}.cell.choice.label").get("text") == "High"


def test_an_enum_value_that_is_not_a_choice_is_shown_as_the_first_and_left_as_it_is(tmp_path):
    view, vm = opened(tmp_path, options=CHOICES, items=["nope"])
    assert view.node(f"{row(view, 0)}.cell.choice.label").get("text") == "Low" and vm.items.get() == ["nope"] and vm.log == []


def test_a_colour_row_is_a_swatch_that_opens_the_picker_and_writes_the_colour(tmp_path):
    view, vm = opened(tmp_path, options=", item_kind: colour", items=["#ff0000", "#00ff00"])
    trigger = view.node(f"{row(view, 1)}.cell.colour.trigger")
    assert trigger.get("fill") == (0, 255, 0, 255) and trigger.get("role") == "button"
    press(view, trigger)
    assert view._shown_layers
    square = view._built.controls[f"{row(view, 1)}.cell.colour.layer.surface.popup_panel.square"]
    node_ = square.node
    view.window.simulate("pointer_down", node_, x=128, y=44)
    view.window.simulate("pointer_up", x=node_.get("layout_x") + 128, y=node_.get("layout_y") + 44)
    settle(view, 4)
    assert vm.items.get()[0] == "#ff0000" and vm.items.get()[1] != "#00ff00" and colour.is_valid(vm.items.get()[1]) and vm.log


def test_a_colour_that_is_not_one_is_shown_as_black_and_left_alone(tmp_path):
    view, vm = opened(tmp_path, options=", item_kind: colour", items=["red"])
    assert view.node(f"{row(view, 0)}.cell.colour.trigger").get("fill") == (0, 0, 0, 255) and vm.items.get() == ["red"] and vm.log == []


def test_an_item_kind_that_is_not_one_is_named_and_the_list_is_shown_as_text(tmp_path):
    with pytest.raises(LoadError, match="item_kind"):
        opened(tmp_path, options=", item_kind: date")


# -- the keyboard, a11y, disabled, the look ------------------------------------------------------------------------------------------------


def test_the_keyboard_reaches_each_widget_in_a_row_and_its_buttons_and_enter_presses_one(tmp_path):
    view, vm = opened(tmp_path)
    first = text_box(view, 1)
    first.focus()
    for _ in range(3):
        key(view, "tab")
        if node(view, 1, "up").get("focused"):
            break
    assert node(view, 1, "up").get("focused")
    key(view, "enter")
    assert vm.items.get() == ["beta", "alpha", "gamma"]
    for part in ("up", "down", "remove"):
        assert node(view, 1, part).get("focusable")
    assert view.node("root.le.actions.add").get("focusable")


def test_the_names_a_screen_reader_hears(tmp_path):
    view, vm = opened(tmp_path, options=", label: Shortcuts")
    assert view.node("root.le").get("role") == "group" and view.node("root.le").get("label") == "Shortcuts"
    assert view.node("root.le.rows").get("role") == "list" and view.node("root.le.rows").get("label") == "Shortcuts"
    assert view.node(row(view, 1)).get("role") == "listitem" and view.node(row(view, 1)).get("label") == "Shortcuts 2"
    assert text_box(view, 2).get("label") == "Shortcuts 3"
    assert [node(view, 0, p).get("label") for p in ("up", "down", "remove")] == ["Move up", "Move down", "Remove"]
    assert view.node("root.le.actions.add").get("label") == "Add"


def test_a_removed_row_or_a_new_one_renames_the_others_by_their_place(tmp_path):
    view, vm = opened(tmp_path)
    press(view, node(view, 0, "remove"))
    assert [view.node(row(view, i)).get("label") for i in (0, 1)] == ["Items 1", "Items 2"]


def test_disabled_it_edits_nothing(tmp_path):
    view, vm = opened(tmp_path, options=", disabled: true")
    assert ctl(view).disabled.get()
    for part in ("up", "down", "remove"):
        assert node(view, 1, part).get("disabled") is True
    assert view.node("root.le.actions.add").get("disabled") is True
    press(view, node(view, 1, "remove"))
    press(view, view.node("root.le.actions.add"))
    command(view, "add")
    command(view, "remove 0")
    command(view, "set 0 changed")
    assert vm.items.get() == ["alpha", "beta", "gamma"] and vm.log == []


def test_an_unknown_property_of_the_editor_is_named(tmp_path):
    with pytest.raises(LoadError, match="colour"):
        opened(tmp_path, call="{widget: ListEditor, name: le, colour: red%s}")


def test_text_typed_and_not_yet_committed_is_committed_by_pressing_a_button_and_goes_with_its_row(tmp_path):
    view, vm = opened(tmp_path)
    box = text_box(view, 1)
    box.focus()
    box.set(text="be")
    view.window.simulate("key_down", key="end")
    view.window.simulate("input", text="e")
    settle(view, 3)
    press(view, node(view, 1, "up"))
    assert vm.items.get() == ["bee", "alpha", "gamma"] and shown(view) == ["bee", "alpha", "gamma"]


def test_another_rows_edit_leaves_a_row_that_is_being_typed_in_alone(tmp_path):
    view, vm = opened(tmp_path)
    box = text_box(view, 0)
    box.focus()
    box.set(text="alph")
    view.window.simulate("key_down", key="end")
    view.window.simulate("input", text="x")
    settle(view, 3)
    ctl(view).follow({**ctl(view)._values, "command": "950 set 2 omega"})  # the person did not leave row 0; something else wrote item 2
    settle(view, 4)
    assert vm.items.get() == ["alpha", "beta", "omega"] and text_box(view, 0).get("text") == "alphx"


def test_an_enum_opens_from_the_keyboard_and_escape_closes_it_and_the_choice_is_kept(tmp_path):
    view, vm = opened(tmp_path, options=CHOICES, items=["low"])
    button = view.node(f"{row(view, 0)}.cell.choice")
    button.focus()
    key(view, "enter")
    assert view._shown_layers
    key(view, "escape")
    assert not view._shown_layers and vm.items.get() == ["low"] and vm.log == []
    assert button.get("focusable")


def test_a_colour_popup_closes_with_escape_and_changes_nothing(tmp_path):
    view, vm = opened(tmp_path, options=", item_kind: colour", items=["#ff0000"])
    press(view, view.node(f"{row(view, 0)}.cell.colour.trigger"))
    assert view._shown_layers
    key(view, "escape", n=6)
    assert not view._shown_layers and vm.items.get() == ["#ff0000"] and vm.log == []
