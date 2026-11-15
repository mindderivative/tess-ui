"""#209 phase 3: the node model -- every key of spec section 2, property checks, ids and names, and the shape of the errors."""

import pytest

from tess_ui.expr import Template
from tess_ui.spec import widgets as W
from tess_ui.spec.nodes import EVENTS, LoadError, load_marked, parse_view
from tess_ui.spec.widgets import Property, WidgetDecl


def tdl(root, name="T"):
    """A TDL view's text: its metadata block and the root block `root`."""
    return f"---\nTDL: 0.2\nName: {name}\n---\n{root}\n"


def node(root, **kw):
    return parse_view(tdl(root), "T_View.tdl", **kw).root


def fails(root, message, **kw):
    with pytest.raises(LoadError) as caught:
        parse_view(tdl(root), "T_View.tdl", **kw)
    assert message in str(caught.value), str(caught.value)
    return caught.value


def view_decl(name):
    return WidgetDecl(name, {"label": Property("str", required=True)}, container=True, view=True)


def resolver(name):
    return view_decl(name) if name in ("Button", "Card") else None


# -- every key of section 2 -----------------------------------------------------------------------------------------------


def accepting_foreground():
    """The widgets that declare `foreground` among their style extras, as the error names them."""
    from tess_ui.spec import widgets as registry

    registry._load_builtins()
    return ", ".join(sorted(name for name, decl in registry._REGISTRY.items() if "foreground" in decl.extras))


def test_the_root_block_picks_the_widget_and_an_unknown_one_is_an_error():
    assert node("Text { }").widget == "Text"
    err = fails("Texxt { }", "no widget named 'Texxt'")
    assert "did you mean 'Text'" in str(err)


def test_name_is_optional_and_a_plain_identifier():
    assert node("Text { Name: label }").name == "label"
    assert node("Text { }").name is None
    for bad in ("2cool", "has space", "a-b", "5"):
        fails(f'Text {{ Name: "{bad}" }}', "a name is letters, digits")


def test_if_is_an_expression():
    assert node("Container { Children { If <| unread > 0 |> { Text { } } } }").children[0].when is not None
    fails("Container { Children { If <| unread > |> { Text { } } } }", "syntax error")
    fails("Container { Children { If <| |> { Text { } } } }", "This slot is empty")


def test_for_binds_names_over_an_expression_and_the_key_may_be_none():
    n = node("Container { Children { For i, item In <| enumerate(items) |> Key <| item.id |> { Text { } } } }").children[0]
    assert n.loop.targets == ("i", "item") and n.loop.source == "i, item in enumerate(items)" and n.key is not None
    n = node("Container { Children { For x In <| range(3) |> Key <| None |> { Text { } } } }").children[0]
    assert n.loop.targets == ("x",) and n.key is None
    fails("Container { Children { For x In <| items + |> Key <| None |> { Text { } } } }", "syntax error")


def test_slot_names_the_parents_slot():
    assert node("Container { Children { Text { Slot: actions } } }").children[0].slot == "actions"
    fails('Text { Slot: "a b" }', "'slot:' takes a slot name")


def test_state_declares_names_with_starting_values():
    n = node("Text { State { On: false, Label: <| 1 + 1 |> } }")
    assert n.state["on"] is False and isinstance(n.state["label"], Template)
    fails("Text { State: [a] }", "'state:' takes a mapping")


def test_style_takes_universal_fields_a_widgets_extras_and_expressions():
    n = node("Container { Style { Width: 100, Background: <| color |>, Flex_Direction: vertical } }")
    assert n.style["width"] == 100 and isinstance(n.style["background"], Template)
    err = fails("Container { Style { Widht: 100 } }", "Container: style 'widht' is not valid here")
    assert "did you mean 'width'" in str(err)
    fails("Container { Style: [1] }", "'style:' takes a mapping")
    fails('Container { Style: "row_Style.yaml" }', "a style file (`*_Style.yaml`) is not part of the view language")
    fails("Container { Style: row }", "'style:' takes a mapping of style fields; write the fields here")
    assert node("Text { Style { Foreground: on_surface } }").style["foreground"] == "on_surface"  # an extra of the widgets that draw text
    err = fails("Container { Style { Foreground: red } }", "Container: style 'foreground' is not valid here")
    assert f"widgets that accept it: {accepting_foreground()}" in str(err)
    W.register_widget(WidgetDecl("Gauge", {}, extras=("track_height",)))
    try:
        assert node("Gauge { Style { Track_Height: 4 } }").style["track_height"] == 4
        fails("Rect { Style { Track_Height: 4 } }", "style 'track_height' is not valid here")
    finally:
        W.unregister_widget("Gauge")


def test_classes_is_a_list_of_names():
    assert node("Text { Classes: [a, b] }").classes == ["a", "b"]
    fails("Text { Classes: a }", "'classes:' takes a list")
    fails("Text { Classes: [1] }", "'classes:' takes a list")


def test_handlers_map_known_events_to_an_action_or_statements():
    n = node("""Rect {
  Handlers {
    On_Click: save
    On_Hover_Enter { Set { Target: hint, Value: <| 'Save' |> } Set { Target: count, Value: <| count + 1 |> } }
    On_Change: navigate.back
  }
}""")
    assert n.handlers["on_click"].action == "save" and n.handlers["on_change"].action == "navigate.back"
    assert n.handlers["on_hover_enter"].statements is not None and n.handlers["on_hover_enter"].action is None
    err = fails("Rect { Handlers { On_Clck: save } }", "no event 'on_clck'")
    assert "did you mean 'on_click'" in str(err)
    fails("Rect { Handlers { Click: save } }", "'click' is not an event name")
    fails("Rect { Handlers { On_Click: 5 } }", "a handler is an action name or statements")
    fails("Rect { Handlers: [on_click] }", "'handlers:' takes a mapping")


def test_the_events_are_the_views_events_plus_on_key():
    from tess_ui.view import _EVENTS

    assert set(EVENTS) == set(_EVENTS) | {"on_key", "on_submit", "on_press", "on_move", "on_release", "on_input", "on_dismiss"}


def test_a11y_takes_the_documented_fields_checked_and_bound():
    n = node("Rect { A11y { Label: Save, Role: button, Hidden: false, Live: polite, Level: 2 } }")
    assert n.a11y["role"] == "button" and n.a11y["level"] == 2
    assert isinstance(node("Rect { A11y { Label: <| title |> } }").a11y["label"], Template)
    fails("Rect { A11y { Lable: x } }", "no a11y field 'lable'")
    fails("Rect { A11y { Role: wizard } }", "a11y role 'wizard'")
    fails("Rect { A11y { Level: 0 } }", "a11y level must be a positive whole number")
    fails("Rect { A11y { Live: <| x |> } }", "a11y 'live' cannot be bound")


def test_interaction_is_a_switch_or_a_colour_role():
    assert node("Rect { Interaction: true }").interaction is True
    assert node("Rect { Interaction: on_primary }").interaction == "on_primary"
    fails("Rect { Interaction { Color: x } }", "write interaction: <colour>")
    fails("Rect { Interaction: [1] }", "'interaction:' takes true, false or a colour role")


def test_window_region_is_drag_or_none():
    assert node("Rect { Window_Region: drag }").window_region == "drag"
    err = fails("Rect { Window_Region: dragg }", "'window_region:' is one of drag, none")
    assert "did you mean 'drag'" in str(err)


def test_route_is_for_a_view_call():
    assert node('Card { Label: x, Route: "" }', resolver=resolver).route == ""
    assert node("Card { Label: x, Route: notes }", resolver=resolver).route == "notes"
    fails("Rect { Route: notes }", "'route:' is for a view call")
    fails("Card { Label: x, Route: 5 }", "'route:' takes a path", resolver=resolver)


def test_children_need_a_container_and_each_child_is_a_node():
    n = node("Container { Children { Text { } Rect { } } }")
    assert [c.widget for c in n.children] == ["Text", "Rect"]
    fails("Text { Children { } }", "Text takes no children")
    fails("Container { Children: x }", "'children:' takes a list of nodes")


def test_params_and_expects_are_only_valid_on_the_root():
    doc = parse_view(tdl("Text { Params: [label], Expects { Count: int }, Text: <| label |> }"), "C_View.tdl", view_name="C")
    assert doc.params == ["label"] and doc.expects == {"count": int and "int"} and doc.decl.view and doc.decl.properties["label"].required
    fails("Container { Children { Text { Params: [a] } } }", "'params:' is only valid at the top of a view file")
    fails("Text { Params: 5 }", "params is a list or a mapping")


def test_a_property_is_checked_against_its_widgets_declaration():
    assert node("Slider { Value: 0.5 }").props["value"] == 0.5
    assert node("Slider { Value: 1 }").props["value"] == 1.0
    assert isinstance(node("Slider { Value: <| volume |> }").props["value"], Template)
    err = fails("Slider { Valu: 1 }", "Slider: no property 'valu'")
    assert "did you mean 'value'" in str(err) and "properties: value, min, max, step, ticks, value_indicator, vertical, size, icon, label, disabled" in str(err)
    fails("Slider { Value: loud }", "Slider: 'value' takes a number")
    fails("Checkbox { Checked: \"yes\" }", "'checked' takes true or false")
    fails("Icon { }", "Icon: give one of 'icon', 'path'")
    fails('Icon { Icon: home, Path: "M0 0Z" }', "'icon' and 'path' cannot both be given")
    node('Icon { Path: "M0 0Z" }')
    fails("Icon { Icon: hom }", "names no built-in icon")
    fails("Text { Wrap: sideways }", "which is not one of: word, none")
    fails("Card { }", "'label' is required", resolver=resolver)


def test_a_node_and_nodes_property_hold_nodes():
    W.register_widget(WidgetDecl("Bar", {"leading": Property("node"), "actions": Property("nodes")}))
    try:
        n = node("Bar { Leading { Icon { Icon: home } } Actions { Text { Name: t } Rect { } } }")
        assert n.props["leading"].widget == "Icon" and [a.widget for a in n.props["actions"]] == ["Text", "Rect"]
        assert [x.id for x in n.walk()] == ["root", "root.leading", "root.t", "root.actions[1]"]
        fails("Bar { Actions: x }", "'actions' takes a list of nodes")
        fails("Bar { Leading: x }", "a node is a mapping")
    finally:
        W.unregister_widget("Bar")


def test_the_0_4_keys_say_what_to_write():
    for old, hint in (("Kind: Text", "widget: X"), ("Component: Card", "widget: X"), ("View: A_View.yaml", "widget: X"),
                      ("Include: A.yaml", "widget: X")):
        fails(f"Rect {{ {old} }}", "is not a key in 0.5.0")
        assert hint in str(fails(f"Rect {{ {old} }}", "is not a key in 0.5.0"))
    for key, hint in (("Id: a", "name:"), ("Repeat: x", "for: item in items"), ("When: x", "if: expression"), ("Bindings { }", "text:"),
                      ("With { }", "plain keys"), ("Two_Way: checked", "bare reference"), ("Component_Of: x", "address it as a part")):
        assert hint in str(fails(f"Rect {{ {key} }}", "is not a key in 0.5.0"))


# -- ids, names ------------------------------------------------------------------------------------------------------------


def test_every_node_gets_a_stable_id_from_its_path():
    n = node("Container { Name: top, Children { Text { } Container { Name: row, Children { Text { } Text { Name: last } } } } }")
    assert [x.id for x in n.walk()] == ["root", "root.children[0]", "root.row", "root.row.children[0]", "root.row.last"]


def test_names_are_unique_in_a_view_but_a_parent_and_child_may_share_one():
    node("Container { Name: a, Children { Text { Name: a } } }")
    err = fails("Container {\n  Children {\n    Text { Name: x }\n    Rect { Name: x }\n  }\n}", "the name 'x' is already used")
    assert "root.x" in str(err) and (err.line, err.column) == (8, 17)
    fails("Container { Children { Container { Name: x, Children { Text { } } } Container { Children { Text { Name: x } } } } }", "already used")


def test_nesting_is_capped():
    text = "Container { Children { " * 70 + "Text { }" + " } }" * 70
    fails(text, "nested more than 64 levels deep")


# -- errors name the file, line and column ------------------------------------------------------------------------------


def test_an_error_names_the_file_line_and_column_and_renders_a_caret():
    err = fails("Container {\n  Children {\n    Slider {\n      Valu: 1\n    }\n  }\n}", "T_View.tdl:8:7: error: Slider: no property 'valu'")
    shown = err.render()
    assert "Valu: 1" in shown
    assert shown.splitlines()[-1].strip() == "|     ^".strip() or shown.endswith("^")


def test_an_error_inside_an_expression_points_into_the_slot():
    err = fails("Text {\n  Text: Hi <| user. |>\n}", "T_View.tdl:6:")
    assert err.line == 6 and err.column > 8


def test_a_syntax_error_and_a_duplicate_key_are_load_errors():
    fails("Text { Bad: [ }", "T_View.tdl:5:")
    err = fails("Text {\n  Text: a\n  Text: b\n}", "already used")
    assert err.line == 7


def test_a_state_named_on_is_a_name_not_a_boolean():
    assert node("Text { State { On: false } }").state == {"on": False}
