"""The adapter that evaluates tess-ui's expressions with TEL (`tess_ui.tel`, piece 11a of `design/tdl-switch-plan.md`): name lookup order, the built-in functions, what an
evaluation reads (the reactive layer), the errors, and the places where it differs from `tess_ui.expr`. `tests/test_tel_parity.py` runs both evaluators over every
expression of the repository; these tests say why the adapter is shaped as it is.

Needs `tess_el` (tess-el at git SHA 8b56fd0b02e6ade68fa4e05bd075ebe556d21c2a), which tess-ui does not depend on yet: without it the module is skipped.
"""

import datetime
import os
from types import SimpleNamespace

import pytest

pytest.importorskip("tess_el", reason="tess_el (tess-el at 8b56fd0b02e6ade68fa4e05bd075ebe556d21c2a) is not installed; it is not a dependency of tess-ui yet")

from tess_ui import expr, tel  # noqa: E402
from tess_ui.reactive import Computed, Effect, Signal  # noqa: E402
from tess_ui.spec.compose import Scope  # noqa: E402


def both(source, scope):
    """The value from `expr.py` and from the adapter, which must be the same."""
    old = expr.compile_expr(source).evaluate(scope)
    new = tel.compile_expr(source).evaluate(scope)
    assert old == new and type(old) is type(new), (source, old, new)
    return new


def both_fail(source, scope):
    """The errors from both evaluators (each is an error of its own package, both are `ValueError`s)."""
    with pytest.raises(expr.ExprError) as old:
        expr.compile_expr(source).evaluate(scope)
    with pytest.raises(tel.ExprError) as new:
        tel.compile_expr(source).evaluate(scope)
    return old.value, new.value


# -- the order names resolve in ---------------------------------------------------------------------------------------------------------------------------


def views_scopes():
    """What a view's scope is made of: the ViewModel, the view's local state and params, and a loop's variables over them."""
    viewmodel = SimpleNamespace(count=Signal(1), title="from the viewmodel", name="viewmodel name", items=[1, 2, 3], total=Computed(lambda: 6))
    state = Scope(None, {"name": "state name", "title": "state title", "open": Signal(False)}, root=viewmodel)
    params = Scope(state, {"label": "param label", "title": "param title"}, readonly=True)
    loop = Scope(params, {"name": "loop name", "it": {"id": 4}}, readonly=True)
    return viewmodel, state, params, loop


def test_a_loop_variable_shadows_local_state_which_shadows_the_viewmodel():
    viewmodel, state, params, loop = views_scopes()
    assert both("name", loop) == "loop name"
    assert both("name", params) == "state name" and both("name", state) == "state name"
    assert both("title", loop) == "param title"  # a param over the state's own
    assert both("title", state) == "state title"
    assert both("label", loop) == "param label"
    assert both("items", loop) == [1, 2, 3]
    assert tel.compile_expr("name").evaluate(Scope(None, {}, root=viewmodel)) == "viewmodel name"


def test_the_viewmodels_signals_and_computed_values_read_as_their_values():
    viewmodel, state, params, loop = views_scopes()
    assert both("count + 1", loop) == 2
    assert both("total * 2", loop) == 12
    assert both("not open", loop) is True
    viewmodel.count.set(5)
    assert both("count", loop) == 5


def test_app_is_the_last_name_and_a_view_model_attribute_of_that_name_wins():
    app = SimpleNamespace(width_class="compact")

    class Actions:
        def __call__(self, path):
            return None

        @staticmethod
        def app():
            return app

    scope = Scope(None, {}, root=SimpleNamespace(), actions=Actions())
    assert both("app.width_class", scope) == "compact"
    assert both("app.width_class == 'compact'", scope) is True
    own = Scope(None, {}, root=SimpleNamespace(app=SimpleNamespace(width_class="own")), actions=Actions())
    assert both("app.width_class", own) == "own"


def test_the_built_in_functions_are_last_and_a_name_in_the_scope_does_not_change_what_a_call_means():
    assert both("len", Scope(None, {"len": "mine"})) == "mine"  # read as a value, the scope's name wins
    assert both("len([1, 2])", Scope(None, {"len": "mine"})) == 2  # called, it is the function
    assert both("max(a, b)", Scope(None, {"a": 1, "b": 2})) == 2


def test_names_that_do_not_exist_are_errors_and_underscore_names_do_not_exist():
    _, _, _, loop = views_scopes()
    old, new = both_fail("nmae", loop)
    assert new.code == "unknown-name" and "did you mean 'name'" in str(new) and "did you mean 'name'" in str(old)
    both_fail("count + missing", loop)
    viewmodel = SimpleNamespace(_hidden=1)
    scope = Scope(None, {}, root=viewmodel)
    with pytest.raises(tel.ExprError) as private:
        tel.compile_expr("_hidden")
    assert private.value.code == "private-name"
    with pytest.raises(tel.ExprError):
        tel.compile_expr("x").evaluate(scope)


def test_the_adapter_reads_only_and_an_evaluation_never_writes_a_signal():
    class Strict(Signal):
        def set(self, value):
            raise AssertionError("an expression wrote a Signal")

        def update(self, fn):
            raise AssertionError("an expression wrote a Signal")

    scope = expr.MapScope({"n": Strict(1)})
    assert not hasattr(tel.adapt(scope), "assign") and not hasattr(tel.adapt(scope), "call_action")
    assert tel.compile_expr("n + 1").evaluate(scope) == 2
    for text in ("n = 2", "n += 1", "n.set(2)"):
        with pytest.raises(tel.ExprError):
            tel.compile_expr(text).evaluate(scope)


def test_event_is_a_name_only_when_the_caller_gives_one():
    scope = expr.MapScope({"n": 1})
    event = SimpleNamespace(key="space", ctrl=False)
    assert tel.compile_expr("event.key == 'space' and n == 1").evaluate(scope, event=event) is True
    assert tel.adapt(scope, event=event).lookup("event").key == "space"
    with pytest.raises(tel.ExprError, match="'event' is not defined"):
        tel.compile_expr("event.key").evaluate(scope)
    assert "event" in tel.adapt(scope, event=event).names() and "event" not in tel.adapt(scope).names()
    assert tel.adapt(tel.adapt(scope)) is not None and tel.adapt(scope).scope is scope


# -- the functions ----------------------------------------------------------------------------------------------------------------------------------------


def test_the_host_functions_are_what_expr_had_and_tel_did_not():
    import tess_el._whitelist as whitelist

    assert set(tel.HOST_FUNCTIONS) == set(expr.BUILTIN_FUNCTIONS) - whitelist.BUILTIN_NAMES == {
        "format_number", "pluralize", "date_add_days", "date_weekday", "days_in_month", "format_date", "current_date"}
    assert tel.BUILTIN_NAMES == frozenset(expr.BUILTIN_FUNCTIONS)


@pytest.mark.parametrize("source", [
    "format_number(1234567.891, 2)", "format_number(5)", "format_number(x, 1)", "pluralize(1, 'item')", "pluralize(2, 'item')", "pluralize(2, 'child', 'children')",
    "pluralize(0, 'box', 'boxes')", "clamp(15, 0, 10)", "clamp(-3, 0, 10)", "date_add_days('2026-11-14', 30)", "date_add_days('2026-03-01', -1)", "date_weekday('2026-11-14')",
    "days_in_month(2024, 2)", "days_in_month(2026, 2)", "days_in_month(2026, 12)", "format_date('2026-11-14')", "format_date('2026-11-14', '%A, %B %e %Y')",
    "format_date('2026-01-05', '%d/%m/%y %j %% %b %a')", "format_date(d, '%Y')", "len(format_date('2026-11-14'))",
    "[format_date(date_add_days('2026-11-14', k), '%a') for k in range(7)]",
])
def test_the_host_functions_behave_as_they_did(source):
    assert both(source, expr.MapScope({"x": 2.5, "d": "2024-02-29"})) is not None


def test_the_clock_function_is_the_clock():
    assert tel.compile_expr("current_date()").evaluate(expr.MapScope()) == datetime.date.today().isoformat() == expr.compile_expr("current_date()").evaluate(expr.MapScope())


def test_a_function_that_fails_says_why_as_expr_did():
    old, new = both_fail("format_date('not a date')", expr.MapScope())
    assert "is not a date written year-month-day" in str(old) and "is not a date written year-month-day" in str(new)
    assert new.code == "bad-call" and str(new).startswith("format_date() failed: ValueError: ")
    _, bad_pattern = both_fail("format_date('2026-11-14', '%Q')", expr.MapScope())
    assert "'%Q' is not a date field" in str(bad_pattern)


def test_the_reason_of_one_failure_is_never_given_to_another():
    with pytest.raises(tel.ExprError):
        tel.compile_expr("format_date('nope')").evaluate(expr.MapScope())
    with pytest.raises(tel.ExprError) as other:
        tel.compile_expr("int('x')").evaluate(expr.MapScope())
    assert "format_date" not in str(other.value) and other.value.code == "bad-call"
    with pytest.raises(tel.ExprError) as limit:
        tel.compile_expr("range(10 ** 7)").evaluate(expr.MapScope())
    assert limit.value.code == "limit-range"


def test_an_unknown_function_is_refused_when_the_text_is_read_with_the_nearest_name():
    with pytest.raises(expr.ExprError, match="did you mean 'clamp'"):
        expr.compile_expr("clmap(1, 0, 2)")
    with pytest.raises(tel.ExprError, match="did you mean 'clamp'") as error:
        tel.compile_expr("clmap(1, 0, 2)")
    assert error.value.code == "call-not-function"


def test_the_methods_are_the_whitelist_of_expr():
    scope = expr.MapScope({"s": " Ada ", "d": {"k": 1, "j": 2}, "t": (1, 2, 2), "items": [3, 1]})
    for source in ("s.strip().upper()", "s.split('d')", "'-'.join(['a', 'b'])", "d.get('k')", "d.get('zz', 0)", "list(d.keys())", "list(d.items())",
                   "d.values()", "t.count(2)", "items.index(1)", "s.zfill(8)", "s.removeprefix(' ')", "s.center(9)"):
        both(source, scope)
    for source in ("items.append(1)", "items.sort()", "d.update({})", "s.format()", "s.encode()"):
        with pytest.raises(tel.ExprError):
            tel.compile_expr(source)


# -- what an evaluation reads (the reactive layer) --------------------------------------------------------------------------------------------------------


def test_a_computed_over_an_expression_depends_on_what_the_evaluation_read():
    flag, a, b = Signal(True), Signal(1), Signal(2)
    scope = expr.MapScope({"flag": flag, "a": a, "b": b})
    program = tel.compile_expr("a * 10 if flag else b * 10")
    runs: list[int] = []

    def evaluate():
        runs.append(1)
        return program.evaluate(scope)

    shown = Computed(evaluate)
    assert shown.get() == 10 and len(runs) == 1
    b.set(5)  # not read while flag is true
    assert shown.get() == 10 and len(runs) == 1
    a.set(2)
    assert shown.get() == 20 and len(runs) == 2
    flag.set(False)
    assert shown.get() == 50 and len(runs) == 3
    a.set(7)  # not read now
    assert shown.get() == 50 and len(runs) == 3
    b.set(6)
    assert shown.get() == 60 and len(runs) == 4


def test_an_effect_over_a_template_follows_a_signal_inside_an_object():
    state = SimpleNamespace(user=Signal("ada"))
    scope = expr.MapScope({"app": SimpleNamespace(state=state)})
    seen: list[str] = []
    template = tel.compile_template("Hello {{ app.state.user.upper() }}!")
    Effect(lambda: seen.append(template.evaluate(scope)))
    state.user.set("grace")
    assert seen == ["Hello ADA!", "Hello GRACE!"]


def test_tracked_evaluation_says_which_paths_were_read():
    scope = expr.MapScope({"flag": True, "a": 1, "b": 2, "app": SimpleNamespace(state=SimpleNamespace(user="ada"))})
    value, reads = tel.compile_expr("a if flag else b").evaluate_tracked(scope)
    assert value == 1 and reads == {"flag", "a"}
    value, reads = tel.compile_expr("app.state.user + str(a)").evaluate_tracked(scope)
    assert value == "ada1" and reads == {"app.state.user", "a"}
    program = tel.compile_expr("a if flag else b")
    assert program.names == {"a", "b", "flag"} and program.paths == {"a", "b", "flag"}
    _, reads = tel.compile_template("{{ flag }} {{ b }}").evaluate_tracked(scope)
    assert reads == {"flag", "b"}


def test_names_and_reactivity_are_what_the_callers_ask():
    scope = expr.MapScope({"count": Signal(1), "label": "x"}, reactive={"count"})
    assert tel.compile_expr("count + 1").is_reactive(scope) and not tel.compile_expr("label.upper()").is_reactive(scope)
    assert tel.compile_expr("[i * k for i in items]").names == {"k", "items"} == expr.compile_expr("[i * k for i in items]").names
    assert tel.compile_expr("len(items) > 0").names == {"items"}  # the function is not a name it reads (expr.py counts it, and callers drop it)
    assert tel.compile_expr("count").bare_name() == "count" and tel.compile_expr("count + 1").bare_name() is None and tel.compile_expr("1").bare_name() is None
    assert not tel.compile_expr("count").is_reactive(object())  # a scope that cannot say is static
    frames = Scope(None, {"s": Signal(1), "t": 2}, root=SimpleNamespace(vm=Signal(3)))
    assert tel.compile_expr("s + vm").is_reactive(frames) and not tel.compile_expr("t + 1").is_reactive(frames)


def test_evaluate_raw_keeps_the_signal_for_a_two_way_property():
    count = Signal(1)
    scope = expr.MapScope({"count": count})
    assert tel.compile_expr("count").evaluate_raw(scope) is count and tel.compile_expr("count").evaluate(scope) == 1
    assert tel.compile_expr("count + 1").evaluate_raw(scope) == 2
    with pytest.raises(tel.ExprError, match="'nothing' is not defined"):
        tel.compile_expr("nothing").evaluate_raw(scope)


# -- Signals and objects of the application's ------------------------------------------------------------------------------------------------------------


def test_get_is_the_signals_own_read_and_on_a_signal_of_a_dict_it_is_not():
    scope = expr.MapScope({"count": Signal(4), "items": Signal([1, 2]), "none": Signal(None), "user": SimpleNamespace(name=Signal("ada"))})
    assert both("count.get() * 2", scope) == 8
    assert both("items.get()", scope) == [1, 2] and both("none.get()", scope) is None and both("user.name.get().upper()", scope) == "ADA"
    # the one case that stays different: a dict has its own `get`, which needs a key
    with pytest.raises(tel.ExprError):
        tel.compile_expr("d.get()").evaluate(expr.MapScope({"d": Signal({"k": 1})}))
    assert expr.compile_expr("d.get()").evaluate(expr.MapScope({"d": Signal({"k": 1})})) == {"k": 1}
    # and TEL lets `get()` on a plain value through, which expr.py refused
    assert tel.compile_expr("n.get()").evaluate(expr.MapScope({"n": 3})) == 3
    with pytest.raises(expr.ExprError):
        expr.compile_expr("n.get()").evaluate(expr.MapScope({"n": 3}))


class Plain:
    def __init__(self):
        self.title = "t"
        self.items = [1, 2]
        self.sub = SimpleNamespace(level=Signal(3), more=SimpleNamespace(deep="d"))
        self.watched = Signal("w")
        self._secret = "no"

    def method(self):
        return 1


class Narrow:
    __expose__ = ("shown",)
    shown = 1
    hidden = 2


def test_an_object_of_the_applications_is_read_by_attribute_and_nothing_else():
    scope = expr.MapScope({"o": Plain()})
    assert both("o.title", scope) == "t" and both("o.items[1]", scope) == 2
    assert both("o.sub.level + 1", scope) == 4  # a Signal that is an attribute reads as its value, in the middle of an expression too
    assert both("o.sub.more.deep + o.watched", scope) == "dw"
    assert both("[o.watched, o.sub.level]", scope) == ["w", 3]
    for source in ("o.method", "o.method()", "o.nothing", "o + 1", "o == o", "str(o)", "[o][0] + 1", "o.sub.nothing"):
        both_fail(source, scope)
    with pytest.raises(tel.ExprError) as private:
        tel.compile_expr("o._secret")
    assert private.value.code == "private-attribute"


def test_an_object_that_is_the_result_is_the_object_and_not_a_wrapper():
    plain = Plain()
    scope = expr.MapScope({"o": plain, "n": Signal(plain)})
    assert tel.compile_expr("o").evaluate(scope) is plain and tel.compile_expr("n").evaluate(scope) is plain
    assert tel.compile_expr("o.sub").evaluate(scope) is plain.sub
    assert tel.compile_expr("o").evaluate_raw(scope) is plain and tel.compile_expr("n").evaluate_raw(scope) is scope.values["n"]
    assert tel.compile_expr("o.watched").evaluate(scope) == "w"


def test_a_class_can_narrow_what_an_expression_reads_of_it():
    scope = expr.MapScope({"o": Narrow()})
    assert both("o.shown", scope) == 1
    both_fail("o.hidden", scope)


def test_nothing_that_could_run_code_is_wrapped_or_readable():
    scope = expr.MapScope({"os": os, "f": print, "cls": Plain, "mod": os.path})
    for source in ("os.name", "os.path.sep", "f.__name__", "cls.title", "mod.sep"):
        with pytest.raises(tel.ExprError):
            tel.compile_expr(source).evaluate(scope)
    assert tel.compile_expr("f").evaluate(scope) is print  # a function can be the value, and nothing else
    with pytest.raises(tel.ExprError):
        tel.compile_expr("f(1)")


def test_a_signal_inside_a_list_or_a_mapping_is_not_read_mid_expression():
    """`expr.py` read every Signal it met; TEL reads attributes itself, so only the scope's names and the attributes of an object are unwrapped. A list of Signals, or a
    dict holding one, is not: the value is the Signal (and `.get()` still reads it)."""
    scope = expr.MapScope({"rows": [Signal(1)], "d": {"k": Signal(2)}})
    assert expr.compile_expr("rows[0] + 1").evaluate(scope) == 2 and expr.compile_expr("d.k + 1").evaluate(scope) == 3
    for source in ("rows[0] + 1", "d.k + 1"):
        with pytest.raises(tel.ExprError) as error:
            tel.compile_expr(source).evaluate(scope)
        assert error.value.code == "value-not-plain"
    assert tel.compile_expr("rows[0].get() + 1").evaluate(scope) == 2 and tel.compile_expr("d.k.get() + 1").evaluate(scope) == 3
    assert tel.compile_expr("rows[0]").evaluate(scope) == 1  # ending in a Signal, it is read


# -- templates --------------------------------------------------------------------------------------------------------------------------------------------


def test_a_template_with_one_part_keeps_the_type_and_otherwise_makes_text():
    scope = expr.MapScope({"n": Signal(3), "name": None, "items": [1]})
    template = tel.compile_template("{{ n }}")
    assert template.single and template.evaluate(scope) == 3 and tel.compile_template("{{ items }}").evaluate(scope) == [1]
    text = tel.compile_template("n is {{ n }} and name is [{{ name }}]")
    assert not text.single and text.evaluate(scope) == "n is 3 and name is []"
    assert text.names == {"n", "name"} and [type(p).__name__ for p in text.parts] == ["str", "TelExpr", "str", "TelExpr", "str"]
    assert tel.compile_template("plain text") is None and expr.compile_template("plain text") is None
    assert tel.compile_template("a {{ {'k': {'j': 1}}['k']['j'] }} b").evaluate(scope) == "a 1 b"
    assert tel.compile_template("{{ n }}").is_reactive(expr.MapScope({}, reactive={"n"})) and not text.is_reactive(expr.MapScope({}))


def test_a_nested_template_works_out_each_string_and_keeps_the_shape():
    scope = expr.MapScope({"who": "ada", "n": 2})
    nested = tel.TelNestedTemplate([{"text": tel.compile_template("Hi {{ who }}"), "count": tel.compile_template("{{ n }}"), "plain": "x"}, "y"])
    assert nested.evaluate(scope) == [{"text": "Hi ada", "count": 2, "plain": "x"}, "y"]
    assert nested.names == {"who", "n"} and nested.is_reactive(expr.MapScope({}, reactive={"n"})) and not nested.is_reactive(expr.MapScope({}))


# -- errors -----------------------------------------------------------------------------------------------------------------------------------------------


def where(error):
    return error.file, error.line, error.column, error.end_column


ORIGIN_OLD, ORIGIN_NEW = expr.Origin("Main_View.tdl", 12, 8), tel.Origin("Main_View.tdl", 12, 8)


@pytest.mark.parametrize("source", [
    "1 + zork", "  count + zork", "count + 'a'", "count / 0", "[i for i in count]", "items[5]", "d.nope", "o.nothing", "clmap(1)", "1 +", "a b", "x if", "len(", "lambda: 1",
    "count.set(1)", "name.upper", "range(10 ** 7)", "7 % 'a'",
])
def test_an_error_names_the_file_line_and_column_as_expr_did(source):
    scope = expr.MapScope({"count": 1, "items": [1], "d": {"k": 1}, "o": SimpleNamespace(), "name": "ada"})
    with pytest.raises(expr.ExprError) as old:
        expr.compile_expr(source, origin=ORIGIN_OLD).evaluate(scope)
    with pytest.raises(tel.ExprError) as new:
        tel.compile_expr(source, origin=ORIGIN_NEW).evaluate(scope)
    assert new.value.file == "Main_View.tdl" and str(new.value).startswith(f"Main_View.tdl:{new.value.line}:{new.value.column + 1}: ")
    assert new.value.code and where(new.value)[:2] == where(old.value)[:2]
    if source != "1 +":  # at the end of the input Python's own offset is one on from TEL's
        # the span's end is not compared: TEL gives one for a syntax error and for a whole call that is refused, expr.py did not
        assert where(old.value)[:3] == where(new.value)[:3], (old.value.render(), new.value.render())


def test_an_error_has_a_hint_and_draws_a_caret():
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr("cnt + 1", origin=tel.Origin("v.tdl", 3, 4)).evaluate(expr.MapScope({"count": 1}))
    assert error.value.hint == "did you mean 'count'" and error.value.code == "unknown-name"
    assert str(error.value) == "v.tdl:3:5: 'cnt' is not defined (did you mean 'count')"
    assert error.value.render().splitlines()[1:] == ["    cnt + 1", "    ^^^"]


def test_the_origin_moves_past_leading_space_and_lines_as_expr_does():
    scope = expr.MapScope({"a": 1})
    for source in ("  a + zork", "\n  a +\n  zork", "\n\n   zork"):
        with pytest.raises(expr.ExprError) as old:
            expr.compile_expr(source, origin=ORIGIN_OLD).evaluate(scope)
        with pytest.raises(tel.ExprError) as new:
            tel.compile_expr(source, origin=ORIGIN_NEW).evaluate(scope)
        assert where(old.value)[:3] == where(new.value)[:3], (source, where(old.value), where(new.value))
    assert tel.compile_expr(" \n  a", origin=ORIGIN_NEW).origin == tel.Origin("Main_View.tdl", 13, 2)


def test_without_an_origin_the_position_is_in_the_text_and_has_no_file():
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr("a +  zork").evaluate(expr.MapScope({"a": 1}))
    assert error.value.file is None and (error.value.line, error.value.column) == (1, 5) and str(error.value).startswith("'zork'")


def test_an_error_in_a_template_points_at_its_own_part():
    text = "Hello {{ name }}, you have {{ coutn }} new"
    scope = expr.MapScope({"name": "ada", "count": 2})
    with pytest.raises(expr.ExprError) as old:
        expr.compile_template(text, origin=ORIGIN_OLD).evaluate(scope)
    with pytest.raises(tel.ExprError) as new:
        tel.compile_template(text, origin=ORIGIN_NEW).evaluate(scope)
    assert where(old.value) == where(new.value) and new.value.hint == "did you mean 'count'"
    assert new.value.column == 8 + text.index("coutn")
    multi = "line one\n  {{ zork }}"
    with pytest.raises(expr.ExprError) as old:
        expr.compile_template(multi, origin=ORIGIN_OLD).evaluate(scope)
    with pytest.raises(tel.ExprError) as new:
        tel.compile_template(multi, origin=ORIGIN_NEW).evaluate(scope)
    assert where(old.value) == where(new.value)


@pytest.mark.parametrize("text", ["a {{ b", "a {{ }} b", "a {{ b + }} c", "{{ lambda: 1 }}", "{{ _x }}"])
def test_a_template_that_does_not_read_is_an_error_at_the_part(text):
    with pytest.raises(expr.ExprError):
        expr.compile_template(text, origin=ORIGIN_OLD)
    with pytest.raises(tel.ExprError) as new:
        tel.compile_template(text, origin=ORIGIN_NEW)
    assert new.value.file == "Main_View.tdl" and new.value.line == 12


def test_a_limit_is_an_error_with_its_code():
    scope = expr.MapScope({"n": 10 ** 4})
    for source, code in (("range(n * n)", "limit-range"), ("[i for i in range(n) for j in range(n)]", "limit-steps"), ("2 ** 65", "limit-pow-exponent"), ("'x' * 10 ** 7", "limit-sequence")):
        with pytest.raises(tel.ExprError) as error:
            tel.compile_expr(source).evaluate(scope)
        assert error.value.code == code, (source, error.value)
    with pytest.raises(tel.ExprError) as long:
        tel.compile_expr("1 + " * 600 + "1")
    assert long.value.code in ("limit-source", "limit-nodes", "limit-depth")
    small = tel.Limits(max_steps=50)
    with pytest.raises(tel.ExprError) as steps:
        tel.compile_expr("sum([i for i in range(100)])", limits=small).evaluate(scope)
    assert steps.value.code == "limit-steps"


def test_a_source_that_is_not_text_is_an_error_and_the_origin_may_be_any_object_with_a_file_line_and_column():
    for bad in (None, 3, b"1"):
        with pytest.raises(tel.ExprError, match="an expression is text"):
            tel.compile_expr(bad)
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr("zork", origin=expr.Origin("w.tdl", 2, 6)).evaluate(expr.MapScope())
    assert where(error.value) == ("w.tdl", 2, 6, 10)
    assert isinstance(error.value, ValueError)


def test_an_error_inside_a_scope_lookup_that_is_not_a_missing_name_is_the_applications_bug():
    class Broken:
        def lookup(self, name):
            raise RuntimeError("bug")

    with pytest.raises(RuntimeError):
        tel.compile_expr("x").evaluate(Broken())

    class Missing:
        def lookup(self, name):
            raise AttributeError(name)

    with pytest.raises(tel.ExprError, match="'x' is not defined"):
        tel.compile_expr("x").evaluate(Missing())


# -- where TEL is stricter or different, as listed ----------------------------------------------------------------------------------------------------------


def test_tel_refuses_when_the_text_is_read_what_expr_refused_when_it_ran():
    for source in ("items.append(1)", "d.pop('k')", "isinstance(x, (int, str))", "2 ** 100000", "[f(1) for f in [len]]", "'{}'.format(x)"):
        expr.compile_expr(source)  # compiles
        with pytest.raises(expr.ExprError):
            expr.compile_expr(source).evaluate(expr.MapScope({"items": [1], "d": {"k": 1}, "x": 1}))
        with pytest.raises(tel.ExprError):
            tel.compile_expr(source)  # refused at once


def test_an_underscore_alone_is_refused_as_a_name_and_a_long_template_is_refused_as_a_whole():
    assert expr.compile_expr("_").evaluate(expr.MapScope({"_": 1})) == 1
    with pytest.raises(tel.ExprError):
        tel.compile_expr("_")
    long = "x" * 2100 + " {{ a }}"
    assert expr.compile_template(long).evaluate(expr.MapScope({"a": 1})).endswith(" 1")
    with pytest.raises(tel.ExprError) as error:
        tel.compile_template(long)
    assert error.value.code == "limit-source"
