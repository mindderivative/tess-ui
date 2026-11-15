"""The TEL adapter against `tess_ui.expr` on every expression the repository uses (piece 11a of `design/tdl-switch-plan.md`).

`tests/tel_parity.py` collects the texts and runs both evaluators on sample scopes; the differences that remain are listed, each with its reason and the kind of
fix it needs, in `tests/tel_parity_known.json`. This test fails on a difference that is not listed (a new one) and on a listed one that is gone (so the list only
shrinks): when it is gone, delete its entry.
"""

import pytest

import tel_parity  # noqa: E402  (tests/ is on the path)
from tess_ui import expr, tel  # noqa: E402


@pytest.fixture(scope="module")
def found():
    return tel_parity.differences()


def test_the_harness_has_something_to_compare():
    groups = tel_parity.collect()
    sizes = {name: len(units) for name, units in groups.items()}
    assert sizes["views"] >= 900 and sizes["docs"] >= 250 and sizes["tests"] >= 350 and sizes["corpus"] >= 300, sizes
    kinds = {u.kind for units in groups.values() for u in units}
    assert kinds == {"expr", "template"}


def test_every_sample_scope_set_is_the_same_each_run_and_not_all_errors():
    unit = tel_parity.Unit("expr", "[a['name'] for a in rows if a['done']] + [str(n)]")
    first = tel_parity.scopes_for(unit.text, {"rows", "n"})
    assert first == tel_parity.scopes_for(unit.text, {"rows", "n"}) and len(first) == tel_parity.SCOPES
    outcomes = [tel_parity._run(expr.compile_expr(unit.text), expr.MapScope(values)).state for values in first]
    assert "ok" in outcomes  # the samples are typed from how the text uses its names: `rows` is a list of rows, so the text does evaluate


def test_no_new_difference(found):
    known = {tel_parity.known_key(e) for e in tel_parity.load_known()}
    new = [d for d in found if d.key() not in known]
    assert not new, "differences between expr.py and the TEL adapter that are not in tests/tel_parity_known.json (fix the adapter, or list each with its reason):\n" + "\n".join(
        f"  {d.key()}\n      {d.detail}" for d in new)


def test_no_known_difference_has_gone(found):
    present = {d.key() for d in found}
    gone = [e for e in tel_parity.load_known() if tel_parity.known_key(e) not in present]
    assert not gone, "listed in tests/tel_parity_known.json but no longer a difference (delete the entry):\n" + "\n".join(f"  {tel_parity.known_key(e)}" for e in gone)


def test_each_known_difference_has_a_category_and_a_reason():
    known = tel_parity.load_known()
    keys = [tel_parity.known_key(e) for e in known]
    assert len(keys) == len(set(keys))
    for entry in known:
        assert entry["what"] in ("compile", "names", "result") and entry["kind"] in ("expr", "template")
        assert entry["category"] in tel_parity.CATEGORIES, entry["category"]
        assert len(entry["reason"]) > 40 and entry["reason"] != "placeholder"


def test_both_evaluators_have_the_same_functions_and_methods():
    assert set(expr.BUILTIN_FUNCTIONS) == set(tel.BUILTIN_NAMES)
    import tess_el._whitelist as whitelist

    assert whitelist.STR_METHODS == expr._STR_METHODS
    assert whitelist.SEQUENCE_METHODS == expr._LIST_METHODS
    assert whitelist.DICT_METHODS == expr._DICT_METHODS


# -- the comparison itself must see a difference ------------------------------------------------------------------------


class _Stub:
    def __init__(self, names, value=None, error=None):
        self.names, self._value, self._error = frozenset(names), value, error

    def evaluate(self, scope):
        if self._error is not None:
            raise self._error
        return self._value


def _with(monkeypatch, new):
    monkeypatch.setattr(tel, "compile_expr", lambda text, **kw: new)


def test_the_comparison_sees_a_different_value(monkeypatch):
    _with(monkeypatch, _Stub({"x"}, value=99))
    found = tel_parity.compare(tel_parity.Unit("expr", "x + 1"))
    assert [d.what for d in found] == ["result"]


def test_the_comparison_sees_an_error_where_the_other_has_a_value(monkeypatch):
    _with(monkeypatch, _Stub({"x"}, error=tel.ExprError("no")))
    assert [d.what for d in tel_parity.compare(tel_parity.Unit("expr", "x + 1"))] == ["result"]


def test_the_comparison_sees_a_different_type_and_names(monkeypatch):
    _with(monkeypatch, _Stub({"y"}, value=[1]))
    found = tel_parity.compare(tel_parity.Unit("expr", "[x]"))
    assert sorted(d.what for d in found) == ["names", "result"]
    _with(monkeypatch, _Stub({"x"}, value=(1,)))
    assert [d.what for d in tel_parity.compare(tel_parity.Unit("expr", "[x]"))] == ["result"]  # a tuple is not a list


def test_the_comparison_sees_a_text_that_only_one_refuses(monkeypatch):
    def refuse(text, **kw):
        raise tel.ExprError("refused")

    monkeypatch.setattr(tel, "compile_expr", refuse)
    assert [d.what for d in tel_parity.compare(tel_parity.Unit("expr", "x + 1"))] == ["compile"]


def test_two_errors_are_no_difference_whatever_their_text(monkeypatch):
    _with(monkeypatch, _Stub(set(), error=tel.ExprError("any message")))
    assert tel_parity.compare(tel_parity.Unit("expr", "1 / 0")) == []  # expr.py is an error too: the class agrees, the text is not compared
