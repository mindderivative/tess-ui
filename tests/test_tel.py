"""What tess-ui adds to TEL (`tess_ui.tel`): the order names resolve in, the host functions and methods, what an evaluation reads (the reactive layer), the errors
and where they point, the handler steps. TEL's own grammar, sandbox and limits are tested by `tess-el` and, as tess-ui meets them, in `test_expressions.py`.
"""

import datetime
import os
from types import SimpleNamespace

import pytest

from tess_ui import tel
from tess_ui.reactive import Computed, Effect, Signal
from tess_ui.spec.compose import Scope
from tests.helpers import MapScope, parts, slot


def value(source, scope):
    return tel.compile_expr(source).evaluate(scope)


def fails(source, scope):
    """The `ExprError` the expression gives when it is read or run."""
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr(source).evaluate(scope)
    return error.value


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
    assert value("name", loop) == "loop name"
    assert value("name", params) == "state name" and value("name", state) == "state name"
    assert value("title", loop) == "param title"  # a param over the state's own
    assert value("title", state) == "state title"
    assert value("label", loop) == "param label"
    assert value("items", loop) == [1, 2, 3]
    assert tel.compile_expr("name").evaluate(Scope(None, {}, root=viewmodel)) == "viewmodel name"


def test_the_viewmodels_signals_and_computed_values_read_as_their_values():
    viewmodel, state, params, loop = views_scopes()
    assert value("count + 1", loop) == 2
    assert value("total * 2", loop) == 12
    assert value("not open", loop) is True
    viewmodel.count.set(5)
    assert value("count", loop) == 5


def test_app_is_the_last_name_and_a_view_model_attribute_of_that_name_wins():
    app = SimpleNamespace(width_class="compact")

    class Actions:
        def __call__(self, path):
            return None

        @staticmethod
        def app():
            return app

    scope = Scope(None, {}, root=SimpleNamespace(), actions=Actions())
    assert value("app.width_class", scope) == "compact"
    assert value("app.width_class == 'compact'", scope) is True
    own = Scope(None, {}, root=SimpleNamespace(app=SimpleNamespace(width_class="own")), actions=Actions())
    assert value("app.width_class", own) == "own"


def test_the_built_in_functions_are_last_and_a_name_in_the_scope_does_not_change_what_a_call_means():
    assert value("len", Scope(None, {"len": "mine"})) == "mine"  # read as a value, the scope's name wins
    assert value("len([1, 2])", Scope(None, {"len": "mine"})) == 2  # called, it is the function
    assert value("max(a, b)", Scope(None, {"a": 1, "b": 2})) == 2


def test_names_that_do_not_exist_are_errors_and_underscore_names_do_not_exist():
    _, _, _, loop = views_scopes()
    error = fails("nmae", loop)
    assert error.code == "unknown-name" and "did you mean 'name'" in str(error)
    fails("count + missing", loop)
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

    scope = MapScope({"n": Strict(1)})
    assert not hasattr(tel.adapt(scope), "assign") and not hasattr(tel.adapt(scope), "call_action")
    assert tel.compile_expr("n + 1").evaluate(scope) == 2
    for text in ("n = 2", "n += 1", "n.set(2)"):
        with pytest.raises(tel.ExprError):
            tel.compile_expr(text).evaluate(scope)


def test_event_is_a_name_only_when_the_caller_gives_one():
    scope = MapScope({"n": 1})
    event = SimpleNamespace(key="space", ctrl=False)
    assert tel.compile_expr("event.key == 'space' and n == 1").evaluate(scope, event=event) is True
    assert tel.adapt(scope, event=event).lookup("event").key == "space"
    with pytest.raises(tel.ExprError, match="'event' is not defined"):
        tel.compile_expr("event.key").evaluate(scope)
    assert "event" in tel.adapt(scope, event=event).names() and "event" not in tel.adapt(scope).names()
    assert tel.adapt(tel.adapt(scope)) is not None and tel.adapt(scope).scope is scope


# -- the functions ----------------------------------------------------------------------------------------------------------------------------------------


def test_the_host_functions_are_the_ones_tel_leaves_to_its_host():
    import tess_el._whitelist as whitelist

    assert set(tel.HOST_FUNCTIONS) == {"format_number", "pluralize", "date_add_days", "date_weekday", "days_in_month", "format_date", "current_date", "density_token", "body_role", "dense_text_size", "mnemonic_plain", "mnemonic_of", "mnemonic_runs", "tree_rows", "tree_row"}
    assert tel.BUILTIN_NAMES == whitelist.BUILTIN_NAMES | set(tel.HOST_FUNCTIONS)


@pytest.mark.parametrize("source, expected", [
    ("format_number(1234567.891, 2)", "1,234,567.89"), ("format_number(5)", "5"), ("format_number(x, 1)", "2.5"), ("pluralize(1, 'item')", "item"),
    ("pluralize(2, 'item')", "items"), ("pluralize(2, 'child', 'children')", "children"), ("pluralize(0, 'box', 'boxes')", "boxes"), ("clamp(15, 0, 10)", 10),
    ("clamp(-3, 0, 10)", 0), ("date_add_days('2026-11-14', 30)", "2026-12-14"), ("date_add_days('2026-03-01', -1)", "2026-02-28"),
    ("date_weekday('2026-11-14')", 5), ("days_in_month(2024, 2)", 29), ("days_in_month(2026, 2)", 28), ("days_in_month(2026, 12)", 31),
    ("format_date('2026-11-14')", "Sat, Nov 14"), ("format_date('2026-11-14', '%A, %B %e %Y')", "Saturday, November 14 2026"),
    ("format_date('2026-01-05', '%d/%m/%y %j %% %b %a')", "05/01/26 005 % Jan Mon"), ("format_date(d, '%Y')", "2024"),
    ("len(format_date('2026-11-14'))", 11), ("[format_date(date_add_days('2026-11-14', k), '%a') for k in range(3)]", ["Sat", "Sun", "Mon"]),
])
def test_the_host_functions(source, expected):
    assert value(source, MapScope({"x": 2.5, "d": "2024-02-29"})) == expected


def test_the_clock_function_is_the_clock():
    assert tel.compile_expr("current_date()").evaluate(MapScope()) == datetime.date.today().isoformat()


def test_a_function_that_fails_says_why():
    error = fails("format_date('not a date')", MapScope())
    assert "is not a date written year-month-day" in str(error)
    assert error.code == "bad-call" and str(error).startswith("format_date() failed: ValueError: ")
    assert "'%Q' is not a date field" in str(fails("format_date('2026-11-14', '%Q')", MapScope()))


def test_the_reason_of_one_failure_is_never_given_to_another():
    with pytest.raises(tel.ExprError):
        tel.compile_expr("format_date('nope')").evaluate(MapScope())
    with pytest.raises(tel.ExprError) as other:
        tel.compile_expr("int('x')").evaluate(MapScope())
    assert "format_date" not in str(other.value) and other.value.code == "bad-call"
    with pytest.raises(tel.ExprError) as limit:
        tel.compile_expr("range(10 ** 7)").evaluate(MapScope())
    assert limit.value.code == "limit-range"


def test_an_unknown_function_is_refused_when_the_text_is_read_with_the_nearest_name():
    with pytest.raises(tel.ExprError, match="did you mean 'clamp'") as error:
        tel.compile_expr("clmap(1, 0, 2)")
    assert error.value.code == "call-not-function"


def test_the_methods_are_the_whitelist():
    scope = MapScope({"s": " Ada ", "d": {"k": 1, "j": 2}, "t": (1, 2, 2), "items": [3, 1]})
    for source, expected in (("s.strip().upper()", "ADA"), ("s.split('d')", [" A", "a "]), ("'-'.join(['a', 'b'])", "a-b"), ("d.get('k')", 1), ("d.get('zz', 0)", 0),
                             ("list(d.keys())", ["k", "j"]), ("list(d.items())", [("k", 1), ("j", 2)]), ("d.values()", [1, 2]), ("t.count(2)", 2),
                             ("items.index(1)", 1), ("s.zfill(8)", "000 Ada "), ("s.removeprefix(' ')", "Ada "), ("s.center(9)", "   Ada   ")):
        assert value(source, scope) == expected, source
    for source in ("items.append(1)", "items.sort()", "d.update({})", "s.format()", "s.encode()"):
        with pytest.raises(tel.ExprError):
            tel.compile_expr(source)


# -- what an evaluation reads (the reactive layer) --------------------------------------------------------------------------------------------------------


def test_a_computed_over_an_expression_depends_on_what_the_evaluation_read():
    flag, a, b = Signal(True), Signal(1), Signal(2)
    scope = MapScope({"flag": flag, "a": a, "b": b})
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
    scope = MapScope({"app": SimpleNamespace(state=state)})
    seen: list[str] = []
    template = tel.compile_template(parts("Hello ", slot(" app.state.user.upper() "), "!"))
    Effect(lambda: seen.append(template.evaluate(scope)))
    state.user.set("grace")
    assert seen == ["Hello ADA!", "Hello GRACE!"]


def test_tracked_evaluation_says_which_paths_were_read():
    scope = MapScope({"flag": True, "a": 1, "b": 2, "app": SimpleNamespace(state=SimpleNamespace(user="ada"))})
    value, reads = tel.compile_expr("a if flag else b").evaluate_tracked(scope)
    assert value == 1 and reads == {"flag", "a"}
    value, reads = tel.compile_expr("app.state.user + str(a)").evaluate_tracked(scope)
    assert value == "ada1" and reads == {"app.state.user", "a"}
    program = tel.compile_expr("a if flag else b")
    assert program.names == {"a", "b", "flag"} and program.paths == {"a", "b", "flag"}
    _, reads = tel.compile_template(parts(slot(" flag "), " ", slot(" b "))).evaluate_tracked(scope)
    assert reads == {"flag", "b"}  # the union over the slots
    _, reads = tel.compile_template(parts(slot(" a if flag else b "), " ", slot(" b "))).evaluate_tracked(scope)
    assert reads == {"flag", "a", "b"}


def test_names_and_reactivity_are_what_the_callers_ask():
    scope = MapScope({"count": Signal(1), "label": "x"}, reactive={"count"})
    assert tel.compile_expr("count + 1").is_reactive(scope) and not tel.compile_expr("label.upper()").is_reactive(scope)
    assert tel.compile_expr("[i * k for i in items]").names == {"k", "items"}
    assert tel.compile_expr("len(items) > 0").names == {"items"}  # the function is not a name it reads
    assert tel.compile_expr("count").bare_name() == "count" and tel.compile_expr("count + 1").bare_name() is None and tel.compile_expr("1").bare_name() is None
    assert not tel.compile_expr("count").is_reactive(object())  # a scope that cannot say is static
    frames = Scope(None, {"s": Signal(1), "t": 2}, root=SimpleNamespace(vm=Signal(3)))
    assert tel.compile_expr("s + vm").is_reactive(frames) and not tel.compile_expr("t + 1").is_reactive(frames)


def test_evaluate_raw_keeps_the_signal_for_a_two_way_property():
    count = Signal(1)
    scope = MapScope({"count": count})
    assert tel.compile_expr("count").evaluate_raw(scope) is count and tel.compile_expr("count").evaluate(scope) == 1
    assert tel.compile_expr("count + 1").evaluate_raw(scope) == 2
    with pytest.raises(tel.ExprError, match="'nothing' is not defined"):
        tel.compile_expr("nothing").evaluate_raw(scope)


# -- Signals and objects of the application's ------------------------------------------------------------------------------------------------------------


def test_get_is_the_signals_own_read_and_on_a_signal_of_a_dict_it_is_not():
    scope = MapScope({"count": Signal(4), "items": Signal([1, 2]), "none": Signal(None), "user": SimpleNamespace(name=Signal("ada"))})
    assert value("count.get() * 2", scope) == 8
    assert value("items.get()", scope) == [1, 2] and value("none.get()", scope) is None and value("user.name.get().upper()", scope) == "ADA"
    # a dict has its own `get`, which needs a key: on a Signal that holds one, write the name
    with pytest.raises(tel.ExprError):
        tel.compile_expr("d.get()").evaluate(MapScope({"d": Signal({"k": 1})}))
    assert tel.compile_expr("d").evaluate(MapScope({"d": Signal({"k": 1})})) == {"k": 1}
    assert tel.compile_expr("n.get()").evaluate(MapScope({"n": 3})) == 3  # on a plain value `get()` is the value


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
    scope = MapScope({"o": Plain()})
    assert value("o.title", scope) == "t" and value("o.items[1]", scope) == 2
    assert value("o.sub.level + 1", scope) == 4  # a Signal that is an attribute reads as its value, in the middle of an expression too
    assert value("o.sub.more.deep + o.watched", scope) == "dw"
    assert value("[o.watched, o.sub.level]", scope) == ["w", 3]
    for source in ("o.method", "o.method()", "o.nothing", "o + 1", "o == o", "str(o)", "[o][0] + 1", "o.sub.nothing"):
        fails(source, scope)
    with pytest.raises(tel.ExprError) as private:
        tel.compile_expr("o._secret")
    assert private.value.code == "private-attribute"


def test_an_object_that_is_the_result_is_the_object_and_not_a_wrapper():
    plain = Plain()
    scope = MapScope({"o": plain, "n": Signal(plain)})
    assert tel.compile_expr("o").evaluate(scope) is plain and tel.compile_expr("n").evaluate(scope) is plain
    assert tel.compile_expr("o.sub").evaluate(scope) is plain.sub
    assert tel.compile_expr("o").evaluate_raw(scope) is plain and tel.compile_expr("n").evaluate_raw(scope) is scope.values["n"]
    assert tel.compile_expr("o.watched").evaluate(scope) == "w"


def test_a_class_can_narrow_what_an_expression_reads_of_it():
    scope = MapScope({"o": Narrow()})
    assert value("o.shown", scope) == 1
    fails("o.hidden", scope)


def test_nothing_that_could_run_code_is_wrapped_or_readable():
    scope = MapScope({"os": os, "f": print, "cls": Plain, "mod": os.path})
    for source in ("os.name", "os.path.sep", "f.__name__", "cls.title", "mod.sep"):
        with pytest.raises(tel.ExprError):
            tel.compile_expr(source).evaluate(scope)
    assert tel.compile_expr("f").evaluate(scope) is print  # a function can be the value, and nothing else
    with pytest.raises(tel.ExprError):
        tel.compile_expr("f(1)")


def test_a_signal_inside_a_list_or_a_mapping_is_not_read_mid_expression():
    """TEL reads attributes itself, so only the scope's names and the attributes of an object are unwrapped. A list of Signals, or a dict holding one, is not:
    the value is the Signal (and `.get()` still reads it)."""
    scope = MapScope({"rows": [Signal(1)], "d": {"k": Signal(2)}})
    for source in ("rows[0] + 1", "d.k + 1"):
        with pytest.raises(tel.ExprError) as error:
            tel.compile_expr(source).evaluate(scope)
        assert error.value.code == "value-not-plain"
    assert tel.compile_expr("rows[0].get() + 1").evaluate(scope) == 2 and tel.compile_expr("d.k.get() + 1").evaluate(scope) == 3
    assert tel.compile_expr("rows[0]").evaluate(scope) == 1  # ending in a Signal, it is read


# -- templates: a text is literal parts and slots, split by Tesserae (TEL has no template form) ------------------------------------------------------------------


def test_a_template_with_one_slot_keeps_the_type_and_otherwise_makes_text():
    scope = MapScope({"n": Signal(3), "name": None, "items": [1], "flag": True})
    template = tel.compile_template(parts(slot(" n ")))
    assert template.single and template.evaluate(scope) == 3
    assert tel.compile_template(parts(slot(" items "))).evaluate(scope) == [1]
    assert tel.compile_template(parts(slot(" flag "))).evaluate(scope) is True
    text = tel.compile_template(parts("n is ", slot(" n "), " and name is [", slot(" name "), "]"))
    assert not text.single and text.evaluate(scope) == "n is 3 and name is []"  # None is empty text
    assert text.names == {"n", "name"} and [type(p).__name__ for p in text.parts] == ["str", "Expr", "str", "Expr", "str"]
    assert tel.compile_template(parts("a ", slot(" {'k': {'j': 1}}['k']['j'] "), " b")).evaluate(scope) == "a 1 b"
    assert tel.compile_template(parts("[", slot(" n "), "]")).evaluate(scope) == "[3]"  # a literal around the one slot makes it text
    assert tel.compile_template(parts(slot(" n "))).is_reactive(MapScope({}, reactive={"n"})) and not text.is_reactive(MapScope({}))


def test_several_slots_are_joined_as_text_with_each_value_as_text():
    scope = MapScope({"a": 1.5, "b": True, "c": [1, "x"], "d": None, "e": "é"})
    assert tel.compile_template(parts(slot("a"), slot("b"), slot("c"), slot("d"), slot("e"))).evaluate(scope) == "1.5True[1, 'x']é"
    assert tel.compile_template(parts(slot(" e "), "")).evaluate(scope) == "é"


def test_a_slots_text_is_compiled_as_written_and_braces_and_delimiters_in_it_are_ordinary_text():
    scope = MapScope({"x": "q"})
    assert tel.compile_template(parts("[", slot(" '}}' + x "), "]")).evaluate(scope) == "[}}q]"
    assert tel.compile_template(parts(slot(" {'a': {'b': 1}}['a']['b'] "))).evaluate(scope) == 1
    assert tel.compile_template(parts("{{ ", slot(" x "), " }}")).evaluate(scope) == "{{ q }}"  # literal braces are literal text, not a second slot syntax
    assert tel.compile_template(parts(slot(" '<|' + x + '|>' "))).evaluate(scope) == "<|q|>"


def test_parts_is_the_text_as_tdl_writes_it_and_a_plain_string_is_never_a_template():
    made = parts("Battery ", slot(" level "), "%")
    assert isinstance(made, str) and made == "Battery <| level |>%" and made.items[0] == "Battery " and made.items[1].text == " level "
    assert repr(tel.compile_template(made)) == "Template('Battery <| level |>%')"
    for plain in ("Battery {{ level }}%", "Battery <| level |>%"):
        with pytest.raises(TypeError):
            tel.compile_template(plain)
    import copy
    assert copy.deepcopy(made).items == made.items


def test_a_value_that_is_not_plain_cannot_be_used_in_a_text_of_several_slots():
    scope = MapScope({"obj": SimpleNamespace(v=1), "ok": "x"})
    assert tel.compile_template(parts(slot(" obj.v "), slot(" ok "))).evaluate(scope) == "1x"
    with pytest.raises(tel.ExprError) as error:
        tel.compile_template(parts("a ", slot(" ok "), " b ", slot(" obj ", 12, 30))).evaluate(scope)
    assert error.value.code == "value-not-plain" and str(error.value).startswith("Main_View.tdl:12:32: a SimpleNamespace cannot be used in text")
    assert error.value.hint == "read one of its attributes instead"
    assert tel.compile_template(parts(slot(" obj "))).evaluate(scope) is scope.values["obj"]  # one slot is the value itself


def test_a_nested_template_works_out_each_text_and_keeps_the_shape():
    scope = MapScope({"who": "ada", "n": 2})
    nested = tel.NestedTemplate([{"text": tel.compile_template(parts("Hi ", slot(" who "))), "count": tel.compile_template(parts(slot(" n "))), "plain": "x"}, "y"])
    assert nested.evaluate(scope) == [{"text": "Hi ada", "count": 2, "plain": "x"}, "y"]
    assert nested.names == {"who", "n"} and nested.is_reactive(MapScope({}, reactive={"n"})) and not nested.is_reactive(MapScope({}))


def test_each_slot_has_a_budget_of_its_own_and_the_text_is_held_to_the_string_and_source_limits():
    scope = MapScope({"items": list(range(30))})
    expensive = " sum([i for i in items]) "
    small = tel.Limits(max_steps=150)  # one such slot takes about 118 steps
    with pytest.raises(tel.ExprError) as one:
        tel.compile_template(parts(slot(expensive)), limits=tel.Limits(max_steps=100)).evaluate(scope)
    assert one.value.code == "limit-steps"
    two = tel.compile_template(parts(slot(expensive), "/", slot(expensive)), limits=small)
    assert two.evaluate(scope) == "435/435"  # a text of two slots may take twice the steps of one: the budget is each slot's
    with pytest.raises(tel.ExprError) as long:
        tel.compile_template(parts(slot(" a "), slot(" b ")), limits=tel.Limits(max_string=10)).evaluate(MapScope({"a": "123456", "b": "123456"}))
    assert long.value.code == "limit-string" and "over 10 characters" in str(long.value)
    with pytest.raises(tel.ExprError) as source:
        tel.compile_template(parts("x" * 2100, slot(" a ")))
    assert source.value.code == "limit-source"
    assert tel.compile_template(parts("x" * 1000, slot(" a "), "x" * 900)).evaluate(MapScope({"a": 1})) == "x" * 1000 + "1" + "x" * 900


# -- errors -----------------------------------------------------------------------------------------------------------------------------------------------


def where(error):
    return error.file, error.line, error.column, error.end_column


ORIGIN = tel.Origin("Main_View.tdl", 12, 8)


@pytest.mark.parametrize("source, line, column", [
    ("1 + zork", 12, 12), ("  count + zork", 12, 18), ("count + 'a'", 12, 8), ("count / 0", 12, 8), ("[i for i in count]", 12, 20), ("items[5]", 12, 8),
    ("d.nope", 12, 8), ("o.nothing", 12, 8), ("clmap(1)", 12, 8), ("1 +", 12, 8), ("a b", 12, 10), ("len(", 12, 11), ("lambda: 1", 12, 8),
])
def test_an_error_names_the_file_line_and_column(source, line, column):
    scope = MapScope({"count": 1, "items": [1], "d": {"k": 1}, "o": SimpleNamespace(), "name": "ada"})
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr(source, origin=ORIGIN).evaluate(scope)
    assert error.value.file == "Main_View.tdl" and (error.value.line, error.value.column) == (line, column)
    assert str(error.value).startswith(f"Main_View.tdl:{error.value.line}:{error.value.column + 1}: ") and error.value.code


def test_an_error_has_a_hint_and_draws_a_caret():
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr("cnt + 1", origin=tel.Origin("v.tdl", 3, 4)).evaluate(MapScope({"count": 1}))
    assert error.value.hint == "did you mean 'count'" and error.value.code == "unknown-name"
    assert str(error.value) == "v.tdl:3:5: 'cnt' is not defined (did you mean 'count')"
    assert error.value.render().splitlines()[1:] == ["    cnt + 1", "    ^^^"]


def test_the_origin_moves_past_leading_space_and_lines():
    scope = MapScope({"a": 1})
    for source, line, column in (("  a + zork", 12, 14), ("\n  (a +\n  zork)", 14, 2), ("\n\n   zork", 14, 3)):
        error = fails_at(source, scope)
        assert (error.line, error.column) == (line, column), (source, error.line, error.column)
    assert tel.compile_expr(" \n  a", origin=ORIGIN).origin == tel.Origin("Main_View.tdl", 13, 2)


def fails_at(source, scope):
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr(source, origin=ORIGIN).evaluate(scope)
    return error.value


def test_without_an_origin_the_position_is_in_the_text_and_has_no_file():
    with pytest.raises(tel.ExprError) as error:
        tel.compile_expr("a +  zork").evaluate(MapScope({"a": 1}))
    assert error.value.file is None and (error.value.line, error.value.column) == (1, 5) and str(error.value).startswith("'zork'")


def test_an_error_in_a_template_points_at_its_own_slot():
    made = parts("Hello ", slot(" name ", 12, 16), ", you have ", slot(" coutn ", 12, 37), " new")  # the text starts at column 8 of line 12, `coutn` at 38
    scope = MapScope({"name": "ada", "count": 2})
    with pytest.raises(tel.ExprError) as error:
        tel.compile_template(made).evaluate(scope)
    assert error.value.hint == "did you mean 'count'" and where(error.value) == ("Main_View.tdl", 12, 38, 43)
    with pytest.raises(tel.ExprError) as later:  # a slot on a later line of the file, with its own column
        tel.compile_template(parts("line one", slot(" ok ", 12, 15), " and ", slot(" zork ", 13, 4))).evaluate(MapScope({"ok": 1}))
    assert (later.value.line, later.value.column) == (13, 5) and str(later.value).startswith("Main_View.tdl:13:6: 'zork' is not defined")
    with pytest.raises(tel.ExprError) as bare:  # no origin: the position is in the slot's own text
        tel.compile_template(parts("a ", slot(" zork "))).evaluate(scope)
    assert bare.value.file is None and (bare.value.line, bare.value.column) == (1, 0)  # the text of the slot, without its surrounding space


@pytest.mark.parametrize("text, code", [(" b + ", "syntax-error"), (" lambda: 1 ", "disallowed-construct"), (" _x ", "private-name"), (" ", "empty-expression")])
def test_a_slot_that_does_not_read_is_an_error_at_that_slot_when_the_text_is_compiled(text, code):
    with pytest.raises(tel.ExprError) as new:
        tel.compile_template(parts("a ", slot(" fine ", 12, 10), " b ", slot(text, 12, 30), " c"))
    assert new.value.code == code and (new.value.file, new.value.line, new.value.column) == ("Main_View.tdl", 12, 31)


def test_a_limit_is_an_error_with_its_code():
    scope = MapScope({"n": 10 ** 4})
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
        tel.compile_expr("zork", origin=tel.Origin("w.tdl", 2, 6)).evaluate(MapScope())
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


# -- where TEL is strict ------------------------------------------------------------------------------------------------------------------------------------


def test_what_the_sandbox_refused_when_it_ran_is_refused_when_the_text_is_read():
    for source in ("items.append(1)", "d.pop('k')", "isinstance(x, (int, str))", "2 ** 100000", "[f(1) for f in [len]]", "'{}'.format(x)"):
        with pytest.raises(tel.ExprError):
            tel.compile_expr(source)  # refused at once


def test_an_underscore_alone_is_refused_as_a_name_and_a_long_template_is_refused_as_a_whole():
    with pytest.raises(tel.ExprError):
        tel.compile_expr("_")
    long = parts("x" * 2100, slot(" a "))
    with pytest.raises(tel.ExprError) as error:
        tel.compile_template(long)
    assert error.value.code == "limit-source"


# -- handlers: Set and Call steps -----------------------------------------------------------------------------------------------------------------------------


def test_each_step_sees_what_the_steps_before_it_wrote():
    scope = MapScope({"n": 1, "cmd": ""}, writable={"n", "cmd"})
    tel.compile_statements("n += 2; cmd = str(n)\nn *= (n +\n 1)").run(scope)
    assert scope.values == {"n": 12, "cmd": "3"}


def test_a_set_may_keep_the_result_of_an_action_and_a_call_is_a_step():
    seen = []
    scope = MapScope({"ok": None}, writable={"ok"}, actions={"copy": lambda text: seen.append(text) or True, "navigate.back": lambda: seen.append("back")})
    steps = tel.compile_statements("ok = copy(str(1 + 1)); navigate.back()")
    steps.run(scope)
    assert scope.values["ok"] is True and seen == ["2", "back"]
    assert [type(step).__name__ for step in steps.steps] == ["Set", "Call"] and sorted(call.callee for call in steps.called) == ["copy", "navigate.back"]
    assert steps.names == {"ok", "navigate"}


def test_a_call_that_is_no_action_is_the_expression_it_is_or_the_error():
    scope = MapScope({"n": 1}, writable={"n"})
    tel.compile_statements("str(n)").run(scope)  # a built-in function: nothing to write, nothing to fail
    with pytest.raises(tel.ExprError, match="is not a function"):
        tel.compile_statements("save(n)").run(scope)


def test_a_handler_is_assignments_and_calls_only_and_a_private_name_is_not_assigned():
    for text, message in (("if n: pass", "not available in a handler"), ("_x = 1", "private"), ("a, b = 1, 2", "assign to one name"), ("n |= 1", "not allowed here"), ("", "empty")):
        with pytest.raises(tel.ExprError, match=message):
            tel.compile_statements(text)


def test_the_timer_texts_and_the_position_of_a_mistake_in_a_step():
    steps = tel.compile_statements('after(500, "n = 1"); every(100, "n += 1"); x = 1', origin=tel.Origin("v.tdl", 5, 10))
    assert tel.timer_handlers(steps) == ["n = 1", "n += 1"]
    with pytest.raises(tel.ExprError) as error:
        tel.compile_statements("n = 1; m = nope + 1", origin=tel.Origin("v.tdl", 5, 10)).run(MapScope({"n": 0, "m": 0}, writable={"n", "m"}))
    assert (error.value.file, error.value.line, error.value.column) == ("v.tdl", 5, 10 + len("n = 1; m = "))
