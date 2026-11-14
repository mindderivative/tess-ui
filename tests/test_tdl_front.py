"""Piece 1 of the TDL switch: the TDL front end reads a view into the same mapping with positions that the YAML loader makes, and its errors name the
`.tdl` file, line and column in the same words (`design/tdl-views.md`)."""

import ast
from pathlib import Path

import pytest
import yaml

from tess_ui.spec import tdl as T
from tess_ui.spec.nodes import LoadError, PMap, PSeq, load_marked, parse_data, parse_view
from tess_ui.spec.widgets import Property, WidgetDecl
from tests.tdl_helper import with_single_variable, yaml_to_tdl

VIEWS = sorted((Path(__file__).parent.parent / "src" / "tess_ui" / "views").glob("*_View.yaml"))


def view(body, meta='Tesserae: "0.6"'):
    """A TDL file with the usual metadata around `body`."""
    return f"---\nTDL: 0.1\nName: T\n{meta}\n---\n{body}"


def load(body, **kw):
    return T.load_marked_tdl(view(body), "T_View.tdl", **kw)


def fails(body, message, *, text=None, **kw):
    with pytest.raises(LoadError) as caught:
        T.load_marked_tdl(view(body) if text is None else text, "T_View.tdl", **kw)
    assert message in str(caught.value), str(caught.value)
    return caught.value


def at(err, line, column):
    """The error is at `line` and (0-based) `column` of `T_View.tdl`."""
    assert (err.file, err.line, err.column) == ("T_View.tdl", line, column), (err.file, err.line, err.column, str(err))


# -- (a) the shipped views -------------------------------------------------------------------------------------------------


def normal(data):
    """The mapping as plain data; handler texts through `ast`, which only changes their spacing (the front end writes `a = b; c(d)`)."""

    def handler(text):
        try:
            return "; ".join(ast.unparse(s) for s in ast.parse(text.strip()).body)
        except SyntaxError:
            return text

    def walk(item, key=None):
        if isinstance(item, dict):
            if key == "handlers":
                return {k: handler(v) if isinstance(v, str) else walk(v) for k, v in item.items()}
            return {k: walk(v, k) for k, v in item.items()}
        if isinstance(item, list):
            return [walk(v) for v in item]
        return item

    return walk(data)


def test_every_shipped_view_read_as_tdl_equals_the_yaml_mapping():
    assert len(VIEWS) == 61
    pairs = []
    for path in VIEWS:
        text = path.read_text(encoding="utf-8")
        expected = load_marked(text)
        pairs += with_single_variable(expected)
        tdl_text = yaml_to_tdl(text, path.name.removesuffix("_View.yaml"))
        got = T.load_marked_tdl(tdl_text, path.name.replace(".yaml", ".tdl"))
        assert normal(got) == normal(expected), path.name
    assert len(pairs) == 10  # the loops with a pair target, which the helper writes with one variable (the plan's list)


def check_shape(item):
    if isinstance(item, PMap):
        assert set(item.key_at) == set(item.val_at) == set(item)
        assert isinstance(item.at, tuple)
        for sub in item.values():
            check_shape(sub)
    elif isinstance(item, PSeq):
        assert len(item.item_at) == len(item)
        for sub in item:
            check_shape(sub)


def test_the_tdl_mapping_has_the_same_shape_of_position_maps():
    """Every mapping the front end makes has `at`, `key_at` and `val_at` for exactly its keys, every list `at` and `item_at` for its items."""
    for path in VIEWS[:12]:
        check_shape(T.load_marked_tdl(yaml_to_tdl(path.read_text(encoding="utf-8"), "X"), "X_View.tdl"))


def test_a_converted_view_goes_through_the_node_parser_to_the_same_tree():
    path = next(p for p in VIEWS if p.name == "Button_View.yaml")
    text = path.read_text(encoding="utf-8")
    want = parse_view(text, path.name)
    tdl_text = yaml_to_tdl(text, "Button")
    got = parse_data(T.load_marked_tdl(tdl_text, "Button_View.tdl"), tdl_text, "Button_View.tdl")

    def shape(node):
        return (node.id, node.widget, node.name, sorted(node.props), sorted(node.style), sorted(node.handlers), [shape(c) for c in node.children])

    assert shape(got.root) == shape(want.root)
    assert sorted(got.params) == sorted(want.params)


# -- (b) what the language has ---------------------------------------------------------------------------------------------


def test_a_node_is_a_block_headed_by_its_widget_and_keys_come_back_snake_case():
    m = load("Text {\n  Name: label\n  Max_Lines: 2\n  Typography_Role: body\n  Style { Flex_Direction: horizontal }\n  A11y { Value_Min: 1 }\n}\n")
    assert m == {"widget": "Text", "name": "label", "max_lines": 2, "typography_role": "body", "style": {"flex_direction": "horizontal"},
                 "a11y": {"value_min": 1}}


def test_values_are_typed_as_yaml_types_them_but_without_its_surprises():
    m = load('Text {\n  A: true\n  B: false\n  C: null\n  D: 3\n  E: -0.5\n  F: yes\n  G: "true"\n  H: 50%\n  I: [a, 1, "x y"]\n}\n')
    assert m == {"widget": "Text", "a": True, "b": False, "c": None, "d": 3, "e": -0.5, "f": "yes", "g": "true", "h": "50%", "i": ["a", 1, "x y"]}


def test_crlf_and_a_byte_order_mark_read_the_same_and_positions_stay_true():
    body = 'Container {\n  Name: root\n  Children {\n    Text { Text: "a" }\n  }\n}\n'
    plain = T.load_marked_tdl(view(body), "T_View.tdl")
    crlf = T.load_marked_tdl("\ufeff" + view(body).replace("\n", "\r\n"), "T_View.tdl")
    assert plain == crlf
    assert plain["children"][0].at == crlf["children"][0].at == (9, 4)  # the metadata is five lines
    err = fails("Container {\n  Max_lines: 1\n}\n", "not a Title_Case key", text="\ufeff" + view("Container {\n  Max_lines: 1\n}\n").replace("\n", "\r\n"))
    at(err, 7, 2)
    assert err.render().splitlines()[1].endswith("  Max_lines: 1")


def test_comments_are_skipped_wherever_they_stand():
    m = load("# a head\nContainer { # after the brace\n  # before a key\n  Name: root # after a value\n  Children {\n    # between\n    Text { Text: a }\n  }\n"
             "  Handlers {\n    # before an event\n    On_Click: save # after\n  }\n}\n# a tail\n")
    assert m == {"widget": "Container", "name": "root", "children": [{"widget": "Text", "text": "a"}], "handlers": {"on_click": "save"}}


def test_a_slot_is_the_template_string_and_text_with_a_slot_is_a_template():
    m = load('Text {\n  Text: <| level |>\n  Label: Battery <| level |>%\n  Hint: "a <| plain |> string"\n  Tail: <| a |> and <| b |>\n}\n')
    assert m == {"widget": "Text", "text": "{{ level }}", "label": "Battery {{ level }}%", "hint": "a <| plain |> string", "tail": "{{ a }} and {{ b }}"}


def test_braces_quotes_and_pipes_inside_a_slot_are_ordinary_text():
    m = load("Text {\n  Text: <| {'a': {'b': 1}}['a']['b'] |>\n  Label: <| \"}}\" + x |>\n  Hint: <| a if b else {'k': 'it\\'s'} |>\n  Pipe: <| a | b |>\n}\n")
    assert m["text"] == "{{ {'a': {'b': 1}}['a']['b'] }}"
    assert m["label"] == '{{ "}}" + x }}'
    assert m["hint"] == "{{ a if b else {'k': 'it\\'s'} }}"
    assert m["pipe"] == "{{ a | b }}"


def test_a_slot_is_not_read_in_a_comment():
    assert load("Text { # <| not a slot, and { unbalanced\n  Text: a\n}\n") == {"widget": "Text", "text": "a"}


def test_if_and_for_wrap_a_node_and_are_set_on_it_again():
    m = load("Container {\n  Children {\n    For item In <| items |> Key <| item['id'] |> {\n      If <| item['on'] |> {\n"
             "        Text { Name: row, Text: <| item['label'] |> }\n      }\n    }\n  }\n}\n")
    node = m["children"][0]
    assert node == {"widget": "Text", "name": "row", "text": "{{ item['label'] }}", "for": "item in items", "key": "item['id']", "if": "item['on']"}
    assert list(node.key_at) == list(node.val_at)


def test_a_for_without_a_real_key_has_no_key_and_an_if_alone_is_fine():
    m = load("Container {\n  Children {\n    For n In <| range(3) |> Key <| None |> {\n      Text { Text: <| n |> }\n    }\n    If <| shown |> { Text { Text: b } }\n  }\n}\n")
    assert m["children"][0] == {"widget": "Text", "text": "{{ n }}", "for": "n in range(3)"}
    assert m["children"][1] == {"widget": "Text", "text": "b", "if": "shown"}


def test_the_condition_loop_and_key_are_trimmed_expressions_with_true_positions():
    text = view("Container {\n  Children {\n    For n In <|  range(3)  |> Key <| n |> {\n      Text { }\n    }\n  }\n}\n")
    node = T.load_marked_tdl(text, "T_View.tdl")["children"][0]
    line = text.splitlines()[7]
    assert node["for"] == "n in range(3)"
    # the position of the `for:` text is chosen so that the parser's offset of the iterable (after `n in `) lands on `range`
    assert node.val_at["for"][0] == 8 and node.val_at["for"][1] + len("n in ") == line.index("range")
    assert node.val_at["key"] == (8, line.index("n |>"))
    assert node.key_at["for"] == (8, line.index("For")) and node.key_at["key"] == (8, line.index("Key"))


def test_a_for_outside_an_if_only_and_one_of_each():
    fails("Container {\n  Children {\n    If <| a |> { For n In <| xs |> Key <| n |> { Text { } } }\n  }\n}\n", "a For outside the If")
    fails("Container {\n  Children {\n    If <| a |> { If <| b |> { Text { } } }\n  }\n}\n", "at most one For and one If")
    fails("Container {\n  Children {\n    If <| a |> { Text { } } Else { Text { } }\n  }\n}\n", "has no Else")
    fails("Container {\n  Children {\n    If <| a |> { Text { } Text { } }\n  }\n}\n", "an If holds exactly one node")


def test_handlers_are_set_and_call_steps_in_order_and_an_action_name_is_a_property():
    m = load('Button {\n  Handlers {\n    On_Click {\n      Set { Target: open, Value: <| not open |> }\n      # a comment between steps\n'
             '      Call { Action: "on_toggle" }\n      Call { Action: surface.dismiss }\n'
             '      Call { Action: "pick", Args: [<| row[\'ref\'] |>, <| 2 |>], Index: <| i |>, Mode: <| \'fast\' |> }\n    }\n    On_Hover_Enter: hover\n  }\n}\n')
    assert m["handlers"] == {"on_click": "open = not open; on_toggle(); surface.dismiss(); pick(row['ref'], 2, index=i, mode='fast')", "on_hover_enter": "hover"}
    assert m["handlers"].key_at["on_hover_enter"][0] == 15


def test_a_handler_text_compiles_in_the_runtime_and_a_hover_event_is_known():
    text = view("Container {\n  Handlers {\n    On_Click {\n      Set { Target: n, Value: <| n + 1 |> }\n      Set { Target: cmd, Value: <| str(n) |> }\n      Call { Action: save }\n    }\n  }\n}\n")
    doc = parse_data(T.load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")
    assert doc.root.handlers["on_click"].statements is not None
    assert doc.root.handlers["on_click"].action is None


def test_a_map_is_a_block_and_a_list_of_maps_is_a_block_of_item_blocks():
    m = load('Text {\n  Tooltip {\n    Text: "hi"\n    Actions {\n      Item { Label: "A", On_Click { Call { Action: a } } }\n      Item { Label: "B", On_Click: b }\n    }\n  }\n'
             "  State { Open: false, Count: 0 }\n}\n")
    assert m["tooltip"] == {"text": "hi", "actions": [{"label": "A", "on_click": "a()"}, {"label": "B", "on_click": "b"}]}
    assert m["state"] == {"open": False, "count": 0}
    assert isinstance(m["tooltip"]["actions"], PSeq)


def test_a_property_the_widget_declares_as_a_node_or_nodes_is_read_as_nodes():
    decl = WidgetDecl("Panel", {"header": Property("node"), "items": Property("nodes")}, container=True)

    def resolver(name):
        return decl if name == "Panel" else None

    m = load("Panel {\n  Header { Text { Text: hi } }\n  Items {\n    Text { Text: a }\n    Text { Text: b }\n  }\n  Style { Gap: 1 }\n}\n", resolver=resolver)
    assert m == {"widget": "Panel", "header": {"widget": "Text", "text": "hi"}, "items": [{"widget": "Text", "text": "a"}, {"widget": "Text", "text": "b"}],
                 "style": {"gap": 1}}
    fails("Panel {\n  Header { Text { } Text { } }\n}\n", "'Header' holds one node", resolver=resolver)


def test_the_marker_is_checked_as_the_first_line_of_a_yaml_file_is():
    fails("Text { }\n", "written for Tesserae 0.5", text=view("Text { }\n", 'Tesserae: "0.5"'))
    fails("Text { }\n", "written for Tesserae 9.1", text=view("Text { }\n", 'Tesserae: "9.1"'))
    err = fails("Text { }\n", "write `Tesserae: 0.6`", text=view("Text { }\n", "Tesserae: soon"))
    at(err, 4, 10)
    assert T.load_marked_tdl(view("Text { }\n", "Tesserae: 0.6"), "T_View.tdl") == {"widget": "Text"}  # an unquoted 0.6 is the series too
    assert T.load_marked_tdl(view("Text { }\n", ""), "T_View.tdl") == {"widget": "Text"}  # the key is optional, as in YAML
    err = fails("Text { }\n", "no metadata key 'Sheet'", text=view("Text { }\n", "Sheet: x"))
    at(err, 4, 0)


# -- errors: the file, the line, the column ---------------------------------------------------------------------------------


def test_a_syntax_error_from_tess_dl_names_the_tdl_file_line_and_column_and_says_slot_the_new_way():
    err = fails("Container {\n  Children {\n    Text { }\n", "This block is never closed")
    at(err, 7, 11)
    assert "Add the missing }" in str(err) and "T_View.tdl:7:12: error:" in str(err)
    err = fails("Text {\n  Text: <| level\n}\n", "this '<|' has no '|>' on its line")
    at(err, 7, 8)
    err = fails("Container {\n  If <| a |>\n}\n", "An If needs", )
    assert "{{" not in str(err) and "<|" in str(err)
    err = fails("Text {\n  Text: <|  |>\n}\n", "This slot is empty")
    at(err, 7, 8)


def test_a_pair_target_is_refused_with_a_hint():
    err = fails("Container {\n  Children {\n    For i, it In <| enumerate(items) |> Key <| i |> {\n      Text { }\n    }\n  }\n}\n", "For is missing In")
    assert "one variable" in str(err)
    at(err, 8, 9)


def test_a_key_that_is_not_title_case_says_what_to_write():
    for bad, good in (("max_lines", "Max_Lines"), ("maxLines", "Max_Lines"), ("MaxLines", "Max_Lines"), ("MAX_LINES", "Max_Lines")):
        err = fails(f"Text {{\n  {bad}: 2\n}}\n", f"'{bad}' is not a Title_Case key")
        assert f"write '{good}'" in str(err)
        at(err, 7, 2)
    err = fails("Text {\n  style { Gap: 1 }\n}\n", "'style' is not a Title_Case key")
    at(err, 7, 2)
    err = fails("Button {\n  Handlers {\n    on_click: save\n  }\n}\n", "'on_click' is not a Title_Case key")
    at(err, 8, 4)
    err = fails("Text {\n  Style { gap: 1 }\n}\n", "'gap' is not a Title_Case key")
    at(err, 7, 10)


def test_a_bad_set_target_and_other_bad_steps_say_what_a_step_is():
    h = "Button {\n  Handlers {\n    On_Click {\n      %s\n    }\n  }\n}\n"
    err = fails(h % "Set { Target: a.b, Value: <| 1 |> }", "a Set's Target is one plain name, got 'a.b'")
    at(err, 9, 20)
    err = fails(h % 'Set { Target: "a[0]", Value: <| 1 |> }', "a Set's Target is one plain name")
    fails(h % "Set { Target: a, Value: 1 }", "'Value:' takes one expression")
    fails(h % "Set { Target: a }", "a Set needs a Value")
    fails(h % "Set { Value: <| 1 |> }", "a Set needs a Target")
    err = fails(h % "Set { Target: a, Value: <| 1 |>, Valeu: 2 }", "a Set has a Target and a Value, not 'Valeu'")
    err = fails(h % "Call { Args: [<| 1 |>] }", "a Call needs an Action")
    fails(h % "Call { Action: 'a b' }", "a Call's Action is an action name")
    fails(h % "Call { Action: a, Args: [1] }", "'Args:' is a list of expressions")
    fails(h % "Call { Action: a, Mode: fast }", "'Mode:' takes one expression")
    fails(h % "Call { Action: a, mode: <| 1 |> }", "'mode' is not a Title_Case key")
    err = fails(h % "Sett { Target: a, Value: <| 1 |> }", "a handler is made of Set and Call steps, got 'Sett'")
    assert "did you mean 'Set'" in str(err)
    fails(h % "Target: a", "a handler is made of Set and Call steps")
    fails("Button {\n  Handlers {\n    On_Click { }\n  }\n}\n", "a handler needs at least one step")
    fails(h % "Set { Block { } }", "a Set step holds properties, not blocks")


def test_a_property_in_children_and_a_wrapper_in_a_map_are_errors_that_say_where_things_go():
    err = fails("Container {\n  Children {\n    Label: x\n  }\n}\n", "'Children' holds nodes, and 'Label:' is a property")
    at(err, 8, 4)
    err = fails("Container {\n  Style {\n    If <| a |> { Text { } }\n  }\n}\n", "an If wraps a node, and 'Style' holds a map")
    at(err, 8, 4)
    err = fails("Container {\n  If <| a |> { Text { } }\n}\n", "an If wraps a node: it goes inside Children")
    err = fails("Container {\n  Handlers {\n    For n In <| xs |> Key <| n |> { }\n  }\n}\n", "Handlers hold events, not If or For")
    err = fails("Container {\n  Style { A: 1 }\n  Style { B: 2 }\n}\n", "duplicate key 'style'")
    at(err, 8, 2)


def test_a_map_where_a_node_is_expected_and_a_node_where_a_map_is_expected_fail_in_the_node_parser_in_yaml_words():
    """Both reach the node parser, which says what the YAML loader says."""
    # a block that is no widget, among the children
    text = view("Container {\n  Children {\n    Stlye { Gap: 1 }\n  }\n}\n")
    with pytest.raises(LoadError) as caught:
        parse_data(T.load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")
    assert caught.value.message == "no widget named 'Stlye'"
    at(caught.value, 8, 4)
    # a widget block where a style map is
    text = view("Container {\n  Style {\n    Text { Gap: 1 }\n  }\n}\n")
    with pytest.raises(LoadError) as caught:
        parse_data(T.load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")
    assert caught.value.message == "Container: style 'text' is not valid here"
    at(caught.value, 8, 4)


def pair(tdl_body, yaml_body):
    """The `LoadError`s of the same mistake written in TDL and in YAML."""
    out = []
    for loader, text, file in ((lambda t, f: T.load_marked_tdl(t, f), view(tdl_body), "T_View.tdl"), (load_marked, yaml_body, "T_View.yaml")):
        with pytest.raises(LoadError) as caught:
            parse_data(loader(text, file), text, file)
        out.append(caught.value)
    return out


@pytest.mark.parametrize("tdl_body, yaml_body", [
    ("Texxt { }\n", "widget: Texxt\n"),
    ("Text { Style { Colour: red } }\n", "widget: Text\nstyle:\n  colour: red\n"),
    ("Text { Max_Linez: 2 }\n", "widget: Text\nmax_linez: 2\n"),
    ("Text { Name: 2cool }\n", "widget: Text\nname: 2cool\n"),
    ("Text { Name: a }\nText { }\n", None),
    ("Container { Children { Text { Name: a }\n Text { Name: a } } }\n", "widget: Container\nchildren:\n  - {widget: Text, name: a}\n  - {widget: Text, name: a}\n"),
    ("Text { Handlers { On_Clik: save } }\n", "widget: Text\nhandlers:\n  on_clik: save\n"),
    ("Container { Children { Text { Key_Only: 1 } } }\n", "widget: Container\nchildren:\n  - {widget: Text, key_only: 1}\n"),
])
def test_a_mistake_the_node_parser_finds_has_the_same_message_and_hint_as_in_yaml(tdl_body, yaml_body):
    if yaml_body is None:
        return  # a second root block is tess_dl's own error, tested elsewhere
    tdl_err, yaml_err = pair(tdl_body, yaml_body)
    assert (tdl_err.message, tdl_err.hint) == (yaml_err.message, yaml_err.hint)
    assert tdl_err.file == "T_View.tdl" and yaml_err.file == "T_View.yaml"


def test_the_nearest_name_hint_and_the_position_of_the_mistake_are_in_the_tdl_file():
    text = view("Text {\n  Style { Colour: red }\n}\n")
    with pytest.raises(LoadError) as caught:
        parse_data(T.load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")
    err = caught.value
    at(err, 7, 10)
    assert err.render().splitlines()[1].strip() == "7 |   Style { Colour: red }"
    text = view("Text {\n  Max_Linez: 2\n}\n")
    with pytest.raises(LoadError) as caught:
        parse_data(T.load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")
    assert "did you mean 'max_lines'" in str(caught.value)
    at(caught.value, 7, 2)


def test_an_expression_mistake_in_a_slot_points_at_the_column_inside_the_slot():
    for body, line, key in (("Text {\n  Text: <| level + |>\n}\n", 7, "level +"), ("Text {\n  Text: Battery <| level + |>%\n}\n", 7, "level +")):
        text = view(body)
        with pytest.raises(LoadError) as caught:
            parse_data(T.load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")
        err = caught.value
        assert err.file == "T_View.tdl" and err.line == line
        source_line = text.splitlines()[line - 1]
        assert source_line.index(key) <= err.column <= source_line.index(key) + len(key) + 1, (err.column, source_line)
    # the condition of an If, and the iterable of a For (the chosen position makes the parser's offset land on it)
    for body, key in (("Container {\n  Children {\n    If <| a > |> { Text { } }\n  }\n}\n", "a >"),
                      ("Container {\n  Children {\n    For n In <| range( |> Key <| n |> { Text { } }\n  }\n}\n", "range(")):
        text = view(body)
        with pytest.raises(LoadError) as caught:
            parse_data(T.load_marked_tdl(text, "T_View.tdl"), text, "T_View.tdl")
        source_line = text.splitlines()[7]
        assert caught.value.line == 8 and source_line.index(key) <= caught.value.column <= source_line.index(key) + len(key) + 1, str(caught.value)


def test_a_call_value_and_a_file_that_is_not_utf8_are_errors(tmp_path):
    err = fails("Text {\n  Color: rgba(0 0 0 0.5)\n}\n", "'rgba(...)' is not a value a view takes")
    at(err, 7, 9)
    bad = tmp_path / "Bad_View.tdl"
    bad.write_bytes(b"---\nTDL: 0.1\nName: T\n---\nText { Label: \xff }\n")
    with pytest.raises(LoadError) as caught:
        T.load_tdl_file(bad)
    assert caught.value.file == "Bad_View.tdl" and "not UTF-8" in str(caught.value)


def test_load_tdl_file_reads_a_file_and_names_it_in_errors(tmp_path):
    good = tmp_path / "Good_View.tdl"
    good.write_bytes(view("Text { Text: hi }\n").encode())
    assert T.load_tdl_file(good) == {"widget": "Text", "text": "hi"}
    broken = tmp_path / "Broken_View.tdl"
    broken.write_text(view("Text {\n"), encoding="utf-8")
    with pytest.raises(LoadError) as caught:
        T.load_tdl_file(broken)
    assert str(caught.value).startswith("Broken_View.tdl:6:") and "never closed" in str(caught.value)


def test_the_helper_refuses_what_it_cannot_write_back_exactly():
    with pytest.raises(ValueError, match="no TDL form"):
        yaml_to_tdl("widget: Text\nmaxLines: 1\n", "X")
    with pytest.raises(ValueError, match="no step form"):
        yaml_to_tdl("widget: Button\nhandlers:\n  on_click: |\n    if a:\n      b()\n", "X")
    with pytest.raises(ValueError, match="cannot be written unquoted"):
        yaml_to_tdl("widget: Text\ntext: 'a, {{ b }}'\n", "X")
    assert yaml.safe_load("a: 1") == {"a": 1}  # pyyaml is what the helper's input goes through


def test_the_snake_case_conversion_is_exact_both_ways():
    for snake in ("max_lines", "a11y", "typography_role", "on_click", "value_min", "x"):
        assert T.snake_case(T.title_case(snake)) == snake
    for bad in ("max_lines", "maxLines", "Max_lines", "MAX"):
        assert T.snake_case(bad) is None, bad


def test_the_stand_in_leaves_everything_but_slots_alone():
    text = view('Text {\n  A: "x <| y |>"  # <| z |>\n  B: <| a |> # c\n  C: [<| p |>, "q <| r |>"]\n  D: Don\'t <| s |>\n}\n')
    want = text.replace("<| a |>", "{{ a }}").replace("<| p |>", "{{ p }}").replace("<| s |>", "{{ s }}")
    assert T._standin_rewrite(text, "f") == want  # a slot in a string or a comment stays as it is
    assert len(T._standin_rewrite(text, "f")) == len(text)  # every column stays true
    assert T.snake_case("Max__Lines") == "max__lines"


def test_a_quoted_string_is_positioned_at_its_text_a_slot_and_a_word_at_their_start():
    text = view('Text {\n  Name: "2cool"\n  Label: <| x |>\n  Other: word\n}\n')
    m = T.load_marked_tdl(text, "T_View.tdl")
    lines = text.splitlines()
    assert m.val_at["name"] == (7, lines[6].index("2cool"))  # YAML marks a quoted string after its quote too
    assert m.val_at["label"] == (8, lines[7].index("<|")) and m.val_at["other"] == (9, lines[8].index("word"))
    assert m.key_at["name"] == (7, 2) and m.at == (6, 0)
    with pytest.raises(LoadError) as caught:
        parse_data(m, text, "T_View.tdl")
    at(caught.value, 7, lines[6].index("2cool"))
