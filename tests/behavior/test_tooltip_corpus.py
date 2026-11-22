"""The `tooltip` corpus of the Tesserae behavior standard, run on tess-ui's real tooltip (see `tooltip_host.py`).

Two runs of the same cases. The strict one is conformance: the tooltip emits no behavior events yet, so every case that expects `before_change`
and `change` (or a `focus_move` the adapter has to derive) fails on its events. The second ignores `events` so what the tooltip really does
shows: its open state, focus, parts, consumption and tree. Each result is recorded with its reason; a gap that gets fixed must be removed
here, or the test fails. Skipped without the `tesserae-behavior` package (`tests/behavior/requirements.txt`)."""

import pytest

pytest.importorskip("tess_behavior")
from tess_behavior.corpus import FAIL, NOT_RUN, PASS, behaviour_cases, corpus_root, run_case  # noqa: E402
from tooltip_host import TooltipHost  # noqa: E402

CASES = {c.name.removesuffix(".case.json"): c for c in behaviour_cases(corpus_root()) if c.parent.name == "tooltip"}

NO_EVENTS = "the tooltip emits no before_change/change (tess_ui.behavior is not wired into it)"

#: Strict run (events checked): case -> (status, why). Not listed: pass.
STRICT: dict[str, tuple[str, str]] = {
    **{name: (FAIL, NO_EVENTS) for name in (
        "a11y-tree-open", "blur-closes", "escape-closes-and-stays-closed", "grace-closes-at-150", "grace-enter-tip-keeps-open",
        "grace-reenter-trigger-keeps-open", "key-enter-closes", "key-space-closes", "keyboard-focus-opens-without-delay", "open-delay",
        "pointer-press-closes", "scroll-closes", "window-focus-loss-closes")},
    "pointer-press-before-delay-shows-nothing": (FAIL, "a pointer press focuses the trigger (a focus_move the corpus does not expect: the standard "
                                                       "does not say a press on a Tab-stop part takes focus)"),
    "pointer-focus-shows-no-tooltip": (NOT_RUN, "a pointer focus without a press cannot be driven: a pointer on the trigger presses it"),
}

#: Events ignored: what the tooltip really does. Not listed: pass.
STATE: dict[str, tuple[str, str]] = {
    "a11y-tree-open": (FAIL, "the tip layer has no role (the spec: tooltip) and is hidden from assistive technology; the trigger holds the description"),
    "escape-closes-and-stays-closed": (FAIL, "`consumed` is not observable (the adapter reports it false): adapter limit"),
    "pointer-focus-shows-no-tooltip": (NOT_RUN, "a pointer focus without a press cannot be driven: a pointer on the trigger presses it"),
}


def _host(tmp_path):
    return lambda spec, options, controlled, responses: TooltipHost(tmp_path, spec, options, controlled, responses)


def test_the_corpus_has_the_tooltip_cases():
    assert len(CASES) == 17


@pytest.mark.parametrize("name", sorted(CASES))
def test_strict_run(name, tmp_path):
    result = run_case(CASES[name], _host(tmp_path))
    assert result.status == STRICT.get(name, (PASS, ""))[0], f"{name}: {result.status} {result.detail}"


@pytest.mark.parametrize("name", sorted(CASES))
def test_the_state_of_the_tooltip_with_events_ignored(name, tmp_path):
    result = run_case(CASES[name], _host(tmp_path), ignore={"events"})
    assert result.status == STATE.get(name, (PASS, ""))[0], f"{name}: {result.status} {result.detail}"
