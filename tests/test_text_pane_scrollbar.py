"""The multi-line text field's scrollbar (Text Field, Multi-line: vertical overflow shows a vertical scrollbar), the engine's `scrollbar_*` on a
multiline `text_input` (tre 0.6.13): the spec's thumb look, shown when the content exceeds the box."""

from tess_ui import App

TDL = "---\nTDL: 0.2\nName: main\n---\n"


def opened(tmp_path, lines, multiline=True):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    text = "\\n".join(str(i) for i in range(lines))
    flag = ", Multiline: true" if multiline else ""
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        TDL + f'Container {{ Name: main, Style {{ Width: 300, Height: 200 }}, Children {{ TextField {{ Name: f, Label: Notes, Text: "{text}"{flag}, '
        'Style { Width: 240, Height: 120 } } } }\n')
    app = App(root=tmp_path, width=300, height=200)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(8):
        view.window.advance(16)
    return view


def field(view):
    return next(node for node in view._built.nodes.values() if node.get("kind") == "text_input")


def test_a_multiline_field_has_the_specs_scrollbar_shown_on_overflow(tmp_path):
    node = field(opened(tmp_path, 40))
    assert node.get("scrollbar_show") == "overflow"
    assert (node.get("scrollbar_width"), node.get("scrollbar_radius"), node.get("scrollbar_hit_width"), node.get("scrollbar_min_length")) == (8.0, 4.0, 12.0, 32.0)
    assert node.get("scrollbar_opacity") == 0.7 and node.get("scrollbar_fill") is not None


def test_a_single_line_field_has_no_scrollbar(tmp_path):
    node = field(opened(tmp_path, 1, multiline=False))
    assert node.get("scrollbar_show") in (None, "never") and node.get("multiline") is False


def test_the_thumb_is_drawn_at_the_right_edge_when_the_content_exceeds_the_box_and_not_when_it_fits(tmp_path):
    def right_edge_ink(view):
        node = field(view)
        rgba, width, _ = view.window.snapshot()
        x = int(node.get("layout_x") + node.get("layout_width") - 6)
        rows = range(int(node.get("layout_y")) + 4, int(node.get("layout_y") + node.get("layout_height")) - 4)
        base = tuple(rgba[(rows[0] * width + x) * 4:][:3])
        return sum(1 for y in rows if tuple(rgba[(y * width + x) * 4:][:3]) != base)

    long_field = opened(tmp_path / "long", 40)
    short_field = opened(tmp_path / "short", 2)
    assert right_edge_ink(long_field) > 20  # a thumb at least 32 dp long down the right edge
    assert right_edge_ink(short_field) == 0
