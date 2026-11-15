"""#251: a function name that does not exist is found when the view loads, not when the expression runs -- in a template, an `if:`, a `for:`,
a stylesheet rule and a handler -- with the line, and the names that are near."""

import pytest

from tess_ui import Signal
from tess_ui.expr import BUILTIN_FUNCTIONS, ExprError, compile_expr, compile_statements, compile_template
from tess_ui.spec.compose import Composer
from tess_ui.spec.nodes import LoadError, parse_view
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet
from tess_ui.spec.rules import RuleSheet


class VM:
    def __init__(self):
        self.count = Signal(0)
        self.items = Signal([1, 2, 3])
        self.log = []

    def bump(self, by=1):
        self.log.append(by)


def actions(path):
    """What an app's built-in actions answer: `copy` and `focus` exist, the rest do not."""
    return (lambda *args: None) if path in ("copy", "focus", "after", "every") else None


actions.names = ("copy", "focus", "after", "every")


def view(body):
    """A view whose root Container holds `body` (the TDL of its children, indented four spaces)."""
    return parse_view(f"---\nTDL: 0.2\nName: Main\n---\nContainer {{\n  Children {{\n{body}  }}\n}}\n", "Main_View.tdl")


def click(*steps, name="r"):
    """A Rect whose `On_Click` runs `steps` (each the TDL of one `Set` or `Call` block)."""
    lines = "".join(f"          {step}\n" for step in steps)
    return f"    Rect {{\n      Name: {name}\n      Handlers {{\n        On_Click {{\n{lines}        }}\n      }}\n    }}\n"


def composed(body, vm=None, **kwargs):
    return Composer({}, vm or VM(), actions=actions, **kwargs).compose(view(body))


# -- an expression, a template, an `if:`, a `for:`: found when the text is compiled ---------------------------------------


def test_an_unknown_function_in_an_expression_is_a_load_error_naming_it():
    with pytest.raises(ExprError) as caught:
        compile_expr("nosuch(1)")
    assert "'nosuch' is not a function you can call here" in caught.value.message
    assert caught.value.hint.startswith("allowed: ") and "clamp" in caught.value.hint  # nothing is near: the whole list


def test_the_near_names_are_offered():
    with pytest.raises(ExprError) as caught:
        compile_expr("clmap(x, 0, 10)")
    assert caught.value.hint == "did you mean 'clamp'"


def test_the_builtin_functions_still_compile():
    for name in ("clamp", "min", "max", "len", "format_number", "pluralize", "format_date", "current_date"):
        assert name in BUILTIN_FUNCTIONS
        compile_expr(f"{name}(x)")


def test_a_call_inside_a_comprehension_is_checked_too():
    with pytest.raises(ExprError, match="'nosuch' is not a function"):
        compile_expr("[nosuch(i) for i in items]")


def test_an_unknown_function_in_a_template_names_the_file_and_line():
    with pytest.raises(LoadError) as caught:
        view("    Text {\n      Name: t\n      Text: a <| nosuch(1) |> b\n    }\n")
    assert caught.value.file == "Main_View.tdl" and caught.value.line == 9
    assert "'nosuch' is not a function you can call here" in str(caught.value)


def test_an_unknown_function_in_an_if_and_a_for_is_a_load_error():
    with pytest.raises(LoadError, match="'nosuch' is not a function"):
        view("    If <| nosuch(count) |> {\n      Rect { Name: r }\n    }\n")
    with pytest.raises(LoadError, match="'nosuch' is not a function"):
        view("    For i In <| nosuch(3) |> Key <| i |> {\n      Rect { Name: r }\n    }\n")


def test_an_unknown_function_in_a_stylesheet_rule_is_a_load_error():
    text = "---\nTDL: 0.2\nName: S\n---\nStyles {\n  Rule { Widget: Text, Style { Width: <| nosuch(1) |> } }\n}\n"
    with pytest.raises(LoadError, match="'nosuch' is not a function"):
        RuleSheet.of(load_marked_tdl_stylesheet(text, "S_Stylesheet.tdl"), "S_Stylesheet.tdl", text)


# -- a handler: found when the view is composed, against what the scope knows ---------------------------------------------


def test_an_unknown_function_in_a_handler_is_a_load_error_with_the_line():
    with pytest.raises(LoadError) as caught:
        composed(click("Set { Target: count, Value: <| nosuch(1) |> }"))
    assert "'nosuch' is not a function or an action you can call here" in str(caught.value)
    assert caught.value.line == 10


def test_an_unknown_call_statement_in_a_handler_is_a_load_error_that_offers_near_names():
    with pytest.raises(LoadError) as caught:
        composed(click('Call { Action: "bmup", Args: [<| 2 |>] }'))
    assert caught.value.hint == "did you mean 'bump'"


def test_a_viewmodel_method_a_builtin_action_and_a_builtin_function_still_load():
    vm = VM()
    composed(click('Call { Action: "bump", Args: [<| 2 |>] }', 'Call { Action: "copy", Args: [<| str(count) |>] }',
                   "Set { Target: count, Value: <| clamp(count + 1, 0, 5) |> }"), vm)


def test_without_the_actions_a_handlers_names_cannot_be_judged_so_it_loads():
    Composer({}, VM()).compose(view(click('Call { Action: "copy", Args: [<| "x" |>] }')))


def test_compile_statements_keeps_the_calls_it_saw():
    statements = compile_statements("bump(1); count = nosuch(2)")
    assert sorted(call.func.id for call in statements.calls) == ["bump", "nosuch"]


# -- #283: the text of an `after(...)` or `every(...)` in a handler is checked as the handler is --------------------------------------------------


def test_an_unknown_action_in_a_timer_text_is_a_load_error():
    with pytest.raises(LoadError, match="'nosuch' is not a function or an action you can call here"):
        composed(click('Call { Action: "after", Args: [<| 10 |>, <| "nosuch()" |>] }'))


def test_an_unknown_action_in_an_every_text_is_a_load_error():
    with pytest.raises(LoadError, match="'nosuch' is not a function or an action"):
        composed(click('Call { Action: "every", Args: [<| 10 |>, <| "nosuch()" |>] }'))


def test_a_timer_text_inside_a_timer_text_is_checked_too():
    nested = click('Call { Action: "after", Args: [<| 10 |>, <| \'after(5, "nosuch()")\' |>] }')
    with pytest.raises(LoadError, match="'nosuch' is not a function or an action"):
        composed(nested)


def test_a_good_timer_text_loads_and_runs():
    comp = composed(click('Call { Action: "after", Args: [<| 10 |>, <| "count += 1" |>] }'))
    assert comp.find("root.r") is not None


def test_a_timer_text_that_is_an_action_name_or_not_a_literal_is_left_alone():
    composed(click('Call { Action: "after", Args: [<| 10 |>, <| "copy" |>] }'))
    composed(click('Call { Action: "after", Args: [<| 10 |>, <| bump |>] }', name="s"))
