"""The `search_field` corpus of the Tesserae behavior standard, run on tess-ui's `search_bar` (see `search_bar_host.py`).

The result of each case is a fact about the widget. `KNOWN_GAPS` lists what does not conform yet, each with the reason, so the list is the to-do
list of the widget and a gap that gets fixed must be removed from it (the test fails when a listed case passes). Skipped without the
`tesserae-behavior` package (`tests/behavior/requirements.txt`): it is installed from a private repository for now."""

import pytest

pytest.importorskip("tess_behavior")
from search_bar_host import SearchBarHost  # noqa: E402
from tess_behavior.corpus import FAIL, NOT_RUN, PASS, behaviour_cases, corpus_root, run_case  # noqa: E402

#: case -> (status, why). `not run` is a case the widget cannot run; `fail` is one it runs and does not conform to.
KNOWN_GAPS: dict[str, tuple[str, str]] = {
    # the widget cannot run it
    "search_field/a11y-tree": (NOT_RUN, "the case sets clear_label; the clear button's label is fixed (\"Clear\")"),
    "search_field/controlled-reject": (NOT_RUN, "no controlled query and no way to veto a change"),
    "search_field/disabled": (NOT_RUN, "the `search_bar` helper has no `disabled` argument (the view has the parameter)"),
    "search_field/focus-none-part-via-pointer": (NOT_RUN, "a pointer on the clear button presses it, so it cannot take focus by pointer alone"),
    # it runs and does not conform
    "search_field/clear-press-returns-focus": (FAIL, "Clear returns the focus now; only the missing before_change differs (the events expectation)"),
    "search_field/clear-press-keyboard-returns-focus": (FAIL, "the same, by keyboard"),
    "search_field/escape-clears": (FAIL, "Escape clears the query; only the missing before_change differs (the events expectation)"),
    "search_field/type-updates-value": (FAIL, "the value follows; the widget emits no before_change (only the events expectation differs)"),
    # a limit of the adapter, not of the widget
    "search_field/type-same-value": (FAIL, "`consumed` is not observable (simulate returns nothing): inferred from a change, which is false when typing the same value"),
}

CASES = {f"{c.parent.name}/{c.name.removesuffix('.case.json')}": c for c in behaviour_cases(corpus_root())}


def test_the_corpus_has_the_cases_this_adapter_was_written_for():
    assert "search_field/escape-clears" in CASES


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_case_gives_the_result_recorded_for_the_widget(name):
    result = run_case(CASES[name], SearchBarHost)
    want = KNOWN_GAPS.get(name, (PASS, ""))
    assert result.status == want[0], f"{name}: {result.status} {result.detail}"
