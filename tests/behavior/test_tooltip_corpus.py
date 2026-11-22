"""The `tooltip` corpus of the Tesserae behavior standard, run on tess-ui's real tooltip (see `tooltip_host.py`).

The result of each case is a fact about the tooltip. The tooltip reports its own events (`on_tooltip_before_change`, `on_tooltip_change`); the
adapter derives only `focus_move`. A gap that gets fixed must be removed from `KNOWN_GAPS`, or the test fails. Skipped without the
`tesserae-behavior` package (`tests/behavior/requirements.txt`)."""

import pytest

pytest.importorskip("tess_behavior")
from tess_behavior.corpus import FAIL, NOT_RUN, PASS, behaviour_cases, corpus_root, run_case  # noqa: E402
from tooltip_host import TooltipHost  # noqa: E402

CASES = {c.name.removesuffix(".case.json"): c for c in behaviour_cases(corpus_root()) if c.parent.name == "tooltip"}

#: case -> (status, why). Not listed: pass.
KNOWN_GAPS: dict[str, tuple[str, str]] = {
    "escape-closes-and-stays-closed": (FAIL, "`consumed` is not observable (the adapter reports it false): adapter limit"),
    "pointer-focus-shows-no-tooltip": (NOT_RUN, "a pointer focus without a press cannot be driven: a pointer on the trigger presses it"),
}


def _host(tmp_path):
    return lambda spec, options, controlled, responses: TooltipHost(tmp_path, spec, options, controlled, responses)


def test_the_corpus_has_the_tooltip_cases():
    assert len(CASES) == 17


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_case_gives_the_result_recorded_for_the_tooltip(name, tmp_path):
    result = run_case(CASES[name], _host(tmp_path))
    assert result.status == KNOWN_GAPS.get(name, (PASS, ""))[0], f"{name}: {result.status} {result.detail}"
