"""#209 phase 5: lowering instances to the builder's spec -- each widget's properties in the shape `tess_ui.spec.build` reads."""

import pytest

from tess_ui import Signal
from tess_ui.spec.compose import Composer
from tess_ui.spec.lower import lower
from tess_ui.spec.nodes import parse_data
from tess_ui.spec.tdl import load_marked_tdl


class VM:
    def __init__(self):
        self.label = Signal("hi")
        self.on = Signal(True)


def parsed(root):
    """The document of a TDL view whose root block is `root`."""
    text = f"---\nTDL: 0.2\nName: T\n---\n{root}\n"
    return parse_data(load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")


def spec(source, vm=None):
    return lower(Composer({}, vm or VM()).compose(parsed(source)).root)


def test_text_icon_image_and_svg_take_the_builders_nested_shapes():
    assert spec("Text { Text: <| label |>, Typography_Role: body_large, Wrap: none, Font_Size: 14 }") == {
        "id": "root", "kind": "Text", "text": {"content": "hi", "typography_role": "body_large", "wrap": "none", "font_size": 14.0}}
    assert spec("Link { Text: go, Font_Family: Roboto }")["text"] == {"content": "go", "font_family": "Roboto"}
    assert spec("TextInput { Text: typed, Typography_Role: body_large, Placeholder: Name, Obscured: true }")["text"] == {"content": "typed", "typography_role": "body_large", "placeholder": "Name", "obscured": True}
    assert spec("Icon { Icon: home }")["icon"] == {"name": "home"}
    assert spec("Image { Src: \"a.png\", Fit: contain }")["image"] == {"src": "a.png", "fit": "contain"}
    assert spec('Svg { Content: "<svg/>" }')["svg"] == {"content": "<svg/>"}
    assert spec("Text { }")["text"] == {"content": ""}


def test_controls_and_windows_keep_their_properties_flat():
    assert spec("Checkbox { Checked: <| on |>, Disabled: true }") == {"id": "root", "kind": "Checkbox", "checked": True, "disabled": True}
    assert spec("Slider { Value: 0.25 }")["value"] == 0.25
    node = spec("Window { Title: App, Borderless: true, Min_Width: 400, Title_Bar { Title: App, Buttons: [close] } }")
    assert node["kind"] == "Window" and node["title"] == "App" and node["borderless"] is True and node["title_bar"] == {"title": "App", "buttons": ["close"]}
    assert spec("DockPanel { Title: Files }")["title"] == "Files"


def test_the_universal_keys_are_carried_at_their_current_values():
    node = spec("Rect {\n  Style { Width: 10, Background: <| \"#112233\" if on else \"#445566\" |> }\n  Classes: [a, b]\n"
                "  A11y { Label: <| label |>, Role: button }\n  Interaction: on_primary\n  Window_Region: drag\n}")
    assert node["style"] == {"width": 10, "background": "#112233"} and node["classes"] == ["a", "b"]
    assert node["a11y"] == {"label": "hi", "role": "button"}
    assert node["interaction"] == {"color": "on_primary"} and node["window_region"] == "drag"
    assert spec("Rect { Interaction: true }")["interaction"] is True
    assert "style" not in spec("Rect { }") and "children" not in spec("Rect { }")


def test_children_are_lowered_in_order_with_their_ids():
    node = spec("Container { Children { Text { Name: a } Rect { } Icon { Icon: home, Name: c } } }")
    assert [(c["id"], c["kind"]) for c in node["children"]] == [("root.a", "Text"), ("root.children[1]", "Rect"), ("root.c", "Icon")]


def test_values_are_read_at_lowering_so_a_new_lowering_sees_the_change():
    vm = VM()
    comp = Composer({}, vm).compose(parsed("Text { Text: <| label |> }"))
    assert lower(comp.root)["text"]["content"] == "hi"
    vm.label.set("bye")
    assert lower(comp.root)["text"]["content"] == "bye"


def test_an_image_frame_is_not_lowered_it_is_followed_by_the_view():
    node = spec("Image { Frame: x }")
    assert "frame" not in node and "frame" not in node["image"]


def test_flat_properties_of_a_widget_with_a_nested_shape_are_kept():
    assert spec("TextInput { Text: x, Disabled: true }")["disabled"] is True
    assert spec("Icon { Icon: home }") == {"id": "root", "kind": "Icon", "icon": {"name": "home"}}  # a folded property is not repeated flat
