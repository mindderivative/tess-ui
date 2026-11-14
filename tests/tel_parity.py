"""The differential harness behind `tests/test_tel_parity.py`: every expression the repository uses, run through `tess_ui.expr` and through the TEL adapter
(`tess_ui.tel`), and where the two differ.

    python tests/tel_parity.py                 # the differences, as `tests/tel_parity_known.json` entries to fill in
    python tests/tel_parity.py --speed         # the 20 heaviest expressions, both evaluators timed
    python tests/tel_parity.py --info          # how often the error text and position of the two agree

*What is collected* (`collect`): each `{{ }}` text (a template), and each bare expression a view writes: `if:`, `for:` (its iterable), `key:`, and the right-hand
sides and call arguments of a handler's statements, from the shipped YAML (`src`, `examples`, `apps`, `tools`), the fenced `yaml` blocks of `docs`, the strings in
`tests/*.py` that are YAML or a `{{ }}` text, the `{{ }}` texts in the docs' prose, and every one-line string of the expression language's own tests
(`CORPUS_FILES`: the grammar table, the sandbox escapes). Unique texts only.

*What is compared* (`compare`): compiling (both accept, or both refuse), the names read, and the outcome in each of `SCOPES` sample scopes made from the names the
text reads (typed from how it uses them: iterated, indexed, a method called, an attribute read, a number, a text), some of them holding `Signal`s. Two outcomes
are equal when both are the same value (same type, a NaN equals a NaN), or both are an error of this package: it is the error class that must agree, not the text.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
KNOWN = Path(__file__).resolve().parent / "tel_parity_known.json"
SCOPES = 16
CORPUS_FILES = ("test_expr.py", "test_date_functions.py", "test_docs_expr_lists.py")
CATEGORIES = ("function missing", "semantics differ", "TEL refuses the syntax", "performance")


# -- collecting ---------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Unit:
    """One text to compare: a `template` (text with `{{ }}` parts) or an `expr` (one bare expression)."""

    kind: str
    text: str

    def key(self) -> str:
        return f"{self.kind}: {self.text}"


def _handler_expressions(text: str) -> list[str]:
    """The expressions of a handler's statements: what is assigned, and the arguments of a call. A bare action name or text that is no statements gives none."""
    try:
        tree = ast.parse(text.strip(), mode="exec")
    except SyntaxError:
        return []
    found: list[str] = []
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            found.append(ast.unparse(statement.value))
        elif isinstance(statement, ast.AugAssign):
            found.append(ast.unparse(ast.BinOp(left=ast.Name(id=statement.target.id, ctx=ast.Load()), op=statement.op, right=statement.value))  # type: ignore[attr-defined]
                         if isinstance(statement.target, ast.Name) else ast.unparse(statement.value))
        elif isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            found.extend(ast.unparse(arg) for arg in [*statement.value.args, *(k.value for k in statement.value.keywords)])
    return found


def _walk(node: Any, units: set[Unit], key: str = "") -> None:
    """The units in a loaded YAML structure."""
    if isinstance(node, dict):
        for k, v in node.items():
            _walk(v, units, str(k))
    elif isinstance(node, list):
        for v in node:
            _walk(v, units, key)
    elif isinstance(node, str):
        if key in ("if", "key"):
            units.add(Unit("expr", node.strip()))
        elif key == "for":
            match = re.match(r"^\s*[\w\s,()]+?\s+in\s+(.+)$", node, re.S)
            units.add(Unit("expr", (match.group(1) if match else node).strip()))
        elif key == "handlers" or key.startswith("on_"):
            units.update(Unit("expr", e) for e in _handler_expressions(node))
        elif "{{" in node:
            units.add(Unit("template", node))


def _yaml_units(text: str, units: set[Unit]) -> bool:
    """Whether `text` loaded as a YAML mapping or list, its units added."""
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError:
        return False
    if not isinstance(loaded, (dict, list)):
        return False
    _walk(loaded, units)
    return True


def collect() -> dict[str, set[Unit]]:
    """The units, by where they came from: `views` (the shipped YAML), `docs`, `tests`, `corpus`."""
    out: dict[str, set[Unit]] = {"views": set(), "docs": set(), "tests": set(), "corpus": set()}
    for top in ("src", "examples", "apps", "tools"):
        for path in sorted((ROOT / top).rglob("*.yaml")):
            if "tests" in path.parts or ".venv" in path.parts or "node_modules" in path.parts:
                continue
            _yaml_units(path.read_text(encoding="utf-8"), out["views"])
    for path in sorted((ROOT / "docs").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for block in re.findall(r"^```ya?ml[^\n]*\n(.*?)^```", text, re.S | re.M):
            _yaml_units(block, out["docs"])
        for inline in re.findall(r"`([^`\n]*\{\{[^`\n]*)`", text):
            out["docs"].add(Unit("template", inline))
    for name in CORPUS_FILES:  # the expression language's own tests: every one-line text in them is tried as an expression (the grammar, the sandbox escapes)
        for node in ast.walk(ast.parse((ROOT / "tests" / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip() and "\n" not in node.value and len(node.value) < 300:
                out["corpus"].add(Unit("expr", node.value.strip()))
    for path in sorted((ROOT / "tests").glob("*.py")):
        if path.name == "tel_parity.py" or path.name.startswith("test_tel"):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and "{{" in node.value:
                if not _yaml_units(node.value, out["tests"]) and "\n" not in node.value.strip() and len(node.value) < 400:
                    out["tests"].add(Unit("template", node.value))
    return out


def all_units() -> list[Unit]:
    merged: set[Unit] = set()
    for units in collect().values():
        merged |= units
    return sorted(merged, key=lambda u: (u.kind, u.text))


# -- scopes -------------------------------------------------------------------------------------------------------------

_ITERATING = {"len", "sum", "sorted", "min", "max", "list", "enumerate", "zip", "any", "all", "reversed", "set", "tuple", "dict", "range"}
_NUMERIC = {"abs", "round", "clamp", "int", "float", "format_number", "pluralize", "days_in_month"}
_DATES = {"format_date", "date_add_days", "date_weekday"}
_STR_METHODS = {"lower", "upper", "title", "capitalize", "strip", "lstrip", "rstrip", "split", "splitlines", "join", "startswith", "endswith", "replace", "find",
                "count", "zfill", "isdigit", "isalpha", "center", "ljust", "rjust", "removeprefix", "removesuffix"}
_DICT_METHODS = {"get", "keys", "values", "items"}


_SIGNAL: Any = {"signal": True}  # in a `_Use.attrs` tree: this attribute holds a Signal


@dataclass
class _Use:
    attrs: dict[str, Any] = field(default_factory=dict)  # attribute -> its own sub-uses (a nested dict of the same shape)
    kinds: set[str] = field(default_factory=set)
    rows: set[str] = field(default_factory=set)  # the keys read of each item, when the name is a list that a comprehension loops over


def _keys_of(tree: ast.AST, variable: str) -> set[str]:
    """The keys and attributes the text reads of the comprehension variable `variable`: `a['name']`, `a.get('k')`, `a.done`."""
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == variable and isinstance(node.slice, ast.Constant) \
                and isinstance(node.slice.value, str):
            keys.add(node.slice.value)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == variable:
            keys.add(node.attr)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == variable \
                and node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            keys.add(node.args[0].value)
    return keys


def _uses(text: str, names: Iterable[str]) -> dict[str, _Use]:
    """How each name is used in `text`, read from its syntax tree: `iter`, `index`, `num`, `str`, `date`, `dict`, and the attributes read on it."""
    uses = {n: _Use() for n in names}
    try:
        tree = ast.parse(text.strip(), mode="eval")
    except SyntaxError:
        return uses

    def root(node: ast.AST) -> Optional[str]:
        while isinstance(node, ast.Attribute):
            node = node.value
        return node.id if isinstance(node, ast.Name) and node.id in uses else None

    def mark(node: ast.AST, kind: str) -> None:
        name = root(node)
        if name is not None and isinstance(node, ast.Name):
            uses[name].kinds.add(kind)

    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}  # `x.method(...)`: the method is not an attribute to give `x`
    for node in ast.walk(tree):  # `x.a.b.get()`: `b` of `x.a` is a Signal
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and not node.args and not node.keywords
                and isinstance(node.func.value, ast.Attribute)):
            chain = []
            inner = node.func.value
            while isinstance(inner, ast.Attribute):
                chain.append(inner.attr)
                inner = inner.value
            if isinstance(inner, ast.Name) and inner.id in uses:
                cursor = uses[inner.id].attrs
                for attr in reversed(chain[1:]):
                    cursor = cursor.setdefault(attr, {})
                cursor[chain[0]] = _SIGNAL
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and id(node) not in called:
            chain: list[str] = []
            inner: ast.AST = node
            while isinstance(inner, ast.Attribute):
                chain.append(inner.attr)
                inner = inner.value
            if isinstance(inner, ast.Name) and inner.id in uses:
                cursor = uses[inner.id].attrs
                for attr in reversed(chain):
                    cursor = cursor.setdefault(attr, {})
                    if cursor is _SIGNAL:
                        break
        if isinstance(node, ast.Subscript):
            mark(node.value, "index")
            if isinstance(node.slice, ast.Constant):
                mark(node.value, "dict" if isinstance(node.slice.value, str) else "list")
        elif isinstance(node, ast.comprehension):
            mark(node.iter, "iter")
            if isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Name) and node.iter.id in uses:
                keys = _keys_of(tree, node.target.id)
                if keys:
                    uses[node.iter.id].rows.update(keys)
        elif isinstance(node, ast.Compare):
            for op, right in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    mark(right, "iter")
            for side in [node.left, *node.comparators]:
                for other in [node.left, *node.comparators]:
                    if isinstance(other, ast.Constant):
                        mark(side, "str" if isinstance(other.value, str) else "num")
        elif isinstance(node, ast.BinOp):
            for side, other in ((node.left, node.right), (node.right, node.left)):
                mark(side, "str" if isinstance(other, (ast.Constant, ast.JoinedStr)) and isinstance(getattr(other, "value", ""), str) else "num")
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if isinstance(part, ast.FormattedValue):
                    mark(part.value, "str")
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                for position, arg in enumerate(node.args):
                    mark(arg, "iter" if func.id in _ITERATING else "date" if func.id in _DATES and position == 0 else "num" if func.id in _NUMERIC else "str")
            elif isinstance(func, ast.Attribute):
                name = root(func.value)
                if name is not None and isinstance(func.value, ast.Name):
                    if func.attr == "get" and not node.args and not node.keywords:
                        uses[name].kinds.add("signal-get")
                    else:
                        uses[name].kinds.add("str" if func.attr in _STR_METHODS else "dict" if func.attr in _DICT_METHODS else "list")
    return uses


_POOL = [3, "abc", True, [1, 2, 3], 0, None, "2026-11-14", 7.5, [], {"a": 1, "b": 2}, "", False, -2, ["b", "a", "c"], "Hello World"]
_ROWS = [{"id": 1, "name": "x", "done": True, "label": "X", "value": 4}, {"id": 2, "name": "y", "done": False, "label": "Y", "value": 5}]
_BY_KIND: dict[str, list[Any]] = {
    "iter": [[1, 2, 3], ["b", "a", "c"], [], _ROWS, "abc", {"a": 1, "b": 2}], "index": [[10, 20, 30], _ROWS, {"a": 1, "k": 2}, "abc"],
    "list": [[10, 20, 30], _ROWS, ["a", "b"]], "num": [3, 0, 7.5, -2, 120], "str": ["abc", "", "Hello World", "2026-11-14"],
    "date": ["2026-11-14", "2024-02-29", "not a date"], "dict": [{"a": 1, "b": 2, "k": 3, "label": "L", "value": 9}, {}],
    "signal-get": ["abc", 3, [1, 2, 3], None, True, 0],  # `x.get()`: a Signal's own read, so what the Signal holds is never a dict (see `HOST_METHODS`)
}


def _leaf(attr: str, seed: int) -> Any:
    return _POOL[(sum(map(ord, attr)) + seed) % len(_POOL)]


def _object(attrs: dict[str, Any], seed: int, as_mapping: bool) -> Any:
    from tess_ui.reactive import Signal

    values = {a: (Signal(_leaf(a, seed) if not isinstance(_leaf(a, seed), dict) else 3) if sub is _SIGNAL else _object(sub, seed, as_mapping) if sub else _leaf(a, seed))
              for a, sub in attrs.items()}
    return values if as_mapping else SimpleNamespace(**values)


def _candidates(use: _Use, seed: int) -> list[Any]:
    out: list[Any] = []
    if use.rows:
        as_dicts = [{k: _leaf(k, seed + row) for k in sorted(use.rows)} for row in range(3)]
        out += [as_dicts, [SimpleNamespace(**d) for d in as_dicts], as_dicts[:1], []]
    if use.attrs:
        out += [_object(use.attrs, seed, True), _object(use.attrs, seed, False), _object(use.attrs, seed + 5, True)]
    for kind in sorted(use.kinds):
        out += _BY_KIND[kind][:3]
    out += [_POOL[(seed + i) % len(_POOL)] for i in range(4)] + [None, 0, "x"]
    return [v for v in out if not isinstance(v, dict)] if "signal-get" in use.kinds else out


def scopes_for(text: str, names: Iterable[str]) -> list[dict[str, Any]]:
    """`SCOPES` assignments of values to `names`, the same each run: the first uses the best guess for every name, the rest step through the candidates."""
    ordered = sorted(names)
    uses = _uses(text, ordered)
    lists = [_candidates(uses[n], i) for i, n in enumerate(ordered)]
    return [{n: lists[i][(j * (i + 1) + j * j) % len(lists[i])] for i, n in enumerate(ordered)} for j in range(SCOPES)]


# -- running both -------------------------------------------------------------------------------------------------------


@dataclass
class Outcome:
    """What one evaluator did: `ok` with a value, or `error` with the error's class name and code, or `crash` with an exception that is not an `ExprError`."""

    state: str
    value: Any = None
    detail: str = ""


def _canon(value: Any) -> Any:
    """A value in a form that compares by structure and type: NaN equals NaN, sets and dicts are ordered by their text."""
    if isinstance(value, float) and value != value:
        return ("float", "nan")
    if isinstance(value, (bool, int, float, str, type(None))):
        return (type(value).__name__, value)
    if isinstance(value, (list, tuple)):
        return (type(value).__name__, [_canon(v) for v in value])
    if isinstance(value, dict):
        return ("dict", sorted(((_canon(k), _canon(v)) for k, v in value.items()), key=repr))
    if isinstance(value, (set, frozenset)):
        return (type(value).__name__, sorted((_canon(v) for v in value), key=repr))
    if isinstance(value, range):
        return ("range", value.start, value.stop, value.step)
    return ("object", type(value).__name__, id(value))


def same(a: Outcome, b: Outcome) -> bool:
    if a.state != b.state:
        return False
    if a.state == "ok":
        return _canon(a.value) == _canon(b.value)
    return a.detail == b.detail if a.state == "crash" else True


def _show(value: Any) -> str:
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _describe(outcome: Outcome) -> str:
    return f"{_show(outcome.value)}" if outcome.state == "ok" else f"{outcome.state} {outcome.detail}".strip()


@dataclass
class Pair:
    """The two evaluators for one unit: compiled objects, or the error that refused it."""

    old: Any = None
    new: Any = None
    old_error: Optional[Exception] = None
    new_error: Optional[Exception] = None


def compile_both(unit: Unit) -> Pair:
    from tess_ui import expr, tel

    pair = Pair()
    for which, module, error in (("old", expr, "old_error"), ("new", tel, "new_error")):
        try:
            made = module.compile_template(unit.text) if unit.kind == "template" else module.compile_expr(unit.text)
            setattr(pair, which, made if made is not None else "plain")
        except (expr.ExprError, tel.ExprError) as exc:
            setattr(pair, error, exc)
    return pair


def _run(compiled: Any, scope: Any) -> Outcome:
    from tess_ui import expr, tel

    if compiled == "plain":
        return Outcome("ok", "plain")
    try:
        return Outcome("ok", compiled.evaluate(scope))
    except (expr.ExprError, tel.ExprError) as exc:
        return Outcome("error", value=exc)
    except Exception as exc:  # noqa: BLE001 - any other failure is a crash and a difference unless both crash alike
        return Outcome("crash", detail=type(exc).__name__)


def _expression_texts(unit: Unit) -> list[str]:
    """The expression texts of a unit: itself, or each `{{ }}` part of a template (found by the old evaluator's own reading of it)."""
    if unit.kind == "expr":
        return [unit.text]
    from tess_ui import expr

    made = expr.compile_template(unit.text)
    return [p.source for p in made.parts if isinstance(p, expr.Expr)] if made is not None else []


def _trees(unit: Unit) -> list[ast.AST]:
    out: list[ast.AST] = []
    for text in _expression_texts(unit):
        try:
            out.append(ast.parse(text.strip(), mode="eval"))
        except SyntaxError:
            pass
    return out


def _only_called(unit: Unit, candidates: Iterable[str]) -> set[str]:
    """Which of `candidates` the unit uses only as the name of a function it calls (never read as a value)."""
    called: dict[str, int] = {}
    loaded: dict[str, int] = {}
    for tree in _trees(unit):
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called[node.func.id] = called.get(node.func.id, 0) + 1
                if node.func.id == "isinstance" and len(node.args) == 2 and isinstance(node.args[1], ast.Name):  # a type name, not a read
                    called[node.args[1].id] = called.get(node.args[1].id, 0) + 1
            if isinstance(node, ast.Name):
                loaded[node.id] = loaded.get(node.id, 0) + 1
    return {n for n in candidates if called.get(n, 0) and called[n] == loaded.get(n, 0)}


def _signal_gets(unit: Unit, names: Iterable[str]) -> set[str]:
    """The names the unit calls `.get()` on with no arguments: a view says that of a `Signal`, so the sample scopes give them one."""
    found: set[str] = set()
    for tree in _trees(unit):
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and not node.args and not node.keywords
                    and isinstance(node.func.value, ast.Name)):
                found.add(node.func.value.id)
    return found & set(names)


@dataclass
class Difference:
    unit: Unit
    what: str  # compile, names or result
    detail: str

    def key(self) -> str:
        return f"{self.what} | {self.unit.key()}"


def compare(unit: Unit, *, signals: bool = True) -> list[Difference]:
    """The differences between the two evaluators on `unit` (at most one per `what`)."""
    from tess_ui.expr import BUILTIN_FUNCTIONS, MapScope
    from tess_ui.reactive import Signal

    pair = compile_both(unit)
    found: list[Difference] = []
    if (pair.old_error is None) != (pair.new_error is None):
        if unit.kind == "expr" and pair.new_error is not None and _fails_everywhere(unit, pair.old):
            return found  # TEL refuses when the text is read what `expr.py` refuses whenever it is run: the same error, found earlier
        refused = "expr.py refuses it" if pair.old_error else "TEL refuses it"
        why = pair.old_error or pair.new_error
        found.append(Difference(unit, "compile", f"{refused}: {why}"))
        return found
    if pair.old_error is not None:
        return found
    # `expr.py` counts the name of a function it calls among the names an expression reads (callers filter `BUILTIN_FUNCTIONS` out again); TEL does not
    if pair.old != "plain" and pair.new != "plain" and set(pair.old.names) - _only_called(unit, BUILTIN_FUNCTIONS) != set(pair.new.names):
        found.append(Difference(unit, "names", f"expr.py reads {sorted(pair.old.names)}, TEL {sorted(pair.new.names)}"))
    if pair.old == "plain" or pair.new == "plain":
        return found
    names = set(pair.old.names) | set(pair.new.names)
    gets = _signal_gets(unit, names)
    for index, values in enumerate(scopes_for(unit.text, names)):
        wrapped = {k: Signal(v) if (signals and index % 4 == 3) or k in gets else v for k, v in values.items()}
        old, new = _run(pair.old, MapScope(wrapped)), _run(pair.new, MapScope(wrapped))
        if not same(old, new):
            found.append(Difference(unit, "result", f"{{{', '.join(f'{k}={_show(v)}' for k, v in values.items())}}}: expr.py {_describe(old)}; TEL {_describe(new)}"))
            break
    return found


def _fails_everywhere(unit: Unit, old: Any) -> bool:
    """Whether the old evaluator, which compiled `unit`, is an error in every sample scope."""
    from tess_ui.expr import MapScope

    if old == "plain":
        return False
    return all(_run(old, MapScope(values)).state != "ok" for values in scopes_for(unit.text, old.names))


def differences(units: Optional[list[Unit]] = None) -> list[Difference]:
    found: list[Difference] = []
    for unit in units if units is not None else all_units():
        found.extend(compare(unit))
    return found


# -- the known list -----------------------------------------------------------------------------------------------------


def load_known() -> list[dict[str, str]]:
    return list(json.loads(KNOWN.read_text(encoding="utf-8"))["differences"]) if KNOWN.exists() else []


def known_key(entry: dict[str, str]) -> str:
    return f"{entry['what']} | {entry['kind']}: {entry['text']}"


# -- speed and information ----------------------------------------------------------------------------------------------


def _timed(function: Any, repeat: int = 5, floor: float = 0.004) -> float:
    """Microseconds for one call: the best of `repeat` runs, each long enough to measure."""
    number = 1
    while True:
        start = time.perf_counter()
        for _ in range(number):
            function()
        if time.perf_counter() - start >= floor:
            break
        number *= 4
    best = min(_loop(function, number) for _ in range(repeat))
    return best / number * 1e6


def _loop(function: Any, number: int) -> float:
    start = time.perf_counter()
    for _ in range(number):
        function()
    return time.perf_counter() - start


def speed(count: int = 20) -> list[tuple[Unit, float, float]]:
    """The `count` units that cost `expr.py` most to evaluate (on the first sample scope where both succeed): `(unit, expr.py microseconds, TEL microseconds)`."""
    from tess_ui.expr import MapScope

    rows: list[tuple[Unit, float, float, Any, Any, Any]] = []
    groups = collect()  # the expressions views, docs and tests use; the language's own corpus has loops of thousands of items that would only dominate the table
    for unit in sorted(groups["views"] | groups["docs"] | groups["tests"], key=lambda u: (u.kind, u.text)):
        pair = compile_both(unit)
        if pair.old_error or pair.new_error or "plain" in (pair.old, pair.new):
            continue
        for values in scopes_for(unit.text, set(pair.old.names) | set(pair.new.names)):
            scope = MapScope(values)
            if _run(pair.old, scope).state == "ok" and _run(pair.new, scope).state == "ok":
                old_time = _timed(lambda: pair.old.evaluate(scope), repeat=1, floor=0.001)
                rows.append((unit, old_time, 0.0, pair, scope, None))
                break
    rows.sort(key=lambda r: -r[1])
    out = []
    for unit, _, _, pair, scope, _ in rows[:count]:
        out.append((unit, _timed(lambda: pair.old.evaluate(scope)), _timed(lambda: pair.new.evaluate(scope))))
    return out


def info() -> dict[str, int]:
    """How the evaluation errors of the two agree: pairs, same line and column, same message."""
    from tess_ui.expr import MapScope

    counts = {"pairs": 0, "same position": 0, "same message": 0}
    for unit in all_units():
        pair = compile_both(unit)
        if pair.old_error or pair.new_error or "plain" in (pair.old, pair.new):
            continue
        for values in scopes_for(unit.text, set(pair.old.names) | set(pair.new.names)):
            old, new = _run(pair.old, MapScope(values)), _run(pair.new, MapScope(values))
            if old.state == "error" and new.state == "error":
                counts["pairs"] += 1
                counts["same position"] += (old.value.line, old.value.column) == (new.value.line, new.value.column)
                counts["same message"] += str(old.value) == str(new.value)
    return counts


def main(argv: list[str]) -> None:
    if "--speed" in argv:
        print("| expression | expr.py us | TEL us | TEL is |\n|---|---:|---:|---:|")
        for unit, old, new in speed():
            shown = unit.text.replace("\n", " ").replace("|", "\\|")
            print(f"| `{shown[:70]}` | {old:.1f} | {new:.1f} | {old / new:.1f}x faster |")
        return
    if "--info" in argv:
        print(info())
        return
    units = all_units()
    found = differences(units)
    print(f"{len(units)} units, {len(found)} differences")
    for d in found:
        print(json.dumps({"what": d.what, "kind": d.unit.kind, "text": d.unit.text, "category": "", "reason": ""}, ensure_ascii=False))
        print("   ", d.detail)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "src"))
    main(sys.argv[1:])
