"""The combo box's behaviour (ux spec Autocomplete AC-ACP-2 to AC-ACP-7, tess-behavior SPEC 2.5d): no window, the model alone."""

import pytest

from tess_ui.combobox_controls import ComboboxModel

FRUIT = [{"value": "apple", "label": "Apple"}, {"value": "avocado", "label": "Avocado"}, {"value": "banana", "label": "Banana"}, {"value": "cherry", "label": "Cherry", "disabled": True},
         {"value": "date", "label": "Date"}]


def labels(model):
    return [r["label"] for r in model.results]


def test_typing_narrows_by_containing_text_in_the_order_of_the_options_and_marks_the_match_AC_ACP_2():
    m = ComboboxModel(FRUIT)
    m.type("a")
    assert labels(m) == ["Apple", "Avocado", "Banana", "Date"] and m.open and m.active == -1
    m.type("av")
    assert labels(m) == ["Avocado"] and m.results[0]["runs"] == [{"text": "Av", "weight": 500}, "ocado"]
    m.type("zzz")
    assert labels(m) == [] and m.open
    m.type("")
    assert len(m.results) == 5


def test_down_opens_with_the_first_enabled_row_or_the_selected_one_and_stops_at_the_last_AC_ACP_3():
    m = ComboboxModel(FRUIT)
    m.key("arrow_down")
    assert m.open and m.active == 0
    for _ in range(9):
        m.key("arrow_down")
    assert m.active == 4  # Cherry (disabled) is skipped on the way, and the last row stops it
    m2 = ComboboxModel(FRUIT, value="banana")
    m2.key("arrow_down")
    assert m2.active == 2
    m3 = ComboboxModel(FRUIT)
    m3.key("arrow_down", alt=True)
    assert m3.open and m3.active == -1


def test_up_opens_with_the_last_row_goes_up_and_from_the_first_row_makes_none_active_AC_ACP_3():
    m = ComboboxModel(FRUIT)
    m.key("arrow_up")
    assert m.open and m.active == 4
    for _ in range(9):
        m.key("arrow_up")
    assert m.active == -1


def test_home_and_end_are_the_texts_and_leave_the_active_row_AC_ACP_3():
    m = ComboboxModel(FRUIT)
    m.key("arrow_down")
    assert m.key("home") is False and m.key("end") is False and m.active == 0


def test_enter_on_an_active_row_picks_it_closes_and_the_field_shows_its_label_AC_ACP_4():
    m = ComboboxModel(FRUIT)
    m.type("a")
    m.key("arrow_down")
    m.key("arrow_down")
    m.key("enter")
    assert (m.value, m.text, m.open) == ("avocado", "Avocado", False) and m.picked["value"] == "avocado"
    assert len(m.results) == 5  # the query is empty again: every option shows


def test_strict_enter_with_no_active_row_keeps_the_value_and_tab_picks_an_exact_label_else_reverts_AC_ACP_5():
    m = ComboboxModel(FRUIT, value="banana")
    m.type("xyz")
    m.key("enter")
    assert (m.value, m.text, m.open) == ("banana", "Banana", False)
    m.type("xyz")
    m.leave()
    assert (m.value, m.text) == ("banana", "Banana")
    m.type("apple")
    m.leave()
    assert (m.value, m.text) == ("apple", "Apple") and m.picked["value"] == "apple"


def test_tab_picks_an_active_row_only_when_an_arrow_key_chose_it():
    m = ComboboxModel(FRUIT)
    m.type("a")
    m.leave()
    assert m.value == ""  # typing makes no row active, and "a" is no label
    m = ComboboxModel(FRUIT)
    m.type("a")
    m.key("arrow_down")
    m.leave()
    assert m.value == "apple"


def test_free_takes_the_typed_text_on_enter_and_an_active_row_wins_AC_ACP_6():
    m = ComboboxModel(FRUIT, strict=False)
    m.type("kiwi")
    m.key("enter")
    assert m.value == "kiwi" and m.picked["value"] == "kiwi"
    m = ComboboxModel(FRUIT, strict=False)
    m.type("kiwi")
    m.key("arrow_down")
    m.type("kiwi")  # no change: still no row
    m = ComboboxModel(FRUIT, strict=False)
    m.key("arrow_down")
    m.key("enter")
    assert m.value == "apple"


def test_escape_closes_the_list_and_keeps_the_text_then_strict_restores_and_free_leaves_it_AC_ACP_7():
    m = ComboboxModel(FRUIT, value="banana")
    m.type("xyz")
    assert m.escape() is True and not m.open and m.text == "xyz"
    assert m.escape() is True and m.text == "Banana"
    assert m.escape() is False  # nothing to undo: the key is not consumed
    f = ComboboxModel(FRUIT, strict=False, value="banana")
    f.type("xyz")
    f.escape()
    assert f.escape() is False and f.text == "xyz"


def test_a_disabled_row_is_not_pickable_and_the_order_stays_the_options():
    m = ComboboxModel(FRUIT)
    m.type("e")
    assert labels(m) == ["Apple", "Cherry", "Date"] and m.pick(1) is False and m.value == ""


def test_page_keys_move_by_a_page_of_rows():
    m = ComboboxModel([{"value": i, "label": f"Row {i}"} for i in range(30)], page_rows=8)
    m.key("arrow_down")
    m.key("page_down")
    assert m.active == 8
    m.key("page_up")
    assert m.active == 0
