"""#298: the colour picker as a view -- inline and in a popup, bound to a ViewModel's text, every part in step with the others."""

import pytest

from tess_ui import App, Signal, ViewModel, colour, tokens
from tess_ui.follow import app_of
from tess_ui.shipped import shipped_views
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.widgets import lookup


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.c = Signal("#3366cc")
        self.pop = Signal(False)
        self.log = []

    def changed(self):
        self.log.append(self.c.get())


def opened(tmp_path, call="{widget: ColourPicker, name: cp, value: \"{{ c }}\", on_change: changed}", extra="", dark=False, size=(400, 640)):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.yaml").write_text(f"""tesserae: 0.6
name: main
widget: Container
style: {{flex_direction: horizontal, gap: 16, padding: 16, width: {size[0]}, height: {size[1]}}}
children:
  - {call}
  - {{widget: Rect, name: elsewhere, style: {{width: 80, height: 80, background: surface_variant}}}}
{extra}""")
    app = App(root=tmp_path, width=size[0], height=size[1], theme_seed=(0x67, 0x50, 0xA4, 0xFF), dark=dark)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 4)
    return view, app.bindings.viewmodel_for("main")


def settle(view, n=6):
    for _ in range(n):
        view.window.advance(16)


def control(view, name, prefix="root.cp.panel"):
    return view._built.controls[f"{prefix}.{name}"]


def local(node, x, y):
    return {"x": node.get("layout_x") + x, "y": node.get("layout_y") + y}


def drag(view, ctl, points):
    node = ctl.node
    view.window.simulate("pointer_down", node, x=points[0][0], y=points[0][1])
    for x, y in points[1:]:
        view.window.simulate("pointer_move", **local(node, x, y))
    view.window.simulate("pointer_up", **local(node, *points[-1]))
    settle(view, 2)


def typed(view, field, text):
    field.input.focus()
    field.input.set(text=text[:-1])
    view.window.simulate("key_down", key="end")
    view.window.simulate("input", text=text[-1])
    settle(view, 2)


def test_the_picker_and_its_parts_are_shipped_and_declared():
    assert {"ColourPicker", "ColourPickerPanel"} <= set(shipped_views())
    for name in ("ColourArea", "ColourStrip", "ColourField", "ColourSwatches"):
        assert lookup(name) is not None, name
    assert lookup("ColourArea").properties["value"].model and lookup("ColourStrip").properties["hue"].model


def test_inline_it_shows_every_part_at_the_value_and_the_view_matches_its_viewmodel(tmp_path):
    view, vm = opened(tmp_path)
    for name in ("square", "hue_strip", "alpha_strip", "hex", "channels.red", "channels.green", "channels.blue", "channels.alpha", "swatches"):
        assert control(view, name).value.get() == "#3366cc", name
    assert control(view, "hex").input.get("text") == "#3366cc"
    assert [control(view, f"channels.{c}").input.get("text") for c in ("red", "green", "blue", "alpha")] == ["51", "102", "204", "255"]
    assert control(view, "hue_strip").hue.get() == pytest.approx(220.0)
    assert not view._shown_layers and "root.cp.trigger" not in view._built.nodes


def test_dragging_the_square_writes_text_to_the_viewmodel_and_every_part_follows(tmp_path):
    view, vm = opened(tmp_path)
    square = control(view, "square")
    drag(view, square, [(128, 44), (200, 100)])
    expected = vm.c.get()
    assert colour.is_valid(expected) and expected != "#3366cc"
    assert all(control(view, n).value.get() == expected for n in ("square", "hue_strip", "alpha_strip", "hex", "channels.red", "swatches"))
    assert control(view, "hex").input.get("text") == expected
    s, v = colour.hsva(expected)[1:3]
    assert (s, v) == pytest.approx((200 / 256, 1 - 100 / 176), abs=0.01)
    assert colour.hsva(expected, control(view, "hue_strip").hue.get())[0] == pytest.approx(220.0, abs=0.01)


def test_a_value_set_in_code_reads_back_the_same_for_any_colour_and_capitals_come_back_lowercase(tmp_path):
    view, vm = opened(tmp_path)
    for text in ("#000000", "#ffffff", "#ff0000", "#00ff00", "#0000ff", "#12345678", "#ffffff00", "#7f7f7f", "#abcdef", "#fedcba99"):
        vm.c.set(text)
        settle(view, 3)
        assert vm.c.get() == text
        assert control(view, "square").value.get() == text and control(view, "hex").input.get("text") == text, text
    vm.c.set("#ABCDEF")
    settle(view, 3)
    assert control(view, "hex").value.get() == "#abcdef" and vm.c.get() == "#ABCDEF"  # the app's own text is left as it wrote it


def test_a_drag_does_not_drift_and_keeps_the_hue_through_black_and_white(tmp_path):
    view, vm = opened(tmp_path)
    square, strip = control(view, "square"), control(view, "hue_strip")
    drag(view, strip, [(10 + 236 * 160 / 360, 12)])
    hue = strip.hue.get()
    assert hue == pytest.approx(160.0, abs=0.5)
    drag(view, square, [(128, 40)])
    drag(view, square, [(100, 100), (0, 176), (100, 100), (255, 1), (1, 1), (128, 40)])  # through black and white, and home
    assert strip.hue.get() == pytest.approx(hue, abs=1e-9)
    drag(view, square, [(255, 1), (256, 0)])
    assert vm.c.get() == colour.from_hsva(hue, 1, 1)
    drag(view, square, [(128, 40)] * 40)  # forty events at one place: the same text each time
    first = vm.c.get()
    drag(view, square, [(128, 40)] * 40)
    assert vm.c.get() == first


def test_the_hue_a_picker_opens_with_survives_a_trip_through_black(tmp_path):
    """Nothing has written the shared hue yet: the picker has only the text, whose hue is 220, and the square has to hand it on before the text loses it."""
    view, vm = opened(tmp_path)
    square, strip = control(view, "square"), control(view, "hue_strip")
    drag(view, square, [(128, 40), (0, 176)])  # to black, which has no hue
    assert vm.c.get() == "#000000"
    assert colour.hsva(vm.c.get(), strip.hue.get())[0] == pytest.approx(220.0, abs=0.01)
    drag(view, square, [(1, 174), (255, 1), (256, 0)])  # and out to the corner of the full colour
    assert vm.c.get() == colour.from_hsva(colour.hsva("#3366cc")[0], 1, 1)


def test_the_hue_strip_changes_the_text_and_keeps_saturation_and_value_exactly(tmp_path):
    view, vm = opened(tmp_path)
    s0, v0 = colour.hsva(vm.c.get())[1:3]
    drag(view, control(view, "hue_strip"), [(10, 12), (60, 12), (120, 12), (200, 12), (240, 12)])
    s, v = colour.hsva(vm.c.get())[1:3]
    assert (s, v) == (s0, v0)
    assert vm.c.get() != "#3366cc"


def test_the_alpha_strip_and_the_alpha_field_agree(tmp_path):
    view, vm = opened(tmp_path)
    drag(view, control(view, "alpha_strip"), [(10 + 118, 12)])
    assert len(vm.c.get()) == 9 and vm.c.get().startswith("#3366cc")
    alpha_field = control(view, "channels.alpha")
    assert alpha_field.input.get("text") == str(int(vm.c.get()[7:], 16))
    typed(view, alpha_field, "255")
    assert vm.c.get() == "#3366cc"  # full alpha: six digits


def test_a_valid_hex_typed_in_the_field_sets_the_value_and_moves_the_others(tmp_path):
    view, vm = opened(tmp_path)
    typed(view, control(view, "hex"), "#ff8800")
    assert vm.c.get() == "#ff8800"
    assert control(view, "square").value.get() == "#ff8800"
    assert [control(view, f"channels.{c}").input.get("text") for c in ("red", "green", "blue", "alpha")] == ["255", "136", "0", "255"]
    assert control(view, "hue_strip").hue.get() == pytest.approx(colour.hsva("#ff8800")[0], abs=0.5)
    typed(view, control(view, "hex"), "#ff880080")
    assert vm.c.get() == "#ff880080" and control(view, "channels.alpha").input.get("text") == "128"


def test_an_invalid_hex_typed_in_the_field_leaves_the_value_and_marks_the_field(tmp_path):
    view, vm = opened(tmp_path)
    field = control(view, "hex")
    typed(view, field, "#33")
    typed(view, field, "#3366zz")
    assert vm.c.get() == "#3366cc" and vm.log == []
    assert field.error.get() is True and field.input.get("invalid") is True
    typed(view, field, "#3366cd")
    assert vm.c.get() == "#3366cd" and field.error.get() is False


def test_the_number_fields_edit_one_channel_each(tmp_path):
    view, vm = opened(tmp_path)
    typed(view, control(view, "channels.red"), "255")
    assert vm.c.get() == "#ff66cc"
    typed(view, control(view, "channels.green"), "0")
    typed(view, control(view, "channels.blue"), "17")
    assert vm.c.get() == "#ff0011"
    typed(view, control(view, "channels.alpha"), "0")
    assert vm.c.get() == "#ff001100"
    typed(view, control(view, "channels.alpha"), "300")
    assert vm.c.get() == "#ff001100" and control(view, "channels.alpha").error.get() is True


def test_a_theme_swatch_sets_the_value_to_the_roles_colour(tmp_path):
    view, vm = opened(tmp_path)
    swatches = control(view, "swatches")
    theme = app_of(view.window).theme
    for index, role in enumerate(("primary", "secondary", "tertiary", "error", "surface")):
        view.window.simulate("click", node=swatches.swatches[index])
        settle(view, 3)
        assert vm.c.get() == colour.format_hex(*tokens.theme_color(theme, role)[:3]), role
        assert control(view, "hex").input.get("text") == vm.c.get()
    assert vm.log[-1] == vm.c.get()


def test_the_swatches_follow_the_theme_and_a_caller_can_name_other_roles(tmp_path):
    view, _ = opened(tmp_path, dark=False)
    dark, _ = opened(tmp_path / "dark", dark=True)
    assert control(view, "swatches").swatches[0].get("fill") != control(dark, "swatches").swatches[0].get("fill")
    view, vm = opened(tmp_path / "roles", call="{widget: ColourPicker, name: cp, value: \"{{ c }}\", roles: [primary, scrim, outline]}")
    swatches = control(view, "swatches")
    assert swatches.roles == ["primary", "scrim", "outline"] and len(swatches.swatches) == 3
    view.window.simulate("click", node=swatches.swatches[1])
    settle(view, 3)
    assert vm.c.get() == "#000000"


def test_on_change_is_called_after_every_change_the_user_makes_and_not_for_the_apps(tmp_path):
    view, vm = opened(tmp_path)
    vm.c.set("#112233")
    settle(view, 3)
    assert vm.log == []
    square = control(view, "square")
    square.node.focus()
    view.window.simulate("key_down", key="arrow_right")
    view.window.simulate("key_down", key="arrow_up")
    assert len(vm.log) == 2 and vm.log[-1] == vm.c.get()
    typed(view, control(view, "hex"), "#445566")
    assert vm.log[-1] == "#445566" and len(vm.log) == 3
    drag(view, square, [(10, 10), (20, 20), (30, 30)])
    assert len(vm.log) >= 6 and all(colour.is_valid(c) for c in vm.log)  # while a drag goes on, not only at its end


def test_tab_goes_square_hue_alpha_the_fields_and_then_the_swatches(tmp_path):
    view, _ = opened(tmp_path)
    parts = [control(view, n) for n in ("square", "hue_strip", "alpha_strip", "hex", "channels.red", "channels.green", "channels.blue", "channels.alpha")]
    targets = [getattr(p, "input", None) or p.node for p in parts] + list(control(view, "swatches").swatches)
    targets[0].focus()
    settle(view, 2)
    seen = []
    for _ in range(len(targets)):
        seen.append([t.get("focused") for t in targets].index(True))
        view.window.simulate("key_down", key="tab")
        settle(view, 1)
    assert seen == list(range(len(targets)))


def test_screen_reader_roles_labels_and_values(tmp_path):
    view, _ = opened(tmp_path)
    square, hue, alpha = (control(view, n) for n in ("square", "hue_strip", "alpha_strip"))
    assert view._built.nodes["root.cp.panel"].get("role") == "group" and view._built.nodes["root.cp.panel"].get("label") == "Colour"
    assert (square.node.get("role"), square.node.get("label")) == ("slider", "Saturation and value")
    assert square.node.get("value_text").startswith("saturation 75 percent, value 80 percent")
    assert (hue.node.get("label"), hue.node.get("value_text")) == ("Hue", "220 degrees")
    assert (alpha.node.get("label"), alpha.node.get("value_text")) == ("Alpha", "100 percent")
    labels = [control(view, n).input.get("label") for n in ("hex", "channels.red", "channels.green", "channels.blue", "channels.alpha")]
    assert labels == ["Hex colour", "Red", "Green", "Blue", "Alpha"]
    assert control(view, "swatches").node.get("label") == "Theme colours"
    named, _ = opened(tmp_path / "named", call="{widget: ColourPicker, name: cp, value: \"{{ c }}\", label: Fill}")
    assert named._built.nodes["root.cp.panel"].get("label") == "Fill"


def test_disabled_it_changes_nothing_and_takes_no_focus(tmp_path):
    view, vm = opened(tmp_path, call="{widget: ColourPicker, name: cp, value: \"{{ c }}\", disabled: true}")
    drag(view, control(view, "square"), [(200, 20)])
    view.window.simulate("click", node=control(view, "swatches").swatches[3])
    assert vm.c.get() == "#3366cc"
    parts = [control(view, n) for n in ("square", "hue_strip", "alpha_strip", "hex", "channels.red")]
    assert not any((getattr(p, "input", None) or p.node).get("focusable") for p in parts)
    assert not any(s.get("focusable") for s in control(view, "swatches").swatches)


def test_a_value_that_is_not_a_colour_is_an_error_that_names_the_widget(tmp_path):
    with pytest.raises(Exception, match="#rrggbb or #rrggbbaa"):
        view, vm = opened(tmp_path)
        vm.c.set("#12")
        settle(view, 3)


# -- the popup --------------------------------------------------------------------------------------------------------------------------

POPUP = "{widget: ColourPicker, name: cp, popup: true, open: \"{{ pop }}\", value: \"{{ c }}\", on_change: changed}"


def press(view, node):
    view.window.simulate("pointer_down", node=node)
    view.window.simulate("pointer_up", node=node)
    settle(view, 4)


def test_a_popup_is_a_swatch_of_the_colour_until_it_is_opened(tmp_path):
    view, vm = opened(tmp_path, call=POPUP)
    trigger = view.node("root.cp.trigger")
    assert (trigger.get("layout_width"), trigger.get("layout_height")) == (40.0, 40.0)
    assert trigger.get("fill") == tokens.resolve_color("#3366cc", {}) and trigger.get("corner_radius") == 8.0
    assert trigger.get("role") == "button" and trigger.get("label") == "Colour" and trigger.get("expanded") is False
    assert not view._shown_layers and vm.pop.get() is False
    vm.c.set("#ff000080")
    settle(view, 3)
    assert view.node("root.cp.trigger").get("fill") == (255, 0, 0, 128)


def test_pressing_the_swatch_opens_the_picker_in_a_layer_and_it_is_the_same_picker(tmp_path):
    view, vm = opened(tmp_path, call=POPUP)
    press(view, view.node("root.cp.trigger"))
    assert vm.pop.get() is True and view._shown_layers
    assert view.node("root.cp.trigger").get("expanded") is True
    square = control(view, "square", "root.cp.layer.surface.popup_panel")
    assert square.value.get() == "#3366cc"
    surface = view.node("root.cp.layer.surface")
    assert surface.get("corner_radius") == 12.0 and surface.get("fill") == (view._scheme or tokens.BASELINE)["surface_container"]
    drag(view, square, [(128, 44)])
    assert vm.c.get() == colour.from_hsva(220, 0.5, 0.75) and vm.log
    assert view.node("root.cp.trigger").get("fill") == tokens.resolve_color(vm.c.get(), {})  # the swatch shows it


def test_escape_closes_the_popup_and_writes_false_back(tmp_path):
    view, vm = opened(tmp_path, call=POPUP)
    press(view, view.node("root.cp.trigger"))
    assert vm.pop.get() is True
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers
    press(view, view.node("root.cp.trigger"))  # and it opens again
    assert vm.pop.get() is True and view._shown_layers


def test_a_press_outside_closes_the_popup(tmp_path):
    view, vm = opened(tmp_path, call=POPUP)
    press(view, view.node("root.cp.trigger"))
    assert vm.pop.get() is True
    view.window.simulate("pointer_down", x=370, y=620)
    view.window.simulate("pointer_up", x=370, y=620)
    settle(view, 6)
    assert vm.pop.get() is False and not view._shown_layers


def test_pressing_the_swatch_again_closes_the_popup(tmp_path):
    view, vm = opened(tmp_path, call=POPUP)
    press(view, view.node("root.cp.trigger"))
    press(view, view.node("root.cp.trigger"))
    assert vm.pop.get() is False and not view._shown_layers


def test_a_disabled_popup_does_not_open(tmp_path):
    view, vm = opened(tmp_path, call=POPUP.replace("popup: true", "popup: true, disabled: true"))
    press(view, view.node("root.cp.trigger"))
    assert vm.pop.get() is False and not view._shown_layers
    assert view.node("root.cp.trigger").get("opacity") == pytest.approx(0.38) or view.node("root.cp.trigger").get("disabled")


def test_a_popup_can_be_opened_from_the_viewmodel(tmp_path):
    view, vm = opened(tmp_path, call=POPUP)
    vm.pop.set(True)
    settle(view, 6)
    assert view._shown_layers
    vm.pop.set(False)
    settle(view, 6)
    assert not view._shown_layers


def test_the_unknown_property_of_a_picker_is_named(tmp_path):
    with pytest.raises(LoadError, match="colour"):
        opened(tmp_path, call="{widget: ColourPicker, name: cp, colour: red}")
