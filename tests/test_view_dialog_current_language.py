"""#268: `ViewDialog` reads its view with the older loader. A view in the current language used to fail inside it with `every widget needs an id`; it is now refused up
front with what to write instead (a modal `widget: Overlay` in a view), by path and by name."""

import pytest

from tess_ui import App
from tess_ui.overlays import ViewDialog

CURRENT = ('---\nTDL: 0.2\nName: Settings\n---\nContainer {\n  Name: Settings\n  Children {\n'
           '    Text { Name: t, Text: hi, Typography_Role: body_large, Style { Foreground: on_surface } }\n  }\n}\n')


def _app(tmp_path=None):
    return App(width=480, height=320, root=tmp_path) if tmp_path is not None else App(width=480, height=320)


def test_a_current_language_view_by_path_is_refused_and_says_what_to_do(tmp_path):
    (tmp_path / "Settings_View.tdl").write_text(CURRENT)
    app = _app()
    with pytest.raises(ValueError) as caught:
        ViewDialog(app.window, tmp_path / "Settings_View.tdl")
    text = str(caught.value)
    assert "Settings_View.tdl" in text and "widget: Overlay" in text and "surface.dismiss" in text and "current language" in text


def test_a_current_language_view_by_name_is_refused_too(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Settings_View.tdl").write_text(CURRENT)
    app = _app(tmp_path)
    with pytest.raises(ValueError, match="widget: Overlay"):
        ViewDialog(app.window, "Settings")


def test_the_replacement_the_message_names_works(tmp_path):
    """A modal `widget: Overlay` bound to `open`, closed by `surface.dismiss`, is the dialog the message points to."""
    from tess_ui import Signal, ViewModel

    class VM(ViewModel):
        views = "main"

        def __init__(self):
            super().__init__()
            self.show = Signal(True)

    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        "---\nTDL: 0.2\nName: main\n---\nContainer {\n  Name: main\n  Style { Width: 300, Height: 200, Background: surface }\n  Children {\n"
        "    Overlay {\n      Name: dlg\n      Open: <| show |>\n      Modal: true\n      Style { Width: 200, Height: 100, Background: surface_container_high }\n"
        "      Children {\n        Button { Name: close, Label: Close, Handlers { On_Click { Call { Action: \"surface.dismiss\" } } } }\n      }\n    }\n  }\n}\n")
    app = App(root=tmp_path, width=300, height=200)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(50)
    vm = app.bindings.viewmodel_for("main")
    assert vm.show.get() is True
    view.window.simulate("click", node=view.node("root.dlg.close"))
    view.window.advance(50)
    assert vm.show.get() is False
