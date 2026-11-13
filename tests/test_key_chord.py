"""T-034 (3): the key-chord field -- `tess_ui.key_chords` (the text rules), the `ChordRecorder` control and the `KeyChordField` view, driven by key events on a headless window.
Nothing here reads outside `tmp_path`."""

import pytest

from tess_ui import App, Signal, ViewModel, key_chords, tokens
from tess_ui.shipped import shipped_views
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.widgets import lookup

# -- the text rules ----------------------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text, chord", [
    ("Ctrl+Shift+F1", "Ctrl+Shift+F1"),
    ("ctrl+shift+f1", "Ctrl+Shift+F1"),
    ("SHIFT+CTRL+f1", "Ctrl+Shift+F1"),  # the order is fixed
    ("Meta+Shift+Alt+Ctrl+a", "Ctrl+Alt+Shift+Meta+A"),
    ("  Control + Return ", "Ctrl+Enter"),
    ("super+pgup", "Meta+PageUp"),
    ("Option+Del", "Alt+Delete"),
    ("cmd+esc", "Meta+Escape"),
    ("alt+arrow_left", "Alt+Left"),
    ("Alt+ArrowRight", "Alt+Right"),
    ("ctrl+space", "Ctrl+Space"),
    ("Ctrl+plus", "Ctrl+Plus"),
    ("ctrl+1", "Ctrl+1"),
    ("F24", "F24"),
    ("Escape", "Escape"),
    ("a", "A"),
    ("Ctrl+/", "Ctrl+/"),
])
def test_a_chord_in_any_case_and_any_common_name_reads_as_the_canonical_text(text, chord):
    assert key_chords.normalise(text) == chord


@pytest.mark.parametrize("text", ["", "   ", "+", "Ctrl+", "+A", "Ctrl+Shift", "Ctrl+Ctrl+A", "Ctrl+A+B", "Ctrl+Foo", "F0", "F25", "F01", "Ctrl++", "Hyper+A+", "Ctrl+Alt"])
def test_text_that_is_not_one_chord_is_not_read(text):
    assert key_chords.normalise(text) is None


def test_the_canonical_text_is_its_own_normal_form():
    for text in ("Ctrl+Alt+Shift+Meta+A", "Ctrl+Shift+F1", "Alt+Left", "PageDown", "Meta+Space", "Shift+Plus"):
        assert key_chords.normalise(text) == text


@pytest.mark.parametrize("key, mods, chord", [
    ("F1", {"ctrl": True, "shift": True}, "Ctrl+Shift+F1"),
    ("f5", {}, "F5"),
    ("a", {"ctrl": True}, "Ctrl+A"),
    ("A", {"shift": True}, "Shift+A"),
    ("arrow_left", {"alt": True}, "Alt+Left"),
    ("page_down", {}, "PageDown"),
    ("escape", {"ctrl": True}, "Ctrl+Escape"),
    (" ", {"meta": True}, "Meta+Space"),
    ("+", {"ctrl": True}, "Ctrl+Plus"),
    ("1", {"ctrl": True, "alt": True, "shift": True, "meta": True}, "Ctrl+Alt+Shift+Meta+1"),
    ("enter", {}, "Enter"),
    ("backspace", {"shift": True}, "Shift+Backspace"),
])
def test_a_key_press_is_a_chord_with_the_modifiers_in_order_and_the_key_last(key, mods, chord):
    assert key_chords.from_event(key, **mods) == chord


@pytest.mark.parametrize("key", ["shift", "shift_left", "shift_right", "control", "control_left", "ctrl", "alt", "alt_graph", "alt_right", "meta", "super", "meta_left", "caps_lock", "num_lock", "hyper"])
def test_a_bare_modifier_is_no_key_of_a_chord(key):
    assert key_chords.is_modifier_key(key) and key_chords.from_event(key, shift=True) is None


@pytest.mark.parametrize("key", ["print_screen", "audio_volume_up", "foo", "f25", ""])
def test_a_key_no_chord_can_have_is_none(key):
    assert key_chords.from_event(key) is None and not key_chords.is_modifier_key(key)


def test_modifier_of_names_the_modifier_a_key_is():
    assert [key_chords.modifier_of(k) for k in ("shift_left", "control", "ctrl_right", "alt_graph", "super", "meta", "caps_lock", "a")] == ["Shift", "Ctrl", "Ctrl", "Alt", "Meta", "Meta", None, None]


# -- the view -----------------------------------------------------------------------------------------------------------------------------


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.chord = Signal("Ctrl+Shift+F1")
        self.rec = Signal(False)
        self.log = []

    def changed(self):
        self.log.append(self.chord.get())


CALL = '{widget: KeyChordField, name: kc, value: "{{ chord }}", on_change: changed%s}'


def opened(tmp_path, call=CALL, options="", chord=None, dark=False, size=(560, 200)):
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
    if chord is not None:
        vm.chord.set(chord)
        settle(view, 6)
    return view, vm


def settle(view, n=6):
    for _ in range(n):
        view.window.advance(16)


def ctl(view):
    return view._built.controls["root.kc.recorder"]


def record_button(view):
    return view.node("root.kc.record")


def field(view):
    return view._built.nodes["root.kc.field.box.body.input"]


def keys(view, name, n=3, **mods):
    """A key press, heard by the record button (it holds the focus first)."""
    button = record_button(view)
    if not button.get("focused"):
        button.focus()
    view.window.simulate("key_down", key=name, **mods)
    settle(view, n)


def start(view):
    """Starts a recording with a press of the pointer on the button."""
    view.window.simulate("pointer_down", node=record_button(view))
    view.window.simulate("pointer_up", node=record_button(view))
    settle(view, 4)
    assert ctl(view).recording.get()


def type_in_field(view, text, commit="Enter"):
    box = field(view)
    box.focus()
    box.set(text=text[:-1])
    if text:
        view.window.simulate("key_down", key="end")
        view.window.simulate("input", text=text[-1])
    settle(view, 3)
    if commit == "Enter":
        view.window.simulate("key_down", key="Enter")
    else:  # leaving it
        record_button(view).focus()
    settle(view, 4)


def test_the_field_and_the_recorder_are_shipped_and_declared():
    assert "KeyChordField" in set(shipped_views())
    declared = lookup("ChordRecorder")
    assert declared is not None and declared.properties["value"].model and declared.properties["recording"].model and declared.properties["draft"].model


def test_it_shows_the_chord_in_the_field_and_is_ready_not_recording(tmp_path):
    view, vm = opened(tmp_path)
    assert view.handle.viewmodel is vm
    assert field(view).get("text") == "Ctrl+Shift+F1" and ctl(view).value.get() == "Ctrl+Shift+F1"
    assert ctl(view).recording.get() is False and ctl(view).invalid.get() is False
    assert view.node("root.kc.record.record_text").get("text") == "Record"


def test_a_value_set_by_the_app_is_shown_as_it_is_and_not_rewritten(tmp_path):
    view, vm = opened(tmp_path, chord="ctrl+shift+f1")
    assert field(view).get("text") == "ctrl+shift+f1" and vm.chord.get() == "ctrl+shift+f1" and vm.log == []
    assert ctl(view).invalid.get() is False


def test_a_value_that_is_not_a_chord_is_shown_in_the_error_colours_and_kept(tmp_path):
    view, vm = opened(tmp_path, chord="Ctrl+Shift")
    assert ctl(view).invalid.get() is True and "not a key chord" in ctl(view).message.get()
    assert vm.chord.get() == "Ctrl+Shift" and field(view).get("text") == "Ctrl+Shift" and vm.log == []
    notes = [k for k in view._built.nodes if k.startswith("root.kc.field.") and k.endswith(".supporting")]
    assert len(notes) == 1 and "not a key chord" in view._built.nodes[notes[0]].get("text")
    vm.chord.set("Ctrl+A")
    settle(view, 6)
    assert ctl(view).invalid.get() is False and not [k for k in view._built.nodes if k.startswith("root.kc.field.") and k.endswith(".supporting")]


def test_an_empty_value_is_no_shortcut_and_not_an_error(tmp_path):
    view, vm = opened(tmp_path, chord="")
    assert ctl(view).invalid.get() is False and field(view).get("text") == ""


def test_pressing_the_button_starts_a_recording_and_the_button_says_so(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    assert record_button(view).get("focused")
    assert view.node("root.kc.record.record_text").get("text") == "Press keys"
    assert record_button(view).get("label") == "Recording Shortcut: press the keys, Escape cancels, Backspace clears" and record_button(view).get("pressed") is True
    assert record_button(view).get("fill") == (view._scheme or tokens.BASELINE)["primary_container"]
    assert vm.chord.get() == "Ctrl+Shift+F1"  # nothing is written until a key is pressed


def test_a_key_press_while_recording_is_the_chord_with_the_modifiers_in_order(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    keys(view, "F5", ctrl=True, shift=True)
    assert vm.chord.get() == "Ctrl+Shift+F5" and vm.log == ["Ctrl+Shift+F5"] and ctl(view).recording.get() is False
    assert field(view).get("text") == "Ctrl+Shift+F5" and view.node("root.kc.record.record_text").get("text") == "Record"
    start(view)
    keys(view, "a", meta=True, shift=True, alt=True, ctrl=True)
    assert vm.chord.get() == "Ctrl+Alt+Shift+Meta+A"
    start(view)
    keys(view, "arrow_left", alt=True)
    start(view)
    keys(view, "page_down")
    start(view)
    keys(view, "A", shift=True)
    assert vm.log == ["Ctrl+Shift+F5", "Ctrl+Alt+Shift+Meta+A", "Alt+Left", "PageDown", "Shift+A"]


def test_a_bare_modifier_does_not_finish_the_chord_and_shows_what_is_held(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    keys(view, "control_left", ctrl=True)
    assert ctl(view).recording.get() is True and ctl(view).preview.get() == "Ctrl+"
    assert view.node("root.kc.record.record_text").get("text") == "Press keys Ctrl+"
    keys(view, "shift", shift=True, ctrl=True)
    assert ctl(view).preview.get() == "Ctrl+Shift+" and ctl(view).recording.get() is True
    keys(view, "meta", ctrl=True, shift=True)  # a press whose own flag is not set yet still counts as the key it is
    assert ctl(view).preview.get() == "Ctrl+Shift+Meta+"
    keys(view, "caps_lock")
    assert ctl(view).recording.get() is True and vm.chord.get() == "Ctrl+Shift+F1" and vm.log == []
    keys(view, "t", ctrl=True, shift=True, meta=True)
    assert vm.chord.get() == "Ctrl+Shift+Meta+T" and ctl(view).preview.get() == ""


def test_escape_cancels_and_leaves_the_chord(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    keys(view, "escape")
    assert ctl(view).recording.get() is False and vm.chord.get() == "Ctrl+Shift+F1" and vm.log == []
    assert field(view).get("text") == "Ctrl+Shift+F1"


def test_backspace_clears_the_chord_and_tells_on_change(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    keys(view, "backspace")
    assert vm.chord.get() == "" and vm.log == [""] and ctl(view).recording.get() is False and field(view).get("text") == ""


def test_escape_and_backspace_with_a_modifier_are_chords(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    keys(view, "escape", ctrl=True)
    assert vm.chord.get() == "Ctrl+Escape"
    start(view)
    keys(view, "backspace", shift=True)
    assert vm.chord.get() == "Shift+Backspace"


def test_enter_and_space_start_a_recording_and_while_recording_are_chords(tmp_path):
    view, vm = opened(tmp_path)
    keys(view, "enter")
    assert ctl(view).recording.get() is True and vm.log == []
    keys(view, "enter")
    assert vm.chord.get() == "Enter" and ctl(view).recording.get() is False
    keys(view, " ")
    assert ctl(view).recording.get() is True
    keys(view, " ", ctrl=True)
    assert vm.chord.get() == "Ctrl+Space" and ctl(view).recording.get() is False


def test_a_key_is_ignored_when_not_recording(tmp_path):
    view, vm = opened(tmp_path)
    keys(view, "a", ctrl=True)
    keys(view, "F5")
    keys(view, "backspace")
    keys(view, "escape")
    assert vm.chord.get() == "Ctrl+Shift+F1" and vm.log == [] and ctl(view).recording.get() is False
    keys(view, "enter", ctrl=True)  # Enter with a modifier does not start one
    assert ctl(view).recording.get() is False


def test_a_key_no_chord_can_have_says_so_and_the_recording_goes_on(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    keys(view, "print_screen")
    assert ctl(view).recording.get() is True and "print_screen" in ctl(view).message.get() and vm.log == []
    keys(view, "F2")
    assert vm.chord.get() == "F2" and ctl(view).message.get() == ""


def test_leaving_the_button_ends_the_recording(tmp_path):
    view, vm = opened(tmp_path)
    start(view)
    field(view).focus()
    settle(view, 4)
    assert ctl(view).recording.get() is False and vm.chord.get() == "Ctrl+Shift+F1" and vm.log == []


def test_the_app_can_start_and_stop_a_recording_through_recording(tmp_path):
    view, vm = opened(tmp_path, call='{widget: KeyChordField, name: kc, value: "{{ chord }}", recording: "{{ rec }}", on_change: changed%s}')
    vm.rec.set(True)
    settle(view, 6)
    assert ctl(view).recording.get() is True and view.node("root.kc.record.record_text").get("text") == "Press keys"
    keys(view, "F9")
    assert vm.chord.get() == "F9" and vm.rec.get() is False  # a finished recording writes false back
    vm.rec.set(True)
    settle(view, 6)
    vm.rec.set(False)
    settle(view, 6)
    assert ctl(view).recording.get() is False


@pytest.mark.parametrize("commit", ["Enter", "leave"])
def test_a_typed_chord_is_read_in_any_case_and_written_in_the_canonical_form(tmp_path, commit):
    view, vm = opened(tmp_path)
    type_in_field(view, "  control + return ", commit)
    assert vm.chord.get() == "Ctrl+Enter" and vm.log == ["Ctrl+Enter"] and field(view).get("text") == "Ctrl+Enter"
    assert ctl(view).invalid.get() is False


def test_typing_does_not_write_the_value_until_it_is_committed(tmp_path):
    view, vm = opened(tmp_path)
    box = field(view)
    box.focus()
    box.set(text="ctrl+al")
    settle(view, 4)
    assert vm.chord.get() == "Ctrl+Shift+F1" and vm.log == [] and ctl(view).invalid.get() is False


def test_a_typed_text_that_is_not_a_chord_is_refused_in_the_error_colours_and_the_value_stays(tmp_path):
    view, vm = opened(tmp_path)
    type_in_field(view, "ctrl+shift")
    assert vm.chord.get() == "Ctrl+Shift+F1" and vm.log == [] and ctl(view).invalid.get() is True
    assert "Ctrl+Shift+F1" in ctl(view).message.get() and field(view).get("text") == "ctrl+shift"  # what was typed stays, to be mended
    type_in_field(view, "ctrl+shift+f2")
    assert vm.chord.get() == "Ctrl+Shift+F2" and ctl(view).invalid.get() is False and ctl(view).message.get() == ""


def test_a_typed_empty_text_clears_the_chord_and_a_typed_same_chord_changes_nothing(tmp_path):
    view, vm = opened(tmp_path)
    type_in_field(view, "Ctrl+Shift+F1")
    assert vm.log == []
    type_in_field(view, "   ")
    assert vm.chord.get() == "" and vm.log == [""]
    type_in_field(view, "")
    assert vm.log == [""]  # clearing what is clear is no change


def test_a_typed_chord_that_only_differs_in_form_is_rewritten_once(tmp_path):
    view, vm = opened(tmp_path, chord="ctrl+shift+f1")
    type_in_field(view, "ctrl+shift+f1")  # the person committed it: now it is canonical
    assert vm.chord.get() == "Ctrl+Shift+F1" and vm.log == ["Ctrl+Shift+F1"]


def test_disabled_it_records_and_reads_nothing(tmp_path):
    view, vm = opened(tmp_path, options=", disabled: true")
    assert ctl(view).disabled.get()
    view.window.simulate("pointer_down", node=record_button(view))
    view.window.simulate("pointer_up", node=record_button(view))
    settle(view, 4)
    keys(view, "enter")
    keys(view, "F5")
    type_in_field(view, "ctrl+a")
    assert vm.chord.get() == "Ctrl+Shift+F1" and vm.log == [] and ctl(view).recording.get() is False


def test_the_names_a_screen_reader_hears_and_the_tab_order(tmp_path):
    view, vm = opened(tmp_path, options=", label: Reveal key")
    assert view.node("root.kc").get("role") == "group" and view.node("root.kc").get("label") == "Reveal key"
    assert record_button(view).get("role") == "button" and record_button(view).get("label") == "Record Reveal key" and record_button(view).get("pressed") is False
    assert view._built.nodes["root.kc.field.box.body.input"].get("label") == "Reveal key"
    assert field(view).get("focusable") and record_button(view).get("focusable")
    start(view)
    assert record_button(view).get("pressed") is True


def test_an_unknown_property_of_the_field_is_named(tmp_path):
    with pytest.raises(LoadError, match="colour"):
        opened(tmp_path, call="{widget: KeyChordField, name: kc, colour: red%s}")
