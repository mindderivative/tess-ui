"""The `list` corpus (the Selection behavior, SPEC 2.5b) run on tess-ui's `list_` and `Tree` (see `list_host.py`).

Three runs, each pinned case by case; a case not listed passes. A gap that gets fixed must be removed from its table, or the test fails.
 * LIST_STRICT: `list_` against every expectation of the corpus.
 * TREE_STRICT: the same for the `Tree` (its `On_Change` reports `selection_change`; in the single mode it reports nothing).
 * LIST_DIAG and TREE_DIAG: only state and focus (`ignore=("events", "consumed")`, a diagnostic and not a conformance run). Skipped without the `tesserae-behavior` package (`tests/behavior/requirements.txt`)."""

import pytest

pytest.importorskip("tess_behavior")
from list_host import ListHost, TreeHost  # noqa: E402
from tess_behavior.corpus import FAIL, NOT_RUN, PASS, behaviour_cases, corpus_root, run_case  # noqa: E402

CASES = {c.name.removesuffix(".case.json"): c for c in behaviour_cases(corpus_root()) if c.parent.name == "list"}

WHY = {
    "tree": "not applicable: the Tree is a tree (roles tree and treeitem), the standard's list primitive is a listbox of options",
    "focus_model": "no active-descendant model: `list_` and the Tree keep the focus on their rows (roving tabindex), and the engine has no container that holds focus and names the active child",
    "anchor": "a single-mode list or tree has no anchor to read: the engine keeps one only for a multiple selection",
    "order": "the focus moves after the engine has made the range (Shift+Arrow), the standard has focus_move first",
    "announce": "the engine's announcement (`selection_announce`) cannot be read back from a headless window",
    "consumed": "`consumed` is not observable: the adapter reports whether any event came, and a Space on an unselectable row is consumed without one",
    "unselectable": "the Tree has no unselectable rows (a row that takes focus but is never chosen)",
    "on_focus": "the Tree never selects on focus: a focus event does not say whether Ctrl was held, and Ctrl+Arrow moves the focus alone",
}
_UNSEL = ("unselectable-arrow-lands-on-row", "unselectable-row-skipped-by-range", "unselectable-select-all-skips", "unselectable-set-from-code-ignores-row",
          "unselectable-space-selects-nothing")
_COMMON = {
    "announce-clear": (NOT_RUN, "announce"), "announce-once-after-300ms": (NOT_RUN, "announce"), "announce-range": (NOT_RUN, "announce"),
    "announce-select-all": (NOT_RUN, "announce"), "announce-single-none": (FAIL, "anchor"), "api-set-is-not-announced": (NOT_RUN, "announce"),
    "single-mode-keeps-before-change": (FAIL, "anchor"), "single-select-on-focus": (FAIL, "anchor"),
    "single-space-chooses": (FAIL, "anchor"),
}
_VARIANTS = {name: (NOT_RUN, "focus_model") for name in CASES if name.endswith("-active-descendant")}
LIST_DIAG = {**_COMMON, **_VARIANTS}
TREE_DIAG = {**_COMMON, **_VARIANTS, **dict.fromkeys(_UNSEL, (NOT_RUN, "unselectable")), "a11y-tree-multiple": (FAIL, "tree"), "a11y-tree-single": (FAIL, "tree"),
             "single-select-on-focus": (NOT_RUN, "on_focus")}
TREE_STRICT = {**TREE_DIAG, "shift-arrow-range": (FAIL, "order")}
LIST_STRICT = {**LIST_DIAG, "shift-arrow-range": (FAIL, "order"), "unselectable-space-selects-nothing": (FAIL, "consumed")}


def test_the_corpus_has_the_list_cases_and_every_recorded_gap_names_its_reason():
    assert len(CASES) == 36
    for table in (LIST_STRICT, LIST_DIAG, TREE_DIAG, TREE_STRICT):
        assert set(table) <= set(CASES) and all(why in WHY for _, why in table.values())


def _tree_host(tmp_path):
    return lambda spec, options, controlled, responses, **extra: TreeHost(tmp_path, spec, options, controlled, responses, **extra)


@pytest.mark.parametrize("name", sorted(CASES))
def test_list_strict(name):
    assert run_case(CASES[name], ListHost).status == LIST_STRICT.get(name, (PASS, ""))[0], name


@pytest.mark.parametrize("name", sorted(CASES))
def test_list_state_and_focus(name):
    assert run_case(CASES[name], ListHost, ignore=("events", "consumed")).status == LIST_DIAG.get(name, (PASS, ""))[0], name


@pytest.mark.parametrize("name", sorted(CASES))
def test_tree_state_and_focus(name, tmp_path):
    assert run_case(CASES[name], _tree_host(tmp_path), ignore=("events", "consumed")).status == TREE_DIAG.get(name, (PASS, ""))[0], name


@pytest.mark.parametrize("name", sorted(CASES))
def test_tree_strict(name, tmp_path):
    assert run_case(CASES[name], _tree_host(tmp_path)).status == TREE_STRICT.get(name, (PASS, ""))[0], name
