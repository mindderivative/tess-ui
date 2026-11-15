"""Piece 2 of the TDL switch: `tesserae migrate-tdl` writes `*_View.yaml` as `*_View.tdl`, keeping comments and key order, laid out one entry to a line,
idempotent, refusing what it cannot write back, and writing the pair-target loops as `For i, it In` (`design/tdl-views.md`, `src/tess_ui/migrate_tdl.py`)."""

import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("tess_dl", reason="the TDL front end needs tess_dl (Python 3.14)")

from tess_ui import cli  # noqa: E402
from tess_ui.migrate_tdl import ConvertError, convert_view, migrate_tdl  # noqa: E402
from tess_ui.spec.nodes import load_marked  # noqa: E402
from tess_ui.spec.tdl import load_marked_tdl  # noqa: E402
from tess_ui.spec.widgets import Property, WidgetDecl  # noqa: E402
from tests.tdl_helper import normal  # noqa: E402

VIEWS = Path(__file__).parent.parent / "src" / "tess_ui" / "views"
SHIPPED = sorted(VIEWS.glob("*_View.yaml"))


def reads_equal(yaml_text, tdl_text, **kw):
    """The TDL text loads to the mapping the YAML loader makes."""
    expected = load_marked(yaml_text)
    got = load_marked_tdl(tdl_text, "T_View.tdl", **kw)
    return normal(got) == normal(expected)


def view(body, series="tesserae: 0.6\n"):
    return series + body


def conv(body, name="T", **kw):
    return convert_view(view(body), name, "T_View.yaml", **kw)


def body_of(tdl_text):
    """The text after the metadata block."""
    return tdl_text.split("---\n", 2)[2]


def make_project(tmp_path, files):
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return tmp_path


# -- (a) the shipped views ---------------------------------------------------------------------------------------------------


def test_the_61_shipped_views_convert_and_load_to_the_yaml_mapping():
    assert len(SHIPPED) == 61
    loops = 0
    for path in SHIPPED:
        text = path.read_text(encoding="utf-8")
        result = convert_view(text, path.name.removesuffix("_View.yaml"), path.name)
        assert reads_equal(text, result.text), path.name
        loops += len(re.findall(r"^\s*For \w+, \w+ In ", result.text, re.M))
    assert loops == 10


def test_the_report_of_the_shipped_views_has_no_loop_to_adjust_and_no_todo_line(tmp_path):
    for path in SHIPPED:
        (tmp_path / path.name).write_bytes(path.read_bytes())
    report = migrate_tdl(tmp_path)
    assert len(report.converted) == 61 and not report.failed and report.steps > 100
    rendered = report.render(tmp_path)
    assert "tuple" not in rendered.lower() and "adjust" not in rendered.lower()
    assert "61 files would be converted" in rendered and "nothing written" in rendered
    assert not list(tmp_path.glob("*.tdl"))  # a dry run
    for result in report.converted:
        assert result.text is not None and "TODO" not in result.text and "i_it" not in result.text and result.text.startswith("---\nTDL: 0.2\n")


def test_every_view_is_laid_out_one_entry_to_a_line_within_150_columns_unless_one_value_is_longer():
    for path in SHIPPED:
        text = convert_view(path.read_text(encoding="utf-8"), "X").text
        for line in text.splitlines():
            assert not line.startswith("\t") and (len(line) - len(line.lstrip())) % 2 == 0, (path.name, line)
            if len(line) > 150 and not line.lstrip().startswith("#"):  # a comment is not wrapped
                assert re.match(r"\s*(?:[A-Za-z_]+: |For |If )", line), (path.name, line[:60])  # one long value (a doc string, an expression), nothing wrapped badly


# -- (b) comments are kept ---------------------------------------------------------------------------------------------------

SAMPLE = """tesserae: 0.6  # the series
# A header comment.

# Second paragraph.
params:
  # the label
  label: {type: str, default: ""}  # end of the label line
  items: {type: list, default: []}
widget: Container
# above style
style:
  # inside style
  flex_direction: horizontal  # trailing
  gap: 8

  width: 100%
handlers:
  on_click: |
    # first, set
    a = 1  # trailing py
    b += 2
    # last words
    save(a, flag=b)
children:
  # first child
  - widget: Text  # the text
    name: t
    # before the if
    if: "label != ''"
    choices:
      - a
      - b  # bee
      # between
      - c
    text: "{{ label }}"
  - widget: Button
    for: i, it in enumerate(items)
    key: it['v']
    if: it['on']
    label: "Item {{ i }}"
  # trailing child comment
# the end
"""

SAMPLE_TDL = """---
TDL: 0.2
Name: Sample
Tesserae: "0.6"  # the series
---
# A header comment.

# Second paragraph.
Container {
  Params {
    # the label
    Label { Type: str, Default: "" }  # end of the label line
    Items { Type: list, Default: [] }
  }
  # above style
  Style {
    # inside style
    Flex_Direction: horizontal  # trailing
    Gap: 8

    Width: 100%
  }
  Handlers {
    On_Click {
      # first, set
      Set { Target: a, Value: <| 1 |> }  # trailing py
      Set { Target: b, Value: <| b + 2 |> }
      # last words
      Call { Action: "save", Args: [<| a |>], Flag: <| b |> }
    }
  }
  Children {
    # first child
    # before the if
    If <| label != '' |> {
      Text {  # the text
        Name: t
        Choices: [
          a,
          b,  # bee
          # between
          c,
        ]
        Text: <| label |>
      }
    }
    For i, it In <| enumerate(items) |> Key <| it['v'] |> {
      If <| it['on'] |> {
        Button {
          Label: Item <| i |>
        }
      }
    }
  }
}
# trailing child comment
# the end
"""


def test_a_file_with_comments_everywhere_converts_to_the_golden_text():
    result = convert_view(SAMPLE, "Sample", "Sample_View.yaml")
    assert result.text == SAMPLE_TDL
    assert reads_equal(SAMPLE, result.text)
    assert result.steps == 3
    assert len(result.notes) == 1 and "augmented assignment" in result.notes[0]


def test_the_same_file_with_windows_line_ends_converts_to_the_same_text_with_windows_line_ends():
    result = convert_view(SAMPLE.replace("\n", "\r\n"), "Sample", "Sample_View.yaml")
    assert result.text == SAMPLE_TDL.replace("\n", "\r\n")
    assert "\r\r" not in result.text and result.text.count("\r\n") == result.text.count("\n")
    assert reads_equal(SAMPLE.replace("\n", "\r\n"), result.text)
    byte_order_mark = convert_view("\ufeff" + SAMPLE, "Sample", "Sample_View.yaml")
    assert byte_order_mark.text == SAMPLE_TDL


def comment_lines(text):
    """The text of each comment (`# ...` to the end of the line) in order; a `#` inside a quoted string or a slot is not one."""
    found = []
    for line in text.splitlines():
        for match in re.finditer(r"""(?:^|\s)(#[^\n]*)$""", re.sub(r"\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)*'|<\|.*?\|>", '""', line)):
            found.append(match.group(1).strip())
    return found


@pytest.mark.parametrize("name", ["Button", "Dialog", "TextField"])
def test_the_comments_of_a_shipped_view_survive_in_order_and_the_header_is_exact(name):
    text = (VIEWS / f"{name}_View.yaml").read_text(encoding="utf-8")
    out = convert_view(text, name).text
    want = [c for c in comment_lines(text) if c]
    assert want and comment_lines(body_of(out)) == want
    header = [line for line in text.splitlines()[1:] if line.startswith("#")]
    top = []
    for line in body_of(out).splitlines():
        if not line.startswith("#"):
            break
        top.append(line)
    assert top == header[:len(top)] and len(top) >= 4
    for kept in header:
        assert kept in out.splitlines()


def test_the_end_of_line_comments_of_text_field_stay_on_their_lines():
    out = convert_view((VIEWS / "TextField_View.yaml").read_text(encoding="utf-8"), "TextField").text.splitlines()
    sent = next(line for line in out if "# sent to the screen reader" in line)
    assert sent.startswith("                Description: <| error if error != '' else supporting |>  # sent to the screen reader when tess_re takes it")
    glides = next(line for line in out if "# the label glides up" in line)
    assert glides.strip().startswith("Transition { X: 150, Y: 150 }  # the label glides up")
    above = out.index(next(line for line in out if line.strip().startswith("# an outlined label sits on the border")))
    assert out[above + 1].strip().startswith("Background:") and out[above].startswith(" " * 14 + "#")


# -- (c) layout --------------------------------------------------------------------------------------------------------------


def test_a_flow_collection_on_one_line_stays_on_one_line_and_one_that_is_too_long_is_opened():
    short = conv("widget: Text\nstyle: {width: 10, height: 20}\ntooltip: {text: hi, delay: 3}\n").text
    assert "  Style { Width: 10, Height: 20 }\n" in short and "  Tooltip { Text: hi, Delay: 3 }\n" in short
    long_value = "{{ " + " + ".join(["'aaaaaaaaaaaaaaaaaaaa'"] * 9) + " }}"
    text = f'widget: Text\nstyle: {{width: "{long_value}", height: 20}}\n'
    opened = conv(text).text
    assert "  Style {\n    Width: <|" in opened and "    Height: 20\n  }\n" in opened and reads_equal(view(text), opened)


def test_a_long_list_is_wrapped_at_150_columns_and_a_block_list_of_scalars_is_a_list_property():
    items = [f"item_number_{i}" for i in range(30)]
    text = "widget: Text\nchoices: [" + ", ".join(items) + "]\nother:\n  - a\n  - b\n"
    out = conv(text).text
    lines = out.splitlines()
    wrapped = [line for line in lines if re.match(r"\s*(Choices: \[|item_number|\s)", line) and "Other" not in line]
    assert len(wrapped) >= 3 and all(len(line) <= 150 for line in lines)
    assert lines[lines.index(wrapped[0]) + 1].startswith(" " * (2 + len("Choices: [")))  # continuation lines line up under the first item
    assert "  Other: [a, b]\n" in out and reads_equal(view(text), out)


def test_blank_lines_between_entries_are_kept_and_one_run_of_them_is_one_blank_line():
    out = conv("widget: Container\nstyle:\n  gap: 1\n\n\n\n  width: 2\n").text
    assert "    Gap: 1\n\n    Width: 2\n" in out


def test_values_keep_their_types_and_percent_widths_and_templates_are_written_plainly():
    text = ("widget: Text\na: true\nb: false\nc: null\nd: 3\ne: -0.5\nf: yes\ng: 'true'\nh: 50%\ni: '10'\nj: 'a b'\nk: ''\nl: [a, 1, 'x y', true]\n"
            "m: 'Battery {{ level }}%'\nn: '{{ a }}{{ b }}'\no: 'it''s'\np: 'tab\\there'\nq: []\nr: {}\n")
    out = conv(text).text
    for line in ("  A: true", "  B: false", "  C: null", "  D: 3", "  E: -0.5", "  F: true", '  G: "true"', "  H: 50%", '  I: "10"', '  J: "a b"',
                 '  K: ""', '  L: [a, 1, "x y", true]', "  M: Battery <| level |>%", "  N: <| a |><| b |>", '  O: "it\'s"', "  Q: []", "  R { }"):
        assert line in out.splitlines(), line
    assert reads_equal(view(text), out)


# -- (d) the language: wrappers, steps, nodes --------------------------------------------------------------------------------


def test_a_for_with_an_if_on_one_node_writes_the_for_outside_the_if_and_loads_back_the_same():
    text = ("widget: Container\nchildren:\n  - widget: Text\n    name: row\n    for: item in items\n    key: item['id']\n    if: item['on']\n    text: '{{ item }}'\n"
            "  - widget: Text\n    key_only: 1\n    if: shown\n  - widget: Text\n    for: n in range(3)\n")
    out = conv(text).text
    assert ("    For item In <| items |> Key <| item['id'] |> {\n      If <| item['on'] |> {\n        Text {\n          Name: row\n          Text: <| item |>\n"
            "        }\n      }\n    }\n") in out
    assert "    For n In <| range(3) |> Key <| None |> {\n      Text { }\n    }\n" in out
    assert reads_equal(view(text), out)
    node = load_marked_tdl(out, "T_View.tdl")["children"][0]
    assert (node["for"], node["key"], node["if"]) == ("item in items", "item['id']", "item['on']")


def test_handlers_become_set_and_call_steps_and_a_bare_action_stays_a_property():
    text = ("widget: Button\nhandlers:\n  on_click: save\n  on_hover_enter: surface.dismiss\n  on_change: 'open = not open; on_toggle()'\n"
            "  on_key: |\n    a = (b) if c else d\n    count += 2 * n\n    pick(row['ref'], index=i, kind='x')\n    nav.go()\n")
    result = conv(text)
    out = result.text
    assert "    On_Click: save\n    On_Hover_Enter: surface.dismiss\n" in out
    assert "    On_Change {\n      Set { Target: open, Value: <| not open |> }\n      Call { Action: \"on_toggle\" }\n    }\n" in out
    assert "Set { Target: a, Value: <| (b) if c else d |> }" in out  # the expression as the author wrote it
    assert "Set { Target: count, Value: <| count + 2 * n |> }" in out
    assert "Call { Action: \"pick\", Args: [<| row['ref'] |>], Index: <| i |>, Kind: <| 'x' |> }" in out and 'Call { Action: "nav.go" }' in out
    assert result.steps == 6 and reads_equal(view(text), out)


def test_a_single_step_event_is_one_line_and_a_view_own_on_param_is_text():
    out = conv("widget: Container\nchildren:\n  - widget: Pick\n    on_pick: 'which = pick'\n    handlers: {on_click: 'open = False'}\n").text
    assert '      On_Pick: "which = pick"\n' in out
    assert "        On_Click { Set { Target: open, Value: <| False |> } }\n" in out


def test_a_list_of_maps_is_a_block_of_item_blocks_and_a_map_handler_is_steps():
    text = "widget: Text\ntooltip:\n  text: hi\n  actions:\n    - {label: A, on_click: 'a()'}\n    - {label: B, on_click: b}\n    - label: C\n      on_click: 'x = 1; y()'\n"
    out = conv(text).text
    assert "    Item { Label: A, On_Click { Set" not in out
    assert "      Item {\n        Label: A\n        On_Click { Call { Action: \"a\" } }\n      }\n" in out and "      Item { Label: B, On_Click: b }\n" in out
    assert "        On_Click {\n          Set { Target: x, Value: <| 1 |> }\n          Call { Action: \"y\" }\n        }\n" in out
    assert reads_equal(view(text), out)


def test_a_property_the_widget_declares_as_a_node_is_a_block_holding_the_node():
    decl = WidgetDecl("Panel", {"header": Property("node"), "items": Property("nodes")}, container=True)
    resolver = {"Panel": decl}.get
    text = "widget: Panel\nheader: {widget: Text, text: hi}\nitems:\n  - {widget: Text, name: a}\n  - {widget: Icon, icon: x}\n"
    out = conv(text, resolver=resolver).text
    assert "  Header {\n    Text {\n      Text: hi\n    }\n  }\n" in out and "  Items {\n    Text {\n      Name: a\n    }\n" in out
    assert reads_equal(view(text), out, resolver=resolver)
    unknown = conv(text)  # without the declaration the converter says it does not know
    assert any("looks like a node" in n for n in unknown.notes)


def test_empty_children_handlers_and_nodes_are_written_empty():
    text = "widget: Container\nchildren: []\nhandlers: {}\nstyle: {}\n"
    out = conv(text).text
    assert "  Children { }\n  Handlers { }\n  Style { }\n" in out and reads_equal(view(text), out)


# -- (e) the metadata --------------------------------------------------------------------------------------------------------


def test_the_metadata_names_the_view_by_its_name_key_or_else_by_its_file():
    assert conv("widget: Text\n", name="Foo").text.startswith('---\nTDL: 0.2\nName: Foo\nTesserae: "0.6"\n---\n')
    assert conv("name: Bound\nwidget: Text\n", name="Foo").text.startswith('---\nTDL: 0.2\nName: Bound\nTesserae: "0.6"\n---\n')
    assert "  Name: Bound\n" in conv("name: Bound\nwidget: Text\n", name="Foo").text  # and the node keeps its own name
    plain = convert_view("widget: Text\n", "Foo", "Foo_View.yaml").text  # the series line is optional
    assert plain == "---\nTDL: 0.2\nName: Foo\n---\nText { }\n"
    with pytest.raises(ConvertError, match="cannot be a TDL Name"):
        convert_view("widget: Text\n", "My-View", "My-View_View.yaml")


# -- (f) refusals say file, line and what to write ---------------------------------------------------------------------------


@pytest.mark.parametrize("body, line, message, hint", [
    ("widget: Text\nmaxLines: 1\n", 3, "the key 'maxLines' is not lower snake_case", "write 'max_lines'"),
    ("widget: Text\nMax_Lines: 1\n", 3, "not lower snake_case", "write 'max_lines'"),
    ("widget: Text\nstyle:\n  a-b: 1\n", 4, "not lower snake_case", None),
    ("widget: Text\nif_: 1\nfor: x\n", 4, "'for:' reads 'name in expression'", "write for: item in items"),
    ("widget: Text\nkey: k\n", 3, "a key: without a for:", None),
    ("widget: Button\nhandlers:\n  on_click: |\n    a = 1\n    if a:\n      b()\n", 6, "no step form", None),
    ("widget: Button\nhandlers:\n  on_click: 'a = b = 1'\n", 4, "a Set writes one plain name", None),
    ("widget: Button\nhandlers:\n  on_click: 'a, b = 1, 2'\n", 4, "a Set writes one plain name", None),
    ("widget: Button\nhandlers:\n  on_click: \"items['x'] = 1\"\n", 4, "a Set writes one plain name", None),
    ("widget: Button\nhandlers:\n  on_click: 'a = 1; save'\n", 4, "a bare name among statements", "write the call: save()"),
    ("widget: Button\nhandlers:\n  on_click: 'go(*a)'\n", 4, "a Call takes plain arguments", None),
    ("widget: Button\nhandlers:\n  on_click: 'go(action=1)'\n", 4, "clashes with the Call's own Action", None),
    ("widget: Button\nhandlers:\n  on_click: 'items[0]()'\n", 4, "a Call names an action", None),
    ("widget: Button\nhandlers:\n  on_click: 'a = 1 +'\n", 4, "the handler is not Python statements", None),
    ("widget: Text\ntext: 'a, {{ b }}'\n", 3, "text with a slot that cannot be written unquoted", "make the whole value one slot"),
    ("widget: Text\ntext: 'oops {{ b'\n", 3, "is never closed", None),
    ("widget: Text\nwhen: 2020-01-01\n", 3, "a value of type date has no TDL form", "quote it as text"),
    ("widget: Container\nchildren:\n  - text\n", 4, "holds nodes", None),
    ("widget: Container\nchildren:\n  - widget: Text\n  - name: x\n", 5, "a node needs a widget:", None),
    ("widget: Text\nstyle:\n  a: [[1], [2]]\n", 4, "a list that holds lists", None),
    ("widget: Text\nx: &a 1\ny: *a\nstyle: &s {a: 1}\nz: *s\n", 4, "an anchor or alias has no TDL form", None),
    ("kind: Text\n", 2, "not a view in the current syntax", "tesserae migrate-yaml"),
    ("widget: Text\nwidget2: [\n", 4, "YAML", None),  # where PyYAML finds the list is never closed: the end of the file
    ("widget: Text\na: 1\na: 2\n", 4, "duplicate key 'a'", None),
    ("widget: Container\nchildren:\n  - widget: Text\n    if: 'a |> b'\n", 5, "cannot sit in a slot", None),
    ("widget: Container\nchildren:\n  - widget: Text\n    for: In in xs\n", 5, "cannot be the variable", None),
    ("widget: Text\nif: true\n", 3, "'if:' is text", None),
])
def test_a_refusal_names_the_line_and_says_what_to_write(body, line, message, hint):
    with pytest.raises(ConvertError) as caught:
        conv(body)
    error = caught.value
    assert message in error.message, error
    assert error.line == line, (error.line, str(error))
    if hint:
        assert hint in (error.hint or ""), error


def test_a_file_that_is_not_a_current_view_is_refused_with_the_series_message():
    with pytest.raises(ConvertError, match="written for Tesserae 0.5") as caught:
        convert_view("tesserae: 0.5\nwidget: Text\n", "T", "T_View.yaml")
    assert "migrate-yaml" in str(caught.value) and caught.value.line == 1
    with pytest.raises(ConvertError, match="must be the first line"):
        convert_view("widget: Text\ntesserae: 0.6\n", "T", "T_View.yaml")


# -- (g) files and folders ---------------------------------------------------------------------------------------------------

BUTTON = "tesserae: 0.6\n# A button.\nparams:\n  label: {type: str, default: ''}\nwidget: Text\ntext: '{{ label }}'\n"
CHECK = "tesserae: 0.6\nwidget: Container\nhandlers:\n  on_click: 'a = 1; go(b)'\nchildren:\n  - widget: Text\n    for: i, it in enumerate(items)\n    text: '{{ it }}'\n"


def test_a_dry_run_reports_and_writes_nothing(tmp_path):
    make_project(tmp_path, {"Views/Button_View.yaml": BUTTON, "Views/Check_View.yaml": CHECK})
    report = migrate_tdl(tmp_path)
    assert [r.status for r in report.results] == ["converted", "converted"] and not report.written
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == ["Button_View.yaml", "Check_View.yaml"]
    text = report.render(tmp_path)
    assert "would convert" in text and "Views/Button_View.yaml -> Views/Button_View.tdl" in text and "(2 steps)" in text
    assert "2 files would be converted, 2 steps would be written" in text
    assert "nothing written: use --write" in text


def test_write_writes_the_tdl_files_beside_the_yaml_and_keeps_the_yaml(tmp_path):
    make_project(tmp_path, {"Views/Button_View.yaml": BUTTON, "Views/Check_View.yaml": CHECK})
    report = migrate_tdl(tmp_path, write=True)
    assert report.written and not report.failed
    for name in ("Button", "Check"):
        assert (tmp_path / "Views" / f"{name}_View.yaml").is_file()
        written = (tmp_path / "Views" / f"{name}_View.tdl").read_bytes().decode("utf-8")
        assert written == convert_view((tmp_path / "Views" / f"{name}_View.yaml").read_text(encoding="utf-8"), name).text
    assert (tmp_path / "Views" / "Button_View.tdl").read_text(encoding="utf-8").splitlines()[5] == "# A button."
    text = report.render(tmp_path)
    assert "converted     Views/Button_View.yaml -> Views/Button_View.tdl" in text and "2 files converted, 2 steps written" in text
    assert text.endswith("written")


def test_a_second_run_changes_nothing(tmp_path):
    make_project(tmp_path, {"Button_View.yaml": BUTTON, "Check_View.yaml": CHECK})
    migrate_tdl(tmp_path, write=True)
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()}
    again = migrate_tdl(tmp_path, write=True)
    assert [r.status for r in again.results] == ["current", "current"] and not again.converted
    assert {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in tmp_path.iterdir()} == before
    assert "2 current" in again.render(tmp_path)
    assert "0 files converted, 0 steps written" in again.render(tmp_path)
    assert convert_view(BUTTON, "Button").text == convert_view(BUTTON, "Button").text


def test_it_never_overwrites_a_different_file_without_write(tmp_path):
    make_project(tmp_path, {"Button_View.yaml": BUTTON, "Button_View.tdl": "---\nTDL: 0.2\nName: Button\n---\nText { }\n"})
    dry = migrate_tdl(tmp_path)
    assert dry.results[0].status == "converted" and any("exists and differs" in n for n in dry.results[0].notes)
    assert (tmp_path / "Button_View.tdl").read_text(encoding="utf-8") == "---\nTDL: 0.2\nName: Button\n---\nText { }\n"
    migrate_tdl(tmp_path, write=True)
    assert "Params" in (tmp_path / "Button_View.tdl").read_text(encoding="utf-8")


def test_remove_source_deletes_the_yaml_only_with_write_and_only_for_files_that_were_written(tmp_path):
    make_project(tmp_path, {"Button_View.yaml": BUTTON, "Bad_View.yaml": "tesserae: 0.6\nwidget: Text\nmaxLines: 1\n"})
    migrate_tdl(tmp_path, remove_source=True)  # no write: nothing happens
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Bad_View.yaml", "Button_View.yaml"]
    report = migrate_tdl(tmp_path, write=True, remove_source=True)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Bad_View.yaml", "Button_View.tdl"]  # the one that failed is left alone
    assert [r.status for r in report.results] == ["failed", "converted"] and report.results[1].removed
    assert "removed" in report.render(tmp_path)
    assert [r.status for r in migrate_tdl(tmp_path, write=True, remove_source=True).results] == ["failed"]  # the removed YAML is not looked for again
    make_project(tmp_path, {"Button_View.yaml": BUTTON})  # a file whose TDL is already current has its YAML removed too
    current = migrate_tdl(tmp_path, write=True, remove_source=True)
    assert [(r.path.name, r.status, r.removed) for r in current.results] == [("Bad_View.yaml", "failed", False), ("Button_View.yaml", "current", True)]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Bad_View.yaml", "Button_View.tdl"]


def test_a_file_that_fails_is_reported_with_its_line_and_the_others_are_still_written(tmp_path):
    make_project(tmp_path, {"Bad_View.yaml": "tesserae: 0.6\nwidget: Text\nmaxLines: 1\n", "Good_View.yaml": BUTTON})
    report = migrate_tdl(tmp_path, write=True)
    assert [r.status for r in report.results] == ["failed", "converted"]
    assert (tmp_path / "Good_View.tdl").is_file() and not (tmp_path / "Bad_View.tdl").exists()
    assert report.failed[0].line == 3
    assert "failed    Bad_View.yaml:3: the key 'maxLines' is not lower snake_case (write 'max_lines')" in report.render(tmp_path)
    assert "1 failed" in report.render(tmp_path)


def test_components_are_skipped_with_a_note_and_stylesheets_and_themes_are_converted(tmp_path):  # stylesheets since piece 4, themes since piece 5
    make_project(tmp_path, {"A_Stylesheet.yaml": "tesserae: 0.6\nstyles: []\n", "B_Theme.yaml": "tesserae: 0.6\nseed: blue\n",
                            "C_Component.yaml": "kind: Text\n", "notes.yaml": "a: 1\n", "D_View.yaml": BUTTON})
    report = migrate_tdl(tmp_path, write=True)
    assert [(r.path.name, r.status) for r in report.results] == [
        ("A_Stylesheet.yaml", "converted"), ("B_Theme.yaml", "converted"), ("C_Component.yaml", "skipped"), ("D_View.yaml", "converted")]
    assert "only views, stylesheets and themes are converted" in (report.results[2].error or "")
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        ["A_Stylesheet.yaml", "A_Stylesheet.tdl", "B_Theme.yaml", "B_Theme.tdl", "C_Component.yaml", "notes.yaml", "D_View.yaml", "D_View.tdl"])
    assert "1 skipped" in report.render(tmp_path) and migrate_tdl(tmp_path / "C_Component.yaml").results[0].status == "skipped"


def test_a_single_file_is_converted_and_a_file_of_another_kind_is_refused(tmp_path):
    make_project(tmp_path, {"Button_View.yaml": BUTTON, "other.yaml": "a: 1\n"})
    report = migrate_tdl(tmp_path / "Button_View.yaml", write=True)
    assert report.results[0].status == "converted" and (tmp_path / "Button_View.tdl").is_file()
    with pytest.raises(ValueError, match="other.yaml is not a \\*_View.yaml or \\*_Stylesheet.yaml file"):
        migrate_tdl(tmp_path / "other.yaml")


def test_a_project_folder_resolves_its_own_widgets_for_node_properties(tmp_path):
    make_project(tmp_path, {
        "Panel_View.yaml": "tesserae: 0.6\nparams:\n  header: {type: node}\n  items: {type: nodes}\nwidget: Container\n",
        "Use_View.yaml": "tesserae: 0.6\nwidget: Panel\nheader: {widget: Text, text: hi}\nitems:\n  - {widget: Text, name: a}\n"})
    report = migrate_tdl(tmp_path, write=True)
    assert not report.failed
    out = (tmp_path / "Use_View.tdl").read_text(encoding="utf-8")
    assert "  Header {\n    Text {\n      Text: hi\n    }\n  }\n" in out and not any(r.notes for r in report.results)


def test_an_empty_folder_says_so(tmp_path):
    report = migrate_tdl(tmp_path)
    assert report.results == [] and "no view or stylesheet files found" in report.render(tmp_path)


# -- (h) the command ---------------------------------------------------------------------------------------------------------


def test_the_command_reports_writes_and_says_what_goes_with_what(tmp_path, capsys):
    make_project(tmp_path, {"Button_View.yaml": BUTTON, "Check_View.yaml": CHECK})
    assert cli.main(["migrate-tdl", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "would convert Button_View.yaml -> Button_View.tdl" in out and not list(tmp_path.glob("*.tdl"))
    assert "tuple" not in out.lower()
    assert cli.main(["migrate-tdl", str(tmp_path), "--write", "--remove-source"]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Button_View.tdl", "Check_View.tdl"]
    assert cli.main(["migrate-tdl", str(tmp_path / "Button_View.tdl")]) == 2  # not a *_View.yaml or *_Stylesheet.yaml file
    assert "is not a *_View.yaml or *_Stylesheet.yaml file" in capsys.readouterr().err


def test_the_command_exits_1_when_a_file_fails_and_2_for_a_mistake(tmp_path, capsys):
    make_project(tmp_path, {"Bad_View.yaml": "tesserae: 0.6\nwidget: Text\nmaxLines: 1\n"})
    assert cli.main(["migrate-tdl", str(tmp_path)]) == 1
    assert "Bad_View.yaml:3: the key 'maxLines'" in capsys.readouterr().out
    assert cli.main(["migrate-tdl", str(tmp_path / "missing")]) == 2
    assert "does not exist" in capsys.readouterr().err
    assert cli.main(["migrate-tdl", str(tmp_path), "--remove-source"]) == 2
    assert "--remove-source goes with --write" in capsys.readouterr().err


def test_a_crlf_file_is_written_with_crlf_and_a_second_run_leaves_it_alone(tmp_path):
    make_project(tmp_path, {"Sample_View.yaml": SAMPLE.replace("\n", "\r\n")})
    migrate_tdl(tmp_path, write=True)
    written = (tmp_path / "Sample_View.tdl").read_bytes()
    assert written == SAMPLE_TDL.replace("\n", "\r\n").encode("utf-8") and b"\r\r" not in written
    again = migrate_tdl(tmp_path, write=True)
    assert [r.status for r in again.results] == ["current"] and (tmp_path / "Sample_View.tdl").read_bytes() == written


def test_the_command_says_what_is_missing_when_tess_dl_cannot_be_imported(tmp_path, capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "tess_ui.migrate_tdl", None)  # an import of it now fails, as without tess_dl
    assert cli.main(["migrate-tdl", str(tmp_path)]) == 2
    assert "migrate-tdl needs the `tess_dl` package, which needs Python 3.14" in capsys.readouterr().err


def test_backslashes_in_text_and_an_empty_or_numeric_handler_are_written_as_the_text_they_are():
    text = "widget: Button\nlabel: 'a\\\\b'\npath: 'C:\\temp'\nhandlers:\n  on_click: ''\n  on_hover_enter: 5\n  on_key: ~\n"
    out = conv(text).text
    assert '  Label: "a\\\\\\\\b"\n' in out and '  Path: "C:\\\\temp"\n' in out
    assert '    On_Click: ""\n    On_Hover_Enter: 5\n    On_Key: null\n' in out
    assert reads_equal(view(text), out)


def test_a_conversion_that_does_not_read_back_the_same_is_refused_and_says_where(monkeypatch):
    import tess_ui.migrate_tdl as module

    monkeypatch.setattr(module, "_scalar", lambda value: "99")  # a converter that writes a wrong value
    with pytest.raises(ConvertError, match=r"does not read back as the same view: style\.gap: .* read back as") as caught:
        conv("widget: Container\nstyle:\n  gap: 8\n")
    assert "no TDL form the converter knows" in (caught.value.hint or "")
