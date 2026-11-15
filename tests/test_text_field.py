"""#184: the Material 3 text field -- the `TextInput` primitive, and `TextField`, a shipped view with a shipped look, opened in a real app window.

Each test writes a small project with one view that uses `TextField`, opens it through `App.open_view`, and drives it the way a user would
(`focus`, `input`, `key_down`, pointer moves), reading the nodes the field drew.
"""

import pytest

from tess_ui import App, Signal, ViewModel, tokens
from tess_ui.shipped import shipped_rules, shipped_views
from tess_ui.spec.nodes import LoadError


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.name = Signal("")
        self.email = Signal("")
        self.msg = Signal("")
        self.log = []

    def submit(self):
        self.log.append("submit")

    def keyed(self):
        self.log.append("key")


TDL = "---\nTDL: 0.2\nName: Main\n---\n"


def opened(tmp_path, field, extra="", vm=None, app_kwargs=None):
    """An app with one view whose only child is the `field` (TDL for one node), plus any `extra` children."""
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(
        TDL + "Container {\n  Name: main\n  Style { Flex_Direction: vertical, Width: 400, Height: 400, Gap: 16, Padding: 16 }\n  Children {\n" + field + extra + "  }\n}\n")
    app = App(root=tmp_path, **(app_kwargs or {}))
    app.bind(vm or VM)
    view = app.open_view("Main")
    app.show("main")  # a view is on the window, and so can be hovered and clicked, once it is shown
    return app, view, app.bindings.viewmodel_for("main")


def part(view, base, name):
    return view.node(f"root.{base}.{name}")


def input_of(view, base="f"):
    return view.node(f"root.{base}.box.body.input")


def role(view, name):
    """The colour of a theme role as this view draws it (an app with no theme draws the baseline one)."""
    return (view._scheme or tokens.BASELINE)[name]


def test_the_field_is_a_shipped_view_with_a_shipped_look():
    assert "TextField" in shipped_views()
    assert any(rule.widget == "TextField" for sheet in shipped_rules() for rule in sheet.rules)


def test_a_filled_field_has_its_parts_and_only_the_ones_asked_for(tmp_path):
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Label: Name }\n')
    ids = {i.id for i in view.handle.composition.walk()}
    assert {"root.f.box", "root.f.box.body.input", "root.f.box.label_box.label", "root.f.indicator"} <= ids
    assert not ids & {"root.f.box.leading_icon", "root.f.box.error_icon", "root.f.box.trailing_icon", "root.f.box.reveal_button", "root.f.footer.supporting",
                      "root.f.box.body.prefix", "root.f.box.body.suffix"}


def test_everything_a_field_can_show_is_shown_when_asked_for(tmp_path):
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Label: Amount, Leading: search, Trailing: close, Prefix: "$", Suffix: USD, Supporting: "In dollars", Counter: true, Max_Length: 12 }\n')
    ids = {i.id for i in view.handle.composition.walk()}
    assert {"root.f.box.leading_icon", "root.f.box.trailing_icon", "root.f.box.body.prefix", "root.f.box.body.suffix", "root.f.footer.supporting",
            "root.f.footer.counter"} <= ids
    assert view.node("root.f.footer.supporting").get("text") == "In dollars" and view.node("root.f.footer.counter").get("text") == "0/12"
    assert part(view, "f.box.body", "prefix").get("text") == "$" and part(view, "f.box.body", "suffix").get("text") == "USD"


def test_an_outlined_field_has_a_border_and_no_line_under_it(tmp_path):
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Variant: outlined, Label: Name }\n')
    ids = {i.id for i in view.handle.composition.walk()}
    assert "root.f.indicator" not in ids
    box = view.node("root.f.box")
    assert box.get("stroke_width") == 1.0 and box.get("stroke_color") == role(view, "outline")


def test_typing_writes_the_signal_and_the_signal_writes_the_input(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Name, Text: <| name |> }\n')
    field = input_of(view)
    field.focus()
    view.window.advance(16)
    view.window.simulate("input", text="Ada")
    assert vm.name.get() == "Ada" and field.get("text") == "Ada"
    vm.name.set("Grace")
    assert field.get("text") == "Grace"


def test_a_field_with_a_one_way_text_shows_it_and_reverts_the_users_edit(tmp_path):
    _, view, vm = opened(tmp_path, "TextField { Name: f, Label: Name, Text: <| name + '!' |> }\n")
    vm.name.set("a")
    assert input_of(view).get("text") == "a!"


def test_max_length_stops_the_typing_and_the_counter_counts(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Text: <| name |>, Max_Length: 3, Counter: true }\n')
    input_of(view).focus()
    view.window.advance(16)
    view.window.simulate("input", text="abcdef")
    assert vm.name.get() == "abc" and input_of(view).get("text") == "abc"
    assert view.node("root.f.footer.counter").get("text") == "3/3"


def test_read_only_keeps_the_text_and_disabled_dims_the_field(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Text: <| name |>, Read_Only: true }\nTextField { Name: g, Text: <| email |>, Disabled: true }\n')
    vm.name.set("fixed")
    input_of(view).focus()
    view.window.advance(16)
    view.window.simulate("input", text="x")
    assert vm.name.get() == "fixed" and input_of(view).get("text") == "fixed"
    assert view.node("root.g").get("opacity") == 0.38 and view.node("root.f").get("opacity") == 1.0
    assert input_of(view, "g").get("disabled") is True and input_of(view).get("disabled") is False


def test_the_label_is_raised_by_focus_or_text_and_comes_back(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Name, Text: <| name |>, Placeholder: "Type here" }\n')
    label_box, label = view.node("root.f.box.label_box"), view.node("root.f.box.label_box.label")
    field = input_of(view)
    lowered = (label_box.get("y"), label.get("font_size"), field.get("placeholder"))
    assert lowered[0] == 18.0 and field.get("placeholder") == ""  # the hint is the label while the field is empty and idle
    field.focus()
    for _ in range(3):
        view.window.advance(16)
    assert 8.0 < label_box.get("y") < 18.0  # it glides: part of the way after three frames
    for _ in range(20):
        view.window.advance(16)
    raised = (label_box.get("y"), label.get("font_size"), field.get("placeholder"))
    assert raised[0] == 8.0 and raised[1] < lowered[1] and raised[2] == "Type here"
    vm.name.set("Ada")  # with text it stays raised, focused or not
    view.window.simulate("pointer_down", x=700, y=700)
    view.window.simulate("pointer_up", x=700, y=700)
    for _ in range(20):
        view.window.advance(16)
    assert label_box.get("y") == 8.0
    vm.name.set("")
    for _ in range(20):
        view.window.advance(16)
    assert label_box.get("y") in (8.0, 18.0)  # back down if the field has lost the focus too


def test_an_outlined_label_sits_on_the_border_with_a_fill_behind_it(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Variant: outlined, Label: Name, Text: <| name |> }\n')
    label_box = view.node("root.f.box.label_box")
    assert label_box.get("y") == 18.0 and label_box.get("fill") in (None, (0, 0, 0, 0))
    vm.name.set("x")
    for _ in range(20):
        view.window.advance(16)
    assert label_box.get("y") == -8.0 and label_box.get("fill") == role(view, "surface")


def test_focus_hover_and_error_change_the_line_the_border_and_the_label(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Name, Text: <| name |> }\nTextField { Name: o, Variant: outlined, Label: Name, Text: <| email |> }\nTextField { Name: e, Label: Name, Error: Wrong }\n')
    line, label = view.node("root.f.indicator"), view.node("root.f.box.label_box.label")
    assert line.get("fill") == role(view, "on_surface_variant") and line.get("layout_height") == 1.0
    assert label.get("fill") == role(view, "on_surface_variant")
    view.window.advance(16)
    view.window.simulate("pointer_move", x=60, y=40)  # over the first field
    assert line.get("fill") == role(view, "on_surface")
    input_of(view).focus()
    view.window.advance(16)
    view.window.advance(16)
    assert line.get("fill") == role(view, "primary") and line.get("layout_height") == 2.0 and label.get("fill") == role(view, "primary")
    outlined = view.node("root.o.box")
    assert outlined.get("stroke_width") == 1.0
    input_of(view, "o").focus()
    view.window.advance(16)
    assert outlined.get("stroke_width") == 2.0 and outlined.get("stroke_color") == role(view, "primary")
    assert view.node("root.e.indicator").get("fill") == role(view, "error")
    assert view.node("root.e.box.label_box.label").get("fill") == role(view, "error")


def test_an_error_shows_its_message_in_place_of_the_supporting_text_with_an_icon(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Email, Supporting: "Your address", Error: <| msg |>, Trailing: close }\n')
    assert "root.f.box.error_icon" not in {i.id for i in view.handle.composition.walk()}
    assert view.node("root.f.footer.supporting").get("text") == "Your address" and "root.f.box.trailing_icon" in {i.id for i in view.handle.composition.walk()}
    vm.msg.set("Not an email")
    ids = {i.id for i in view.handle.composition.walk()}
    assert "root.f.box.error_icon" in ids and "root.f.box.trailing_icon" not in ids
    assert view.node("root.f.footer.supporting").get("text") == "Not an email"
    assert view.node("root.f.footer.supporting").get("fill") == role(view, "error")
    assert view.node("root.f.box.error_icon").get("fill") == role(view, "error")
    vm.msg.set("")
    assert view.node("root.f.footer.supporting").get("text") == "Your address"


def test_the_inputs_name_includes_the_error_for_assistive_technology(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Email, Error: <| msg |> }\n')
    field = input_of(view)
    assert field.get("role") == "textbox" and field.get("label") == "Email"
    vm.msg.set("Not an email")
    assert field.get("label") == "Email: Not an email"


def test_a_password_field_hides_the_text_and_a_button_shows_it(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Password, Obscured: true, Text: <| name |> }\n')
    field, button = input_of(view), view.node("root.f.box.reveal_button")
    assert field.get("obscured") is True and button.get("role") == "button" and button.get("label") == "Show password"
    view.window.advance(16)
    view.window.simulate("click", node=button)
    assert field.get("obscured") is False and view.node("root.f.box.reveal_button").get("label") == "Hide password"
    view.window.simulate("click", node=view.node("root.f.box.reveal_button"))
    assert field.get("obscured") is True
    assert view.handle.node("f").state["reveal"].get() is False


def test_multiline_makes_a_taller_input_that_takes_enter(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Notes, Multiline: true, Text: <| name |>, Handlers { On_Submit: submit } }\n')
    field = input_of(view)
    assert field.get("multiline") is True and view._built.outer["root.f.box.body.input"].get("min_height") == 72.0
    field.focus()
    view.window.advance(16)
    view.window.simulate("key_down", key="Enter")
    assert vm.log == []  # Enter is a new line here, not a submit


def test_enter_submits_a_single_line_field_and_keys_reach_on_key(tmp_path):
    _, view, vm = opened(tmp_path, 'TextField { Name: f, Label: Name, Text: <| name |>, Handlers { On_Submit: submit, On_Key: keyed } }\n')
    input_of(view).focus()
    view.window.advance(16)
    view.window.simulate("key_down", key="Enter")
    assert vm.log == ["key", "submit"] or vm.log == ["submit", "key"]
    vm.log.clear()
    view.window.simulate("key_down", key="a")
    assert vm.log == ["key"]


def test_a_value_the_field_does_not_allow_is_an_error_with_a_suggestion(tmp_path):
    with pytest.raises(LoadError) as caught:
        opened(tmp_path, 'TextField { Name: f, Variant: filld }\n')
    assert "TextField.variant" not in str(caught.value) or "filld" in str(caught.value)
    assert "is 'filld', which is not one of: filled, outlined" in str(caught.value) and "did you mean 'filled'" in str(caught.value)
    with pytest.raises(LoadError) as caught:
        opened(tmp_path, 'TextField { Name: f, Lable: Name }\n')
    assert "TextField: no property 'lable'" in str(caught.value) and "did you mean 'label'" in str(caught.value)


def test_the_app_can_restyle_the_field_and_a_call_can_resize_it(tmp_path):
    sheet = {"styles": [{"widget": "TextField", "part": "box", "variant": "filled", "style": {"background": "#112233"}},
                        {"widget": "TextField", "style": {"width": 300}}]}
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Label: A }\nTextField { Name: g, Label: B, Style { Width: 200 } }\n',
                        app_kwargs={"stylesheet_spec": sheet})
    assert view.node("root.f.box").get("fill") == (17, 34, 51, 255)  # the app's rule beats the shipped one
    assert view.node("root.f").get("layout_width") == 300.0 and view.node("root.g").get("layout_width") == 200.0  # inline beats every rule


def test_a_project_can_replace_the_shipped_field_with_a_view_of_the_same_name(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "TextField_View.tdl").write_text(
        "---\nTDL: 0.2\nName: TextField\n---\nText {\n  Params: [label]\n  Text: mine: <| label |>\n  Typography_Role: body_large\n  Style { Foreground: \"#000000\" }\n}\n")
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Label: Name }\n')
    assert view.node("root.f").get("text") == "mine: Name"


def test_the_text_input_primitive_is_the_bare_input(tmp_path):
    _, view, vm = opened(tmp_path, 'TextInput { Name: f, Text: <| name |>, Placeholder: Go, Obscured: true, Max_Length: 2, Style { Width: 100, Height: 30, Background: "#FFFFFF", Foreground: "#000000" }, Typography_Role: body_large }\n')
    field = view.node("root.f")
    assert field.get("placeholder") == "Go" and field.get("obscured") is True
    field.focus()
    view.window.advance(16)
    view.window.simulate("input", text="abc")
    assert vm.name.get() == "ab"


# -- the files and the schema --------------------------------------------------------------------------------------------------


def test_the_shipped_view_validates_against_the_widget_schema_all_the_way_down():
    import json
    import jsonschema
    from pathlib import Path

    from tess_ui import shipped
    from tess_ui.spec import widgets
    from tess_ui.spec.tdl import load_marked_tdl
    from tess_ui.spec.tdl_theme import plain

    schema = widgets.json_schema()
    validator = jsonschema.Draft7Validator(schema)
    views = shipped.shipped_views()

    def unwrapped(node):
        """The schema describes the built-in widgets; a shipped view that uses another shipped view (Tabs uses Badge) is checked as the Container it stands in."""
        if isinstance(node, dict):
            node = {k: unwrapped(v) for k, v in node.items()}
            if node.get("widget") in views:
                node = {k: v for k, v in node.items() if k in ("name", "if", "for", "key", "children")} | {"widget": "Container"}
        elif isinstance(node, list):
            node = [unwrapped(v) for v in node]
        return node

    for path in views.values():
        errors = list(validator.iter_errors(unwrapped(plain(load_marked_tdl(path.read_text(encoding="utf-8"), path.name)))))
        assert not errors, f"{path.name}: {errors[0].message[:200]}"
    broken = plain(load_marked_tdl(views["TextField"].read_text(encoding="utf-8"), "TextField_View.tdl"))
    broken["children"][1]["children"][1]["children"][1]["valu"] = 1  # a misspelt property deep inside
    assert list(validator.iter_errors(broken))
    json.dumps(schema)


def test_the_old_builder_draws_a_placeholder_a_password_and_a_multiline_field_too():
    from tess_ui import View

    spec = {"id": "root", "kind": "Container", "style": {"width": 300, "height": 200}, "children": [
        {"id": "f", "kind": "TextField", "text": {"content": "", "font_family": "Roboto", "font_size": 16, "placeholder": "Name", "obscured": True,
                                                 "multiline": True}, "style": {"width": 200, "height": 60, "background": "#FFFFFF"}}]}
    field = View(spec, theme_seed=(103, 80, 164, 255)).node("f")
    assert (field.get("placeholder"), field.get("obscured"), field.get("multiline")) == ("Name", True, True)
    for bad, message in (({"obscured": "yes"}, "text.obscured is true or false"), ({"placeholder": 5}, "text.placeholder is text")):
        bad_spec = {**spec, "children": [{**spec["children"][0], "text": {**spec["children"][0]["text"], **bad}}]}
        with pytest.raises(ValueError, match=message):
            View(bad_spec, theme_seed=(103, 80, 164, 255))


def test_the_old_text_field_kind_becomes_the_text_input_primitive_when_migrated():
    from tess_ui.spec.translate import Translator

    new = Translator().translate({"id": "root", "kind": "Container", "children": [
        {"id": "f", "kind": "TextField", "text": {"content": "hi", "font_family": "Roboto", "font_size": 14}, "style": {"background": "#FFFFFF"}}]})
    assert new["children"][0]["widget"] == "TextInput" and new["children"][0]["text"] == "hi"


def test_lowering_leaves_out_what_only_the_renderer_acts_on():
    from tess_ui.spec.compose import Composer
    from tess_ui.spec.lower import lower
    from tess_ui.spec.nodes import parse_view

    node = lower(Composer({}, VM()).compose(parse_view("---\nTDL: 0.2\nName: T\n---\nTextInput { Max_Length: 3, Read_Only: true, Placeholder: x }\n", "T_View.tdl")).root)
    assert node["kind"] == "TextField" and node["text"]["placeholder"] == "x" and "max_length" not in node and "read_only" not in node


# -- what was left (#244): the glide, the filled corners, describedby, autocomplete ---------------------------------------------


def settle(view, n=20):
    for _ in range(n):
        view.window.advance(16)


def test_a_filled_field_has_a_four_pixel_top_corner_and_a_square_bottom(tmp_path):
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Label: Name }\n')
    assert view.node("root.f.box").get("corner_radius") == (4.0, 4.0, 0.0, 0.0)
    (tmp_path / "o").mkdir()
    _, outlined, _ = opened(tmp_path / "o", 'TextField { Name: f, Label: Name, Variant: outlined }\n')
    assert outlined.node("root.f.box").get("corner_radius") == 4.0


def test_the_input_is_described_by_the_help_line_and_the_footer_is_there_even_with_no_help(tmp_path):
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Label: Name, Supporting: "Your name" }\n')
    node = input_of(view)
    assert node.get("describedby") == [view._built.outer["root.f.footer"]]
    assert view.node("root.f.footer").get("layout_height") > 0
    (tmp_path / "n").mkdir()
    _, bare, _ = opened(tmp_path / "n", 'TextField { Name: f, Label: Name }\n')
    assert bare.node("root.f.footer").get("layout_height") == 0.0  # no room taken when there is nothing to say


SUGGESTIONS = "[Alice, Alan, Albert, Bob, Carol]"


def typed(view, text):
    node = input_of(view)
    node.focus()
    settle(view, 2)
    node.set(text="")
    view.window.simulate("input", text=text)
    settle(view, 8)


def test_suggestions_show_in_a_menu_under_the_field_that_contain_what_is_typed(tmp_path):
    _, view, vm = opened(tmp_path, f"TextField {{ Name: f, Label: Name, Text: <| name |>, Suggestions: {SUGGESTIONS} }}\n")
    assert not view._shown_layers
    typed(view, "al")
    assert view._shown_layers
    labels = [view.node(k).get("text") for k in view._built.specs if k.startswith("root.f.offers.surface.row[") and k.endswith("].item.label")]
    assert labels == ["Alice", "Alan", "Albert"]
    surface = view.node("root.f.offers.surface")
    box = view.node("root.f.box")
    assert surface.get("layout_y") >= box.get("layout_y") + box.get("layout_height")


def test_pressing_a_suggestion_fills_the_field_in_and_closes_the_menu(tmp_path):
    _, view, vm = opened(tmp_path, f"TextField {{ Name: f, Label: Name, Text: <| name |>, Suggestions: {SUGGESTIONS} }}\n")
    typed(view, "al")
    view.window.simulate("click", node=view.node("root.f.offers.surface.row[1].item"))
    settle(view, 8)
    assert vm.name.get() == "Alan" and not view._shown_layers


def test_no_menu_when_nothing_matches_or_the_text_is_already_a_suggestion(tmp_path):
    _, view, _ = opened(tmp_path, f"TextField {{ Name: f, Label: Name, Text: <| name |>, Suggestions: {SUGGESTIONS} }}\n")
    typed(view, "zz")
    assert not view._shown_layers
    typed(view, "Bob")
    assert not view._shown_layers


def test_a_field_without_suggestions_builds_no_menu(tmp_path):
    _, view, _ = opened(tmp_path, 'TextField { Name: f, Label: Name }\n')
    assert "root.f.offers" not in view._built.specs


def test_escape_closes_the_suggestions_and_typing_again_brings_them_back(tmp_path):
    _, view, _ = opened(tmp_path, f"TextField {{ Name: f, Label: Name, Text: <| name |>, Suggestions: {SUGGESTIONS} }}\n")
    typed(view, "al")
    assert view._shown_layers
    view.window.simulate("key_down", key="escape")
    settle(view, 6)
    assert not view._shown_layers
    typed(view, "alb")
    assert view._shown_layers
