"""The `list` corpus (the Selection behavior, SPEC 2.5b) run on tess-ui's `list_` and `Tree` (see `list_host.py`).

Three runs, each pinned case by case; a case not listed passes. A gap that gets fixed must be removed from its table, or the test fails.
 * LIST_STRICT: `list_` against every expectation of the corpus.
 * LIST_DIAG and TREE_DIAG: only state and focus (`ignore=("events", "consumed")`, a diagnostic and not a conformance run), for the `list_` and the
   `Tree`. The Tree reports no events, so a strict run of it would fail every case on its first event; this one says whether the SET and the
   FOCUS follow the standard. Skipped without the `tesserae-behavior` package (`tests/behavior/requirements.txt`)."""

import pytest

pytest.importorskip("tess_behavior")
from list_host import ListHost, TreeHost  # noqa: E402
from tess_behavior.corpus import FAIL, NOT_RUN, PASS, behaviour_cases, corpus_root, run_case  # noqa: E402

CASES = {c.name.removesuffix(".case.json"): c for c in behaviour_cases(corpus_root()) if c.parent.name == "list"}

WHY = {
    "name": "the list has no accessible name (`list_` takes no label) and the Tree's roles are tree and treeitem, not listbox and option",
    "anchor": "a single-mode list or tree has no anchor to read: the engine keeps one only for a multiple selection",
    "order": "the focus moves after the engine has made the range (Shift+Arrow), the standard has focus_move first",
    "announce": "the engine's announcement (`selection_announce`) cannot be read back from a headless window",
    "consumed": "`consumed` is not observable: the adapter reports whether any event came, and a Space on an unselectable row is consumed without one",
    "unselectable": "the Tree has no unselectable rows (a row that takes focus but is never chosen)",
    "ctrl_a": "Ctrl+A cannot be switched off",
    "on_focus": "selection never follows focus",
}
_UNSEL = ("unselectable-arrow-lands-on-row", "unselectable-row-skipped-by-range", "unselectable-select-all-skips", "unselectable-set-from-code-ignores-row",
          "unselectable-space-selects-nothing")
_COMMON = {
    "a11y-tree-multiple": (FAIL, "name"), "a11y-tree-single": (FAIL, "name"),
    "announce-clear": (NOT_RUN, "announce"), "announce-once-after-300ms": (NOT_RUN, "announce"), "announce-range": (NOT_RUN, "announce"),
    "announce-select-all": (NOT_RUN, "announce"), "announce-single-none": (FAIL, "anchor"), "api-set-is-not-announced": (NOT_RUN, "announce"),
    "select-all-key-off": (NOT_RUN, "ctrl_a"), "single-mode-keeps-before-change": (FAIL, "anchor"), "single-select-on-focus": (NOT_RUN, "on_focus"),
    "single-space-chooses": (FAIL, "anchor"),
}
LIST_DIAG = dict(_COMMON)
TREE_DIAG = {**_COMMON, **dict.fromkeys(_UNSEL, (NOT_RUN, "unselectable"))}
LIST_STRICT = {**LIST_DIAG, "shift-arrow-range": (FAIL, "order"), "unselectable-space-selects-nothing": (FAIL, "consumed")}


def test_the_corpus_has_the_list_cases_and_every_recorded_gap_names_its_reason():
    assert len(CASES) == 26
    for table in (LIST_STRICT, LIST_DIAG, TREE_DIAG):
        assert set(table) <= set(CASES) and all(why in WHY for _, why in table.values())


def _tree_host(tmp_path):
    return lambda spec, options, controlled, responses: TreeHost(tmp_path, spec, options, controlled, responses)


@pytest.mark.parametrize("name", sorted(CASES))
def test_list_strict(name):
    assert run_case(CASES[name], ListHost).status == LIST_STRICT.get(name, (PASS, ""))[0], name


@pytest.mark.parametrize("name", sorted(CASES))
def test_list_state_and_focus(name):
    assert run_case(CASES[name], ListHost, ignore=("events", "consumed")).status == LIST_DIAG.get(name, (PASS, ""))[0], name


@pytest.mark.parametrize("name", sorted(CASES))
def test_tree_state_and_focus(name, tmp_path):
    assert run_case(CASES[name], _tree_host(tmp_path), ignore=("events", "consumed")).status == TREE_DIAG.get(name, (PASS, ""))[0], name
