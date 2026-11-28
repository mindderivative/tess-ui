"""A stylesheet written in TDL is read into a mapping with positions, and every error of a stylesheet points into the `.tdl` file
(`design/tdl-views.md`, `src/tess_ui/spec/tdl_stylesheet.py`)."""

from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

from tess_ui.spec.nodes import LoadError, PMap, PSeq  # noqa: E402
from tess_ui.spec.rules import RuleSheet  # noqa: E402
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet, load_rule_sheet_tdl, load_tdl_stylesheet_file  # noqa: E402
from tess_ui.tel import Parts  # noqa: E402

VIEWS = Path(__file__).parent.parent / "src" / "tess_ui" / "views"
SHIPPED = sorted(VIEWS.glob("*_Stylesheet.tdl"))


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


def test_the_52_shipped_stylesheets_load_with_position_maps_and_go_through_rule_sheet():
    assert len(SHIPPED) == 52
    rules = 0
    for path in SHIPPED:
        text = path.read_text(encoding="utf-8")
        got = load_marked_tdl_stylesheet(text, path.name)
        check_shape(got)
        rules += len(got["styles"])
        assert len(RuleSheet.of(got, path.name, text).rules) == len(got["styles"])
    assert rules == 288  # every rule of every shipped sheet


def test_positions_of_the_tdl_mapping_land_on_the_key_and_the_head_of_each_block():
    """Each key's position is its text, a block's the head word, a rule's `Rule`."""
    for path in SHIPPED:
        written = path.read_text(encoding="utf-8")
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
    written = sheet("Styles {\n  Rule { Widget: Button, Variant: tonal, Classes: [a], Style { Gap: 8, Background: <| x |>, Padding { Left: 4 } } }\n}\n")
    lines = written.split("\n")
    rule = load_marked_tdl_stylesheet(written, "T_Stylesheet.tdl")["styles"][0]
    assert text_at(lines, rule.val_at["widget"], 6) == "Button" and text_at(lines, rule.val_at["variant"], 5) == "tonal"
    assert text_at(lines, rule.val_at["classes"], 3) == "[a]"
    style = rule["style"]
    assert text_at(lines, style.val_at["gap"], 1) == "8" and text_at(lines, style.val_at["background"], 7) == "<| x |>"
    assert text_at(lines, style["padding"].key_at["left"], 4) == "Left" and text_at(lines, style.val_at["padding"], 7) == "Padding"


# -- (b) what the language has -----------------------------------------------------------------------------------------------


def test_a_stylesheet_is_a_styles_block_of_rule_blocks_with_title_case_keys_that_come_back_snake_case():
    m = load("Styles {\n  Rule { Widget: Button, Variant: tonal, Style { Gap: 8, Transition { Corner_Radius: 200 } } }\n}\n")
    assert m == {"styles": [{"widget": "Button", "variant": "tonal", "style": {"gap": 8, "transition": {"corner_radius": 200}}}]}
    assert list(m["styles"][0]) == ["widget", "variant", "style"]  # the order is the written order


def test_values_are_typed_and_a_slot_is_parts():
    m = load("Styles {\n  Rule {\n    Widget: Text\n    Classes: [a, b]\n    Style {\n      Opacity: 0.5\n      Clip_Children: true\n      Flex: null\n"
             "      Width: 50%\n      Height: <| a * 2 |>\n      Label: Hello <| name |>!\n      Font: \"<| not a slot |>\"\n    }\n  }\n}\n")
    style = m["styles"][0]["style"]
    assert style == {"opacity": 0.5, "clip_children": True, "flex": None, "width": "50%", "height": "<| a * 2 |>", "label": "Hello <| name |>!",
                     "font": "<| not a slot |>"}
    assert isinstance(style["height"], Parts) and isinstance(style["label"], Parts) and not isinstance(style["font"], Parts)  # a quoted string is plain text
    assert [i if isinstance(i, str) else (i.text, i.origin.file, i.origin.line, i.origin.column) for i in style["label"].items] == ["Hello ", (" name ", "T_Stylesheet.tdl", 16, 21), "!"]
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


def test_a_duplicate_key_in_a_rule_or_a_style_is_refused():
    at(fails("Styles {\n  Rule { Widget: Text, Widget: Button, Style { Gap: 1 } }\n}\n", "The key Widget is already used on line 7"), 7, 23)
    at(fails("Styles {\n  Rule { Widget: Text, Style { Gap: 1, Gap: 2 } }\n}\n", "The key Gap is already used on line 7"), 7, 39)
    at(fails("Styles {\n  Rule { Widget: Text, Style { Gap: 1 } Style { Gap: 2 } }\n}\n", "duplicate key 'style'"), 7, 40)


def test_the_marker_is_checked_in_the_metadata_block():
    err = fails("Styles { }\n", "written for Tesserae 0.5", meta='Tesserae: "0.5"')
    at(err, 4, 10)
    fails("Styles { }\n", "names the release series", meta="Tesserae: soon")
    assert load("Styles { }\n", meta="") == {"styles": []}  # optional
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


# -- (e) files, folders and the command ---------------------------------------------------------------------------------------

SMALL = "tesserae: 0.6\nstyles:\n  - {widget: Button, style: {gap: 4}}\n"




@pytest.mark.parametrize("extra", ["Seed: red\n", "Theme { Seed: red }\n"])
def test_nothing_may_follow_the_styles_block(extra):
    """A stray property or a second root block after `Styles` is an error naming the file, not ignored."""
    with pytest.raises(LoadError) as caught:
        load("Styles {\n  Rule {\n    Widget: Link\n    Style { Foreground: primary }\n  }\n}\n" + extra)
    assert caught.value.file == "T_Stylesheet.tdl" and "more than one root block" in caught.value.message
