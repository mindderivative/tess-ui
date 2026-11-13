"""T-034 (2): the font list -- `tess_ui.font_families` (the provider), `FontBrowser` (the model), the `FontBrowser` control, and the `FontList` view inline and in a popup, over a fake provider and
a fake `fc-list` under `tmp_path`. Nothing here runs the real `fc-list` or reads outside `tmp_path`."""

import stat

import pytest

from tess_ui import App, Signal, ViewModel, font_families, fonts, reactive, tokens
from tess_ui.font_controls import FontBrowser
from tess_ui.font_families import FontListError
from tess_ui.shipped import shipped_views
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.widgets import lookup

FAMILIES = ["Zilla Slab", "Fira Sans", "arial", "Roboto", "Noto Sans", "Hack Nerd Font Mono", "Droid Sans", "fira code", "Courier New"] + [f"Test Face {n:03d}" for n in range(60)]


class Provider:
    """A provider that counts its calls."""

    def __init__(self, names=FAMILIES, error=None):
        self.names, self.error, self.calls = names, error, 0

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return list(self.names)


@pytest.fixture(autouse=True)
def provider():
    """Every test has its own provider (the default one runs `fc-list`)."""
    fake = Provider()
    previous = font_families.use(fake)
    yield fake
    font_families.use(previous if previous is not font_families.default_provider else None)


def fake_fc_list(tmp_path, body):
    """A `fc-list` script in its own folder, and `PATH` set to that folder only."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "fc-list"
    script.write_text("#!/bin/sh\n" + body)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return bin_dir


# -- the provider ------------------------------------------------------------------------------------------------------------------------

def test_parse_splits_lines_and_commas_trims_drops_repeats_and_sorts_without_regard_to_case():
    text = "Fira Sans,Fira Sans Eight\nNoto Sans Arabic\n\n  Zilla Slab \nfira sans\nDejaVu Sans,DejaVu Sans Condensed\nNoto Sans Arabic\narial,\n"
    assert font_families.parse(text) == ["arial", "DejaVu Sans", "DejaVu Sans Condensed", "Fira Sans", "Fira Sans Eight", "Noto Sans Arabic", "Zilla Slab"]


def test_parse_keeps_an_escaped_comma_and_backslash_in_a_name():
    assert font_families.parse("Odd\\, Name,Plain\nBack\\\\slash") == ["Back\\slash", "Odd, Name", "Plain"]


def test_the_default_provider_runs_fc_list_with_family_and_reads_what_it_prints(tmp_path, monkeypatch):
    (tmp_path / "args").write_text("")
    bin_dir = fake_fc_list(tmp_path, f'echo "$@" > {tmp_path}/args\nprintf "Beta,Beta Light\\nalpha\\nBeta\\n"\n')
    monkeypatch.setenv("PATH", str(bin_dir))
    assert font_families.default_provider() == ["alpha", "Beta", "Beta Light"]
    assert (tmp_path / "args").read_text().strip() == ": family"


def test_a_machine_with_no_fc_list_is_a_font_list_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(FontListError, match="not installed"):
        font_families.default_provider()


@pytest.mark.parametrize("body, message", [("exit 3\n", "failed"), ("exit 0\n", "no fonts"), ("printf '\\n\\n'\n", "no fonts")])
def test_an_fc_list_that_fails_or_lists_nothing_is_a_font_list_error(tmp_path, monkeypatch, body, message):
    monkeypatch.setenv("PATH", str(fake_fc_list(tmp_path, body)))
    with pytest.raises(FontListError, match=message):
        font_families.default_provider()


def test_an_fc_list_that_takes_too_long_is_a_font_list_error(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", f"{fake_fc_list(tmp_path, 'exec sleep 5')}:/usr/bin:/bin")
    monkeypatch.setattr(font_families, "TIMEOUT", 0.2)
    with pytest.raises(FontListError, match="more than"):
        font_families.default_provider()


def test_families_asks_the_provider_once_and_refresh_asks_again(provider):
    first = font_families.families()
    assert first == sorted(set(FAMILIES), key=str.casefold) and provider.calls == 1
    assert font_families.families() == first and provider.calls == 1
    provider.names = ["Only One"]
    font_families.refresh()
    assert font_families.families() == ["Only One"] and provider.calls == 2


def test_a_provider_that_cannot_say_is_kept_as_an_error_and_not_asked_again(provider):
    provider.error = FontListError("no fontconfig here")
    for _ in range(3):
        with pytest.raises(FontListError, match="no fontconfig"):
            font_families.families()
    assert provider.calls == 1
    provider.error, provider.names = None, ["A"]
    font_families.refresh()
    assert font_families.families() == ["A"]


def test_a_provider_that_gives_nothing_or_raises_an_os_error_is_a_font_list_error(provider):
    provider.names = []
    with pytest.raises(FontListError, match="no fonts"):
        font_families.families()
    provider.names, provider.error = ["A"], OSError(5, "I/O error")
    font_families.refresh()
    with pytest.raises(FontListError, match="I/O error"):
        font_families.families()


def test_use_returns_the_provider_it_replaced_and_none_puts_fc_list_back(provider):
    other = Provider(["Z", "a"])
    assert font_families.use(other) is provider
    assert font_families.families() == ["a", "Z"]
    assert font_families.use(None) is other and font_families._provider is font_families.default_provider


# -- the model ---------------------------------------------------------------------------------------------------------------------------

def browser(names=None, page=4):
    return FontBrowser(names or [f"Face {n:02d}" for n in range(30)], page)


def test_search_takes_every_word_without_regard_to_case_and_puts_a_name_that_starts_with_it_first():
    model = FontBrowser(["Droid Sans", "Sans Forgetica", "Noto Sans", "Fira Code"])
    model.set_query("SANS")
    assert model.results == ["Sans Forgetica", "Droid Sans", "Noto Sans"]
    model.set_query("sans noto")
    assert model.results == ["Noto Sans"]
    model.set_query("nothing")
    assert model.results == [] and model.cursor == -1 and model.picked is None
    model.set_query("")
    assert len(model.results) == 4 and model.cursor == 0


def test_the_keys_move_the_cursor_and_stop_at_the_ends():
    model = browser()
    assert model.cursor == 0
    model.press("arrow_down")
    model.press("arrow_down")
    assert model.cursor == 2
    model.press("page_down")
    assert model.cursor == 6
    model.press("end")
    assert model.cursor == 29
    model.press("arrow_down")
    assert model.cursor == 29
    model.press("home")
    model.press("arrow_up")
    model.press("page_up")
    assert model.cursor == 0
    assert model.press("enter") == "pick" and model.press("space") == "pick" and model.press("x") is None


def test_in_the_search_field_home_end_and_space_are_the_texts():
    model = browser()
    model.cursor = 5
    for key in ("home", "end", " ", "arrow_left"):
        assert model.press(key, in_field=True) is None and model.cursor == 5
    model.press("page_down", in_field=True)
    assert model.cursor == 9 and model.press("enter", in_field=True) == "pick"


def test_the_keys_do_nothing_with_no_results():
    model = FontBrowser(["A"])
    model.set_query("zzz")
    assert model.press("arrow_down") is None and model.press("enter") is None and model.click(0) is None and model.click(-1) is None


def test_reveal_keeps_the_cursor_row_in_the_window():
    model = browser(page=3)
    model.cursor = 7
    assert model.reveal(0.0, 40.0) == 5 * 40.0
    assert model.reveal(5 * 40.0, 40.0) == 5 * 40.0
    model.cursor = 2
    assert model.reveal(5 * 40.0, 40.0) == 2 * 40.0
    assert model.reveal(0.0, 40.0) == 0.0


# -- the view ----------------------------------------------------------------------------------------------------------------------------

class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.font = Signal("Roboto")
        self.pop = Signal(False)
        self.log = []

    def changed(self):
        self.log.append(self.font.get())


CALL = '{widget: FontList, name: fl, value: "{{ font }}", on_change: changed%s}'
POPUP = '{widget: FontList, name: fl, popup: true, open: "{{ pop }}", value: "{{ font }}", on_change: changed%s}'


def opened(tmp_path, call=CALL, options="", dark=False, size=(460, 600), sheet=None):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.yaml").write_text(f"""tesserae: 0.6
name: main
widget: Container
style: {{flex_direction: vertical, gap: 16, padding: 16, width: {size[0]}, height: {size[1]}}}
children:
  - {call % options}
  - {{widget: Rect, name: elsewhere, style: {{width: 80, height: 80, background: surface_variant}}}}
""")
    if sheet:
        (tmp_path / "Views" / "Main_Stylesheet.yaml").write_text(sheet)
    app = App(root=tmp_path, width=size[0], height=size[1], theme_seed=(0x67, 0x50, 0xA4, 0xFF), dark=dark)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 4)
    return view, app.bindings.viewmodel_for("main")


def settle(view, n=6):
    for _ in range(n):
        view.window.advance(16)


def panel_of(popup=False):
    return "root.fl.layer.surface.popup_panel" if popup else "root.fl.panel"


def ctl(view, popup=False):
    return view._built.controls[f"{panel_of(popup)}.browser"]


def node(view, name, popup=False):
    return view._built.nodes[f"{panel_of(popup)}.{name}"]


def search(view, popup=False):
    return node(view, "search.box.body.input", popup)


def typed(view, text, popup=False):
    field = search(view, popup)
    field.focus()
    field.set(text=text[:-1])
    view.window.simulate("key_down", key="end")
    view.window.simulate("input", text=text[-1])
    settle(view, 3)


def key(view, name, popup=False, n=3):
    box = node(view, "list_group.list_box", popup)
    if not box.get("focused"):
        box.focus()
    view.window.simulate("key_down", key=name)
    settle(view, n)


def field_key(view, name, popup=False):
    search(view, popup).focus()
    view.window.simulate("key_down", key=name)
    settle(view, 3)


def row_ids(view, popup=False):
    prefix = f"{panel_of(popup)}.list_group.list_box.list.row["
    return sorted((k for k in view._built.nodes if k.startswith(prefix) and k.endswith("]")), key=lambda k: view._built.nodes[k].get("layout_y"))


def shown(view, popup=False):
    prefix = f"{panel_of(popup)}.list_group.list_box.list.row["
    return [k[len(prefix):-1] for k in row_ids(view, popup)]


def row(view, family, popup=False):
    return view._built.nodes[f"{panel_of(popup)}.list_group.list_box.list.row[{family}]"]


def press(view, target, n=4):
    view.window.simulate("pointer_down", node=target)
    view.window.simulate("pointer_up", node=target)
    settle(view, n)


def test_the_list_and_its_parts_are_shipped_and_declared():
    assert {"FontList", "FontListPanel"} <= set(shipped_views())
    declared = lookup("FontBrowser")
    assert declared is not None and declared.properties["value"].model and declared.properties["mode"].model


def test_inline_it_lists_the_families_sorted_without_regard_to_case_with_the_value_picked(tmp_path, provider):
    view, vm = opened(tmp_path)
    assert view.handle.viewmodel is vm
    control = ctl(view)
    assert control.mode.get() == "list" and control.count.get() == len(FAMILIES)
    assert [e["family"] for e in control.entries.get()][:4] == ["arial", "Courier New", "Droid Sans", "fira code"]
    assert provider.calls == 1
    assert control.browser.picked == "Roboto" and control.cursor_name.get() == "Roboto"
    assert control.scroll.get() == 0  # `Roboto` is the eighth family: it shows with the first
    assert 0 < len(shown(view)) <= 8 + 2 * 3 + 1  # the rows in view and three past each edge, not all 69
    assert row(view, "Roboto").get("fill") == (view._scheme or tokens.BASELINE)["secondary_container"]


def test_a_family_is_shown_in_its_own_face_only_when_the_engine_can_draw_it(tmp_path):
    assert "Roboto" in fonts.available_families() and "Fira Sans" not in fonts.available_families()
    view, vm = opened(tmp_path)
    name = lambda family: view._built.nodes[f"{panel_of()}.list_group.list_box.list.row[{family}].row_name"]  # noqa: E731
    assert name("Roboto").get("font_family") == "Roboto"
    key(view, "home")
    assert name("arial").get("font_family") != "arial"  # not one the engine has: the ordinary face
    entries = {e["family"]: e["loadable"] for e in ctl(view).entries.get()}
    assert entries["Roboto"] is True and entries["arial"] is False and entries["Hack Nerd Font Mono"] is True


def test_a_press_picks_a_family_writes_value_and_calls_on_change(tmp_path):
    view, vm = opened(tmp_path)
    key(view, "home")
    press(view, row(view, "Courier New"))
    assert vm.font.get() == "Courier New" and vm.log == ["Courier New"]
    assert ctl(view).value.get() == "Courier New" and ctl(view).cursor_name.get() == "Courier New"


def test_a_value_set_from_the_viewmodel_moves_the_selection_and_the_cursor(tmp_path):
    view, vm = opened(tmp_path)
    vm.font.set("Hack Nerd Font Mono")
    settle(view, 6)
    assert ctl(view).value.get() == "Hack Nerd Font Mono" and ctl(view).cursor_name.get() == "Hack Nerd Font Mono"
    vm.font.set("Test Face 050")
    settle(view, 6)
    assert ctl(view).cursor_name.get() == "Test Face 050" and ctl(view).scroll.get() > 0 and "Test Face 050" in shown(view)  # scrolled so that it shows
    assert vm.log == []  # a change the app made is not on_change


def test_a_value_that_is_not_an_installed_family_is_kept_as_it_is_and_nothing_is_selected(tmp_path):
    view, vm = opened(tmp_path)
    vm.font.set("Imaginary Face")
    settle(view, 6)
    assert vm.font.get() == "Imaginary Face" and ctl(view).value.get() == "Imaginary Face"
    assert ctl(view).current.get() == {"family": "Imaginary Face", "loadable": False}


def test_typing_in_the_search_field_narrows_the_list(tmp_path):
    view, vm = opened(tmp_path)
    control = ctl(view)
    typed(view, "fira")
    assert [e["family"] for e in control.entries.get()] == ["Fira Sans", "fira code"] or [e["family"] for e in control.entries.get()] == ["fira code", "Fira Sans"]
    assert control.count.get() == 2 and control.scroll.get() == 0 and control.cursor_name.get() == control.entries.get()[0]["family"]
    typed(view, "zzzz")
    assert control.count.get() == 0 and "root.fl.panel.empty" in view._built.nodes
    typed(view, "face 005")
    assert [e["family"] for e in control.entries.get()] == ["Test Face 005"]


def test_from_the_search_field_down_moves_the_cursor_and_enter_picks(tmp_path):
    view, vm = opened(tmp_path)
    typed(view, "sans")
    control = ctl(view)
    first, second = [e["family"] for e in control.entries.get()][:2]
    field_key(view, "arrow_down")
    assert control.cursor_name.get() == second
    field_key(view, "arrow_up")
    assert control.cursor_name.get() == first
    field_key(view, "arrow_down")
    search(view).focus()
    view.window.simulate("key_down", key="Enter")  # the name a text field's Enter has
    settle(view, 4)
    assert vm.font.get() == second and vm.log == [second]


def test_the_left_and_right_keys_home_and_end_in_the_search_field_are_the_texts(tmp_path):
    view, vm = opened(tmp_path)
    typed(view, "sans")
    for name in ("arrow_right", "end", "home"):
        field_key(view, name)
    assert ctl(view).cursor_name.get() == ctl(view).entries.get()[0]["family"]


def test_the_list_has_the_keys_and_scrolls_to_keep_the_cursor_in_view(tmp_path):
    view, vm = opened(tmp_path)
    control = ctl(view)
    start = control.browser.cursor
    key(view, "arrow_down")
    assert control.browser.cursor == start + 1
    key(view, "arrow_up")
    key(view, "end")
    last = control.count.get() - 1
    assert control.browser.cursor == last and control.scroll.get() == pytest.approx((last + 1 - 8) * 40.0)
    assert shown(view)[-1] == control.entries.get()[-1]["family"]
    key(view, "home")
    assert control.browser.cursor == 0 and control.scroll.get() == 0
    key(view, "page_down")
    assert control.browser.cursor == 8
    assert vm.log == []  # moving is not picking


def test_enter_and_space_pick_the_cursor_family_in_the_list(tmp_path):
    view, vm = opened(tmp_path)
    key(view, "home")
    key(view, "enter")
    assert vm.font.get() == "arial" and vm.log == ["arial"]
    key(view, "arrow_down")
    key(view, " ")
    assert vm.font.get() == "Courier New" and len(vm.log) == 2


def test_the_list_is_in_the_tab_order_after_the_search_field(tmp_path):
    view, vm = opened(tmp_path)
    assert node(view, "list_group.list_box").get("focusable") and search(view).get("focusable")


def test_the_names_a_screen_reader_hears(tmp_path):
    view, vm = opened(tmp_path, options=", label: Body font")
    box = node(view, "list_group.list_box")
    assert box.get("role") == "list" and box.get("label") == "Body font families"
    assert row(view, "Roboto").get("role") == "listitem" and row(view, "Roboto").get("label") == "Roboto" and row(view, "Roboto").get("selected") is True
    assert row(view, "Noto Sans").get("selected") is False
    assert search(view).get("label") == "Search fonts"


def test_disabled_it_changes_nothing(tmp_path):
    view, vm = opened(tmp_path, options=", disabled: true")
    assert ctl(view).disabled.get()
    press(view, row(view, shown(view)[0]))
    key(view, "enter")
    assert vm.font.get() == "Roboto" and vm.log == []


def test_six_thousand_nine_hundred_families_build_only_the_rows_in_view(tmp_path, provider):
    provider.names = [f"Family {n:05d}" for n in range(6900)]
    view, vm = opened(tmp_path)
    control = ctl(view)
    assert control.count.get() == 6900 and len(shown(view)) <= 15
    key(view, "end")
    assert len(shown(view)) <= 15 and control.cursor_name.get() == "Family 06899"
    assert provider.calls == 1


# -- no list of fonts: a text field --------------------------------------------------------------------------------------------------------

def test_when_the_families_cannot_be_listed_there_is_a_text_field_that_says_why_and_no_list(tmp_path, provider):
    provider.error = FontListError("fc-list is not installed")
    view, vm = opened(tmp_path)
    assert "root.fl.panel.free" in view._built.nodes
    assert "root.fl.panel.search" not in view._built.nodes and "root.fl.panel.list_group" not in view._built.nodes
    control = ctl(view)
    assert control.mode.get() == "text" and "fc-list is not installed" in control.message.get()
    free = node(view, "free.box.body.input")
    assert free.get("text") == "Roboto"
    notes = [k for k in view._built.nodes if k.startswith("root.fl.panel.free.") and k.endswith(".supporting")]
    assert len(notes) == 1 and "fc-list is not installed" in view._built.nodes[notes[0]].get("text")


def test_the_text_field_takes_the_value_and_calls_on_change(tmp_path, provider):
    provider.error = FontListError("fc-list is not installed")
    view, vm = opened(tmp_path)
    field = node(view, "free.box.body.input")
    field.focus()
    field.set(text="Fira Sa")
    view.window.simulate("key_down", key="end")
    view.window.simulate("input", text="n")
    settle(view, 4)
    assert vm.font.get() == "Fira San" and vm.log and vm.log[-1] == "Fira San"
    vm.font.set("Hack")
    settle(view, 6)
    assert node(view, "free.box.body.input").get("text") == "Hack"


def test_a_popup_with_no_list_is_the_text_field_and_not_a_button(tmp_path, provider):
    provider.error = FontListError("fc-list is not installed")
    view, vm = opened(tmp_path, POPUP)
    assert "root.fl.free" in view._built.nodes and "root.fl.field" not in view._built.nodes and "root.fl.layer" not in view._built.nodes
    assert view._built.nodes["root.fl.free.box.body.input"].get("text") == "Roboto"


def test_fc_list_missing_through_the_default_provider_gives_the_text_field(tmp_path, monkeypatch):
    font_families.use(None)
    monkeypatch.setenv("PATH", str(tmp_path))
    view, vm = opened(tmp_path)
    assert "root.fl.panel.free" in view._built.nodes and ctl(view).mode.get() == "text"


# -- the popup ---------------------------------------------------------------------------------------------------------------------------

def test_a_popup_is_a_button_with_the_family_in_its_own_face_until_it_is_opened(tmp_path, provider):
    view, vm = opened(tmp_path, POPUP, options=", label: Typeface")
    trigger = view.node("root.fl.field.trigger")
    assert trigger.get("role") == "button" and trigger.get("label") == "Typeface: Roboto" and trigger.get("expanded") is False
    text = view.node("root.fl.field.trigger_text")
    assert text.get("text") == "Roboto" and text.get("font_family") == "Roboto"
    assert not view._shown_layers and vm.pop.get() is False
    vm.font.set("Fira Sans")
    settle(view, 6)
    assert view.node("root.fl.field.trigger_text").get("font_family") != "Fira Sans"  # the engine has no such face: the ordinary one
    vm.font.set("")
    settle(view, 6)
    assert view.node("root.fl.field.trigger_text").get("text") == "Choose a font" and trigger.get("label") == "Typeface"


def test_pressing_the_button_opens_the_list_with_the_search_field_focused(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.fl.field.trigger"))
    assert vm.pop.get() is True and view._shown_layers and search(view, True).get("focused")
    assert view.node("root.fl.field.trigger").get("expanded") is True
    assert view.node("root.fl.layer.surface").get("corner_radius") == 12.0 and ctl(view, True).count.get() == len(FAMILIES)


def test_a_pick_closes_the_popup_and_writes_the_value(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.fl.field.trigger"))
    key(view, "home", popup=True)
    press(view, row(view, "Courier New", True))
    assert vm.font.get() == "Courier New" and vm.log == ["Courier New"] and vm.pop.get() is False and not view._shown_layers
    assert view.node("root.fl.field.trigger_text").get("text") == "Courier New"
    press(view, view.node("root.fl.field.trigger"))
    assert ctl(view, True).browser.picked == "Courier New"  # and it opens again, on the new value


def test_a_pick_leaves_the_popup_open_when_it_says_not_to_close(tmp_path):
    view, vm = opened(tmp_path, POPUP, options=", close_on_pick: false")
    press(view, view.node("root.fl.field.trigger"))
    key(view, "home", popup=True)
    press(view, row(view, "arial", True))
    assert vm.font.get() == "arial" and vm.pop.get() is True and view._shown_layers


def test_enter_in_the_search_field_picks_and_closes(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.fl.field.trigger"))
    typed(view, "courier", popup=True)
    search(view, True).focus()
    view.window.simulate("key_down", key="Enter")
    settle(view, 6)
    assert vm.font.get() == "Courier New" and vm.pop.get() is False


def test_escape_closes_the_popup_from_the_field_and_from_the_list_and_writes_false_back(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.fl.field.trigger"))
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers and vm.font.get() == "Roboto" and vm.log == []
    press(view, view.node("root.fl.field.trigger"))
    assert vm.pop.get() is True
    node(view, "list_group.list_box", True).focus()
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers


def test_the_popup_opens_from_the_keyboard_and_escape_gives_the_focus_back_to_the_button(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    trigger = view.node("root.fl.field.trigger")
    trigger.focus()
    view.window.simulate("key_down", key="enter")
    settle(view, 6)
    assert vm.pop.get() is True and search(view, True).get("focused")
    view.window.simulate("key_down", key="escape")
    settle(view, 8)
    assert vm.pop.get() is False and trigger.get("focused")


def test_a_press_outside_closes_the_popup_and_the_button_closes_it_too(tmp_path):
    view, vm = opened(tmp_path, POPUP)
    press(view, view.node("root.fl.field.trigger"))
    view.window.simulate("pointer_down", x=430, y=580)
    view.window.simulate("pointer_up", x=430, y=580)
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers
    trigger = view.node("root.fl.field.trigger")
    press(view, trigger)
    view.window.advance(1000)
    x, y = trigger.get("layout_x") + 30, trigger.get("layout_y") + 24
    view.window.simulate("pointer_down", x=x, y=y)
    view.window.simulate("pointer_up", x=x, y=y)
    settle(view, 4)
    assert vm.pop.get() is False and not view._shown_layers


def test_a_disabled_popup_does_not_open_and_one_can_be_opened_from_the_viewmodel(tmp_path):
    view, vm = opened(tmp_path / "a", POPUP, options=", disabled: true")
    press(view, view.node("root.fl.field.trigger"))
    assert vm.pop.get() is False and not view._shown_layers
    view, vm = opened(tmp_path / "b", POPUP)
    vm.pop.set(True)
    settle(view, 6)
    assert view._shown_layers
    vm.pop.set(False)
    settle(view, 6)
    assert not view._shown_layers


def test_the_provider_is_asked_once_however_often_the_popup_opens(tmp_path, provider):
    view, vm = opened(tmp_path, POPUP)
    for _ in range(3):
        vm.pop.set(True)
        settle(view, 6)
        vm.pop.set(False)
        settle(view, 6)
    assert provider.calls == 1


def _collect_reentrant(monkeypatch):
    errors = []
    original = reactive._Notifiable._notify

    def watching(self, *args, **kwargs):
        try:
            return original(self, *args, **kwargs)
        except RuntimeError as error:
            errors.append(error)
            raise

    monkeypatch.setattr(reactive._Notifiable, "_notify", watching)
    return errors


STATE_RULES = """tesserae: 0.6
styles:
  - {widget: FontList, state: focused, style: {opacity: 0.99}}
  - {widget: FontList, state: hovered, style: {opacity: 0.98}}
  - {widget: FontList, state: pressed, style: {opacity: 0.97}}
"""


def test_escape_and_a_pick_with_a_state_rule_on_the_popup_root_raise_no_reentrant_write(tmp_path, monkeypatch):
    errors = _collect_reentrant(monkeypatch)
    view, vm = opened(tmp_path, POPUP, sheet=STATE_RULES)
    press(view, view.node("root.fl.field.trigger"))
    view.window.simulate("key_down", key="escape")
    settle(view, 8)
    assert vm.pop.get() is False and not view._shown_layers
    press(view, view.node("root.fl.field.trigger"))
    key(view, "home", popup=True)
    press(view, row(view, "arial", True))
    assert vm.font.get() == "arial" and vm.pop.get() is False and errors == []


def test_an_unknown_property_of_the_list_is_named(tmp_path):
    with pytest.raises(LoadError, match="colour"):
        opened(tmp_path, call="{widget: FontList, name: fl, colour: red%s}")
