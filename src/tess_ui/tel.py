"""tess-ui's expressions on TEL, the Tesserae Expression Language (`tess_el`): an adapter beside `tess_ui.expr`, which it will replace.

Nothing imports this module yet (piece 11a of `design/tdl-switch-plan.md`). It offers what the callers of `tess_ui.expr` use, with the same names and
shapes, so that a later piece can move them one by one: change the import, nothing else.

    expr = compile_expr("count + 1 if ready else 0", origin=Origin("Main_View.yaml", 12, 8))
    expr.evaluate(scope)                        # `scope` is any tess-ui scope: `lookup(name)`, optionally `names()` and `is_reactive(name)`

What the adapter adds to TEL, and nothing else:

- **A scope.** TEL asks a scope for plain values and never touches anything else; tess-ui's scopes hand out `Signal`s and `Computed`s. `adapt(scope)` is a
  scope that reads each one as its value, which is also what puts the read on `tess_ui.reactive`'s recording stack (`Signal.get` records it), so a
  `Computed` or `Effect` that evaluates an expression depends on exactly what the evaluation read. The order in which names resolve is the scope's own
  (`spec.compose.Scope`: loop variables and local state, params, the ViewModel, `app`), unchanged; the one name the adapter itself adds is `event`.
  A handler's `event` is an ordinary name to TEL, so it is put in front of the scope (`adapt(scope, event=...)`), as `expr.py` did.
- **The functions.** `HOST_FUNCTIONS` are the built-ins `expr.py` had that TEL dropped (`format_number`, `pluralize`, the date functions, `current_date`),
  registered with `functions=`. TEL's own built-ins and its method whitelist are the same as `expr.py`'s; `HOST_METHODS` adds only `get()`, the `Signal`'s
  own read, which a view may call (`tests/test_tel.py` pins both facts).
- **The errors.** A `TelError` becomes an `ExprError`: the one class callers catch, with `expr.py`'s fields (`message`, `hint`, `file`, `line` and a
  0-based `column` in the file, `source`, `render()`), and the TEL `code` on top for tests and tools. The message is TEL's, which keeps the hint
  ("did you mean ...") where TEL has one; a function that failed says why, as `expr.py` did.

Where `expr.py` and TEL differ (the cases that are not a function or an error class), `tests/tel_parity_known.json` lists each expression of the
repository's views, docs and tests that comes out differently, with the reason; `tests/test_tel_parity.py` keeps that list honest.
"""

from __future__ import annotations

import contextvars
import datetime
import decimal
import enum
import functools
import types
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable, Optional

import tess_el  # type: ignore[import-not-found,unused-ignore]

from tess_ui.reactive import Computed, Signal

__all__ = [
    "BUILTIN_NAMES", "DEFAULT_LIMITS", "HOST_FUNCTIONS", "HOST_METHODS", "LANGUAGE", "ExprError", "Limits", "Origin", "TelExpr", "TelNestedTemplate",
    "TelScope", "TelTemplate", "adapt", "compile_expr", "compile_template"]

#: The language version tess-ui declares to TEL.
LANGUAGE = "0.1"
Limits = tess_el.Limits
DEFAULT_LIMITS = tess_el.DEFAULT_LIMITS
MISSING: Any = object()


# -- errors -------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Origin:
    """Where an expression's text starts in its file, so errors can name the file, line and column: `line` is 1-based, `column` 0-based (the column of
    the first character of the text). Anything with `file`, `line` and `column` (`tess_ui.expr.Origin`) is taken as one."""

    file: Optional[str] = None
    line: int = 1
    column: int = 0


class ExprError(ValueError):
    """A problem with an expression: it does not parse, uses something the language does not allow, names something that does not exist, goes over a
    limit, or fails to evaluate. `line` and `column` (1-based and 0-based) are in the *file* when an `Origin` was given, else in the expression text;
    `end_column` ends the span on that line (or is `None`). `code` is TEL's stable identifier for the problem (`unknown-name`, `limit-steps`, ...)."""

    def __init__(self, message: str, *, source: str = "", line: int = 1, column: int = 0, end_column: Optional[int] = None,
                 origin: Optional[Origin] = None, hint: Optional[str] = None, code: str = "") -> None:
        self.message = message
        self.source = source
        self.hint = hint
        self.code = code
        self.file = origin.file if origin else None
        self.text_line, self.text_column = line, column  # positions inside the text, mapped to the file's when the origin is known
        if origin is not None:
            self.line = origin.line + line - 1
            self.column = origin.column + column if line == 1 else column
        else:
            self.line, self.column = line, column
        self.end_column = None if end_column is None else self.column + (end_column - column)
        super().__init__(self._summary())

    def _summary(self) -> str:
        where = f"{self.file}:{self.line}:{self.column + 1}: " if self.file is not None else ""
        return f"{where}{self.message}" + (f" ({self.hint})" if self.hint else "")

    def render(self) -> str:
        """The message with the offending line of the expression and a caret under it."""
        lines = self.source.splitlines() or [""]
        line = lines[min(self.text_line, len(lines)) - 1]
        width = max(1, (self.end_column - self.column) if self.end_column is not None else 1)
        return f"{self}\n    {line}\n    {' ' * self.text_column}{'^' * width}"


#: The failure of the last host function (name, exception), kept so the error that TEL makes of it can say why: TEL's own message names the class
#: of the exception and never its text, because a text may hold values from the scope; these functions' texts are tess-ui's own.
_FAILURE: contextvars.ContextVar[Optional[tuple[str, BaseException]]] = contextvars.ContextVar("tess_ui_tel_failure", default=None)


def _error(err: Any, origin: Optional[Origin]) -> ExprError:
    """The `ExprError` of a `TelError`. `origin` is where the text the error came from starts, or `None` when none was given: TEL has already put its
    line and column in the file, and they are turned back into the origin of that text, which is what `ExprError` maps from."""
    message = err.message
    failure = _FAILURE.get()
    if err.code == "bad-call" and failure is not None and failure[0] in message and type(failure[1]).__name__ in message:
        message = f"{failure[0]}() failed: {type(failure[1]).__name__}: {failure[1]}"
    _FAILURE.set(None)
    if err.text_line is None or err.text_column is None:
        return ExprError(message, source=err.source, hint=err.hint, code=err.code)
    at: Optional[Origin] = None
    if origin is not None:
        at = Origin(err.file, err.line - err.text_line + 1, err.column - err.text_column if err.text_line == 1 else 0)
    end = None if err.text_end_column is None else err.text_end_column - 1
    return ExprError(message, source=err.source, line=err.text_line, column=err.text_column - 1, end_column=end, origin=at, hint=err.hint, code=err.code)


def _tel_origin(origin: Any) -> Any:
    if origin is None:
        return None
    return tess_el.Origin(origin.file, origin.line, origin.column + 1)


# -- the functions ------------------------------------------------------------------------------------------------------


def _format_number(x: Any, digits: Any = 0) -> str:
    return f"{x:,.{int(digits)}f}"


def _pluralize(n: Any, one: str, other: Optional[str] = None) -> str:
    return one if n == 1 else (other if other is not None else one + "s")


def _date(iso: Any) -> datetime.date:
    try:
        return datetime.date.fromisoformat(str(iso))
    except ValueError:
        raise ValueError(f"{iso!r} is not a date written year-month-day (2026-10-09)") from None


def _date_add_days(iso: Any, days: Any) -> str:
    """The date `days` after `iso` (before, when negative), as `year-month-day`."""
    return (_date(iso) + datetime.timedelta(days=int(days))).isoformat()


def _date_weekday(iso: Any) -> int:
    """0 for a Monday to 6 for a Sunday."""
    return _date(iso).weekday()


def _days_in_month(year: Any, month: Any) -> int:
    import calendar

    return calendar.monthrange(int(year), int(month))[1]


def _today() -> str:
    """Today's date, as `year-month-day`. It reads the clock, so an expression with it is not a function of its names alone."""
    return datetime.date.today().isoformat()


_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")


def _format_date(iso: Any, pattern: Any = "%a, %b %d") -> str:
    """`iso` written as `pattern` (`%a` a short weekday, `%A` the weekday, `%b` a short month, `%B` the month, `%d` and `%e` the day, `%m`, `%Y`, `%y`, `%j` and `%%`), in English."""
    d = _date(iso)
    names = {"a": _WEEKDAYS[d.weekday()][:3], "A": _WEEKDAYS[d.weekday()], "b": _MONTHS[d.month - 1][:3], "B": _MONTHS[d.month - 1], "d": f"{d.day:02d}",
             "e": str(d.day), "m": f"{d.month:02d}", "Y": str(d.year), "y": f"{d.year % 100:02d}", "j": f"{d.timetuple().tm_yday:03d}", "%": "%"}
    text, out, i = str(pattern), [], 0
    while i < len(text):
        if text[i] == "%":
            if i + 1 >= len(text) or text[i + 1] not in names:
                raise ValueError(f"format_date: {text[i:i + 2]!r} is not a date field")
            out.append(names[text[i + 1]])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def _recorded(name: str, function: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(function)
    def call(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except tess_el.TelError:
            raise
        except Exception as exc:  # noqa: BLE001 - TEL turns it into a `bad-call`; the adapter keeps the reason for the message
            _FAILURE.set((name, exc))
            raise

    return call


#: What an expression may call besides TEL's own built-ins (`len min max abs round sum str int float bool sorted reversed range enumerate zip any all
#: list dict tuple set isinstance clamp`): the functions `expr.py` had and TEL left to its host. Their behaviour is `expr.py`'s.
HOST_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "format_number": _format_number, "pluralize": _pluralize, "date_add_days": _date_add_days, "date_weekday": _date_weekday,
    "days_in_month": _days_in_month, "format_date": _format_date, "current_date": _today,
}
def _itself(value: Any) -> Any:
    return value


def _signal_get(signal: Any) -> Any:
    return signal.get()


#: The methods registered on top of TEL's whitelist (`str`: `lower upper ... removesuffix`, `list` and `tuple`: `index count`, `dict`: `get keys values items`,
#: which is `expr.py`'s): `get()`, because a view may say `count.get()` for a `Signal`'s own value. A scope's `Signal` is already read as its value, so on
#: a plain value `get()` is that value; on a `Signal` that reached the expression inside a list or a mapping it reads it. A `Signal` that holds a `dict` is the
#: one case that stays different: `d.get()` is the dict's own `get`, which needs a key (write `d`).
HOST_METHODS: dict[type, dict[str, Callable[..., Any]]] = {
    **{kind: {"get": _itself} for kind in (str, int, float, bool, type(None), list, tuple, set, frozenset)},
    Signal: {"get": _signal_get}, Computed: {"get": _signal_get},
}
_REGISTERED = {name: _recorded(name, function) for name, function in HOST_FUNCTIONS.items()}


#: Every function an expression may call: TEL's built-ins and `HOST_FUNCTIONS` (what `expr.BUILTIN_FUNCTIONS` was the keys of).
BUILTIN_NAMES: frozenset[str] = frozenset(tess_el._whitelist.BUILTIN_NAMES) | frozenset(HOST_FUNCTIONS)  # noqa: SLF001 - TEL has no public list of them


# -- the scope ----------------------------------------------------------------------------------------------------------


#: What an expression may operate on (TEL's inert values) and what it may never read an attribute of: neither is wrapped by `_Host`.
_PLAIN = (bool, int, float, str, type(None), list, tuple, dict, set, frozenset, range, Mapping, datetime.date, datetime.time, datetime.timedelta,
          decimal.Decimal, enum.Enum)
_DENIED = (types.ModuleType, type, types.FunctionType, types.BuiltinFunctionType, types.MethodType, types.CodeType, types.FrameType, types.GeneratorType,
           types.TracebackType, types.CoroutineType, types.AsyncGeneratorType, types.MethodWrapperType, types.WrapperDescriptorType,
           types.MethodDescriptorType)


class _Host:
    """An object the application owns (the ViewModel's, `app`, a namespace of `Signal`s), as TEL carries it: an expression reads its attributes and does
    nothing else with it. TEL reads an attribute with `getattr` on what it holds, so this is where a `Signal` or `Computed` attribute (`app.state.user`)
    reads as its value, as `expr.py` read every one it met, and where an attribute that is another such object is wrapped in turn."""

    __slots__ = ("_o",)

    def __init__(self, obj: Any) -> None:
        self._o = obj

    def __getattr__(self, name: str) -> Any:
        if name == "__dict__":  # TEL lists the instance's attributes to offer the nearest name for a mistyped one
            return getattr(self._o, "__dict__", {})
        exposed = getattr(type(self._o), "__expose__", None)  # a class may narrow what an expression can read of it, as in `expr.py`
        if name.startswith("_") or (exposed is not None and name not in exposed):
            raise AttributeError(name)
        return _read(getattr(self._o, name))


def _read(value: Any) -> Any:
    """A value as an expression reads it: a `Signal` or `Computed` as what it holds, an object of the application's as a `_Host`."""
    if isinstance(value, (Signal, Computed)):
        value = value.get()
    if isinstance(value, _PLAIN) or isinstance(value, _DENIED) or callable(value):
        return value
    return _Host(value)


def _result(value: Any) -> Any:
    """What an evaluation gives back: the object behind a `_Host`, a `Signal` it ends in as its value."""
    if isinstance(value, (Signal, Computed)):
        value = value.get()
    return value._o if isinstance(value, _Host) else value


class TelScope:
    """A tess-ui scope as TEL reads it: plain values, and the application's own objects as `_Host`s. `lookup` reads a `Signal` or `Computed` as its value
    (which records the read for the reactive layer) and turns the scope's `AttributeError` into the `KeyError` TEL expects. `event`, when given, is the
    name `event`. Reads only: nothing here assigns."""

    __slots__ = ("scope", "event")

    def __init__(self, scope: Any, event: Any = MISSING) -> None:
        self.scope, self.event = scope, event

    def lookup(self, name: str) -> Any:
        if name == "event" and self.event is not MISSING:
            return _read(self.event)
        try:
            value = self.scope.lookup(name)
        except AttributeError:
            raise KeyError(name) from None
        return _read(value)

    def names(self) -> list[str]:
        names = getattr(self.scope, "names", None)
        try:
            found = list(names()) if names is not None else []
        except Exception:  # noqa: BLE001 - only for suggestions
            found = []
        return found + ["event"] if self.event is not MISSING else found


def adapt(scope: Any, *, event: Any = MISSING) -> TelScope:
    """`scope` as a TEL scope (a scope already adapted, with no new `event`, is returned as it is)."""
    if isinstance(scope, TelScope) and event is MISSING:
        return scope
    return TelScope(scope.scope if isinstance(scope, TelScope) else scope, event)


# -- expressions --------------------------------------------------------------------------------------------------------


def _strip(source: str, origin: Optional[Origin]) -> Optional[Origin]:
    """Where the text without its surrounding whitespace starts."""
    if origin is None:
        return None
    lead = source[: len(source) - len(source.lstrip())]
    newlines = lead.count("\n")
    column = (len(lead) - lead.rfind("\n") - 1) if newlines else origin.column + len(lead)
    return Origin(origin.file, origin.line + newlines, column)


class TelExpr:
    """A compiled expression. `names` are the free names it reads (comprehension variables excluded); `paths` the attribute chains on them."""

    __slots__ = ("source", "origin", "names", "paths", "_expression", "_bare")

    def __init__(self, expression: Any, source: str, origin: Optional[Origin]) -> None:
        self._expression = expression
        self.source = expression.text
        self.origin = _strip(source, origin)
        self.names: frozenset[str] = expression.names
        self.paths: frozenset[str] = expression.paths
        self._bare = self.source if self.source.isidentifier() and self.names == {self.source} else None

    def is_reactive(self, scope: Any) -> bool:
        """Whether any name it reads is reactive in `scope` (conservative: a name that may hold a Signal counts)."""
        check = getattr(scope, "is_reactive", None)
        return bool(check) and any(check(name) for name in self.names)

    def evaluate(self, scope: Any, *, event: Any = MISSING) -> Any:
        """The value, with Signals read as their values. Raises `ExprError`."""
        try:
            value = self._expression.evaluate(adapt(scope, event=event))
        except tess_el.TelError as err:
            raise _error(err, self.origin) from None
        return _result(value)

    def evaluate_tracked(self, scope: Any, *, event: Any = MISSING) -> tuple[Any, frozenset[str]]:
        """`evaluate`, and the paths the evaluation actually read (`a`, `a.b.c`): fewer than `paths` when a branch was not taken."""
        try:
            value, reads = self._expression.evaluate_tracked(adapt(scope, event=event))
        except tess_el.TelError as err:
            raise _error(err, self.origin) from None
        return _result(value), reads

    def evaluate_raw(self, scope: Any, *, event: Any = MISSING) -> Any:
        """The value without unwrapping a Signal or Computed it ends in (what a model property needs to write back): a bare name gives the scope's own
        object, an attribute chain what its last step holds."""
        if self._bare is not None and not (self._bare == "event" and event is not MISSING):
            try:
                return scope.lookup(self._bare)
            except (KeyError, AttributeError):
                pass  # evaluating says what is wrong
        try:
            return _result(self._expression.evaluate(adapt(scope, event=event)))
        except tess_el.TelError as err:
            raise _error(err, self.origin) from None

    def bare_name(self) -> Optional[str]:
        """The name, if the whole expression is one bare name (a candidate for two-way binding), else `None`."""
        return self._bare

    def __repr__(self) -> str:
        return f"TelExpr({self.source!r})"


def _as_text(source: Any, origin: Optional[Origin]) -> None:
    if not isinstance(source, str):
        raise ExprError(f"an expression is text, got {type(source).__name__}", origin=origin)


def compile_expr(source: str, *, origin: Optional[Origin] = None, limits: Any = DEFAULT_LIMITS) -> TelExpr:
    """Parses and checks one expression. Raises `ExprError`."""
    _as_text(source, origin)
    try:
        expression = tess_el.compile_expression(source, language=LANGUAGE, origin=_tel_origin(origin), limits=limits, functions=_REGISTERED, methods=HOST_METHODS)
    except tess_el.TelError as err:
        raise _error(err, origin) from None
    return TelExpr(expression, source, origin)


# -- templates ----------------------------------------------------------------------------------------------------------


class TelTemplate:
    """Text with `{{ }}` parts: `"Hello {{ name }}!"`. `parts` are strings and `TelExpr`s. When the whole text is one `{{ }}`, the value keeps its own
    type (`single`); otherwise the parts are joined as text (`None` is empty)."""

    __slots__ = ("parts", "origin", "_template")

    def __init__(self, template: Any, origin: Optional[Origin]) -> None:
        self._template = template
        self.origin = origin
        self.parts: list[Any] = []
        for part in template._parts:  # noqa: SLF001 - TEL gives the parts no public name; each one is made a `TelExpr` of its own
            self.parts.append(part if isinstance(part, str) else TelExpr(part, part.source, _part_origin(origin, part)))

    @property
    def single(self) -> bool:
        return len(self.parts) == 1 and isinstance(self.parts[0], TelExpr)

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._template.names)

    @property
    def paths(self) -> frozenset[str]:
        return frozenset(self._template.paths)

    def is_reactive(self, scope: Any) -> bool:
        return any(p.is_reactive(scope) for p in self.parts if isinstance(p, TelExpr))

    def evaluate(self, scope: Any, *, event: Any = MISSING) -> Any:
        try:
            value = self._template.evaluate(adapt(scope, event=event))
        except tess_el.TelError as err:
            raise _error(err, self.origin) from None
        return _result(value)

    def evaluate_tracked(self, scope: Any, *, event: Any = MISSING) -> tuple[Any, frozenset[str]]:
        try:
            value, reads = self._template.evaluate_tracked(adapt(scope, event=event))
        except tess_el.TelError as err:
            raise _error(err, self.origin) from None
        return _result(value), reads

    def __repr__(self) -> str:
        return f"TelTemplate({self._template.source!r})"


def _part_origin(origin: Optional[Origin], part: Any) -> Optional[Origin]:
    """Where a part of a template starts: TEL knows it (`part.origin`, 1-based), the file's 0-based column is that minus one."""
    if origin is None or part.origin is None:
        return None
    return Origin(part.origin.file, part.origin.line, part.origin.column - 1)


def compile_template(text: str, *, origin: Optional[Origin] = None, limits: Any = DEFAULT_LIMITS) -> Optional[TelTemplate]:
    """Splits `text` at its `{{ }}` parts and compiles each. Returns `None` when there is no `{{` (plain text). Raises `ExprError`."""
    _as_text(text, origin)
    if "{{" not in text:
        return None
    try:
        template = tess_el.compile_template(text, language=LANGUAGE, origin=_tel_origin(origin), limits=limits, functions=_REGISTERED, methods=HOST_METHODS)
    except tess_el.TelError as err:
        raise _error(err, origin) from None
    return TelTemplate(template, origin)


@dataclass
class TelNestedTemplate:
    """A list or mapping with `{{ }}` strings inside it (a `Text`'s `runs`), as `TelTemplate`s: it evaluates to the same shape with each of those strings
    worked out (a string that is one whole `{{ }}` keeps the type of its value), and is reactive if any of them is."""

    value: Any

    def templates(self) -> list[TelTemplate]:
        found: list[TelTemplate] = []

        def walk(item: Any) -> None:
            if isinstance(item, TelTemplate):
                found.append(item)
            elif isinstance(item, list):
                for sub in item:
                    walk(sub)
            elif isinstance(item, dict):
                for sub in item.values():
                    walk(sub)

        walk(self.value)
        return found

    @property
    def names(self) -> frozenset[str]:
        return frozenset().union(*(t.names for t in self.templates()))

    def is_reactive(self, scope: Any) -> bool:
        return any(t.is_reactive(scope) for t in self.templates())

    def evaluate(self, scope: Any) -> Any:
        adapted = adapt(scope)

        def work(item: Any) -> Any:
            if isinstance(item, TelTemplate):
                return item.evaluate(adapted)
            if isinstance(item, list):
                return [work(sub) for sub in item]
            if isinstance(item, dict):
                return {key: work(sub) for key, sub in item.items()}
            return item

        return work(self.value)

