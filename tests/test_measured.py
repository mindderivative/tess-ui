"""A Container's `measured_width` and `measured_height` tell the view how big it is laid out."""

from tess_ui import App


def opened(tmp_path, width=400):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        "---\nTDL: 0.2\nName: main\n---\nContainer {\n  Name: main\n  State { W: 0, H: 0 }\n"
        "  Style { Flex_Direction: vertical, Width: 100%, Height: 100% }\n  Children {\n"
        "    Container { Name: box, Measured_Width: <| w |>, Measured_Height: <| h |>, Style { Width: 100%, Height: 50 } }\n"
        "    Text { Name: t, Text: <| str(w) + 'x' + str(h) |>, Typography_Role: body_medium, Style { Foreground: on_surface } }\n  }\n}\n")
    app = App(root=tmp_path, width=width, height=300)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(6):
        view.window.advance(16)
    return app, view


def said(view):
    return view._built.specs["root.t"]["text"]["content"]


def test_the_size_is_written_after_layout(tmp_path):
    _, view = opened(tmp_path)
    assert said(view) == "400.0x50.0"


def test_it_is_written_again_when_the_window_resizes(tmp_path):
    app, view = opened(tmp_path)
    app.window.resize(300, 300)
    app.window.simulate("resize", width=300, height=300)
    for _ in range(6):
        view.window.advance(16)
    assert said(view) == "300.0x50.0"
