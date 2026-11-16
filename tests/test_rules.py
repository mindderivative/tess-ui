"""#209 phase 6: stylesheet rules -- the shape and its errors, specificity, layers, inline over rules, variants, parts and states."""

import pytest

from tess_ui import App, Signal, ViewModel
from tess_ui.composed import open_composed
from tess_ui.spec import widgets as W
from tess_ui.spec.compose import Composer
from tess_ui.spec.nodes import LoadError, parse_view, read_marked
from tess_ui.spec.rules import Rule, RuleSheet, STATES, is_rule_sheet, load_rule_sheet, ordered
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet
from tess_ui.spec.widgets import Property, WidgetDecl, decl_from_params
from tess_ui.viewmodel import Bindings


HEAD = "---\nTDL: 0.2\nName: S\n---\n"


def sheet(text):
    return RuleSheet.of(load_marked_tdl_stylesheet(text, "S_Stylesheet.tdl"), "S_Stylesheet.tdl", text)


def one(*lines):
    """A stylesheet text with one rule, a line to each of `lines` (the first is on line 7)."""
    return HEAD + "Styles {\n  Rule {\n" + "".join(f"    {line}\n" for line in lines) + "  }\n}\n"


def bad(text, message):
    with pytest.raises(LoadError) as caught:
        sheet(text)
    assert message in str(caught.value), str(caught.value)
    return caught.value


class VM:
    def __init__(self):
        self.mode = Signal("filled")
        self.on = Signal(False)


def compose(main, rules, views=None, vm=None):
    """Composes `main` with the rule sheets (lowest layer first); `views` maps a name to its source."""
    sources = views or {}
    decls = {n: decl_from_params(n, read_marked(s, f"{n}_View.tdl").get("params")) for n, s in sources.items()}
    docs = {n: parse_view(s, f"{n}_View.tdl", resolver=decls.get, view_name=n) for n, s in sources.items()}
    doc = parse_view(main, "Main_View.tdl", resolver=decls.get)
    return Composer(docs, vm or VM(), rules=[sheet(r) if isinstance(r, str) else r for r in rules]).compose(doc)


def test_a_rule_value_with_slots_is_a_template_and_an_error_names_its_slot():
    from tess_ui.tel import Template

    rules = sheet(one("Widget: Text", "Style { Background: c<| a |>-<| b |>, Height: <| h * 2 |>, Width: 50% }")).rules
    style = rules[0].style
    assert isinstance(style["background"], Template) and not style["background"].single and style["height"].single and style["width"] == "50%"
    err = bad(one("Widget: Text", "Style { Background: c<| a |>-<| b + |> }"), "syntax error")
    assert (err.file, err.line, err.column) == ("S_Stylesheet.tdl", 8, 36)


def test_a_dict_stylesheet_value_with_braces_is_refused_because_braces_are_not_a_slot():
    with pytest.raises(LoadError, match=r"style 'height' has \{\{ \}\} in its text, and \{\{ \}\} is not a slot") as caught:
        RuleSheet.of({"styles": [{"widget": "Rect", "style": {"height": "{{ h / 2 }}"}}]})
    assert "tess_ui.tel.Parts" in str(caught.value)
    from tests.helpers import parts, slot

    made = RuleSheet.of({"styles": [{"widget": "Rect", "style": {"height": parts(slot(" h / 2 "))}}]})
    assert made.rules[0].style["height"].single


# -- the shape -------------------------------------------------------------------------------------------------------------


def accepting_foreground():
    """The widgets that declare `foreground` among their style extras, as the error names them."""
    from tess_ui.spec import widgets as registry

    registry._load_builtins()
    return ", ".join(sorted(name for name, decl in registry._REGISTRY.items() if "foreground" in decl.extras))


def test_a_sheet_of_rules_is_checked_and_prepared():
    s = sheet("""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Text, Classes: [big], State: hovered, Style { Foreground: on_surface, Opacity: 0.5 } }
  Rule { Style { Corner_Radius: 4 } }
}
""")
    assert [r.widget for r in s.rules] == ["Text", None]
    assert s.rules[0].classes == {"big"} and s.rules[0].state == "hovered"
    assert [r.widget for r in s.candidates(["Text"])] == [None, "Text"] and [r.widget for r in s.candidates(["Rect"])] == [None]
    assert RuleSheet.of(None).rules == [] and sheet("""---
TDL: 0.2
Name: S
---
Styles { }
""").rules == []


def test_the_old_and_the_new_shape_are_told_apart():
    assert is_rule_sheet({"styles": [{"widget": "Button", "style": {}}]}) and is_rule_sheet({"styles": [{"part": "x"}]})
    assert not is_rule_sheet({"styles": [{"kind": "Rect", "style": {}}, {"id": "a", "style": {}}]}) and not is_rule_sheet({}) and not is_rule_sheet(None)


def test_a_rule_with_an_unknown_key_widget_or_state_says_what_is_allowed():
    err = bad(one("Widgit: Text", "Style { Opacity: 1 }"), "a rule has no 'widgit'")
    assert "did you mean 'widget'" in str(err) and (err.line, err.column) == (7, 4)
    err = bad(one("Widget: Text", "State: hover", "Style { Opacity: 1 }"), "'state:' is one of hovered, focused")
    assert "did you mean 'hovered'" in str(err) and err.line == 8
    bad(one("Widget: Text", "Style { }"), "a rule needs a 'style:' mapping")
    bad(one("Widget: 5", "Style { Opacity: 1 }"), "'widget:' is a widget name")
    bad(HEAD + "Styles {\n  Widget: Text\n}\n", "Styles holds Rule blocks, and 'Widget:' is a property")
    bad(HEAD + "Styles: 5\n", "This text is not valid here")
    bad(HEAD + "Rules { }\n", "a stylesheet is one Styles block of Rule blocks, not 'Rules'")
    bad(one("Classes: a", "Style { Opacity: 1 }"), "'classes:' is a list of names")
    bad(one("Widget: Text", "Name: 5", "Style { Opacity: 1 }"), "'name:' is a node's name")


def test_selectors_must_be_properties_the_widget_declares_and_values_it_allows():
    W.register_widget(WidgetDecl("Btn2", {"variant": Property("enum", choices=("filled", "text"), default="filled")}, parts=("label",)))
    try:
        sheet("""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Btn2, Variant: text, Part: label, Style { Opacity: 1 } }
}
""")
        err = bad(one("Widget: Btn2", "Variant: tonal", "Style { Opacity: 1 }"), "Btn2.variant is one of filled, text, not 'tonal'")
        assert err.line == 8
        bad(one("Widget: Btn2", "Size: large", "Style { Opacity: 1 }"), "Btn2 has no property 'size' to select on")
        err = bad(one("Widget: Btn2", "Part: lable", "Style { Opacity: 1 }"), "Btn2 has no part 'lable'")
        assert "parts: label" in str(err)
    finally:
        W.unregister_widget("Btn2")
    bad(one("Variant: tonal", "Style { Opacity: 1 }"), "'variant:' needs a 'widget:'")
    bad(one("Part: label", "Style { Opacity: 1 }"), "'part:' needs a 'widget:'")
    sheet("""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: SomeView, Variant: anything, Part: whatever, Style { Opacity: 1 } }
}
""")  # a view is checked when it is composed


def test_foreground_is_an_extra_and_the_error_names_who_accepts_it():
    sheet("""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Text, Style { Foreground: primary } }
  Rule { Widget: SomeView, Style { Foreground: primary } }
}
""")
    err = bad(one("Widget: Container", "Style { Foreground: primary }"), "Container: style 'foreground' is not valid here")
    assert f"widgets that accept it: {accepting_foreground()}" in str(err) and (err.line, err.column) == (8, 12)
    err = bad(one("Widget: Container", "Style { Widht: 1 }"), "style 'widht' is not valid here")
    assert "did you mean 'width'" in str(err)


def test_an_expression_in_a_rule_is_checked_where_it_is_written():
    sheet("""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Text, Style { Width: <| height / 2 |> } }
}
""")
    err = bad(one("Widget: Text", "Style { Width: <| height / |> }"), "syntax error")
    assert err.line == 8


def test_a_stylesheet_file_is_read_with_positions(tmp_path):
    path = tmp_path / "App_Stylesheet.tdl"
    path.write_text(one("Widget: Text", "Style { Opacity: 0.5 }"))
    assert load_rule_sheet(path).rules[0].widget == "Text"
    path.write_text(one("Widget: Text", "State: nope", "Style { Opacity: 0.5 }"))
    with pytest.raises(LoadError, match=r"App_Stylesheet.tdl:8:12"):
        load_rule_sheet(path)


# -- specificity -----------------------------------------------------------------------------------------------------------


def rule(**kw):
    kw.setdefault("style", {})
    return Rule(kw.pop("widget", None), kw.pop("style"), **kw)


@pytest.mark.parametrize("weaker, stronger", [
    (rule(widget="Text"), rule(widget="Text", state="hovered")),                       # a state beats the widget alone
    (rule(widget="Text", state="hovered"), rule(widget="Text", selectors={"variant": "a"})),   # a property beats a state
    (rule(widget="Text", selectors={"variant": "a"}), rule(widget="Text", selectors={"variant": "a", "size": "s"})),   # more properties win
    (rule(widget="Text", classes=frozenset({"a"})), rule(widget="Text", classes=frozenset({"a"}), selectors={"size": "s"})),
    (rule(widget="Text", selectors={"variant": "a", "size": "s", "shape": "r"}), rule(widget="Text", name="x")),   # a name beats everything
    (rule(), rule(widget="Text")),                                                      # no widget is the weakest
])
def test_specificity_orders_name_then_property_count_then_state_then_widget(weaker, stronger):
    assert weaker.specificity < stronger.specificity
    first, second = rule(order=0), rule(order=1)
    assert ordered([stronger, weaker])[-1] is stronger
    assert ordered([second, first]) == [first, second]  # a tie goes to the later rule


# -- resolution ------------------------------------------------------------------------------------------------------------


def style(comp, id="root"):
    return comp.find(id).effective_style()


def test_a_widget_rule_styles_the_nodes_of_that_widget_and_inline_wins_only_for_its_own_fields():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Rect { Name: a, Style { Width: 5 } }
    Container { Name: b }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Style { Width: 99, Height: 40, Corner_Radius: 4 } }
}
"""])
    assert style(comp, "root.a") == {"width": 5, "height": 40, "corner_radius": 4}  # inline width over the rule; the rest from the rule
    assert style(comp, "root.b") == {}


def test_a_later_layer_beats_an_earlier_one_whatever_the_specificity_and_a_later_rule_wins_a_tie():
    comp = compose("""---
TDL: 0.2
Name: root
---
Rect { Name: root, Classes: [big] }
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Classes: [big], Name: root, Style { Width: 1, Height: 1 } }
}
""",
                    """---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Style { Width: 2 } }
  Rule { Widget: Rect, Style { Width: 3 } }
}
"""])
    assert style(comp) == {"width": 3, "height": 1}  # the upper layer's later rule; height only the lower layer gave


def test_inside_a_layer_the_most_specific_rule_wins_whatever_the_order():
    comp = compose("""---
TDL: 0.2
Name: me
---
Rect { Name: me, Classes: [big] }
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Name: me, Style { Width: 1 } }
  Rule { Widget: Rect, Classes: [big], Style { Width: 2, Height: 2 } }
  Rule { Widget: Rect, Style { Width: 3, Height: 3, Opacity: 0.5 } }
  Rule { Classes: [big], Style { Opacity: 0.1, Corner_Radius: 7 } }
}
"""])
    assert style(comp) == {"width": 1, "height": 2, "opacity": 0.1, "corner_radius": 7}  # a class rule beats a widget rule alone


def test_classes_must_all_be_on_the_node():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Rect { Name: a, Classes: [x] }
    Rect { Name: b, Classes: [x, y] }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Classes: [x, y], Style { Width: 9 } }
}
"""])
    assert style(comp, "root.a") == {} and style(comp, "root.b") == {"width": 9}


BTN = ("""---
TDL: 0.2
Name: main
---
Rect {
  Params {
    Label { Type: str, Default: "" }
    Variant { Type: str, Default: filled }
    Height { Type: int, Default: 40 }
    Selected { Type: bool, Default: false }
  }
  Style { Width: 100 }
  Children {
    Text { Name: label, Text: <| label |> }
    Icon { Name: icon, Icon: home }
  }
}
""")


def test_a_variant_selects_on_the_params_of_a_view_call_and_follows_them():
    vm = VM()
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Btn { Name: b, Variant: <| mode |> }
    Btn { Name: c, Variant: text }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Btn, Style { Corner_Radius: 4 } }
  Rule { Widget: Btn, Variant: filled, Style { Background: primary } }
  Rule { Widget: Btn, Variant: text, Style { Background: transparent } }
}
"""], {"Btn": BTN}, vm)
    assert style(comp, "root.b") == {"width": 100, "corner_radius": 4, "background": "primary"}   # inline width, rules for the rest
    assert style(comp, "root.c")["background"] == "transparent"
    vm.mode.set("text")  # the variant is a Signal: the look changes with it
    assert style(comp, "root.b")["background"] == "transparent"
    vm.mode.set("filled")
    assert style(comp, "root.b")["background"] == "primary"


def test_a_part_rule_styles_the_named_node_inside_that_widget_only():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Btn { Name: b, Label: Go }
    Text { Name: label, Text: x }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Btn, Part: label, Style { Foreground: on_primary } }
  Rule { Widget: Btn, Part: icon, Style { Foreground: red } }
}
"""],
                   {"Btn": BTN})
    assert style(comp, "root.b.label") == {"foreground": "on_primary"} and style(comp, "root.b.icon") == {"foreground": "red"}
    assert style(comp, "root.label") == {} and style(comp, "root.b") == {"width": 100}


def test_slot_content_belongs_to_the_caller_not_to_the_widget_it_is_passed_to():
    box = """---
TDL: 0.2
Name: main
---
Container {
  Children {
    Slot { }
  }
}
"""
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Box {
      Name: b
      Children {
        Text { Name: label, Text: x }
      }
    }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Box, Part: label, Style { Opacity: 0.5 } }
}
"""], {"Box": box})
    assert style(comp, "root.b.label") == {}


def test_a_rule_value_may_read_the_widgets_own_params():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Btn { Name: b, Height: 30 }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Btn, Style { Corner_Radius: <| height / 2 |> } }
}
"""], {"Btn": BTN})
    assert style(comp, "root.b")["corner_radius"] == 15


def test_a_call_site_style_beats_the_rules_and_a_rule_beats_nothing_inline():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Btn { Name: b, Style { Width: 7, Background: red } }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Btn, Style { Width: 1, Background: primary, Corner_Radius: 4 } }
}
"""], {"Btn": BTN})
    assert style(comp, "root.b") == {"width": 7, "background": "red", "corner_radius": 4}


def test_state_rules_follow_the_interaction_signals_and_the_widgets_own_properties():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Btn { Name: b, Selected: <| on |> }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Btn, Style { Background: surface } }
  Rule { Widget: Btn, State: hovered, Style { Background: hover } }
  Rule { Widget: Btn, State: selected, Style { Opacity: 0.5 } }
  Rule { Widget: Btn, State: pressed, Style { Background: down } }
}
"""],
                   {"Btn": BTN})
    inst = comp.find("root.b")
    assert style(comp, "root.b")["background"] == "surface" and "opacity" not in style(comp, "root.b")
    inst.interaction_signal("hovered").set(True)
    assert style(comp, "root.b")["background"] == "hover"
    inst.interaction_signal("pressed").set(True)
    assert style(comp, "root.b")["background"] == "down"   # pressed and hovered: the later rule of the same specificity
    inst.interaction_signal("pressed").set(False)
    inst.interaction_signal("hovered").set(False)
    comp.root.children  # noqa: B018
    comp2 = compose("""---
TDL: 0.2
Name: b
---
Btn { Name: b, Selected: true }
""", ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Btn, State: selected, Style { Opacity: 0.5 } }
}
"""], {"Btn": BTN})
    assert style(comp2)["opacity"] == 0.5


def test_hovered_focused_and_pressed_are_names_an_expression_can_read_but_not_write():
    comp = compose("""---
TDL: 0.2
Name: main
---
Rect { Interaction: true, Style { Background: <| 'hover' if hovered else 'rest' |> } }
""", [])
    assert style(comp)["background"] == "rest"
    comp.root.interaction_signal("hovered").set(True)
    assert style(comp)["background"] == "hover"
    with pytest.raises(LoadError, match="'hovered' is not writable here"):  # found when the view loads (#277)
        compose("""---
TDL: 0.2
Name: main
---
Rect { Interaction: true, Handlers { On_Click { Set { Target: hovered, Value: <| True |> } } } }
""", [])
    with pytest.raises(LoadError, match="reserved name"):
        compose("""---
TDL: 0.2
Name: main
---
Rect { State { Hovered: false } }
""", [])


def test_every_state_a_rule_can_name_is_documented():
    assert STATES == ("hovered", "focused", "focus_visible", "pressed", "disabled", "selected", "checked", "expanded", "error", "read_only", "visited")


def test_an_instance_with_no_matching_rule_makes_no_computed_and_rules_are_released_on_dispose():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Rect { Name: a }
    Text { Name: t }
  }
}
""", ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Style { Width: 4 } }
}
"""])
    assert comp.find("root.a")._rules is not None and comp.find("root.t")._rules is None and comp.root._rules is None
    comp2 = compose("""---
TDL: 0.2
Name: main
---
Rect { Classes: [x] }
""", ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Style { Width: <| mode.upper() and 4 |> } }
}
"""])
    vm = comp2.root.identities[0].scope.root
    assert vm.mode._subscribers
    comp2.dispose()
    assert vm.mode._subscribers == []


# -- on screen -------------------------------------------------------------------------------------------------------------


def test_a_hover_rule_changes_the_drawn_node_when_the_pointer_enters_and_leaves():
    s = sheet("""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Style { Background: "#112233" } }
  Rule { Widget: Rect, State: hovered, Style { Background: "#AABBCC" } }
}
""")
    doc = parse_view("""---
TDL: 0.2
Name: main
---
Rect { Style { Width: 100, Height: 60 } }
""", "Main_View.tdl")
    bindings = Bindings()
    view = open_composed(doc, bindings, rules=[s], theme_seed=(103, 80, 164, 255))
    rest = view.node("root").get("fill")
    view.window.advance(16)
    view.window.simulate("pointer_move", x=20, y=20)
    hovered = view.node("root").get("fill")
    assert hovered != rest
    view.window.simulate("pointer_move", x=900, y=900)
    assert view.node("root").get("fill") == rest


def test_the_app_uses_a_stylesheet_in_the_rule_shape_for_new_views(tmp_path):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Main_View.tdl").write_text("""---
TDL: 0.2
Name: main
---
Rect { Style { Width: 50, Height: 20 } }
""")
    app = App(root=tmp_path, stylesheet_spec={"styles": [{"widget": "Rect", "style": {"background": "#112233"}}]})
    opened = app.open_view("Main")
    assert opened.node("root").get("fill") == (17, 34, 51, 255)


def test_a_name_selector_matches_only_the_node_with_that_name():
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Rect { Name: a }
    Rect { Name: b }
    Rect { }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Name: a, Style { Width: 9 } }
}
"""])
    assert style(comp, "root.a") == {"width": 9} and style(comp, "root.b") == {} and style(comp, "root.children[2]") == {}


def test_the_root_of_a_view_is_the_widget_itself_not_a_part_of_it():
    named = """---
TDL: 0.2
Name: tag
---
Rect {
  Params: []
  Name: tag
  Children {
    Text { Name: inner, Text: x }
  }
}
"""
    comp = compose("""---
TDL: 0.2
Name: main
---
Container {
  Children {
    Named { Name: n }
  }
}
""",
                   ["""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Named, Part: tag, Style { Width: 1 } }
  Rule { Widget: Named, Style { Height: 2 } }
  Rule { Widget: Named, Part: inner, Style { Opacity: 0.5 } }
}
"""],
                   {"Named": named})
    assert style(comp, "root.n") == {"height": 2} and style(comp, "root.n.inner") == {"opacity": 0.5}


def test_a_pressed_rule_follows_the_pointer_down_and_up_on_screen():
    s = sheet("""---
TDL: 0.2
Name: S
---
Styles {
  Rule { Widget: Rect, Style { Background: "#112233" } }
  Rule { Widget: Rect, State: pressed, Style { Background: "#AABBCC" } }
}
""")
    view = open_composed(parse_view("""---
TDL: 0.2
Name: main
---
Rect { Style { Width: 100, Height: 60 } }
""", "Main_View.tdl"), Bindings(), rules=[s], theme_seed=(103, 80, 164, 255))
    rest = view.node("root").get("fill")
    view.window.advance(16)
    view.window.simulate("pointer_move", x=20, y=20)
    view.window.simulate("pointer_down", x=20, y=20)
    assert view.node("root").get("fill") != rest
    view.window.simulate("pointer_up", x=20, y=20)
    assert view.node("root").get("fill") == rest
