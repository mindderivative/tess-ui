"""#298: the controls of the colour picker -- the saturation/value square, the hue and alpha strips, the hex and channel fields and the theme swatches -- drawn, dragged, typed into and read by a screen reader."""

import pytest

from tess_ui import App, Theme, colour, tokens
from tess_ui import colour_controls as cc

START = "#3366cc"


class Rig:
    """An app's window with a column the controls are added to; the window's own methods (`simulate`, `advance`, `snapshot`) are reachable on it."""

    def __init__(self, tmp_path):
        self.app = App(root=tmp_path, width=320, height=640)
        self.window = self.app.window
        self.column = self.window.create("box", flex_direction="vertical", gap=12.0, padding_left=16.0, padding_top=16.0)
        self.window.root.add_child(self.column)

    def __getattr__(self, name):
        return getattr(self.window, name)

    def add(self, control):
        self.column.add_child(control.node)
        settle(self)
        return control


@pytest.fixture
def rig(tmp_path):
    return Rig(tmp_path)


def alpha_byte(text):
    rgba = colour.parse(text)
    assert rgba is not None, text
    return rgba[3]


def settle(window, n=3):
    for _ in range(n):
        window.advance(16)


def local(node, x, y):
    """Window coordinates of the point (x, y) of `node`."""
    return {"x": node.get("layout_x") + x, "y": node.get("layout_y") + y}


def drag(window, control, points):
    """Press at the first point, move through the rest, release at the last; points are in the control's own pixels."""
    node = control.node
    window.simulate("pointer_down", node, x=points[0][0], y=points[0][1])
    for x, y in points[1:]:
        window.simulate("pointer_move", **local(node, x, y))
    window.simulate("pointer_up", **local(node, *points[-1]))
    settle(window, 1)


def pixel(window, x, y):
    rgba, width, _ = window.snapshot()
    i = (int(y) * width + int(x)) * 4
    return tuple(rgba[i:i + 4])


def key(window, control, name, **more):
    target = getattr(control, "input", None) or control.node
    target.focus()
    window.simulate("key_down", key=name, **more)
    settle(window, 1)


# -- the area ---------------------------------------------------------------------------------------------------------------------------


def test_the_area_shows_the_hue_across_the_top_and_black_along_the_bottom(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#00ff00"))
    node = area.node
    top_left, top_right, bottom = (pixel(rig, node.get("layout_x") + x, node.get("layout_y") + y) for x, y in ((6, 6), (250, 8), (128, 170)))
    assert top_left[0] > 200 and top_left[1] > 200 and top_left[2] > 200  # white
    assert top_right[1] > 200 and top_right[0] < 60 and top_right[2] < 60  # the pure hue
    assert max(bottom[:3]) < 20  # black


def test_pressing_the_area_sets_saturation_and_value_and_keeps_the_hue(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#ff0000"))
    heard = []
    area.on_input(heard.append)
    rig.simulate("pointer_down", area.node, x=128.0, y=44.0)  # half across, a quarter down
    settle(rig, 1)
    assert area.value.get() == colour.from_hsva(0, 0.5, 0.75)
    assert area.hue.get() == 0.0 and heard == [area.value.get()]
    rig.simulate("pointer_up", **local(area.node, 128, 44))


def test_dragging_follows_the_pointer_even_outside_the_square_and_clamps_at_its_edges(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#00aaff"))
    ends = []
    area.on_change(ends.append)
    drag(rig, area, [(10, 10), (400, -50), (-30, 400)])  # inside to start with: a press outside the square does not reach it
    assert area.value.get() == "#000000"  # bottom left: no saturation, no value
    assert ends == ["#000000"]  # on_change once, when the drag is let go
    drag(rig, area, [(1, 1), (256, 0)])
    assert area.value.get() == colour.from_hsva(area.hue.get(), 1, 1) == "#00aaff"


def test_a_drag_that_goes_to_a_corner_with_no_hue_and_comes_back_keeps_the_hue(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#00aaff"))
    hue = area.hue.get()
    assert hue == 200.0
    drag(rig, area, [(100, 60), (0, 176), (100, 60)])  # through black, back again
    assert area.hue.get() == 200.0
    assert colour.hsva(area.value.get(), area.hue.get())[0] == 200.0
    drag(rig, area, [(255, 1), (256, 0)])
    assert area.value.get() == "#00aaff"
    drag(rig, area, [(1, 1), (0, 0)])  # white has no hue either
    assert area.value.get() == "#ffffff" and area.hue.get() == 200.0
    drag(rig, area, [(255, 1), (256, 0)])
    assert area.value.get() == "#00aaff"


def test_a_drag_hands_on_the_hue_the_colour_has_when_the_remembered_one_is_stale(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#00aaff"))
    area.hue.set(0.0)  # a view's shared hue that nothing has written yet
    drag(rig, area, [(100, 60), (110, 70)])
    assert area.hue.get() == 200.0


def test_the_drag_keeps_alpha(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#ff000080"))
    drag(rig, area, [(128, 44)])
    assert alpha_byte(area.value.get()) == 0x80 and len(area.value.get()) == 9


def test_the_arrow_keys_move_the_point_by_a_hundredth_and_shift_by_a_tenth(rig):
    area = rig.add(cc.ColourArea(rig.window, value=colour.from_hsva(0, 0.5, 0.5)))
    heard = []
    area.on_change(heard.append)
    s0, v0 = colour.hsva(area.value.get())[1:3]
    key(rig, area, "arrow_right")
    assert colour.hsva(area.value.get(), area.hue.get())[1] == pytest.approx(s0 + 0.01, abs=0.003)
    key(rig, area, "arrow_up")
    assert colour.hsva(area.value.get(), area.hue.get())[2] == pytest.approx(v0 + 0.01, abs=0.003)
    key(rig, area, "arrow_left", shift=True)
    s1 = colour.hsva(area.value.get(), area.hue.get())[1]
    assert s1 == pytest.approx(s0 + 0.01 - 0.1, abs=0.005)
    key(rig, area, "arrow_down", shift=True)
    assert colour.hsva(area.value.get(), area.hue.get())[2] == pytest.approx(v0 + 0.01 - 0.1, abs=0.005)
    assert len(heard) == 4  # on_change after each key


def test_page_keys_move_the_value_by_a_tenth_and_home_and_end_take_the_saturation_to_its_ends(rig):
    area = rig.add(cc.ColourArea(rig.window, value=colour.from_hsva(120, 0.5, 0.5)))
    key(rig, area, "page_up")
    assert colour.hsva(area.value.get(), area.hue.get())[2] == pytest.approx(0.6, abs=0.005)
    key(rig, area, "page_down")
    key(rig, area, "page_down")
    assert colour.hsva(area.value.get(), area.hue.get())[2] == pytest.approx(0.4, abs=0.01)
    key(rig, area, "end")
    assert colour.hsva(area.value.get(), area.hue.get())[1] == 1.0
    key(rig, area, "home")
    assert colour.hsva(area.value.get(), area.hue.get())[1] == 0.0


def test_keys_cannot_leave_the_square(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#ff0000"))
    key(rig, area, "arrow_right")
    key(rig, area, "arrow_up")
    assert area.value.get() == "#ff0000"
    key(rig, area, "home")
    key(rig, area, "page_down", shift=True)
    for _ in range(12):
        key(rig, area, "page_down")
    assert area.value.get() == "#000000"


def test_the_area_tells_a_screen_reader_the_saturation_and_value_in_percent(rig):
    area = rig.add(cc.ColourArea(rig.window, value=colour.from_hsva(30, 0.4, 0.8)))
    node = area.node
    assert node.get("role") == "slider" and node.get("label") == "Saturation and value"
    assert node.get("value_text") == "saturation 40 percent, value 80 percent"
    assert (node.get("value"), node.get("value_min"), node.get("value_max")) == (40.0, 0.0, 100.0)
    area.value.set("#ffffff")
    settle(rig)
    assert node.get("value_text") == "saturation 0 percent, value 100 percent"


def test_a_screen_reader_can_increment_decrement_and_set_the_saturation(rig):
    area = rig.add(cc.ColourArea(rig.window, value=colour.from_hsva(0, 0.5, 1.0)))
    heard = []
    area.on_change(heard.append)
    rig.simulate("a11y_action", area.node, action="increment")
    assert colour.hsva(area.value.get())[1] == pytest.approx(0.51, abs=0.003)
    rig.simulate("a11y_action", area.node, action="decrement")
    rig.simulate("a11y_action", area.node, action="set_value", value="80")
    assert colour.hsva(area.value.get())[1] == pytest.approx(0.8, abs=0.003)
    assert len(heard) == 3


def test_a_disabled_area_ignores_the_pointer_and_the_keys_and_cannot_be_focused(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#336699", disabled=True))
    drag(rig, area, [(200, 20)])
    key(rig, area, "arrow_right")
    assert area.value.get() == "#336699" and not area.node.get("focusable")
    assert area.node.get("opacity") == pytest.approx(0.38)
    area.disabled.set(False)
    settle(rig)
    assert area.node.get("focusable") and area.node.get("opacity") == 1.0


def test_the_area_refuses_text_that_is_not_a_colour(rig):
    with pytest.raises(ValueError, match="#rrggbb"):
        cc.ColourArea(rig.window, value="blue")


def test_setting_the_value_in_code_moves_the_handle_and_tells_no_listener(rig):
    area = rig.add(cc.ColourArea(rig.window, value="#000000"))
    heard = []
    area.on_input(heard.append)
    area.on_change(heard.append)
    area.value.set("#ffffff")
    settle(rig)
    handle = area.handle
    assert (handle.get("x") + 10, handle.get("y") + 10) == (0.0, 0.0) and heard == []


# -- the strips -------------------------------------------------------------------------------------------------------------------------


def test_the_hue_strip_runs_through_the_rainbow(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="hue", value="#ff0000"))
    node = strip.node
    y = node.get("layout_y") + 12
    left, third, middle, end = (pixel(rig, node.get("layout_x") + x, y) for x in (3, 256 / 3, 128, 253))
    assert left[0] > 200 and left[1] < 60 and left[2] < 60  # red
    assert third[1] > 200 and third[0] < 60 and third[2] < 60  # green at a third
    assert middle[2] > 200 and middle[1] > 200 and middle[0] < 60  # cyan in the middle
    assert end[0] > 200 and end[1] < 60  # red again


def test_pressing_and_dragging_the_hue_strip_sets_the_hue_and_keeps_saturation_value_and_alpha(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="hue", value="#ff000080"))
    heard = []
    strip.on_input(heard.append)
    s, v = colour.hsva("#ff000080")[1:3]
    drag(rig, strip, [(10 + 118, 12), (10 + 236 * 2 / 3 - 3, 12)])  # a third of the way: 120 degrees, then 240
    h, s2, v2, a = colour.hsva(strip.value.get(), strip.hue.get())
    assert h == pytest.approx(240 * 0.99, abs=3) and (s2, v2) == (s, v) and a == pytest.approx(128 / 255)
    assert len(heard) >= 2 and strip.value.get().endswith("80")


def test_the_hue_strip_reaches_both_ends_and_a_pointer_past_them_stays_on_it(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="hue", value="#00ff00"))
    drag(rig, strip, [(120, 12), (-40, 12)])
    assert strip.hue.get() == 0.0 and strip.value.get() == "#ff0000"
    drag(rig, strip, [(120, 12), (500, 12)])
    assert strip.hue.get() == 360.0 and strip.value.get() == "#ff0000"
    drag(rig, strip, [(120, 12), (-40, 12)])
    assert strip.hue.get() == 0.0


def test_the_hue_strip_on_a_grey_still_moves_the_hue_the_picker_remembers(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="hue", value="#808080"))
    heard = []
    strip.on_input(heard.append)
    drag(rig, strip, [(10 + 118, 12)])
    assert strip.value.get() == "#808080"  # no colour to turn
    assert 150 < strip.hue.get() < 200  # but the strip's own number moved, and the handle with it
    assert heard == ["#808080"] * len(heard) and heard


def test_the_hue_strip_keys_step_a_degree_ten_with_shift_and_ten_for_the_page_keys(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="hue", value=colour.from_hsva(100, 1, 1)))
    strip.hue.set(100.0)
    settle(rig)
    heard = []
    strip.on_change(heard.append)
    key(rig, strip, "arrow_right")
    assert strip.hue.get() == pytest.approx(101.0)
    key(rig, strip, "arrow_left", shift=True)
    assert strip.hue.get() == pytest.approx(91.0)
    key(rig, strip, "page_up")
    assert strip.hue.get() == pytest.approx(101.0)
    key(rig, strip, "page_down")
    key(rig, strip, "arrow_down")
    assert strip.hue.get() == pytest.approx(90.0)
    key(rig, strip, "end")
    assert strip.hue.get() == 360.0
    key(rig, strip, "home")
    assert strip.hue.get() == 0.0
    assert len(heard) == 7


def test_the_alpha_strip_runs_from_clear_to_the_colour_over_a_chequerboard(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="alpha", value="#0000ff"))
    node = strip.node
    y = node.get("layout_y") + 12
    left, right = pixel(rig, node.get("layout_x") + 250, y), pixel(rig, node.get("layout_x") + 5, y)
    assert left[2] > 200 and left[0] < 60  # opaque blue at the end
    assert right[0] > 150 and right[2] > 150  # clear at the start: the chequerboard's greys and whites
    cells = {pixel(rig, node.get("layout_x") + x, y + dy)[:3] for x in (8, 14) for dy in (-3, 3)}
    assert len(cells) >= 2  # alternate squares differ


def test_the_alpha_strip_sets_alpha_in_the_text_and_full_alpha_has_no_digits(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="alpha", value="#336699"))
    drag(rig, strip, [(10 + 118, 12)])
    assert strip.value.get().startswith("#336699") and len(strip.value.get()) == 9
    assert alpha_byte(strip.value.get()) == pytest.approx(127, abs=3)
    drag(rig, strip, [(100, 12), (300, 12)])
    assert strip.value.get() == "#336699"
    drag(rig, strip, [(100, 12), (-5, 12)])
    assert strip.value.get() == "#33669900"


def test_the_alpha_strip_keys_step_a_percent_and_ten_and_go_to_the_ends(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="alpha", value="#33669980"))
    a0 = alpha_byte(strip.value.get()) / 255
    key(rig, strip, "arrow_right")
    assert alpha_byte(strip.value.get()) / 255 == pytest.approx(a0 + 0.01, abs=0.003)
    key(rig, strip, "arrow_down", shift=True)
    assert alpha_byte(strip.value.get()) / 255 == pytest.approx(a0 + 0.01 - 0.1, abs=0.004)
    key(rig, strip, "end")
    assert strip.value.get() == "#336699"
    key(rig, strip, "home")
    assert strip.value.get() == "#33669900"
    key(rig, strip, "page_up")
    assert alpha_byte(strip.value.get()) == pytest.approx(0.1 * 255, abs=2)


def test_a_strip_tells_a_screen_reader_degrees_or_percent(rig):
    hue = rig.add(cc.ColourStrip(rig.window, channel="hue", value=colour.from_hsva(200, 1, 1)))
    alpha = rig.add(cc.ColourStrip(rig.window, channel="alpha", value="#33669980"))
    assert hue.node.get("role") == "slider" and hue.node.get("label") == "Hue"
    assert (hue.node.get("value"), hue.node.get("value_min"), hue.node.get("value_max")) == (200.0, 0.0, 360.0)
    assert hue.node.get("value_text") == "200 degrees"
    assert alpha.node.get("role") == "slider" and alpha.node.get("label") == "Alpha"
    assert (alpha.node.get("value"), alpha.node.get("value_max")) == (50.0, 100.0) and alpha.node.get("value_text") == "50 percent"
    rig.simulate("a11y_action", hue.node, action="increment")
    assert hue.hue.get() == pytest.approx(201.0)
    rig.simulate("a11y_action", alpha.node, action="set_value", value="100")
    assert alpha.value.get() == "#336699"


def test_a_strip_names_its_channel_and_refuses_another(rig):
    with pytest.raises(ValueError, match="'hue' or 'alpha'"):
        cc.ColourStrip(rig.window, channel="saturation")


def test_a_disabled_strip_does_nothing(rig):
    strip = rig.add(cc.ColourStrip(rig.window, channel="hue", value="#ff0000", disabled=True))
    drag(rig, strip, [(100, 12)])
    key(rig, strip, "arrow_right")
    rig.simulate("a11y_action", strip.node, action="increment")
    assert strip.value.get() == "#ff0000" and strip.hue.get() == 0.0 and not strip.node.get("focusable")


# -- the fields -------------------------------------------------------------------------------------------------------------------------


def typed(window, field, text):
    """Types `text` into the field as the user would: all but its last character is there already, and the last one arrives as input."""
    field.input.focus()
    if text == "":
        field.input.set(text="x")
        window.simulate("key_down", key="end")
        window.simulate("key_down", key="backspace")
    else:
        field.input.set(text=text[:-1])
        window.simulate("key_down", key="end")
        window.simulate("input", text=text[-1])
    settle(window, 1)


def test_typing_a_valid_hex_sets_the_value_at_once_and_tells_the_listeners(rig):
    field = rig.add(cc.ColourField(rig.window, channel="hex", value=START))
    live, ends = [], []
    field.on_input(live.append)
    field.on_change(ends.append)
    typed(rig, field, "#ff8800")
    assert field.value.get() == "#ff8800" and live == ends == ["#ff8800"] and field.error.get() is False
    typed(rig, field, "#FF880080")
    assert field.value.get() == "#ff880080"  # read in capitals, written back in lowercase
    assert field.input.get("text") == "#FF880080"  # but what the user is typing is not rewritten under them


def test_an_invalid_hex_leaves_the_value_and_marks_the_field_in_error(rig):
    field = rig.add(cc.ColourField(rig.window, channel="hex", value=START))
    live = []
    field.on_input(live.append)
    for bad in ("#12", "#gg0000", "336699", "#3366cc00ff", "blue", ""):
        typed(rig, field, bad)
        assert field.value.get() == START and field.error.get() is True, bad
        assert field.input.get("invalid") is True
    assert live == []
    typed(rig, field, "#336699")
    assert field.error.get() is False and field.input.get("invalid") is False and field.value.get() == "#336699"


def test_the_error_shows_in_the_error_colour(rig):
    field = rig.add(cc.ColourField(rig.window, channel="hex", value=START))
    ok = field.field.get("stroke_color")
    typed(rig, field, "#zz")
    assert field.field.get("stroke_color") == field.color("error") != ok
    assert field.caption.get("fill") == field.color("error")


def test_leaving_the_field_or_escape_puts_back_the_text_of_the_value(rig):
    field = rig.add(cc.ColourField(rig.window, channel="hex", value=START))
    typed(rig, field, "#zz")
    assert field.input.get("text") == "#zz"  # kept while the user is mending it
    field.input.focus()
    rig.simulate("key_down", key="escape")
    settle(rig)
    assert field.input.get("text") == START and field.error.get() is False
    typed(rig, field, "#zz")
    rig.add(cc.ColourArea(rig.window)).node.focus()  # the focus goes elsewhere
    settle(rig)
    assert field.input.get("text") == START and field.error.get() is False


def test_a_change_made_elsewhere_shows_in_the_field(rig):
    field = rig.add(cc.ColourField(rig.window, channel="hex", value=START))
    field.value.set("#112233")
    settle(rig)
    assert field.input.get("text") == "#112233"


def test_channel_fields_show_and_set_one_byte(rig):
    red, green, blue, alpha = (rig.add(cc.ColourField(rig.window, channel=c, value="#33669980")) for c in ("red", "green", "blue", "alpha"))
    assert [f.input.get("text") for f in (red, green, blue, alpha)] == ["51", "102", "153", "128"]
    typed(rig, red, "255")
    assert red.value.get() == "#ff669980"
    typed(rig, alpha, "255")
    assert alpha.value.get() == "#336699"  # full alpha: no digits
    typed(rig, blue, "0")
    assert blue.value.get() == "#33660080"  # each field edits the value it holds (these four are not bound together)


def test_a_channel_field_takes_only_a_whole_number_from_0_to_255(rig):
    field = rig.add(cc.ColourField(rig.window, channel="green", value=START))
    for bad in ("256", "-1", "1.5", "", "abc", "1e2", "\u0661"):
        typed(rig, field, bad)
        assert field.value.get() == START and field.error.get() is True, bad
    typed(rig, field, " 7 ")
    assert field.value.get() == "#3307cc" and field.error.get() is False


def test_the_arrow_keys_step_a_channel_by_one_and_ten_with_shift_and_stop_at_the_ends(rig):
    field = rig.add(cc.ColourField(rig.window, channel="blue", value="#000000"))
    key(rig, field, "arrow_up")
    assert field.value.get() == "#000001" and field.input.get("text") == "1"
    key(rig, field, "arrow_up", shift=True)
    assert field.value.get() == "#00000b"
    key(rig, field, "arrow_down")
    key(rig, field, "arrow_down", shift=True)
    key(rig, field, "arrow_down", shift=True)
    assert field.value.get() == "#000000"
    field.value.set("#0000ff")
    key(rig, field, "arrow_up")
    assert field.value.get() == "#0000ff"


def test_a_field_names_itself_for_a_screen_reader_and_shows_a_short_caption(rig):
    fields = {c: rig.add(cc.ColourField(rig.window, channel=c, value=START)) for c in ("hex", "red", "green", "blue", "alpha")}
    assert {c: f.input.get("label") for c, f in fields.items()} == {"hex": "Hex colour", "red": "Red", "green": "Green", "blue": "Blue", "alpha": "Alpha"}
    assert {c: f.caption.get("text") for c, f in fields.items()} == {"hex": "Hex", "red": "R", "green": "G", "blue": "B", "alpha": "A"}
    assert all(f.input.get("role") == "textbox" for f in fields.values())
    named = rig.add(cc.ColourField(rig.window, channel="hex", value=START, label="Fill"))
    assert named.input.get("label") == "Fill" and named.caption.get("text") == "Fill"


def test_a_disabled_field_cannot_be_focused(rig):
    field = rig.add(cc.ColourField(rig.window, channel="hex", value=START, disabled=True))
    assert not field.input.get("focusable") and field.input.get("disabled")
    field.disabled.set(False)
    settle(rig)
    assert field.input.get("focusable")


def test_a_field_refuses_an_unknown_channel_and_a_bad_value(rig):
    with pytest.raises(ValueError, match="channel"):
        cc.ColourField(rig.window, channel="cyan")
    with pytest.raises(ValueError, match="#rrggbb"):
        cc.ColourField(rig.window, value="#12")


# -- the swatches -----------------------------------------------------------------------------------------------------------------------


def test_the_swatches_are_the_theme_roles_in_the_theme_colours(rig):
    swatches = rig.add(cc.ColourSwatches(rig))
    assert swatches.roles == list(cc.SWATCH_ROLES)
    theme = rig.app.theme
    assert [s.get("fill") for s in swatches.swatches] == [tokens.theme_color(theme, r) for r in cc.SWATCH_ROLES]
    assert [s.get("label") for s in swatches.swatches][:2] == ["Primary", "Secondary"]
    assert all(s.get("role") == "button" for s in swatches.swatches)
    assert swatches.node.get("role") == "group" and swatches.node.get("label") == "Theme colours"


def test_pressing_a_swatch_sets_the_value_to_its_role_opaque_and_tells_the_listeners(rig):
    swatches = rig.add(cc.ColourSwatches(rig.window, value="#33669980"))
    heard = []
    swatches.on_input(heard.append)
    rig.simulate("click", swatches.swatches[3])  # error
    settle(rig)
    expected = colour.format_hex(*tokens.theme_color(rig.app.theme, "error")[:3])
    assert swatches.value.get() == expected and len(expected) == 7 and heard == [expected]
    rig.simulate("click", swatches.swatches[3])
    assert heard == [expected]  # already that colour: no change


def test_the_swatch_that_is_the_value_is_drawn_selected_and_a_screen_reader_is_told(rig):
    swatches = rig.add(cc.ColourSwatches(rig.window, value="#000000"))
    assert not any(s.get("selected") for s in swatches.swatches)
    rig.simulate("click", swatches.swatches[0])
    settle(rig)
    chosen = swatches.swatches[0]
    assert chosen.get("selected") is True and chosen.get("stroke_width") == 3.0
    assert all(not s.get("selected") and s.get("stroke_width") == 1.0 for s in swatches.swatches[1:])
    swatches.value.set(swatches.role_value("tertiary"))
    settle(rig)
    assert swatches.swatches[2].get("selected") is True and chosen.get("selected") is False


def test_other_roles_can_be_asked_for_and_an_unknown_one_is_named(rig):
    swatches = rig.add(cc.ColourSwatches(rig.window, roles=["scrim", "outline"]))
    assert len(swatches.swatches) == 2
    with pytest.raises(ValueError, match="primry"):
        cc.ColourSwatches(rig.window, roles=["primry"])
    with pytest.raises(ValueError, match="at least one"):
        cc.ColourSwatches(rig.window, roles=[])


def test_left_and_right_move_between_swatches_and_stop_at_the_ends(rig):
    swatches = rig.add(cc.ColourSwatches(rig))
    swatches.swatches[0].focus()
    rig.simulate("key_down", key="arrow_right")
    assert swatches.swatches[1].get("focused") is True
    rig.simulate("key_down", key="arrow_left")
    rig.simulate("key_down", key="arrow_left")
    assert swatches.swatches[0].get("focused") is True


def test_disabled_swatches_do_not_set_the_value_or_take_the_focus(rig):
    swatches = rig.add(cc.ColourSwatches(rig.window, value="#000000", disabled=True))
    rig.simulate("click", swatches.swatches[0])
    assert swatches.value.get() == "#000000" and not swatches.swatches[0].get("focusable")


def test_the_swatches_follow_a_theme(rig):
    swatches = rig.add(cc.ColourSwatches(rig))
    light = swatches.swatches[0].get("fill")
    dark = Theme.resolve((0x67, 0x50, 0xA4, 0xFF), dark=True)
    swatches.set_theme(dark)
    assert swatches.swatches[0].get("fill") == tokens.theme_color(dark, "primary") != light
    assert swatches.role_value("primary") == colour.format_hex(*tokens.theme_color(dark, "primary")[:3])
