"""#179 to #183: the Material 3 chips -- assist, filter, input and suggestion; icons and avatars, selection, removal."""

import pytest

from tess_ui import App, Signal, ViewModel, tokens
from tess_ui.shipped import shipped_views


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.on = Signal(False)
        self.gone = Signal(False)
        self.clicks = Signal(0)

    def bump(self):
        self.clicks.set(self.clicks.get() + 1)


def opened(tmp_path, props="Variant: assist", label="Share"):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(f"""---
TDL: 0.2
Name: main
---
Container {{
  Name: main
  Style {{ Flex_Direction: vertical, Align_Content: top_left, Width: 400, Height: 300 }}
  Children {{
    Chip {{ Name: c, Label: "{label}", {props} }}
  }}
}}
""")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    for _ in range(4):
        view.window.advance(16)
    return view, app.bindings.viewmodel_for("main")


def role(view, name):
    return (view._scheme or tokens.BASELINE)[name]


def c(view):
    return view.node("root.c")


def settle(view, n=40):
    for _ in range(n):
        view.window.advance(16)


def test_it_is_shipped():
    assert "Chip" in shipped_views()


def test_an_assist_chip_is_32_tall_with_8_pixel_corners_an_outline_and_16_pixels_of_padding(tmp_path):
    view, _ = opened(tmp_path)
    label = view.node("root.c.label")
    assert c(view).get("layout_height") == 32.0 and c(view).get("corner_radius") == 8.0
    assert c(view).get("stroke_width") == 1.0 and c(view).get("stroke_color") == role(view, "outline_variant") and c(view).get("fill")[3] == 0
    assert c(view).get("layout_width") == 16 + label.get("layout_width") + 16
    assert label.get("font_size") == 14.0 and label.get("fill") == role(view, "on_surface")


def test_an_icon_is_18_pixels_in_primary_with_8_pixels_before_it(tmp_path):
    view, _ = opened(tmp_path, "Variant: assist, Icon: home")
    icon, label = view.node("root.c.icon"), view.node("root.c.label")
    assert (icon.get("layout_width"), icon.get("fill")) == (18.0, role(view, "primary"))
    assert icon.get("layout_x") == c(view).get("layout_x") + 8 and label.get("layout_x") == icon.get("layout_x") + 18 + 8


def test_a_suggestion_chip_is_outlined_like_an_assist_one(tmp_path):
    view, _ = opened(tmp_path, "Variant: suggestion")
    assert c(view).get("stroke_width") == 1.0 and view.node("root.c.label").get("fill") == role(view, "on_surface")


def test_an_elevated_chip_is_a_raised_surface_with_no_outline(tmp_path):
    view, _ = opened(tmp_path, "Variant: assist, Elevated: true")
    assert c(view).get("fill") == role(view, "surface_container_low") and c(view).get("stroke_width") == 0.0 and c(view).get("shadows")


def test_a_press_runs_the_calls_handler(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        "---\nTDL: 0.2\nName: main\n---\nContainer {\n  Name: main\n  Style { Width: 300, Height: 100 }\n  Children {\n"
        "    Chip { Name: c, Label: Share, Handlers { On_Click: bump } }\n  }\n}\n")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 4)
    assert c(view).get("role") == "button" and c(view).get("label") == "Share" and c(view).get("focusable")
    view.window.simulate("click", node=c(view))
    assert app.bindings.viewmodel_for("main").clicks.get() == 1


def test_a_filter_chip_flips_and_turns_secondary_container_with_a_check(tmp_path):
    view, vm = opened(tmp_path, "Variant: filter, Selected: <| on |>, Icon: home")
    assert c(view).get("role") == "checkbox" and c(view).get("checked") is False
    assert c(view).get("stroke_width") == 1.0 and view.node("root.c.label").get("fill") == role(view, "on_surface_variant")
    view.window.simulate("click", node=c(view))
    settle(view)
    assert vm.on.get() is True and c(view).get("checked") is True
    assert c(view).get("fill") == role(view, "secondary_container") and c(view).get("stroke_width") == 0.0
    assert view.node("root.c.label").get("fill") == role(view, "on_secondary_container")
    assert view._built.specs["root.c.icon"]["icon"] == {"name": "check"}
    view.window.simulate("click", node=c(view))
    settle(view)
    assert vm.on.get() is False and view._built.specs["root.c.icon"]["icon"] == {"name": "home"}


def test_a_filter_chip_with_no_icon_gets_a_check_when_selected_and_none_otherwise(tmp_path):
    view, vm = opened(tmp_path, "Variant: filter, Selected: <| on |>")
    assert "root.c.icon" not in view._built.specs
    view.window.simulate("click", node=c(view))
    settle(view)
    assert "root.c.icon" in view._built.specs and c(view).get("layout_width") == 8 + 18 + 8 + view.node("root.c.label").get("layout_width") + 16


def test_an_assist_chip_does_not_toggle_when_pressed(tmp_path):
    view, _ = opened(tmp_path, "Variant: assist, Selected: false")
    view.window.simulate("click", node=c(view))
    settle(view, 10)
    assert c(view).get("fill")[3] == 0


def test_an_avatar_is_a_24_pixel_circle_of_letters_with_8_pixels_before_it(tmp_path):
    view, _ = opened(tmp_path, "Variant: input, Avatar_Text: JD")
    av = view.node("root.c.avatar")
    assert (av.get("layout_width"), av.get("layout_height")) == (24.0, 24.0) and av.get("corner_radius") >= 12
    assert av.get("fill") == role(view, "primary_container") and av.get("layout_x") == c(view).get("layout_x") + 8
    assert "root.c.icon" not in view._built.specs


def test_an_input_chip_has_a_close_button_that_reports_it(tmp_path):
    view, vm = opened(tmp_path, "Variant: input, Removable: true, Removed: <| gone |>")
    close = view.node("root.c.close")
    assert close.get("role") == "button" and close.get("label") == "Remove Share" and close.get("focusable")
    assert close.get("layout_x") + 18 + 8 == c(view).get("layout_x") + c(view).get("layout_width")
    view.window.simulate("click", node=close)
    settle(view, 6)
    assert vm.gone.get() is True


def test_pressing_the_close_does_not_press_the_chip(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        "---\nTDL: 0.2\nName: main\n---\nContainer {\n  Name: main\n  Style { Width: 300, Height: 100 }\n  Children {\n"
        "    Chip { Name: c, Label: Share, Variant: input, Removable: true, Handlers { On_Click: bump } }\n  }\n}\n")
    app = App(root=tmp_path)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view, 4)
    view.window.simulate("click", node=view.node("root.c.close"))
    settle(view, 4)
    assert app.bindings.viewmodel_for("main").clicks.get() == 0


def test_a_selected_input_chip_is_secondary_container(tmp_path):
    view, _ = opened(tmp_path, "Variant: input, Selected: true")
    assert c(view).get("fill") == role(view, "secondary_container") and c(view).get("stroke_width") == 0.0


def test_a_disabled_chip_is_dimmed_and_does_not_respond(tmp_path):
    view, vm = opened(tmp_path, "Variant: filter, Disabled: true, Selected: <| on |>")
    view.window.simulate("click", node=c(view))
    settle(view, 6)
    assert vm.on.get() is False and c(view).get("disabled") is True and c(view).get("opacity") < 0.5
