"""Stylesheets: the Rules in order, the selector builder (what a rule applies to, target, part, state), the style keys a selector's block type takes, a selector the builder cannot read."""

import difflib

import pytest

from tess_shell_config.form import Form
from tess_shell_config.model import DocumentModel
from tess_shell_config.selector import STATES, Selector, parse_selector
from tess_shell_config.structure import label_of

SHEET = """---
TDL: 0.1
Name: Sheet
---

# the base look
Stylesheet {
    Rule {
        Selector: "Text"
        Style { Foreground: $color.on_surface }   # text
    }

    Rule { Selector: "Slider::track:hovered", Background: $color.surface_raised }
    Rule { Selector: ".warning", Foreground: $color.warning }
    Rule { Selector: "#clock_label" }
    Rule { Selector: "Button .child" }
    Rule { Selector: "Text:wobbly" }
    Rule { Selector: ".cls::part" }
    Rule { }
}
"""


def changed(before: str, after: str) -> list[str]:
    return [line[0] + line[2:].rstrip("\n") for line in difflib.ndiff(before.splitlines(True), after.splitlines(True)) if line[0] in "+-"]


def at(model, index):
    rules = [e for e in model.document.root.entries if getattr(e, "type", "") == "Rule"]
    model.select(tuple(rules[index].index_path))
    return rules[index]


@pytest.fixture
def model():
    return DocumentModel.from_bytes(SHEET.encode())


@pytest.mark.parametrize("text, parts", [
    ("Text", Selector("Block or module", "Text")), ("Clock", Selector("Block or module", "Clock")), (".warning", Selector("A class", "warning")), ("#clock_label", Selector("A name", "clock_label")),
    ("Button:hovered", Selector("Block or module", "Button", "", "hovered")), ("Slider::track", Selector("Block or module", "Slider", "track")),
    ("Slider::track:pressed", Selector("Block or module", "Slider", "track", "pressed")), (".raised:focused", Selector("A class", "raised", "", "focused")),
])
def test_a_selector_in_the_grammar_is_read_into_its_parts_and_written_back_the_same(text, parts):
    assert parse_selector(text) == parts and parts.text() == text


@pytest.mark.parametrize("text", ["", "Button .child", "Text:wobbly", ".cls::part", "#n::part", "Text >", "a:b:c", "1Text", "::part", "Text:"])
def test_a_selector_the_builder_cannot_read_is_none(text):
    assert parse_selector(text) is None


def test_every_state_the_note_names_is_a_state():
    assert STATES == ("hovered", "pressed", "disabled", "selected", "checked", "focused")


def test_rules_are_told_apart_in_the_structure_by_their_selector(model):
    labels = [label_of(e) for e in model.document.root.entries if getattr(e, "type", "") == "Rule"]
    assert labels[:4] == ["Rule  Text", "Rule  Slider::track:hovered", "Rule  .warning", "Rule  #clock_label"] and labels[-1] == "Rule"


def test_the_builder_shows_the_four_parts_of_the_selector_first(model, schema):
    at(model, 1)
    view = Form(schema).build(model)
    assert list(view.groups)[0] == "Selector builder"
    rows = view.groups["Selector builder"]
    assert [r.label for r in rows] == ["Applies to", "Target", "Part", "State"]
    assert [view.cell(k).text for k in ("s:base", "s:target", "s:part", "s:state")] == ["Block or module", "Slider", "track", "hovered"]
    assert view.cell("s:base").shown["choices"] and [c["value"] for c in view.cell("s:state").shown["choices"]] == list(STATES)


def test_a_class_and_a_name_have_no_part_and_every_style_key(model, schema):
    at(model, 2)
    view = Form(schema).build(model)
    assert (view.cell("s:base").text, view.cell("s:target").text) == ("A class", "warning")
    every = {k for k in schema.roots["Rule"].style}
    assert every <= {r.key.name for r in view.rows if r.key}  # the union


def test_a_block_type_selector_shows_only_the_style_keys_that_type_takes_and_keeps_a_key_the_rule_already_has(model, schema):
    at(model, 0)  # Text, with Foreground in its Style block
    view = Form(schema).build(model)
    names = {r.key.name for r in view.rows if r.key}
    text_style = set(schema.block("Text").style)
    rule_style = set(schema.roots["Rule"].style)
    assert (names & rule_style) <= text_style and "Foreground" in names
    assert any("style keys a Text takes" in n for n in view.notes)
    assert any("order" in n and "Alt+Up" in n for n in view.notes)


def test_a_module_selector_takes_the_style_keys_of_the_modules_root_block(model, schema):
    at(model, 1)  # Slider::track
    view = Form(schema).build(model)
    root = schema.block(schema.modules["Slider"].root_block)
    assert ({r.key.name for r in view.rows if r.key} & set(schema.roots["Rule"].style)) <= set(root.style) | {"Background"}


@pytest.mark.parametrize("index", [4, 5, 6])
def test_a_selector_the_builder_cannot_read_shows_the_raw_text_and_the_union_of_style_keys(model, schema, index):
    at(model, index)
    view = Form(schema).build(model)
    assert "Selector builder" not in view.groups
    assert any("cannot read" in n for n in view.notes)
    assert view.cell("Selector").text and set(schema.roots["Rule"].style) <= {r.key.name for r in view.rows if r.key}


def test_changing_a_part_of_the_selector_writes_only_the_selector_line(model, schema):
    before = model.text
    at(model, 1)
    form = Form(schema)
    form.build(model)
    assert form.commit("s:target|", {"text": "Scale"}).changed
    assert changed(before, model.text) == ['-    Rule { Selector: "Slider::track:hovered", Background: $color.surface_raised }', '+    Rule { Selector: "Scale::track:hovered", Background: $color.surface_raised }']
    assert form.commit("s:state|", {"value": "pressed"}).changed and 'Selector: "Scale::track:pressed"' in model.text
    assert form.commit("s:part|", {"text": "thumb"}).changed and 'Selector: "Scale::thumb:pressed"' in model.text
    assert form.commit("s:base|", {"value": "A class"}).changed and 'Selector: ".Scale:pressed"' in model.text  # a part goes only with a module name
    assert form.reset("s:state|").changed and 'Selector: ".Scale"' in model.text
    assert model.can_undo


def test_the_builder_refuses_what_it_cannot_write_and_writes_nothing(model, schema):
    at(model, 2)
    form = Form(schema)
    form.build(model)
    before = model.text
    refused = form.commit("s:part|", {"text": "track"})
    assert not refused.ok and "module name" in refused.message and model.text == before
    refused = form.commit("s:target|", {"text": "two words"})
    assert not refused.ok and "one word" in refused.message and model.text == before
    refused = form.commit("s:state|", {"value": "wobbly"})
    assert not refused.ok and "one of" in refused.message and model.text == before


def test_a_rule_with_no_selector_gets_one_from_the_target_and_the_other_parts_wait_for_it(model, schema):
    at(model, 7)
    form = Form(schema)
    form.build(model)
    assert not form.view.cell("s:target").present
    first = form.commit("s:state|", {"value": "hovered"})
    assert not first.ok and "Target first" in first.message
    assert form.commit("s:target|", {"text": "Box"}).changed and "Selector: " in model.text and '"Box"' in model.text
    assert form.commit("s:state|", {"value": "hovered"}).changed and '"Box:hovered"' in model.text


def test_resetting_the_target_removes_the_selector(model, schema):
    at(model, 3)
    form = Form(schema)
    form.build(model)
    assert form.reset("s:target|").changed
    assert "#clock_label" not in model.text


def test_rules_move_up_and_down_and_undo_restores_the_bytes(model):
    before = model.text
    first = at(model, 0)
    path = tuple(first.index_path)
    target = model.neighbour(path, 1)
    assert target is not None
    model.move_block(path, None, target)
    assert [label_of(e) for e in model.document.root.entries if getattr(e, "type", "") == "Rule"][:2] == ["Rule  Slider::track:hovered", "Rule  Text"]
    assert model.undo() and model.text == before
