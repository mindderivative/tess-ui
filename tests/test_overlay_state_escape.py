"""A stylesheet `state:` rule on a view whose root holds an anchored `Overlay` (a shipped popup view such as `ColourPicker`): Escape closes the layer
and the focus returning to the trigger is not an error, nor does it show the layer again."""

import pytest

from tess_ui import App, Signal, ViewModel


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.c = Signal("#3366cc")
        self.pop = Signal(False)


MAIN = """tesserae: 0.6
name: main
widget: Container
style: {flex_direction: horizontal, width: 400, height: 640}
children:
  - {widget: ColourPicker, name: cp, popup: true, open: "{{ pop }}", value: "{{ c }}"}
"""


def opened(tmp_path, state):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.yaml").write_text(MAIN)
    rules = {"styles": [{"widget": "ColourPicker", "state": state, "style": {"opacity": 0.99}}]} if state else None
    app = App(root=tmp_path, width=400, height=640, stylesheet_spec=rules)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(4):
        view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


@pytest.mark.parametrize("state", [None, "hovered", "focused", "focus_visible", "pressed"])
def test_escape_closes_the_popup_and_no_signal_is_written_while_it_notifies(tmp_path, monkeypatch, state):
    from tess_ui.reactive import _Notifiable

    refused = []
    notify = _Notifiable._notify

    def watching(self, *args):
        try:
            return notify(self, *args)
        except RuntimeError as error:  # the engine logs this and swallows it, so a test has to look here
            refused.append(str(error))
            raise

    monkeypatch.setattr(_Notifiable, "_notify", watching)
    view, vm = opened(tmp_path, state)
    trigger = view.node("root.cp.trigger")
    view.window.simulate("click", node=trigger)
    for _ in range(4):
        view.window.advance(16)
    assert vm.pop.get() is True and view._shown_layers
    view.window.simulate("key_down", key="escape")
    for _ in range(8):
        view.window.advance(16)
    assert vm.pop.get() is False and not view._shown_layers
    assert refused == []
