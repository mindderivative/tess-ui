"""`tesserae migrate-tdl`: writes a project's `*_View.yaml` files as `*_View.tdl` (piece 2 of `design/tdl-switch-plan.md`; the mapping is `design/tdl-views.md`).

`convert_view(text, name)` turns the text of one YAML view into TDL: keys `Title_Case`, a node a block headed by its widget, `If` and `For` wrappers, a handler
as `Set` and `Call` step blocks, `{{ expr }}` as `<| expr |>`, the metadata block (`TDL`, `Name`, `Tesserae`). It **keeps** the comments (the ones at the top, the
ones above a key and the ones at the end of a line, in the handler's Python text too), the blank lines between entries and the order of the keys, and lays the
result out one entry per line with two spaces to a level; a YAML flow collection that sits on one line stays on one line when it fits in 150 columns (a list
that does not is wrapped there, a mapping that does not is opened one entry to a line).

Nothing is written that does not read back: every result is loaded again through the front end (`spec/tdl.py`) and compared with the YAML loader's mapping, so a form
the converter cannot express is a `ConvertError` that names the line and says what to write instead, never a nearly right file. The one bent rule is the pair `for:`
target (`i, it in enumerate(items)`): a TDL `For` has one variable, so the loop is written with one variable (`i_it`, the pair), a `# TODO tuple for-target: ...` line
above it, and is reported as a `Loop` whose body the person must adjust.

`migrate_tdl(path, write=, remove_source=)` does it for a file or a project folder; without `write` it only reports. A `*_Stylesheet.yaml` is converted by `migrate_tdl_sheets.convert_sheet`; themes and components are
skipped with a note (their converters come later). Running it again changes nothing.
"""

from __future__ import annotations

import ast
import bisect
import io
import json
import re
import tokenize
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from tess_ui.expr import _closing, is_action_name
from tess_ui.migrate import _files
from tess_ui.spec import marker
from tess_ui.spec import widgets as registry
from tess_ui.spec.nodes import LoadError, PMap, load_marked
from tess_ui.spec.tdl import load_marked_tdl, snake_case, title_case
from tess_ui.spec.widgets import WidgetDecl

__all__ = ["ConvertError", "Converted", "FileResult", "Loop", "Report", "convert_view", "migrate_tdl", "with_single_variable"]

#: The width the converter lays long lists out to, as the YAML views are.
WIDTH = 150

_FOR = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s+in\s+(.+?)\s*$", re.S)
_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")
_NUMBER = re.compile(r"^-?[0-9]+(?:\.[0-9]+)?$")
_PERCENT = re.compile(r"^[0-9]+%$")
_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ACTION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
#: `tess_dl` reads these as wrappers (`If`, `For`, `Else`: never a key) or as the words of a `For` (`In`, `Key`: never a block head).
_NO_KEY = frozenset({"If", "Else", "For"})
_NO_BLOCK = frozenset({"If", "Else", "For", "In", "Key"})
#: What a node's mapping has that is not a property or a map of its own.
_WRAPPER_KEYS = ("widget", "if", "for", "key")


class ConvertError(Exception):
    """A form the converter cannot write as TDL. `line` and `column` (0-based) are in the YAML file; `hint` says what to write instead."""

    def __init__(self, message: str, line: int = 1, column: int = 0, hint: str | None = None) -> None:
        super().__init__(message)
        self.message, self.line, self.column, self.hint = message, line, column, hint

    def __str__(self) -> str:
        return f"{self.message} ({self.hint})" if self.hint else self.message


@dataclass(frozen=True)
class Loop:
    """A `for:` with a pair target, written with one variable: the person adjusts its body."""

    file: str
    line: int
    original: str
    rewrite: str

    @property
    def variable(self) -> str:
        return self.rewrite.split(" in ", 1)[0]


@dataclass
class Converted:
    """The TDL text of one view, the steps written and the pair loops and notes it came with."""

    text: str
    steps: int = 0
    loops: list[Loop] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# -- the values --------------------------------------------------------------------------------------------------------------


def single_variable(target: str) -> str:
    """The one variable a pair target is written with: `i, it` -> `i_it`."""
    return "_".join(t.strip() for t in target.split(","))


def with_single_variable(data: Any) -> list[str]:
    """Rewrites every pair-target `for:` in the YAML mapping `data` in place to the form `convert_view` writes; returns the original texts."""
    found: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            value = item.get("for")
            match = _FOR.match(value) if isinstance(value, str) else None
            if isinstance(value, str) and match and "," in match.group(1):
                found.append(value)
                item["for"] = f"{single_variable(match.group(1))} in {match.group(2)}"
            for sub in item.values():
                walk(sub)
        elif isinstance(item, list):
            for sub in item:
                walk(sub)

    walk(data)
    return found


def _slot(expr: str) -> str:
    text = expr.strip()
    if "|>" in text or "\n" in text:
        raise ConvertError(f"an expression that cannot sit in a slot: {expr!r}", hint="a slot holds one line and no '|>'")
    return f"<| {text} |>"


def _split_template(text: str) -> list[tuple[bool, str]]:
    """`(is_slot, text)` parts: a slot's text is exactly what lies between `{{` and `}}`."""
    parts: list[tuple[bool, str]] = []
    i, literal = 0, 0
    while i < len(text):
        if text.startswith("{{", i):
            end = _closing(text, i + 2)
            if end is None:
                raise ConvertError(f"a '{{{{' is never closed: {text!r}", hint="close it with '}}'")
            if literal < i:
                parts.append((False, text[literal:i]))
            parts.append((True, text[i + 2:end]))
            i = literal = end + 2
        else:
            i += 1
    if literal < len(text):
        parts.append((False, text[literal:]))
    return parts


def _scalar(v: Any) -> str:
    """The TDL value for the YAML scalar `v` (bool, number, null, text, `{{ }}` template)."""
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        text = repr(v)
        if not _NUMBER.match(text):
            raise ConvertError(f"a number TDL reads differently: {text}", hint="write it as text in quotes, or as a plain decimal")
        return text
    if not isinstance(v, str):
        raise ConvertError(f"a value of type {type(v).__name__} has no TDL form: {v!r}", hint="quote it as text")
    if "{{" in v:
        parts = _split_template(v)
        if len(parts) == 1 and parts[0][0]:
            return f"<|{parts[0][1]}|>"
        text = "".join(f"<|{t}|>" if is_slot else t for is_slot, t in parts)
        literal = "".join(t for is_slot, t in parts if not is_slot)
        if (text != text.strip() or "\n" in text or text[0] in "\"'[#" or any(c in literal for c in "{},]") or " #" in literal or "<|" in literal
                or "\r" in text):
            raise ConvertError(f"text with a slot that cannot be written unquoted: {v!r}",
                               hint="TDL text with a slot has no quotes and no , { } ] or ' #' in its text: make the whole value one slot, "
                                    "e.g. <| 'a, ' + str(b) |>")
        return text
    if (_WORD.match(v) and v not in ("true", "false", "null")) or _PERCENT.match(v):
        return v
    out = json.dumps(v, ensure_ascii=False)
    if re.search(r"(?<!\\)(?:\\\\)*\\[bfr/]", out):
        raise ConvertError(f"a string with a control character: {v!r}", hint="remove the control character or write it as \\n or \\t")
    return out


# -- the comments ------------------------------------------------------------------------------------------------------------


@dataclass
class _Comment:
    line: int
    text: str  # "" for a blank line
    own: bool  # on a line of its own (not at the end of a line with something before it)


@dataclass
class _Line:
    """One line of TDL, with the YAML lines whose comments go with it: `keys` (own-line comments above it) and `trails` (the comment at the end)."""

    indent: int
    text: str
    keys: tuple[int, ...] = ()
    trails: tuple[int, ...] = ()
    pre: tuple[str, ...] = ()  # comments written above, after the ones of `keys`
    post: str = ""  # a comment at the end that is already worked out (from a handler's Python text)
    in_list: bool = False  # inside a TDL list, where a `#` needs a space after it


@dataclass
class _Step:
    """A `Set` or `Call`: its head and its `Key: value` parts, which sit on one line or, when that is too long, one to a line."""

    head: str
    parts: tuple[str, ...]
    pre: tuple[str, ...] = ()
    post: str = ""

    @property
    def text(self) -> str:
        return f"{self.head} {{ {', '.join(self.parts)} }}"


def _comments(text: str) -> list[_Comment]:
    """Every comment (and every blank line between entries) of the YAML `text`, found in the gaps between its tokens: a `#` there starts a comment."""
    starts = [0] + [i + 1 for i, c in enumerate(text) if c == "\n"]

    def line_of(index: int) -> int:
        return bisect.bisect_right(starts, index)  # 1-based

    found: list[_Comment] = []
    previous = 0
    for token in yaml.scan(text, Loader=yaml.SafeLoader):
        begin, end = token.start_mark.index, token.end_mark.index
        if begin > previous:
            gap_end = begin
            for hit in re.finditer(r"#[^\n]*", text[previous:gap_end]):
                at = previous + hit.start()
                line = line_of(at)
                found.append(_Comment(line, hit.group().rstrip(), text[starts[line - 1]:at].strip() == ""))
            for line in range(line_of(previous), line_of(gap_end) + 1):
                first = starts[line - 1]
                last = text.find("\n", first)
                last = len(text) if last < 0 else last
                if first >= previous and first < len(text) and last <= gap_end and text[first:last].strip() == "":
                    found.append(_Comment(line, "", True))
        previous = max(previous, end)
    return sorted(found, key=lambda c: (c.line, c.text == ""))


# -- the converter -----------------------------------------------------------------------------------------------------------


def _line_of(node: yaml.Node) -> int:
    return node.start_mark.line + 1


class _Converter:
    def __init__(self, text: str, name: str, file: str, resolver: Callable[[str], WidgetDecl | None] | None) -> None:
        self.text, self.name, self.file, self.resolver = text, name, file, resolver
        self.loader = yaml.SafeLoader(text)
        root = self.loader.get_single_node()
        if not isinstance(root, yaml.MappingNode):
            raise ConvertError("a view is a mapping with a widget:", 1, hint="write widget: Container, then its properties")
        self.root = root
        self.check_aliases(root, _line_of(root), set())
        self.comments = _comments(text)
        self.comment_lines = sorted({c.line for c in self.comments if c.text})
        self.steps = 0
        self.loops: list[Loop] = []
        self.notes: list[str] = []

    def check_aliases(self, node: yaml.Node, line: int, seen: set[int]) -> None:
        """An alias is the very node of its anchor: the second time one is met is where it is used (a node's own mark is the anchor's, so `line` is the entry's)."""
        if id(node) in seen:
            raise ConvertError("an anchor or alias has no TDL form", line, 0, "write the value out where it is used")
        seen.add(id(node))
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                self.check_aliases(key, _line_of(key), seen)
                self.check_aliases(value, _line_of(key), seen)
        elif isinstance(node, yaml.SequenceNode):
            for item in node.value:
                self.check_aliases(item, line, seen)

    # errors, positions and small helpers

    def fail(self, node: yaml.Node | int, message: str, hint: str | None = None) -> ConvertError:
        if isinstance(node, int):
            return ConvertError(message, node, 0, hint)
        return ConvertError(message, node.start_mark.line + 1, node.start_mark.column, hint)

    def note(self, message: str) -> None:
        if message not in self.notes:
            self.notes.append(message)

    def last_line(self, node: yaml.Node) -> int:
        """The last line `node` takes (1-based)."""
        if isinstance(node, yaml.ScalarNode):
            mark = node.end_mark
            line = mark.line + 1
            return line - 1 if mark.column == 0 and line > _line_of(node) else line
        if node.flow_style:  # type: ignore[union-attr]
            return node.end_mark.line + 1
        children = [n for pair in node.value if isinstance(pair, tuple) for n in pair] or [n for n in node.value if isinstance(n, yaml.Node)]  # type: ignore[union-attr]
        return max((self.last_line(c) for c in children), default=_line_of(node))

    def commented(self, first: int, last: int) -> bool:
        """Whether a comment sits after line `first` and up to line `last`."""
        i = bisect.bisect_right(self.comment_lines, first)
        return i < len(self.comment_lines) and self.comment_lines[i] <= last

    def single_line(self, node: yaml.Node) -> bool:
        return bool(getattr(node, "flow_style", False)) and self.last_line(node) == _line_of(node)

    def construct(self, node: yaml.Node) -> Any:
        return self.loader.construct_object(node, deep=True)

    def key_text(self, node: yaml.Node) -> str:
        if not isinstance(node, yaml.ScalarNode):
            raise self.fail(node, "a key is a plain name", "write the key as a word")
        value = self.loader.construct_object(node, deep=True)
        if isinstance(value, bool):
            return node.value  # YAML 1.1 reads `on` as true; the key is the text that was written
        if not isinstance(value, str):
            raise self.fail(node, f"the key {node.value!r} is not a name", "keys are lower snake_case words")
        return value

    def key_of(self, snake: str, node: yaml.Node | int, *, block: bool) -> str:
        title = title_case(snake)
        if snake_case(title) != snake or not _KEY.match(title):
            suggestion = _CAMEL.sub("_", re.sub(r"[^A-Za-z0-9_]+", "_", snake)).lower().strip("_")
            valid = bool(suggestion) and suggestion[0].isalpha() and snake_case(title_case(suggestion)) == suggestion
            raise self.fail(node, f"the key '{snake}' is not lower snake_case",
                            f"write '{suggestion}'" if valid and suggestion != snake else "keys are letters, digits and underscores, starting with a letter, in lower case")
        if title in (_NO_BLOCK if block else _NO_KEY):
            raise self.fail(node, f"the key '{snake}' is a TDL keyword ({title})", "rename the key")
        return title

    def scalar(self, node: yaml.Node) -> str:
        assert isinstance(node, yaml.ScalarNode)
        try:
            return _scalar(self.construct(node))
        except ConvertError as exc:
            raise self.fail(node, exc.message, exc.hint) from None

    def string(self, node: yaml.Node, what: str) -> str:
        if not isinstance(node, yaml.ScalarNode) or not isinstance(self.construct(node), str):
            raise self.fail(node, f"'{what}:' is text", f"write {what}: an expression")
        return self.construct(node)  # type: ignore[no-any-return]

    def slot(self, text: str, node: yaml.Node | int) -> str:
        try:
            return _slot(text)
        except ConvertError as exc:
            raise self.fail(node, exc.message, exc.hint) from None

    # maps

    def is_scalar_list(self, node: yaml.Node) -> bool:
        return isinstance(node, yaml.SequenceNode) and all(isinstance(n, yaml.ScalarNode) for n in node.value)

    def is_map_list(self, node: yaml.Node) -> bool:
        return isinstance(node, yaml.SequenceNode) and bool(node.value) and all(isinstance(n, yaml.MappingNode) for n in node.value)

    def list_entry(self, head: str, kn: yaml.Node, vn: yaml.SequenceNode, indent: int) -> list[_Line]:
        """`Key: [a, b]` for a list of scalars: on one line when it fits, wrapped at `WIDTH` when it does not, one item to a line when it has comments in it."""
        first, last = _line_of(kn), self.last_line(vn)
        items = [(self.scalar(n), n) for n in vn.value]
        if self.commented(first, last):
            out = [_Line(indent, f"{head}: [", (first,), (first,))]
            out += [_Line(indent + 2, f"{text},", (_line_of(n),), (_line_of(n),), in_list=True) for text, n in items]
            return [*out, _Line(indent, "]", trails=(last,))]
        texts = [t for t, _ in items]
        one = f"{head}: [" + ", ".join(texts) + "]"
        if indent + len(one) <= WIDTH or not texts:
            return [_Line(indent, one, (first,), (first, last))]
        pad = indent + len(head) + 3
        out, current, used = [], f"{head}: [", False
        start_indent = indent
        for i, text in enumerate(texts):
            piece = text + ("," if i < len(texts) - 1 else "]")
            if not used:
                current += piece
                used = True
            elif start_indent + len(current) + 1 + len(piece) <= WIDTH:
                current += " " + piece
            else:
                out.append(_Line(start_indent, current, (first,) if not out else (), (first,) if not out else (), in_list=bool(out)))
                start_indent, current = pad, piece
        out.append(_Line(start_indent, current, (first,) if not out else (), (first, last) if not out else (last,), in_list=bool(out)))
        return out

    def inline_map(self, mn: yaml.MappingNode) -> str | None:
        """`{ A: 1, B { C: 2 } }` for a map written on one line, or `None` when some part of it needs its own lines."""
        parts: list[str] = []
        for kn, vn in mn.value:
            key = self.key_text(kn)
            if isinstance(vn, yaml.ScalarNode):
                if key.startswith("on_") and self.handler_text(vn) is not None:
                    return None
                parts.append(f"{self.key_of(key, kn, block=False)}: {self.scalar(vn)}")
            elif self.is_scalar_list(vn):
                parts.append(f"{self.key_of(key, kn, block=False)}: [" + ", ".join(self.scalar(n) for n in vn.value) + "]")  # type: ignore[union-attr]
            elif self.is_map_list(vn):
                items = [self.inline_map(n) for n in vn.value]  # type: ignore[union-attr]
                if any(i is None for i in items):
                    return None
                parts.append(f"{self.key_of(key, kn, block=True)} {{ " + ", ".join(f"Item {i}" for i in items) + " }")
            elif isinstance(vn, yaml.MappingNode):
                sub = self.inline_map(vn)
                if sub is None:
                    return None
                parts.append(f"{self.key_of(key, kn, block=True)} {sub}")
            else:
                raise self.fail(vn, "a list that holds lists, or both text and maps, has no TDL form", "use a list of scalars or a list of maps")
        return "{ " + ", ".join(parts) + " }" if parts else "{ }"

    def map_block(self, head: str, mn: yaml.MappingNode, indent: int, line: int) -> list[_Line]:
        if not mn.value:
            return [_Line(indent, f"{head} {{ }}", (line,), (line,))]
        inline = self.inline_map(mn) if self.single_line(mn) else None
        if inline is not None and indent + len(head) + 1 + len(inline) <= WIDTH:
            return [_Line(indent, f"{head} {inline}", (line,), (line,))]
        out = [_Line(indent, f"{head} {{", (line,), (line,))]
        for kn, vn in mn.value:
            out += self.map_entry(kn, vn, indent + 2)
        return [*out, _Line(indent, "}")]

    def map_entry(self, kn: yaml.Node, vn: yaml.Node, indent: int, *, steps: bool = True) -> list[_Line]:
        """One entry of a map. `steps` is whether an `on_` key whose text is statements is a handler (inside a map it is; a key of a node itself, such as a view's own `on_pick` param, is text)."""
        key = self.key_text(kn)
        line = _line_of(kn)
        if isinstance(vn, yaml.ScalarNode):
            if steps and key.startswith("on_"):  # a handler of a map (a tooltip action's `on_click`) when it is statements; else the text it is
                text = self.handler_text(vn)
                if text is not None:
                    return self.event(self.key_of(key, kn, block=True), line, vn, text, indent)
            return [_Line(indent, f"{self.key_of(key, kn, block=False)}: {self.scalar(vn)}", (line,), (line,))]
        if self.is_scalar_list(vn):
            return self.list_entry(self.key_of(key, kn, block=False), kn, vn, indent)  # type: ignore[arg-type]
        if self.is_map_list(vn):
            head = self.key_of(key, kn, block=True)
            out = [_Line(indent, f"{head} {{", (line,), (line,))]
            for item in vn.value:  # type: ignore[union-attr]
                out += self.map_block("Item", item, indent + 2, _line_of(item))
            return [*out, _Line(indent, "}")]
        if isinstance(vn, yaml.MappingNode):
            return self.map_block(self.key_of(key, kn, block=True), vn, indent, line)
        raise self.fail(vn, "a list that holds lists, or both text and maps, has no TDL form", "use a list of scalars or a list of maps")

    # handlers

    def handler_text(self, vn: yaml.ScalarNode) -> str | None:
        """The Python text of a handler value that is statements (not an action name), or `None` when it is something else or does not read as steps."""
        value = self.construct(vn)
        if not isinstance(value, str) or is_action_name(value):
            return None
        try:
            self.steps_of(value, vn, count=False)
        except ConvertError:
            return None
        return value

    def steps_of(self, text: str, vn: yaml.ScalarNode, *, count: bool = True) -> tuple[list[_Step], tuple[str, ...]]:
        """A handler's statements as steps with the comments of the Python text; the comments left over after the last one come back too."""
        block = vn.style in ("|", ">")
        base = _line_of(vn)

        def where(row: int) -> int:
            return base + row if block else base

        source = text.strip()
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise self.fail(where(exc.lineno or 1), f"the handler is not Python statements: {exc.msg}",
                            "write assignments to a name (a = b) and calls (save(), go(a, b=c)), one to a line or separated by ;") from None
        comments: list[tuple[int, bool, str]] = []
        lines = source.splitlines()
        try:
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.COMMENT:
                    row, column = token.start
                    comments.append((row, lines[row - 1][:column].strip() == "", token.string.rstrip()))
        except (tokenize.TokenError, IndentationError):
            comments = []
        if not tree.body:
            raise self.fail(vn, "a handler needs at least one statement", 'write a call such as save(), or an action name')
        steps: list[_Step] = []
        used = 0
        for statement in tree.body:
            before: list[str] = []
            after = ""
            while used < len(comments) and (comments[used][0] < statement.lineno or (comments[used][0] <= (statement.end_lineno or statement.lineno) and comments[used][1])):
                before.append(comments[used][2])
                used += 1
            while used < len(comments) and comments[used][0] <= (statement.end_lineno or statement.lineno) and not comments[used][1]:
                after = (after + "  " if after else "") + comments[used][2]
                used += 1
            head, parts = self.step(statement, source, where(statement.lineno))
            steps.append(_Step(head, tuple(parts), tuple(before), after))
        tail = tuple(c[2] for c in comments[used:])
        if count:
            self.steps += len(steps)
        return steps, tail

    def expression(self, node: ast.expr, source: str, line: int) -> str:
        text = ast.get_source_segment(source, node)
        if text is None or "\n" in text or "|>" in text:
            text = ast.unparse(node)
        if "|>" in text or "\n" in text:
            raise self.fail(line, f"an expression that cannot sit in a slot: {text!r}", "a slot holds one line and no '|>'")
        return self.slot(text, line)

    def step(self, statement: ast.stmt, source: str, line: int) -> tuple[str, list[str]]:
        shown = ast.unparse(statement)
        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                raise self.fail(line, f"a Set writes one plain name, got '{shown}'", "write one assignment to a name for each target: a = 1, then b = 1")
            return "Set", [f"Target: {statement.targets[0].id}", f"Value: {self.expression(statement.value, source, line)}"]
        if isinstance(statement, ast.AugAssign):
            if not isinstance(statement.target, ast.Name):
                raise self.fail(line, f"a Set writes one plain name, got '{shown}'", "write the name = name + value")
            self.note("an augmented assignment (x += 1) is written as a Set with the operation spelled out (x = x + 1): the name gets a new value, "
                      "it is not changed in place")
            value = ast.BinOp(ast.Name(statement.target.id, ast.Load()), statement.op, statement.value)
            return "Set", [f"Target: {statement.target.id}", f"Value: {self.expression(value, source, line)}"]
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
            call = statement.value
            action = ast.unparse(call.func)
            if not _ACTION.match(action):
                raise self.fail(line, f"a Call names an action such as save or navigate.back, got '{action}'", "call the action by its (dotted) name")
            if any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords):
                raise self.fail(line, f"a Call takes plain arguments, got '{shown}'", "write each argument out")
            parts = [f"Action: {json.dumps(action)}"]
            if call.args:
                parts.append("Args: [" + ", ".join(self.expression(a, source, line) for a in call.args) + "]")
            for keyword in call.keywords:
                assert keyword.arg is not None
                if keyword.arg in ("action", "args"):
                    raise self.fail(line, f"a keyword argument named '{keyword.arg}' clashes with the Call's own {title_case(keyword.arg)}", "rename the argument")
                parts.append(f"{self.key_of(keyword.arg, line, block=False)}: {self.expression(keyword.value, source, line)}")
            return "Call", parts
        if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Name):
            raise self.fail(line, f"a bare name among statements: '{shown}'", f"write the call: {shown}()")
        raise self.fail(line, f"a statement with no step form: {shown}", "a handler is assignments to a name (a = b) and calls (save(), go(a, b=c))")

    @staticmethod
    def step_lines(step: _Step, indent: int) -> list[_Line]:
        if indent + len(step.text) <= WIDTH:
            return [_Line(indent, step.text, pre=step.pre, post=step.post)]
        return [_Line(indent, f"{step.head} {{", pre=step.pre, post=step.post), *[_Line(indent + 2, part) for part in step.parts], _Line(indent, "}")]

    def event(self, head: str, line: int, vn: yaml.ScalarNode, text: str, indent: int) -> list[_Line]:
        steps, tail = self.steps_of(text, vn)
        if len(steps) == 1 and not steps[0].pre and not steps[0].post and not tail:
            one = f"{head} {{ {steps[0].text} }}"
            if indent + len(one) <= WIDTH:
                return [_Line(indent, one, (line,), (line,))]
        out = [_Line(indent, f"{head} {{", (line,), (line,))]
        for step in steps:
            out += self.step_lines(step, indent + 2)
        return [*out, _Line(indent, "}", pre=tail)]

    def handlers(self, kn: yaml.Node, vn: yaml.MappingNode, indent: int) -> list[_Line]:
        line = _line_of(kn)
        if not vn.value:
            return [_Line(indent, "Handlers { }", (line,), (line,))]
        out = [_Line(indent, "Handlers {", (line,), (line,))]
        for ekn, evn in vn.value:
            event, eline = self.key_text(ekn), _line_of(ekn)
            if not isinstance(evn, yaml.ScalarNode):
                raise self.fail(evn, f"the handler '{event}' is an action name or statements", "write an action name (save) or Python statements")
            value = self.construct(evn)
            if not isinstance(value, str) or not value.strip():  # a number, null, or no text at all is a property, as it was
                out.append(_Line(indent + 2, f"{self.key_of(event, ekn, block=False)}: {self.scalar(evn)}", (eline,), (eline,)))
            elif is_action_name(value):
                out.append(_Line(indent + 2, f"{self.key_of(event, ekn, block=False)}: {_scalar(value.strip())}", (eline,), (eline,)))
            else:
                out += self.event(self.key_of(event, ekn, block=True), eline, evn, value, indent + 2)
        return [*out, _Line(indent, "}")]

    # nodes

    def decl_of(self, widget: str) -> WidgetDecl | None:
        found = registry.lookup(widget)
        if found is None and self.resolver is not None:
            found = self.resolver(widget)
        return found

    def children(self, head: str, kn: yaml.Node, vn: yaml.SequenceNode, indent: int) -> list[_Line]:
        line = _line_of(kn)
        if not vn.value:
            return [_Line(indent, f"{head} {{ }}", (line,), (line,))]
        out = [_Line(indent, f"{head} {{", (line,), (line,))]
        for item in vn.value:
            if not isinstance(item, yaml.MappingNode):
                raise self.fail(item, f"'{head.lower()}' holds nodes, each a mapping with a widget:", "write - widget: Text")
            out += self.node(item, indent + 2)
        return [*out, _Line(indent, "}")]

    def node_entry(self, widget: str, decl: WidgetDecl | None, kn: yaml.Node, vn: yaml.Node, indent: int) -> list[_Line]:
        key = self.key_text(kn)
        line = _line_of(kn)
        if key == "children" and isinstance(vn, yaml.SequenceNode):
            return self.children("Children", kn, vn, indent)
        if key == "handlers" and isinstance(vn, yaml.MappingNode):
            return self.handlers(kn, vn, indent)
        prop = decl.properties.get(key) if decl is not None else None
        if prop is not None and prop.type == "node" and isinstance(vn, yaml.MappingNode):
            head = self.key_of(key, kn, block=True)
            return [_Line(indent, f"{head} {{", (line,), (line,)), *self.node(vn, indent + 2), _Line(indent, "}")]
        if prop is not None and prop.type == "nodes" and isinstance(vn, yaml.SequenceNode):
            return self.children(self.key_of(key, kn, block=True), kn, vn, indent)
        if decl is None and self.looks_like_node(vn):
            self.note(f"'{key}' of {widget} holds what looks like a node, but {widget} is not known here, so it is written as a map: if {widget} declares "
                      f"'{key}' as a node, write it as '{self.key_of(key, kn, block=True)} {{ Widget {{ ... }} }}' by hand")
        return self.map_entry(kn, vn, indent, steps=False)

    @staticmethod
    def looks_like_node(vn: yaml.Node) -> bool:
        def has_widget(n: yaml.Node) -> bool:
            return isinstance(n, yaml.MappingNode) and any(isinstance(k, yaml.ScalarNode) and k.value == "widget" for k, _ in n.value)

        return has_widget(vn) or (isinstance(vn, yaml.SequenceNode) and bool(vn.value) and all(has_widget(n) for n in vn.value))

    def node(self, mn: yaml.MappingNode, indent: int, *, extra_keys: tuple[int, ...] = (), skip: frozenset[str] = frozenset()) -> list[_Line]:
        """A node: its wrappers (`For` outside `If`), its head and its entries."""
        entries = [(self.key_text(kn), kn, vn) for kn, vn in mn.value]
        entries = [e for e in entries if e[0] not in skip]
        by = {key: (kn, vn) for key, kn, vn in entries}
        item_line = _line_of(mn)
        if "widget" not in by:
            raise self.fail(mn, "a node needs a widget:", "write widget: Text" if not any(k in by for k in ("kind", "component", "view", "include"))
                            else "this is a view in the older syntax: run `tesserae migrate-yaml` on the project first")
        widget_kn, widget_vn = by["widget"]
        widget = self.construct(widget_vn)
        if not isinstance(widget, str) or not _KEY.match(widget) or widget in _NO_BLOCK:
            raise self.fail(widget_vn, f"the widget {widget!r} cannot head a TDL block", "a widget name is letters, digits and underscores, starting with a letter")
        widget_line = _line_of(widget_kn)
        if "key" in by and "for" not in by:
            raise self.fail(by["key"][0], "a key: without a for:", "a key names the items of a for: loop; remove it or add the for:")
        wrappers: list[tuple[str, tuple[int, ...]]] = []  # (head text, the YAML lines it answers for), outermost first
        pre: tuple[str, ...] = ()
        if "for" in by:
            fkn, fvn = by["for"]
            text = self.string(fvn, "for")
            match = _FOR.match(text)
            if match is None:
                raise self.fail(fvn, f"'for:' reads 'name in expression', got {text!r}", "write for: item in items")
            targets = [t.strip() for t in match.group(1).split(",")]
            variable = "_".join(targets)
            if variable.title() in _NO_BLOCK or variable in _NO_BLOCK:
                raise self.fail(fvn, f"'{variable}' cannot be the variable of a TDL For", "rename the variable")
            if len(targets) > 1:
                original = f"{', '.join(targets)} in {match.group(2)}"
                self.loops.append(Loop(self.file, _line_of(fkn), text.strip(), f"{variable} in {match.group(2)}"))
                pre = (f"# TODO tuple for-target: {original}",)
            key_text = "None"
            lines: tuple[int, ...] = (_line_of(fkn),)
            if "key" in by:
                key_text = self.string(by["key"][1], "key")
                lines = (_line_of(fkn), _line_of(by["key"][0]))
            head = f"For {variable} In {self.slot(match.group(2), fvn)} Key {self.slot(key_text, by['key'][1] if 'key' in by else fvn)} {{"
            wrappers.append((head, lines))
        if "if" in by:
            ikn, ivn = by["if"]
            wrappers.append((f"If {self.slot(self.string(ivn, 'if'), ivn)} {{", (_line_of(ikn),)))
        decl = self.decl_of(widget)
        body = [e for e in entries if e[0] not in _WRAPPER_KEYS]

        out: list[_Line] = []
        level = indent
        first_keys = tuple(sorted({item_line, widget_line, *extra_keys}))
        for number, (head, lines) in enumerate(wrappers):
            keys = (*first_keys, *lines) if number == 0 else lines
            out.append(_Line(level, head, tuple(sorted(set(keys))), lines, pre=pre if head.startswith("For") else ()))
            level += 2
        node_keys = () if wrappers else first_keys
        if not body:
            out.append(_Line(level, f"{widget} {{ }}", node_keys, (item_line, widget_line)))
        else:
            out.append(_Line(level, f"{widget} {{", node_keys, (item_line, widget_line)))
            for _key, kn, vn in body:
                out += self.node_entry(widget, decl, kn, vn, level + 2)
            out.append(_Line(level, "}"))
        for number in range(len(wrappers)):
            out.append(_Line(indent + 2 * (len(wrappers) - 1 - number), "}"))
        return out

    # the file

    def run(self, scanned: marker.Marker, data: Any) -> Converted:
        meta_line = _line_of(self.root.value[0][0]) if scanned.found and self.root.value else 0
        skip = frozenset({marker.KEY}) if scanned.found else frozenset()
        body_first = next((_line_of(kn) for kn, _ in self.root.value if self.key_text(kn) not in skip), _line_of(self.root))
        name = data.get("name") if isinstance(data, dict) else None
        view_name = name if isinstance(name, str) and _KEY.match(name) and name not in _NO_BLOCK else self.name
        if not _KEY.match(view_name) or view_name in _NO_BLOCK:
            raise ConvertError(f"the view's name {view_name!r} cannot be a TDL Name", 1,
                               hint="a Name is letters, digits and underscores, starting with a letter: rename the file or give the root a name:")
        head = [_Line(0, "---"), _Line(0, "TDL: 0.1"), _Line(0, f"Name: {view_name}")]
        if scanned.found and scanned.value:
            head.append(_Line(0, f'Tesserae: "{scanned.value}"', trails=(meta_line,)))
        head.append(_Line(0, "---"))
        body = self.node(self.root, 0, extra_keys=(body_first,), skip=skip)
        text = self.assemble(head, body, body_first)
        return Converted(text, self.steps, self.loops, self.notes)

    def assemble(self, head: list[_Line], body: list[_Line], body_first: int) -> str:
        lines = head + body
        leads = sorted({k for line in lines for k in line.keys})
        groups: dict[int, list[str]] = defaultdict(list)
        tail: list[str] = []
        trails: dict[int, list[str]] = defaultdict(list)
        for comment in self.comments:
            if comment.own:
                i = bisect.bisect_right(leads, comment.line)
                target = tail if i >= len(leads) else groups[leads[i]]
                if comment.text or not target or target[-1] != "":
                    target.append(comment.text)
            else:
                trails[comment.line].append(comment.text)
        anchors = sorted((min(line.keys), n) for n, line in enumerate(lines) if line.keys)
        for at_line in sorted(trails):
            if not any(at_line in host.trails for host in lines):  # a comment at the end of a line that no output line answers for: the nearest entry above it
                at = bisect.bisect_right([a for a, _ in anchors], at_line) - 1
                host = lines[anchors[max(at, 0)][1]]
                host.trails = (*host.trails, at_line)
        out: list[str] = []
        taken: set[int] = set()
        used_trails: set[int] = set()
        first_body = len(head)
        for n, current in enumerate(lines):
            pad = " " * current.indent
            wanted: list[str] = []
            for key in current.keys:
                if key not in taken:
                    taken.add(key)
                    wanted += groups.get(key, [])
            if n == first_body:
                while wanted and wanted[0] == "":
                    wanted.pop(0)
            for text in wanted:
                out.append(self.comment_text(pad, text, current.in_list))
            for text in current.pre:
                out.append(self.comment_text(pad, text, current.in_list))
            ends = []
            for key in current.trails:
                if key not in used_trails and key in trails:
                    used_trails.add(key)
                    ends += [self.comment_text("", t, current.in_list) for t in trails[key]]
            if current.post:
                ends.append(self.comment_text("", current.post, current.in_list))
            out.append(pad + current.text + ("  " + "  ".join(ends) if ends else ""))
        while tail and tail[-1] == "":
            tail.pop()
        out += [self.comment_text("", t, False) for t in tail]
        return "\n".join(out) + "\n"

    @staticmethod
    def comment_text(pad: str, text: str, in_list: bool) -> str:
        if in_list and text[1:2] not in ("", " ", "\t"):
            text = "# " + text[1:]
        return (pad + text).rstrip()


# -- checking what was written -----------------------------------------------------------------------------------------------


def _handler_form(text: str) -> str:
    """A handler text as its statements, written one way (`x += 1` is `x = x + 1`), so two spellings of one program compare equal."""
    try:
        tree = ast.parse(text.strip())
    except SyntaxError:
        return text
    body: list[ast.stmt] = []
    for statement in tree.body:
        if isinstance(statement, ast.AugAssign) and isinstance(statement.target, ast.Name):
            statement = ast.fix_missing_locations(ast.copy_location(
                ast.Assign([ast.Name(statement.target.id, ast.Store())], ast.BinOp(ast.Name(statement.target.id, ast.Load()), statement.op, statement.value)), statement))
        body.append(statement)
    return "; ".join(ast.unparse(s) for s in body)


def _canon(item: Any, key: str | None = None, handlers: bool = False) -> Any:
    """The mapping as comparable plain data: types kept (`True` is not `1`), key order and the spelling of handlers, conditions and loops not."""
    if isinstance(item, dict):
        return ("map", tuple(sorted((k, _canon(v, k, handlers or k == "handlers")) for k, v in item.items())))
    if isinstance(item, list):
        return ("seq", tuple(_canon(v) for v in item))
    if isinstance(item, str):
        if key in ("if", "key"):
            item = item.strip()
        elif key == "for":
            match = _FOR.match(item)
            item = f"{', '.join(t.strip() for t in match.group(1).split(','))} in {match.group(2)}" if match else item
        elif handlers or (key or "").startswith("on_"):
            item = _handler_form(item)
    return (type(item).__name__, item)


def _where(a: Any, b: Any, path: str = "") -> str:
    if a[0] == b[0] == "map":
        da, db = dict(a[1]), dict(b[1])
        for k in [*da, *[k for k in db if k not in da]]:
            if da.get(k) != db.get(k):
                return _where(da.get(k, ("missing",)), db.get(k, ("missing",)), f"{path}.{k}" if path else k)
    if a[0] == b[0] == "seq":
        for i, (x, y) in enumerate(zip(a[1], b[1], strict=False)):
            if x != y:
                return _where(x, y, f"{path}[{i}]")
        return f"{path or 'the view'}: a list of {len(a[1])} items, read back as {len(b[1])}"
    return f"{path or 'the view'}: {a[1:]!r}, read back as {b[1:]!r}"


def convert_view(text: str, name: str, file: str = "<view>", *, resolver: Callable[[str], WidgetDecl | None] | None = None) -> Converted:
    """The TDL for the YAML view `text` (its file name stem is `name`). Raises `ConvertError` (with the YAML line and what to write) for a form with no TDL
    form, and for any result that does not read back as the same view. Line ends are the ones the text has."""
    text = text.removeprefix("\ufeff")
    newline = "\r\n" if "\r\n" in text else "\n"
    scanned = marker.scan(text)
    if scanned.problem:
        raise ConvertError(scanned.problem, scanned.line)
    try:
        data = load_marked(text, file)
    except LoadError as exc:
        raise ConvertError(exc.message, exc.line, exc.column, exc.hint) from None
    if not isinstance(data, PMap) or "widget" not in data:
        old = isinstance(data, dict) and any(k in data for k in ("kind", "component", "view", "include"))
        first = min((line for line, _ in data.key_at.values()), default=1) if isinstance(data, PMap) else 1
        raise ConvertError("this is not a view in the current syntax (a mapping with a widget:)", first,
                           hint="run `tesserae migrate-yaml` on the project first" if old else "write widget: Container, then its properties")
    try:
        result = _Converter(text, name, file, resolver).run(scanned, data)
    except yaml.YAMLError as exc:  # unreachable after load_marked; kept so a scanner difference is an error, not a traceback
        raise ConvertError(f"YAML: {exc}") from None
    expected = load_marked(text, file)
    with_single_variable(expected)
    try:
        got = load_marked_tdl(result.text, file, resolver=resolver)
    except LoadError as exc:
        raise ConvertError(f"the TDL written does not load: {exc.message} (TDL line {exc.line})", 1,
                           hint="this form has no TDL form the converter knows: " + (exc.hint or "simplify the view")) from None
    if _canon(got) != _canon(expected):
        raise ConvertError("the TDL written does not read back as the same view: " + _where(_canon(expected), _canon(got)), 1,
                           hint="this form has no TDL form the converter knows")
    if newline != "\n":
        result.text = result.text.replace("\n", newline)
    return result


# -- files and folders -------------------------------------------------------------------------------------------------------


_VIEW = re.compile(r"^(.+)_View\.yaml$")
_SHEET = re.compile(r"^(.+)_Stylesheet\.yaml$")
_OTHER = re.compile(r"^.+_(Theme|Component)\.yaml$")


@dataclass
class FileResult:
    """What one file becomes. `status`: `converted`, `current` (its `.tdl` is already what the conversion writes), `skipped` or `failed`."""

    path: Path
    status: str
    new_path: Path | None = None
    text: str | None = None
    steps: int = 0
    notes: list[str] = field(default_factory=list)
    error: str | None = None
    line: int = 0
    removed: bool = False


@dataclass
class Report:
    results: list[FileResult] = field(default_factory=list)
    loops: list[Loop] = field(default_factory=list)
    written: bool = False
    removed_source: bool = False

    @property
    def failed(self) -> list[FileResult]:
        return [r for r in self.results if r.status == "failed"]

    @property
    def converted(self) -> list[FileResult]:
        return [r for r in self.results if r.status == "converted"]

    @property
    def steps(self) -> int:
        return sum(r.steps for r in self.results if r.status == "converted")

    def render(self, root: Path | None = None) -> str:
        def rel(path: Path) -> str:
            try:
                return (path.relative_to(root) if root else path).as_posix()
            except ValueError:
                return path.as_posix()

        lines: list[str] = []
        for r in self.results:
            if r.status == "failed":
                lines.append(f"failed    {rel(r.path)}:{r.line}: {r.error}")
                continue
            verb = {"converted": "converted" if self.written else "would convert", "current": "current", "skipped": "skipped"}[r.status]
            target = f" -> {rel(r.new_path)}" if r.new_path and r.status != "skipped" else ""
            detail = f" ({r.steps} steps)" if r.steps else ""
            lines.append(f"{verb:<13} {rel(r.path)}{target}{detail}" + (": " + r.error if r.error else ""))
            lines.extend(f"              note: {note}" for note in r.notes)
            if r.removed:
                lines.append(f"              removed {rel(r.path)}")
        if self.loops:
            lines.append("")
            lines.append(f"Tuple for-targets: {len(self.loops)} (a TDL For has one variable, the pair form is not supported yet). Each loop is written with one "
                         "variable and a `# TODO tuple for-target` line above it. Adjust the body by hand:")
            for loop in self.loops:
                first = loop.original.split(" in ", 1)[0].replace(" ", "")
                parts = first.split(",")
                uses = ", ".join(f"{loop.variable}[{i}] for {p}" for i, p in enumerate(parts))
                lines.append(f"  {loop.file}:{loop.line}: `for: {loop.original}`")
                variable, iterable = loop.rewrite.split(" in ", 1)
                lines.append(f"      written as `For {variable} In <| {iterable} |>`; the body still uses {' and '.join(parts)}, which no longer exist: "
                             f"{loop.variable} is the ({', '.join(parts)}) pair, use {uses}")
        counts = {s: sum(r.status == s for r in self.results) for s in ("converted", "current", "skipped", "failed")}
        lines.append("")
        if self.written:
            summary = [f"{counts['converted']} files converted", f"{self.steps} steps written", f"{len(self.loops)} tuple for-targets to adjust by hand"]
        else:
            summary = [f"{counts['converted']} files would be converted", f"{self.steps} steps would be written", f"{len(self.loops)} tuple for-targets to adjust by hand"]
        extra = [f"{counts[s]} {s}" for s in ("current", "skipped", "failed") if counts[s]]
        lines.append(", ".join(summary + extra))
        if not self.results:
            lines.append("no view or stylesheet files found")
        lines.append("written" if self.written else "nothing written: use --write to write the files")
        return "\n".join(lines)


def _resolver(root: Path) -> Callable[[str], WidgetDecl | None]:
    """A widget name the project's own views (and the ones Tesserae ships) declare, for the properties that hold nodes."""
    from tess_ui.shipped import ViewLibrary

    project = {m.group(1): p for p in _files(root, "*_View.yaml") if (m := _VIEW.match(p.name))}
    library = ViewLibrary(project)

    def resolve(name: str) -> WidgetDecl | None:
        try:
            return library.decl(name)
        except (ValueError, OSError, yaml.YAMLError, AttributeError):
            return None

    return resolve


def migrate_tdl(path: str | Path, *, write: bool = False, remove_source: bool = False) -> Report:
    """Works out (and with `write=True`, writes) the TDL for the `*_View.yaml` or `*_Stylesheet.yaml` file `path`, or every one under the folder `path`. `remove_source` (with `write`)
    deletes each YAML file whose `.tdl` is then written or already current. A file that fails is reported and left alone; the others are still written."""
    from tess_ui.migrate_tdl_sheets import convert_sheet  # it builds on this module's converter

    path = Path(path).resolve()
    report = Report()
    if path.is_file():
        found = [path]
        root = path.parent
    else:
        root = path
        found = sorted(p for p in _files(root, "*.yaml") if _VIEW.match(p.name) or _SHEET.match(p.name) or _OTHER.match(p.name))
    resolver: Callable[[str], WidgetDecl | None] | None = None
    for file in found:
        match = _VIEW.match(file.name)
        sheet = None if match else _SHEET.match(file.name)
        if match is None and sheet is None:
            if _OTHER.match(file.name):
                report.results.append(FileResult(file, "skipped", error="a theme or component: only views and stylesheets are converted so far"))
            else:
                raise ValueError(f"{file.name} is not a *_View.yaml or *_Stylesheet.yaml file")
            continue
        found_name = match or sheet
        assert found_name is not None
        stem = found_name.group(1)
        new_path = file.with_name(f"{stem}_{'View' if match else 'Stylesheet'}.tdl")
        try:
            raw = file.read_bytes().decode("utf-8")
        except UnicodeDecodeError as exc:
            report.results.append(FileResult(file, "failed", error=f"not UTF-8: {exc.reason}", line=1))
            continue
        try:
            if sheet:
                converted = convert_sheet(raw, stem, file.name)
            else:
                if resolver is None:
                    resolver = _resolver(root)
                converted = convert_view(raw, stem, file.name, resolver=resolver)
        except ConvertError as exc:
            report.results.append(FileResult(file, "failed", error=str(exc), line=exc.line))
            continue
        existing = new_path.read_bytes().decode("utf-8", "replace") if new_path.is_file() else None
        result = FileResult(file, "current" if existing == converted.text else "converted", new_path, converted.text, converted.steps, list(converted.notes))
        if existing is not None and existing != converted.text:
            result.notes.append(f"{new_path.name} exists and differs: it is replaced")
        report.results.append(result)
        report.loops += [Loop(f"{file.relative_to(root).as_posix()}", loop.line, loop.original, loop.rewrite) for loop in converted.loops]
    if write:
        for result in report.results:
            if result.status not in ("converted", "current") or result.new_path is None or result.text is None:
                continue
            if result.status == "converted":
                result.new_path.write_bytes(result.text.encode("utf-8"))
            if remove_source:
                result.path.unlink()
                result.removed = True
        report.written = True
    return report
