"""#284: an editable `model` property given one bare name that cannot be written back looks two-way and is not, so the composer says so (a warning in the log,
with the file, line and column), once for the place in the file. Anything that is deliberately one-way, or is two-way, stays quiet."""

import pytest
from loguru import logger

from tess_ui import Computed, Signal

from test_compose import VM, make

CALL = "Checkbox { Params { M { Type: bool, Default: false, Model: true } P { Type: bool, Default: false } }, Checked: <| m |> }"


@pytest.fixture
def said():
    lines = []
    sink = logger.add(lambda message: lines.append(message.record["message"]), level="WARNING")
    yield lines
    logger.remove(sink)


class Flags(VM):
    def __init__(self):
        super().__init__()
        self.done = Signal(False)
        self.inverse = Computed(lambda: not self.done.get())
        self.plain = False
        self.caption = "hi"
        self.flags = Signal([True, False])


def checkbox(value, extra="", vm=None):
    return make(None, f"Container {{\n{extra}  Children {{\n    Checkbox {{ Name: c, Checked: <| {value} |> }}\n  }}\n}}", viewmodel=vm or Flags())


@pytest.mark.parametrize("value, what", [("inverse", "a Computed"), ("plain", "a ViewModel attribute that is not a Signal")])
def test_a_bare_name_that_cannot_be_written_back_is_said_with_its_place(said, value, what):
    checkbox(value)
    assert len(said) == 1 and said[0].startswith("Main_View.tdl:7:") and what in said[0] and "Checkbox checked is given" in said[0]


def test_a_loop_variable_is_said(said):
    make(None, "Container { Children { For f In <| flags |> Key <| f |> { Checkbox { Name: c, Checked: <| f |> } } } }", viewmodel=Flags())
    assert len(said) == 1 and "a read-only param or loop variable" in said[0]  # two rows, one line: it is said once for the place


def test_a_plain_param_given_to_a_model_property_is_said(said):
    view = "Checkbox {\n  Params { P { Type: bool, Default: false } }\n  Checked: <| p |>\n}"
    make({"V": view}, "Container { Children { V { Name: v } } }")
    assert len(said) == 1 and "'p'" in said[0] and "V_View.tdl:7:" in said[0]


def test_a_call_that_gives_a_model_param_such_a_name_is_said(said):
    make({"V": CALL}, "Container {\n  Children {\n    V { Name: v, M: <| inverse |> }\n  }\n}", viewmodel=Flags())
    assert len(said) == 1 and "V m is given 'inverse', which is a Computed" in said[0] and "Main_View.tdl:7:" in said[0]


@pytest.mark.parametrize("value", ["done", "flag", "not done", "inverse and True"])
def test_a_two_way_binding_and_a_deliberate_one_way_expression_say_nothing(said, value):
    checkbox(value, extra="  State { Flag: true }\n")
    assert said == []


def test_a_literal_says_nothing(said):
    make(None, "Container { Children { Checkbox { Name: c, Checked: true } } }", viewmodel=Flags())
    assert said == []


def test_a_model_param_passed_on_is_two_way_and_says_nothing(said):
    out = "V { Params { Q { Type: bool, Default: false, Model: true } }, M: <| q |> }"
    make({"V": CALL, "Out": out}, "Container { Children { Out { Name: o, Q: <| done |> } } }", viewmodel=Flags())
    assert said == []


def test_a_property_the_user_does_not_edit_says_nothing(said):
    make(None, "Container { Children { Text { Name: t, Text: <| caption |> } } }", viewmodel=Flags())
    assert said == []


def test_a_name_nothing_has_is_not_this_warnings_to_make(said):
    with pytest.raises(Exception):
        checkbox("nosuch")
    assert not any("is given" in line for line in said)
