"""Piece 4 of the TDL switch: a stylesheet written in TDL is read into the same mapping with positions that the YAML loader makes, `tesserae migrate-tdl`
writes `*_Stylesheet.yaml` as `*_Stylesheet.tdl` keeping comments and layout, idempotent, refusing what it cannot write back, and every error of a stylesheet
points into the `.tdl` file (`design/tdl-views.md`, `src/tess_ui/spec/tdl_stylesheet.py`, `src/tess_ui/migrate_tdl_sheets.py`)."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

from tess_ui import cli  # noqa: E402
from tess_ui.migrate_tdl import ConvertError, migrate_tdl  # noqa: E402
from tess_ui.migrate_tdl_sheets import _canon, convert_sheet  # noqa: E402
from tess_ui.spec.nodes import LoadError, PMap, PSeq, load_marked  # noqa: E402
from tess_ui.spec.rules import RuleSheet  # noqa: E402
from tess_ui.spec.tdl import title_case  # noqa: E402
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet, load_rule_sheet_tdl, load_tdl_stylesheet_file  # noqa: E402
from tests.test_migrate_tdl import make_project  # noqa: E402

VIEWS = Path(__file__).parent.parent / "src" / "tess_ui" / "views"
SHIPPED = sorted(VIEWS.glob("*_Stylesheet.yaml"))


def sheet(body, meta='Tesserae: "0.6"'):
    """A TDL stylesheet file (`T_Stylesheet.tdl`): the metadata block is five lines, so `body` starts on line 6."""
    return f"---\nTDL: 0.2\nName: T\n{meta}\n---\n{body}"


def load(body, **kw):
    return load_marked_tdl_stylesheet(sheet(body, **kw), "T_Stylesheet.tdl")


def fails(body, message, **kw):
    with pytest.raises(LoadError) as caught:
        load(body, **kw)
    assert message in str(caught.value) or message in caught.value.message
    return caught.value


def at(err, line, column):
    """The error is at `line` and (0-based) `column` of `T_Stylesheet.tdl`."""
    assert (err.line, err.column) == (line, column), f"{err.message}: at {err.line}:{err.column}"
    assert err.file == "T_Stylesheet.tdl"


def to_tdl(body, name="T"):
    return convert_sheet("tesserae: 0.6\n" + body, name, "T_Stylesheet.yaml").text


def reads_equal(yaml_text, tdl_text):
    return _canon(load_marked_tdl_stylesheet(tdl_text, "T_Stylesheet.tdl")) == _canon({"styles": load_marked(yaml_text).get("styles") or []})


def check_shape(item):
    """Every mapping has `at`, `key_at` and `val_at` for exactly its keys, every list `at` and `item_at` for its items."""
    if isinstance(item, PMap):
        assert set(item.key_at) == set(item.val_at) == set(item) and isinstance(item.at, tuple)
        for value in item.values():
            check_shape(value)
    elif isinstance(item, PSeq):
        assert len(item.item_at) == len(item) and isinstance(item.at, tuple)
        for value in item:
            check_shape(value)


def text_at(lines, where, length):
    line, column = where
    return lines[line - 1][column:column + length]


# -- (a) the shipped stylesheets ---------------------------------------------------------------------------------------------


def test_the_49_shipped_stylesheets_convert_and_load_to_the_yaml_mapping():
    assert len(SHIPPED) == 49
    rules = 0
    for path in SHIPPED:
        text = path.read_text(encoding="utf-8")
        written = convert_sheet(text, path.name.removesuffix("_Stylesheet.yaml"), path.name).text
        assert reads_equal(text, written), path.name
        got = load_marked_tdl_stylesheet(written, path.name)
        check_shape(got)
        rules += len(got["styles"])
    assert rules == 276  # every rule of every shipped sheet


def test_positions_of_the_tdl_mapping_land_on_the_key_and_the_head_of_each_block():
    """Each key's position is its text, a block's the head word, a rule's `Rule`; the same holds in the YAML mapping for the key text."""
    for path in SHIPPED:
        written = convert_sheet(path.read_text(encoding="utf-8"), "X", path.name).text
        lines = written.split("\n")
        top = load_marked_tdl_stylesheet(written, path.name)
        assert text_at(lines, top.key_at["styles"], 6) == "Styles" == text_at(lines, top["styles"].at, 6)
        for rule, rule_at in zip(top["styles"], top["styles"].item_at, strict=True):
            assert text_at(lines, rule_at, 4) == "Rule" == text_at(lines, rule.at, 4)
            for key, key_at in rule.key_at.items():
                assert text_at(lines, key_at, len(key)).lower() == key, (path.name, key)
            for field, field_at in rule["style"].key_at.items():
                assert text_at(lines, field_at, len(field)).lower() == field, (path.name, field)


def test_the_property_values_are_positioned_at_their_text():
    written = to_tdl("styles:\n  - {widget: Button, variant: tonal, classes: [a], style: {gap: 8, background: \"{{ x }}\", padding: {left: 4}}}\n")
    lines = written.split("\n")
    rule = load_marked_tdl_stylesheet(written, "T_Stylesheet.tdl")["styles"][0]
    assert text_at(lines, rule.val_at["widget"], 6) == "Button" and text_at(lines, rule.val_at["variant"], 5) == "tonal"
    assert text_at(lines, rule.val_at["classes"], 3) == "[a]"
    style = rule["style"]
    assert text_at(lines, style.val_at["gap"], 1) == "8" and text_at(lines, style.val_at["background"], 7) == "<| x |>"
    assert text_at(lines, style["padding"].key_at["left"], 4) == "Left" and text_at(lines, style.val_at["padding"], 7) == "Padding"


def test_a_converted_sheet_goes_through_rule_sheet_to_the_same_rules():
    """Both mappings give `RuleSheet.of` the same rules (the templates compare by their expressions)."""
    def rules_of(spec, file, text):
        return [(r.widget, r.selectors, r.classes, r.name, r.part, r.state, r.order, r.specificity,
                 {k: (tuple(getattr(p, "source", p) for p in v.parts) if hasattr(v, "parts") else v) for k, v in r.style.items()})
                for r in RuleSheet.of(spec, file, text).rules]

    for path in SHIPPED[:12]:
        text = path.read_text(encoding="utf-8")
        written = convert_sheet(text, "X", path.name).text
        assert rules_of(load_marked(text), path.name, text) == rules_of(load_marked_tdl_stylesheet(written, path.name), path.name, written), path.name


# -- (b) what the language has -----------------------------------------------------------------------------------------------


def test_a_stylesheet_is_a_styles_block_of_rule_blocks_with_title_case_keys_that_come_back_snake_case():
    m = load("Styles {\n  Rule { Widget: Button, Variant: tonal, Style { Gap: 8, Transition { Corner_Radius: 200 } } }\n}\n")
    assert m == {"styles": [{"widget": "Button", "variant": "tonal", "style": {"gap": 8, "transition": {"corner_radius": 200}}}]}
    assert list(m["styles"][0]) == ["widget", "variant", "style"]  # the order is the written order


def test_values_are_typed_as_the_yaml_loader_types_them_and_a_slot_is_the_template_string():
    m = load("Styles {\n  Rule {\n    Widget: Text\n    Classes: [a, b]\n    Style {\n      Opacity: 0.5\n      Clip_Children: true\n      Flex: null\n"
             "      Width: 50%\n      Height: <| a * 2 |>\n      Label: Hello <| name |>!\n      Font: \"<| not a slot |>\"\n    }\n  }\n}\n")
    style = m["styles"][0]["style"]
    assert style == {"opacity": 0.5, "clip_children": True, "flex": None, "width": "50%", "height": "{{ a * 2 }}", "label": "Hello {{ name }}!",
                     "font": "<| not a slot |>"}
    assert m["styles"][0]["classes"] == ["a", "b"] and isinstance(style["clip_children"], bool)


def test_an_empty_styles_block_is_no_rules_and_a_block_of_items_is_a_list_of_maps():
    assert load("Styles { }\n") == {"styles": []}
    assert load("Styles { Rule { Widget: Text, Style { Runs { Item { A: 1 } Item { A: 2 } } } } }\n")["styles"][0]["style"]["runs"] == [{"a": 1}, {"a": 2}]


def test_comments_are_skipped_wherever_they_stand():
    m = load("# top\nStyles {  # a\n  # b\n  Rule {  # c\n    # d\n    Widget: Text  # e\n    Style { # f\n      Gap: 1  # g\n    }\n  }\n}\n# end\n")
    assert m == {"styles": [{"widget": "Text", "style": {"gap": 1}}]}


def test_crlf_and_a_byte_order_mark_read_the_same_and_positions_stay_true():
    body = "Styles {\n  Rule { Widget: Text, Style { Gap: 1 } }\n}\n"
    plain, crlf = load(body), load_marked_tdl_stylesheet("\ufeff" + sheet(body).replace("\n", "\r\n"), "T_Stylesheet.tdl")
    assert plain == crlf and plain["styles"][0].at == crlf["styles"][0].at == (7, 2)


def test_a_duplicate_key_in_a_rule_or_a_style_is_refused_as_the_yaml_loader_refuses_it():
    at(fails("Styles {\n  Rule { Widget: Text, Widget: Button, Style { Gap: 1 } }\n}\n", "The key Widget is already used on line 7"), 7, 23)
    at(fails("Styles {\n  Rule { Widget: Text, Style { Gap: 1, Gap: 2 } }\n}\n", "The key Gap is already used on line 7"), 7, 39)
    at(fails("Styles {\n  Rule { Widget: Text, Style { Gap: 1 } Style { Gap: 2 } }\n}\n", "duplicate key 'style'"), 7, 40)


def test_the_marker_is_checked_as_the_first_line_of_a_yaml_file_is():
    err = fails("Styles { }\n", "written for Tesserae 0.5", meta='Tesserae: "0.5"')
    at(err, 4, 10)
    fails("Styles { }\n", "names the release series", meta="Tesserae: soon")
    assert load("Styles { }\n", meta="") == {"styles": []}  # optional, as the YAML marker is
    at(fails("Styles { }\n", "no metadata key 'Tesserea'", meta="Tesserea: x"), 4, 0)


def test_a_stylesheet_in_a_file_with_utf8_trouble_or_on_disk_is_read_and_named(tmp_path):
    path = tmp_path / "T_Stylesheet.tdl"
    path.write_bytes(sheet("Styles { Rule { Widget: Text, Style { Gap: 1 } } }\n").encode("utf-8"))
    assert load_tdl_stylesheet_file(path)["styles"][0]["widget"] == "Text"
    assert load_rule_sheet_tdl(path).rules[0].widget == "Text" and load_rule_sheet_tdl(path).file == str(path)
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(LoadError, match="not UTF-8"):
        load_tdl_stylesheet_file(path)
    with pytest.raises(LoadError, match="not UTF-8"):
        load_rule_sheet_tdl(path)


# -- (c) errors ------------------------------------------------------------------------------------------------------------


def test_the_root_must_be_styles_and_it_holds_rule_blocks_only():
    at(fails("Button { }\n", "a stylesheet is one Styles block of Rule blocks, not 'Button'"), 6, 0)
    err = fails("Style { }\n", "not 'Style'")
    assert err.hint and "did you mean 'Styles'" in err.hint
    at(fails("Styles {\n  Widget: Button\n}\n", "Styles holds Rule blocks, and 'Widget:' is a property"), 7, 2)
    err = fails("Styles {\n  Rul { Widget: Text }\n}\n", "Styles holds Rule blocks, got 'Rul'")
    at(err, 7, 2)
    assert err.hint == "did you mean 'Rule'"
    at(fails("Styles {\n  If <| a |> {\n    Rule { }\n  }\n}\n", "an If has no place in a stylesheet"), 7, 2)
    at(fails("Styles {\n  For x In <| xs |> Key <| x |> {\n    Rule { }\n  }\n}\n", "a For has no place in a stylesheet"), 7, 2)


def test_a_key_that_is_not_title_case_says_what_to_write():
    err = fails("Styles {\n  Rule { widget: Text, Style { Gap: 1 } }\n}\n", "'widget' is not a Title_Case key")
    at(err, 7, 9)
    assert err.hint == "write 'Widget'"
    at(fails("Styles {\n  Rule { Widget: Text, Style { cornerRadius: 1 } }\n}\n", "'cornerRadius' is not a Title_Case key"), 7, 31)
    at(fails("Styles {\n  Rule { Widget: Text, style { Gap: 1 } }\n}\n", "'style' is not a Title_Case key"), 7, 23)


def test_an_if_in_a_rule_or_in_a_style_is_refused_and_a_call_is_not_a_value():
    at(fails("Styles {\n  Rule {\n    If <| a |> { }\n  }\n}\n", "an If has no place in a rule"), 8, 4)
    at(fails("Styles {\n  Rule { Widget: Text, Style { If <| a |> { } } }\n}\n", "an If has no place in a stylesheet, and 'Style' holds a map"), 7, 31)
    at(fails("Styles {\n  Rule { Widget: Text, Style { Gap: size(2) } }\n}\n", "'size(...)' is not a value a view takes"), 7, 36)


def test_a_syntax_error_from_tess_dl_names_the_tdl_file_line_and_column():
    at(fails("Styles {\n  Rule { Widget: Text\n}\n", "This block is never closed"), 6, 7)
    err = fails("Styles {\n  Rule { Widget: Text, Style { Gap: <| 1 + 2 } }\n}\n", "")
    assert (err.file, err.line) == ("T_Stylesheet.tdl", 7) and "<|" in str(err)


def pair(tdl_body, yaml_body):
    """The same mistake in a `.tdl` and a `.yaml` stylesheet: the `LoadError`s of `RuleSheet.of`."""
    tdl_text = sheet(tdl_body)
    yaml_text = "tesserae: 0.6\n" + yaml_body
    with pytest.raises(LoadError) as from_tdl:
        RuleSheet.of(load_marked_tdl_stylesheet(tdl_text, "T_Stylesheet.tdl"), "T_Stylesheet.tdl", tdl_text)
    with pytest.raises(LoadError) as from_yaml:
        RuleSheet.of(load_marked(yaml_text), "T_Stylesheet.yaml", yaml_text)
    return from_tdl.value, from_yaml.value


@pytest.mark.parametrize("tdl_body, yaml_body, column_word", [
    ("Styles {\n  Rule { Widget: Text, Variant: filld, Style { Gap: 1 } }\n}\n", "styles:\n  - {widget: Text, variant: filld, style: {gap: 1}}\n", "Variant"),
    ("Styles {\n  Rule { Widget: Text, State: hover, Style { Gap: 1 } }\n}\n", "styles:\n  - {widget: Text, state: hover, style: {gap: 1}}\n", "hover"),
    ("Styles {\n  Rule { Widget: Text, Colour: red, Style { Gap: 1 } }\n}\n", "styles:\n  - {widget: Text, colour: red, style: {gap: 1}}\n", "Colour"),
    ("Styles {\n  Rule { Widget: Text, Style { Gapp: 1 } }\n}\n", "styles:\n  - {widget: Text, style: {gapp: 1}}\n", "Gapp"),
    ("Styles {\n  Rule { Widget: Text, Style { Height: wide } }\n}\n", "styles:\n  - {widget: Text, style: {height: wide}}\n", "wide"),
    ("Styles {\n  Rule { Widget: Text, Part: lable, Style { Gap: 1 } }\n}\n", "styles:\n  - {widget: Text, part: lable, style: {gap: 1}}\n", "lable"),
    ("Styles {\n  Rule { Widget: Text, Style { } }\n}\n", "styles:\n  - {widget: Text, style: {}}\n", "Style"),
    ("Styles {\n  Rule { Variant: tonal, Style { Gap: 1 } }\n}\n", "styles:\n  - {variant: tonal, style: {gap: 1}}\n", "Variant"),
    ("Styles {\n  Rule { Widget: Text, Classes: oops, Style { Gap: 1 } }\n}\n", "styles:\n  - {widget: Text, classes: oops, style: {gap: 1}}\n", "oops"),
])
def test_a_mistake_in_what_a_rule_says_has_the_message_and_hint_of_the_yaml_loader_and_points_into_the_tdl_file(tdl_body, yaml_body, column_word):
    from_tdl, from_yaml = pair(tdl_body, yaml_body)
    assert (from_tdl.message, from_tdl.hint) == (from_yaml.message, from_yaml.hint)
    assert (from_tdl.line, from_tdl.file) == (7, "T_Stylesheet.tdl")
    assert sheet(tdl_body).split("\n")[6][from_tdl.column:].startswith(column_word)  # the column is the written word's, as in the YAML file


def test_an_expression_mistake_in_a_slot_points_at_the_column_inside_the_slot():
    body = "Styles {\n  Rule { Widget: Text, Style { Height: <| 1 + |> } }\n}\n"
    text = sheet(body)
    with pytest.raises(LoadError) as caught:
        RuleSheet.of(load_marked_tdl_stylesheet(text, "T_Stylesheet.tdl"), "T_Stylesheet.tdl", text)
    assert caught.value.line == 7 and caught.value.file == "T_Stylesheet.tdl"
    line = text.split("\n")[6]
    assert line[caught.value.column:].startswith("+ |>") or caught.value.column >= line.index("<|")


def test_a_theme_or_a_view_given_as_a_stylesheet_is_refused_and_says_what_a_stylesheet_is():
    err = fails("Theme { Seed: blue }\n", "a stylesheet is one Styles block of Rule blocks, not 'Theme'")
    at(err, 6, 0)
    assert err.hint and "Styles" in err.hint


# -- (d) the converter -----------------------------------------------------------------------------------------------------

SAMPLE = """tesserae: 0.6  # the series
# The look of Sample.
# A second line.

styles:  # the rules
  # a pill
  - {widget: Button, size: xs, style: {height: 32, gap: 4}}  # a small one
  - widget: Button   # filled
    variant: filled
    # the colours
    classes: [a, b]
    style:
      background: "{{ 'primary' if selected else 'surface' }}"  # by state
      # the corners
      corner_radius: {top_left: 4, top_right: 4}
      padding: {left: 12, right: 12, top: 0, bottom: 0}
      label: "{{ a }}px"

  # last
  - widget: Text
    part: label
    state: hovered
    style: {foreground: on_surface, opacity: 0.5, clip_children: true, flex: null}
# the end
"""

SAMPLE_TDL = """---
TDL: 0.2
Name: Sample
Tesserae: "0.6"  # the series
---
# The look of Sample.
# A second line.

Styles {  # the rules
  # a pill
  Rule { Widget: Button, Size: xs, Style { Height: 32, Gap: 4 } }  # a small one
  Rule {  # filled
    Widget: Button
    Variant: filled
    # the colours
    Classes: [a, b]
    Style {
      Background: <| 'primary' if selected else 'surface' |>  # by state
      # the corners
      Corner_Radius { Top_Left: 4, Top_Right: 4 }
      Padding { Left: 12, Right: 12, Top: 0, Bottom: 0 }
      Label: <| a |>px
    }
  }

  # last
  Rule {
    Widget: Text
    Part: label
    State: hovered
    Style { Foreground: on_surface, Opacity: 0.5, Clip_Children: true, Flex: null }
  }
}
# the end
"""

DIVIDER_TDL = """---
TDL: 0.2
Name: Divider
Tesserae: "0.6"
---
# The look of Divider (Material 3): a line in outline_variant that fills the length it is in (in a container that does not set `align_content`). The insets are margins at the ends it keeps clear.
Styles {
  Rule {
    Widget: Divider
    Style {
      Background: outline_variant
      Width: <| thickness if orientation == 'vertical' else 'auto' |>
      Height: <| thickness if orientation == 'horizontal' else 'auto' |>
    }
  }

  Rule {
    Widget: Divider
    Variant: inset
    Style {
      Margin: <| {'left': 16} if orientation == 'horizontal' else {'top': 16} |>
    }
  }

  Rule {
    Widget: Divider
    Variant: middle
    Style {
      Margin: <| {'left': 16, 'right': 16} if orientation == 'horizontal' else {'top': 16, 'bottom': 16} |>
    }
  }
}
"""


def test_golden_comments_blank_lines_order_and_layout_are_kept_on_a_sample_that_has_every_kind_of_comment():
    result = convert_sheet(SAMPLE, "Sample", "Sample_Stylesheet.yaml")
    assert result.text == SAMPLE_TDL and result.steps == 0
    assert reads_equal(SAMPLE, result.text)


def test_golden_a_shipped_stylesheet_keeps_its_top_comment_its_blank_lines_and_its_block_layout():
    path = VIEWS / "Divider_Stylesheet.yaml"
    assert convert_sheet(path.read_text(encoding="utf-8"), "Divider", path.name).text == DIVIDER_TDL


def test_a_rule_in_flow_style_is_one_line_when_it_fits_and_opened_when_it_does_not():
    long_rule = "  - {widget: Button, style: {" + ", ".join(f"transition_{n}: {n}" for n in range(14)) + "}}\n"
    out = to_tdl("styles:\n  - {widget: Text, style: {gap: 1}}\n" + long_rule)
    assert "  Rule { Widget: Text, Style { Gap: 1 } }\n" in out
    assert "  Rule {\n    Widget: Button\n    Style {\n      Transition_0: 0\n" in out and max(map(len, out.split("\n"))) <= 150
    assert reads_equal("styles:\n  - {widget: Text, style: {gap: 1}}\n" + long_rule, out)


def test_an_empty_stylesheet_is_an_empty_styles_block_and_reads_back_as_no_rules():
    for body in ("styles: []\n", "styles:\n", ""):
        out = to_tdl(body)
        assert out.endswith("---\nStyles { }\n"), body
        assert load_marked_tdl_stylesheet(out, "T.tdl") == {"styles": []}


def test_the_name_is_the_file_stem_and_a_series_line_is_written_only_when_the_yaml_had_one():
    out = convert_sheet("styles: []\n", "Fancy_Button", "F_Stylesheet.yaml").text
    assert out.startswith("---\nTDL: 0.2\nName: Fancy_Button\n---\n")
    with pytest.raises(ConvertError, match="name '9Lives' cannot be a TDL Name"):
        convert_sheet("tesserae: 0.6\nstyles: []\n", "9Lives")


def test_a_crlf_file_is_written_with_crlf():
    out = convert_sheet(SAMPLE.replace("\n", "\r\n"), "Sample").text
    assert out == SAMPLE_TDL.replace("\n", "\r\n") and "\r\r" not in out


def test_a_style_that_names_a_style_file_stays_the_text_it_is():
    out = to_tdl("styles:\n  - {widget: Text, style: Compact_Style.yaml}\n")
    assert "Rule { Widget: Text, Style: Compact_Style.yaml }" in out
    assert load_marked_tdl_stylesheet(out, "T.tdl")["styles"][0]["style"] == "Compact_Style.yaml"


@pytest.mark.parametrize("body, line, message", [
    ("styles:\n  - {widget: &w Text, style: {gap: 1}}\n  - {widget: *w, style: {gap: 2}}\n", 3, "an anchor or alias has no TDL form"),
    ("styles:\n  - {widget: Text, style: {Gap: 1}}\n", 2, "the key 'Gap' is not lower snake_case (write 'gap')"),
    ("styles:\n  - {widget: Text, style: {gap: 2026-11-14}}\n", 2, "a value of type date has no TDL form"),
    ("styles:\n  - {widget: Text, style: {label: \"{{ a }}, {{ b }}\"}}\n", 2, "text with a slot that cannot be written unquoted"),
    ("styles:\n  - {widget: Text, style: {a: [[1]]}}\n", 2, "a list that holds lists, or both text and maps, has no TDL form"),
    ("styles:\n  - {widget: Text, style: {gap: 1}}\nextra: 1\n", 3, "a stylesheet has only 'styles:', not 'extra'"),
    ("styles: {widget: Text}\n", 1, "'styles:' is a list of rules"),
    ("styles:\n  - Text\n", 2, "a rule is a mapping"),
    ("styles:\n  - {widget: Text, style: {if: 1}}\n", 2, "the key 'if' is a TDL keyword"),
])
def test_what_has_no_tdl_form_is_refused_with_the_yaml_line_and_what_to_write(body, line, message):
    with pytest.raises(ConvertError) as caught:
        convert_sheet("tesserae: 0.6\n" + body, "T", "T_Stylesheet.yaml")
    assert message in str(caught.value) and caught.value.line == line + 1, (str(caught.value), caught.value.line)


def test_a_theme_a_view_an_old_series_and_a_file_that_is_no_mapping_are_refused():
    with pytest.raises(ConvertError, match="a stylesheet has only 'styles:', not 'seed'") as caught:
        convert_sheet("tesserae: 0.6\nseed: blue\ncolors: {primary: red}\n", "T")
    assert "looks like a theme" in (caught.value.hint or "") and caught.value.line == 2
    with pytest.raises(ConvertError, match="a stylesheet has only 'styles:', not 'widget'"):
        convert_sheet("tesserae: 0.6\nwidget: Text\n", "T")
    with pytest.raises(ConvertError, match="written for Tesserae 0.5"):
        convert_sheet("tesserae: 0.5\nstyles: []\n", "T")
    for text in ("", "# only a comment\n", "- a\n- b\n", "just text\n"):
        with pytest.raises(ConvertError, match="a stylesheet is a mapping with styles:"):
            convert_sheet(text, "T")
    with pytest.raises(ConvertError, match="duplicate key 'styles'"):
        convert_sheet("styles: []\nstyles: []\n", "T")


def test_a_conversion_that_does_not_read_back_the_same_is_refused_and_says_where(monkeypatch):
    import tess_ui.migrate_tdl as module

    monkeypatch.setattr(module, "_scalar", lambda value: "99")  # a converter that writes a wrong value
    with pytest.raises(ConvertError, match=r"does not read back as the same stylesheet: styles\[0\]\.style\.gap: .* read back as") as caught:
        convert_sheet("tesserae: 0.6\nstyles:\n  - {widget: Text, style: {gap: 8}}\n", "T")
    assert "no TDL form the converter knows" in (caught.value.hint or "")


def test_style_fields_with_digits_and_double_underscores_round_trip():
    for key in ("a__b", "a11y", "x_y_z"):
        assert reads_equal(f"styles:\n  - {{widget: Text, style: {{{key}: 1}}}}\n", to_tdl(f"styles:\n  - {{widget: Text, style: {{{key}: 1}}}}\n")), key
    assert title_case("a11y") == "A11y"


# -- (e) files, folders and the command ---------------------------------------------------------------------------------------

SMALL = "tesserae: 0.6\nstyles:\n  - {widget: Button, style: {gap: 4}}\n"


def test_a_project_folder_converts_stylesheets_beside_their_yaml_and_a_second_run_changes_nothing(tmp_path):
    make_project(tmp_path, {"Styles/Tasks_Stylesheet.yaml": SMALL, "Views/Main_View.yaml": "tesserae: 0.6\nwidget: Text\n"})
    report = migrate_tdl(tmp_path, write=True)
    assert [(r.path.name, r.status) for r in report.results] == [("Tasks_Stylesheet.yaml", "converted"), ("Main_View.yaml", "converted")]
    written = tmp_path / "Styles" / "Tasks_Stylesheet.tdl"
    assert written.read_text(encoding="utf-8") == to_tdl("styles:\n  - {widget: Button, style: {gap: 4}}\n", "Tasks")
    before = written.read_bytes()
    stamp = written.stat().st_mtime_ns
    again = migrate_tdl(tmp_path, write=True)
    assert [r.status for r in again.results] == ["current", "current"] and written.read_bytes() == before and written.stat().st_mtime_ns == stamp
    assert (tmp_path / "Styles" / "Tasks_Stylesheet.yaml").is_file()  # the YAML stays


def test_idempotence_the_conversion_of_every_shipped_sheet_is_the_same_text_twice_and_nothing_else_is_needed():
    for path in SHIPPED[:6]:
        text = path.read_text(encoding="utf-8")
        name = path.name.removesuffix("_Stylesheet.yaml")
        assert convert_sheet(text, name, path.name).text == convert_sheet(text, name, path.name).text


def test_a_differing_tdl_file_is_replaced_only_with_write_and_the_yaml_goes_with_remove_source(tmp_path):
    make_project(tmp_path, {"A_Stylesheet.yaml": SMALL, "A_Stylesheet.tdl": "old\n"})
    dry = migrate_tdl(tmp_path)
    assert dry.results[0].status == "converted" and "A_Stylesheet.tdl exists and differs: it is replaced" in dry.results[0].notes
    assert (tmp_path / "A_Stylesheet.tdl").read_text() == "old\n"
    migrate_tdl(tmp_path, write=True, remove_source=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["A_Stylesheet.tdl"]
    assert load_tdl_stylesheet_file(tmp_path / "A_Stylesheet.tdl")["styles"][0]["widget"] == "Button"


def test_a_stylesheet_that_fails_is_reported_with_its_line_and_the_others_are_still_written(tmp_path):
    make_project(tmp_path, {"Bad_Stylesheet.yaml": "tesserae: 0.6\nstyles:\n  - {widget: Text, style: {Gap: 1}}\n", "Good_Stylesheet.yaml": SMALL})
    report = migrate_tdl(tmp_path, write=True)
    assert [r.status for r in report.results] == ["failed", "converted"]
    assert report.failed[0].line == 3
    assert "failed    Bad_Stylesheet.yaml:3: the key 'Gap' is not lower snake_case (write 'gap')" in report.render(tmp_path)
    assert (tmp_path / "Good_Stylesheet.tdl").is_file() and not (tmp_path / "Bad_Stylesheet.tdl").exists()


def test_a_single_stylesheet_file_is_converted_and_other_files_are_refused_naming_both_kinds(tmp_path):
    make_project(tmp_path, {"A_Stylesheet.yaml": SMALL, "other.yaml": "a: 1\n"})
    assert migrate_tdl(tmp_path / "A_Stylesheet.yaml", write=True).results[0].status == "converted"
    with pytest.raises(ValueError, match=r"other.yaml is not a \*_View.yaml or \*_Stylesheet.yaml file"):
        migrate_tdl(tmp_path / "other.yaml")


def test_the_command_converts_stylesheets_and_says_what_goes_with_what(tmp_path, capsys):
    make_project(tmp_path, {"A_Stylesheet.yaml": SMALL})
    assert cli.main(["migrate-tdl", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "would convert A_Stylesheet.yaml -> A_Stylesheet.tdl" in out and not list(tmp_path.glob("*.tdl"))
    assert "1 files would be converted" in out and "nothing written" in out
    assert cli.main(["migrate-tdl", str(tmp_path), "--write", "--remove-source"]) == 0
    assert "A_Stylesheet.yaml -> A_Stylesheet.tdl" in capsys.readouterr().out
    assert sorted(p.name for p in tmp_path.iterdir()) == ["A_Stylesheet.tdl"]
    assert cli.main(["migrate-tdl", str(tmp_path / "A_Stylesheet.tdl")]) == 2
    assert "is not a *_View.yaml or *_Stylesheet.yaml file" in capsys.readouterr().err


def test_the_command_exits_1_when_a_stylesheet_fails(tmp_path, capsys):
    make_project(tmp_path, {"Bad_Stylesheet.yaml": "tesserae: 0.6\nstyles:\n  - {widget: Text, style: {Gap: 1}}\n"})
    assert cli.main(["migrate-tdl", str(tmp_path)]) == 1
    assert "Bad_Stylesheet.yaml:3: the key 'Gap'" in capsys.readouterr().out


def test_a_slot_with_a_pipe_and_a_closing_angle_cannot_be_written_and_is_refused_by_the_read_back():
    with pytest.raises(ConvertError, match="does not read back as the same stylesheet: styles\\[0\\]\\.style\\.gap"):
        convert_sheet("tesserae: 0.6\nstyles:\n  - {widget: Text, style: {gap: \"{{ a |> b }}\"}}\n", "T")
