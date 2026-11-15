"""#265: a `Text` has `runs` in the current language: styled pieces of one text (tre 0.5.4's `spans`), bound to data like any property, with a `link` run
calling `on_link`. They had been left behind when the older `text: {runs: ...}` was the only way to write them."""

import pytest

from tess_ui import App, Signal, ViewModel
from tess_ui.spec.nodes import LoadError
from tess_ui.spec.build import SpecBuildError


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.was = Signal("$12")
        self.heard = []

    def opened(self, event):
        self.heard.append(event.href)


HEAD = ("---\nTDL: 0.2\nName: main\n---\nContainer {\n  Name: main\n  Style { Width: 400, Height: 160, Background: surface, Padding: 16 }\n  Children {\n")
TAIL = "  }\n}\n"


def msg(props=""):
    """The `msg` Text node, with `props` (TDL property lines) added to it."""
    return ("    Text {\n      Name: msg\n      Typography_Role: body_large\n      Style { Foreground: on_surface, Width: 360 }\n"
            + "".join("      " + line + "\n" for line in props.splitlines()) + "    }\n")


def opened(tmp_path, children, vm=VM):
    (tmp_path / "Views").mkdir(exist_ok=True)
    (tmp_path / "Views" / "Main_View.tdl").write_text(HEAD + children + TAIL)
    app = App(root=tmp_path, width=400, height=160)
    app.bind(vm)
    view = app.open_view("Main")
    app.show("main")
    view.window.advance(50)
    return app, view, view.node("root.msg"), app.bindings.viewmodel_for("main")


RUNS = msg('''Runs {
  Item { Text: "Sale: " }
  Item { Text: <| was |>, Strikethrough: true, Color: on_surface_variant }
  Item { Text: " $9", Weight: 700, Color: error }
  Item { Text: " ends Friday. " }
  Item { Text: "Read the terms", Link: terms }
}
Handlers { On_Link: "opened(event)" }''')


def test_runs_make_one_text_with_styled_ranges(tmp_path):
    app, view, node, vm = opened(tmp_path, RUNS)
    assert node.get("text") == "Sale: $12 $9 ends Friday. Read the terms"
    spans = node.get("spans")
    assert len(spans) == 3 and spans[0][:2] == (6, 9) and spans[1][2]["weight"] == 700.0 and spans[2][2]["link"] == "terms"


def test_a_run_that_reads_a_name_follows_it(tmp_path):
    app, view, node, vm = opened(tmp_path, RUNS)
    vm.was.set("$15")
    view.window.advance(50)
    assert node.get("text").startswith("Sale: $15 $9")
    assert node.get("spans")[0][:2] == (6, 9)  # the range follows the new text


def test_a_link_run_calls_on_link_with_its_href(tmp_path):
    app, view, node, vm = opened(tmp_path, RUNS)
    app.window.simulate("link", node, href="terms")
    assert vm.heard == ["terms"]


def test_the_offsets_are_utf8_bytes_not_characters(tmp_path):
    app, view, node, vm = opened(tmp_path, msg('Runs { Item { Text: "é" } Item { Text: "ab", Weight: 700 } }'))
    assert node.get("spans")[0][:2] == (2, 4)


def test_a_text_with_runs_can_be_selectable(tmp_path):
    app, view, node, vm = opened(tmp_path, msg('Selectable: true\nRuns { Item { Text: "a " } Item { Text: "b", Weight: 700 } }'))
    assert node.get("selectable") is True


def test_a_run_may_be_a_whole_expression_that_gives_a_mapping(tmp_path):
    app, view, node, vm = opened(tmp_path, msg('Runs: ["Total ", <| {"text": was, "weight": 700} |>]'))
    assert node.get("text") == "Total $12" and node.get("spans")[0][2]["weight"] == 700.0


@pytest.mark.parametrize("runs, message", [
    ('Runs { }', "list of pieces"),
    ('Runs { Item { Weight: 700 } }', "string, or a mapping with `text:`"),
    ('Runs { Item { Text: a, Bogus: 1 } }', "unknown key"),
    ('Runs { Item { Text: a, Link: "" } }', "link must be a non-empty string"),
    ('Runs { Item { Text: a, Weight: heavy } }', "weight"),
    ('Runs: "just text"', "list"),
])
def test_bad_runs_are_refused_naming_the_text(tmp_path, runs, message):
    with pytest.raises((SpecBuildError, LoadError, ValueError)) as caught:
        opened(tmp_path, msg(runs))
    assert message in str(caught.value) or "runs" in str(caught.value)


def test_runs_and_text_together_are_refused_where_they_are_written(tmp_path):
    with pytest.raises(LoadError) as caught:
        opened(tmp_path, msg("Text: hello\nRuns: [a]"))
    assert "`runs:` is the text" in str(caught.value) and "Main_View.tdl" in str(caught.value)
    with pytest.raises(LoadError, match="runs"):
        opened(tmp_path, msg("Runs: [a]\nText: hello"))


@pytest.mark.parametrize("widget", ["Link", "TextInput", "Button"])
def test_runs_are_for_a_text_only(tmp_path, widget):
    with pytest.raises(LoadError, match="runs"):
        opened(tmp_path, f"    {widget} {{ Name: msg, Runs: [a] }}\n")


def test_a_mistake_in_a_run_expression_is_found_at_load_with_its_position(tmp_path):
    with pytest.raises(LoadError) as caught:
        opened(tmp_path, msg('Runs: [<| was + |>]'))
    assert "Main_View.tdl" in str(caught.value)


def test_a_name_a_run_reads_that_nothing_defines_is_named_when_the_view_opens(tmp_path):
    with pytest.raises(Exception, match="nothing_here"):
        opened(tmp_path, msg('Runs: [<| nothing_here |>]'))


def test_the_contract_check_reads_the_names_in_runs(tmp_path):
    """`check_view` lists names the ViewModel lacks, run strings included."""
    from tess_ui.spec.nodes import parse_view
    from tess_ui.viewmodel import check_view

    doc = parse_view(HEAD + msg('Runs: [<| nothing_here |>]') + TAIL, "Main_View.tdl")
    assert any("nothing_here" in p for p in check_view(doc, VM()))
