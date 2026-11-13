"""A text input whose `text` is two-way keeps its caret while the person types in the middle of the text.

The engine moves the caret to the end of the text when a node is given the text it already shows, and the view re-applied the typed text after each edit (the Signal changed, so the
composition changed, so `patch` set the text again). Typed after `Home`, a second character then landed at the end. Found in the configuration application (its Backspace "did not reach" the
Signal: it deleted at the end instead of at the caret).
"""

from tess_ui import Signal, ViewModel
from tess_ui.composed import open_composed
from tess_ui.spec.nodes import parse_view
from tess_ui.viewmodel import Bindings

SEED = (103, 80, 164, 255)
VIEW = """name: demo
widget: Container
style: {flex_direction: vertical, width: 300, height: 300}
children:
  - widget: TextInput
    name: f
    text: "{{ text }}"
    multiline: true
    typography_role: body_large
    style: {width: 200, height: 100, background: '#FFFFFF', foreground: '#000000'}
"""


class DemoVM(ViewModel):
    views = "demo"

    def __init__(self):
        super().__init__()
        self.text = Signal("hello world")


def rig():
    bindings = Bindings()
    bindings.bind(DemoVM)
    view = open_composed(parse_view(VIEW, "Demo_View.yaml"), bindings, None, theme_seed=SEED)
    view.window.advance(16)
    field = view.node("root.f")
    field.focus()
    view.window.simulate("key_down", key="home")
    return view, view.handle.viewmodel, field


def test_characters_typed_at_the_start_stay_in_order_and_the_caret_follows_them():
    view, vm, field = rig()
    for character in "ABC":
        view.window.simulate("input", text=character)
        view.window.advance(16)
    assert vm.text.get() == "ABChello world" and field.get("selection") == (3, 3)


def test_backspace_deletes_at_the_caret_not_at_the_end():
    view, vm, field = rig()
    view.window.simulate("input", text="X")
    view.window.simulate("input", text="Y")
    view.window.simulate("key_down", key="backspace")
    view.window.advance(16)
    assert vm.text.get() == "Xhello world" and field.get("selection") == (1, 1)


def test_a_text_the_app_sets_still_reaches_the_input_and_puts_the_caret_at_the_end():
    view, vm, field = rig()
    vm.text.set("another text")
    view.window.advance(16)
    assert field.get("text") == "another text"
