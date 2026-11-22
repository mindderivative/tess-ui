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
    "search_field/focus-none-part-via-pointer": (NOT_RUN, "the case asks for a pointer focus without a press; a pointer on the clear button presses it (a click)"),
    # it runs and does not conform
    # a limit of the adapter, not of the widget
    "search_field/type-same-value": (FAIL, "`consumed` is not observable (simulate returns nothing): inferred from a change, which is false when typing the same value"),
}

CASES = {f"{c.parent.name}/{c.name.removesuffix('.case.json')}": c for c in behaviour_cases(corpus_root()) if c.parent.name == "search_field"}


def test_the_corpus_has_the_cases_this_adapter_was_written_for():
    assert "search_field/escape-clears" in CASES


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_case_gives_the_result_recorded_for_the_widget(name):
    result = run_case(CASES[name], SearchBarHost)
    want = KNOWN_GAPS.get(name, (PASS, ""))
    assert result.status == want[0], f"{name}: {result.status} {result.detail}"
