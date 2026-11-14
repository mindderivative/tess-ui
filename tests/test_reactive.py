"""M35: Tesserae's reactivity (`tess_ui.reactive`) behaves exactly like
`tess_re`'s, which it replaces (`tess_re` D5).

Every behavioural test ran against both implementations while `tess_re`
0.3.4 had its own, so a difference showed as one side failing; all passed
on both. M43 retired `tess_re`'s half, since 0.3.5 removes it (M43 Q1).
(M35's bridge, which fed `tess_re`'s own `View` bindings from Tesserae's
signals, was removed in M37 Phase 6; bindings on Tesserae views are
covered by `test_view.py`.)
"""

import pytest

import tess_ui
import tess_ui.reactive

IMPLS = {"tesserae": tess_ui.reactive}


@pytest.fixture(params=sorted(IMPLS))
def rx(request):
    return IMPLS[request.param]


def _counter():
    calls = []
    return calls, (lambda: calls.append(1))


# -- Signal ---------------------------------------------------------------


def test_signal_get_set_update(rx):
    s = rx.Signal(1)
    s.set(2)
    s.update(lambda n: n * 10)
    assert s.get() == 20


def test_a_signal_notifies_only_on_a_change(rx):
    s = rx.Signal(1)
    calls, cb = _counter()
    s._subscribe(cb)
    s.set(1)
    s.update(lambda n: n)
    assert calls == []
    s.set(2)
    assert calls == [1]
    s._unsubscribe(cb)
    s._unsubscribe(cb)  # a second unsubscribe is a no-op
    s.set(3)
    assert calls == [1]


# -- Computed -------------------------------------------------------------


def test_computed_follows_its_dependencies(rx):
    price, qty = rx.Signal(2), rx.Signal(3)
    total = rx.Computed(lambda: price.get() * qty.get())
    assert total.get() == 6
    qty.set(4)
    assert total.get() == 8


def test_computed_is_eager_and_runs_once_per_change(rx):
    runs = []
    s = rx.Signal(1)
    c = rx.Computed(lambda: runs.append(s.get()) or s.get())
    assert runs == [1]
    s.set(2)
    assert runs == [1, 2]  # recomputed at the write, before any get()
    assert c.get() == 2


def test_computed_notifies_only_when_its_value_changes(rx):
    s = rx.Signal(1)
    parity = rx.Computed(lambda: s.get() % 2)
    calls, cb = _counter()
    parity._subscribe(cb)
    s.set(3)  # still odd
    assert calls == []
    s.set(4)
    assert calls == [1]


def test_computed_tracks_dependencies_dynamically(rx):
    use_a, a, b = rx.Signal(True), rx.Signal("a"), rx.Signal("b")
    runs = []
    c = rx.Computed(lambda: runs.append(1) or (a.get() if use_a.get() else b.get()))
    use_a.set(False)
    assert c.get() == "b"
    before = len(runs)
    a.set("a2")  # no longer a dependency
    assert len(runs) == before
    b.set("b2")
    assert c.get() == "b2"


def test_a_chain_of_computeds_updates_in_order(rx):
    s = rx.Signal(1)
    double = rx.Computed(lambda: s.get() * 2)
    plus_one = rx.Computed(lambda: double.get() + 1)
    seen = []
    rx.Effect(lambda: seen.append(plus_one.get()))
    s.set(5)
    assert (double.get(), plus_one.get()) == (10, 11)
    assert seen == [3, 11]


# -- Effect ---------------------------------------------------------------


def test_effect_runs_now_and_on_each_change_until_disposed(rx):
    s = rx.Signal(1)
    seen = []
    e = rx.Effect(lambda: seen.append(s.get()))
    s.set(2)
    e.dispose()
    s.set(3)
    assert seen == [1, 2]


# -- batch ----------------------------------------------------------------


def test_batch_runs_each_subscriber_once(rx):
    x, y = rx.Signal(1), rx.Signal(1)
    runs = []
    total = rx.Computed(lambda: runs.append(1) or x.get() + y.get())
    runs.clear()
    seen = []
    rx.Effect(lambda: seen.append(total.get()))
    seen.clear()
    result = rx.batch(lambda: (x.set(10), y.set(20), "done")[-1])
    assert result == "done"
    assert runs == [1]  # one recompute for two writes
    assert seen == [30]


def test_nested_batches_flush_at_the_outermost(rx):
    s = rx.Signal(0)
    seen = []
    rx.Effect(lambda: seen.append(s.get()))

    def inner():
        s.set(1)
        assert seen == [0]

    def outer():
        rx.batch(inner)
        assert seen == [0]  # still deferred
        s.set(2)

    rx.batch(outer)
    assert seen == [0, 2]


def test_batch_flushes_and_reraises_when_fn_raises(rx):
    s = rx.Signal(0)
    seen = []
    rx.Effect(lambda: seen.append(s.get()))

    def fn():
        s.set(1)
        raise KeyError("boom")

    with pytest.raises(KeyError):
        rx.batch(fn)
    assert seen == [0, 1]


# -- untrack --------------------------------------------------------------


def test_untrack_hides_reads_from_the_enclosing_scope(rx):
    tracked, hidden = rx.Signal(1), rx.Signal(10)
    c = rx.Computed(lambda: tracked.get() + rx.untrack(lambda: hidden.get()))
    hidden.set(20)
    assert c.get() == 11  # didn't recompute
    tracked.set(2)
    assert c.get() == 22  # recomputed, reading hidden's new value


# -- re-entrancy ------------------------------------------------------------


def test_writing_a_signal_while_it_notifies_raises(rx):
    s = rx.Signal(0)
    s._subscribe(lambda: s.set(s._value + 1))
    with pytest.raises(RuntimeError, match="written to again while still notifying"):
        s.set(1)


# -- a deferred effect: one run for one change, however many of its signals it touches ----------------


def test_a_deferred_effect_runs_once_for_a_write_that_reaches_it_by_several_paths(rx):
    base = rx.Signal(1)
    doubled = rx.Computed(lambda: base.get() * 2)
    tripled = rx.Computed(lambda: base.get() * 3)
    seen = []
    plain = []
    rx.Effect(lambda: seen.append((base.get(), doubled.get(), tripled.get())), deferred=True)
    rx.Effect(lambda: plain.append((base.get(), doubled.get(), tripled.get())))
    base.set(2)
    assert seen == [(1, 2, 3), (2, 4, 6)]  # once for the write, and it saw every computed settled
    assert len(plain) == 4 and plain[1] == (2, 4, 3)  # an ordinary effect still runs per path, in the middle of the notification


def test_a_deferred_effect_runs_once_after_a_batch_and_again_for_what_it_sets_off_itself(rx):
    a, b, log = rx.Signal(0), rx.Signal(0), []
    rx.Effect(lambda: log.append((a.get(), b.get())), deferred=True)
    rx.batch(lambda: (a.set(1), b.set(1)))
    assert log == [(0, 0), (1, 1)]
    followers = rx.Signal(0)
    rx.Effect(lambda: followers.set(a.get() * 10))  # an ordinary effect writes a third signal when `a` changes
    rx.Effect(lambda: log.append(("f", followers.get())), deferred=True)
    log.clear()
    a.set(2)
    assert log == [(2, 1), ("f", 20)]  # the deferred one read the follower after it settled, not before (20, not the old 10)


def test_a_deferred_effect_that_is_poked_during_its_own_run_runs_again_after_it(rx):
    log, holder = [], []

    def body():
        log.append(len(log))
        if len(log) == 1:
            holder[0]._poke()  # told to run while running (a view's children changed under its own sync)

    holder.append(rx.Effect.__new__(rx.Effect))
    rx.Effect.__init__(holder[0], body, deferred=True)
    assert log == [0, 1]


def test_a_deferred_effect_still_runs_when_a_subscriber_of_the_same_write_raises(rx):
    s, log = rx.Signal(0), []
    rx.Effect(lambda: log.append(s.get()), deferred=True)

    s._subscribe(lambda: (_ for _ in ()).throw(ValueError("boom")))
    with pytest.raises(ValueError, match="boom"):
        s.set(1)
    assert log == [0, 1]


def test_a_disposed_deferred_effect_never_runs_again_even_when_it_was_waiting(rx):
    s, log = rx.Signal(0), []
    effect = rx.Effect(lambda: log.append(s.get()), deferred=True)
    s._subscribe(effect.dispose)  # disposed in the middle of the notification that told it
    s.set(1)
    assert log == [0]  # it was waiting when it was disposed: it never ran
    n = len(log)
    s.set(2)
    assert len(log) == n and rx._deferred == []


def test_reads_are_recorded_once_each_in_the_order_first_read(rx):
    first, second = rx.Signal(1), rx.Signal(2)
    c = rx.Computed(lambda: first.get() + second.get() + first.get())
    assert c.get() == 4 and c._dependencies == [first, second]


# -- only Tesserae: the public names -------------------------------------------


def test_tesserae_exports_its_own_reactivity():
    for name in ("Signal", "Computed", "Effect", "ViewModel", "batch", "untrack"):
        assert getattr(tess_ui, name) is getattr(tess_ui.reactive, name)
        assert getattr(tess_ui, name).__module__ == "tess_ui.reactive"  # not tess_re's (0.3.5 has none)
