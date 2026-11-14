"""The TDL front end: a view written in TDL, read into the same mapping with positions that `nodes.load_marked` makes of YAML.

Piece 1 of `design/tdl-switch-plan.md`, the rules in `design/tdl-views.md`. Nothing after this changes: `load_marked_tdl(text, file)` returns a `PMap` that
`nodes.parse_data` takes exactly as it takes the YAML one (`{widget, name, style, children, handlers, ...}`, `{{ }}` still the template form inside
strings, `if`/`for`/`key` on the node), with the same position maps (`at`, `key_at`, `val_at`), so every error a view can have keeps its wording and now
points into the `.tdl` file.

What it undoes, in one place each:

- keys are `Title_Case` in TDL and lower snake case in the mapping (`On_Click` -> `on_click`);
- `If` and `For` wrap a node in TDL and are set on the node again (`if`, `for`, `key`);
- `Children { ... }` is the `children` list; `Handlers { On_Click { Set {...} Call {...} } }` is the handler text the runtime takes
  (`open = not open; on_toggle()`); a handler that is a bare action name is a property (`On_Click: save`);
- a slot (`<| expr |>`) is the string `{{ expr }}`, text with slots in it is the template string, a quoted string is plain text;
- the metadata line `Tesserae: "0.6"` goes through `marker.scan` as the first line of a YAML file does.

Where a block is a node and where it is a map is told by position, never by letter case: a block directly in `Children`, `If` or `For` is a node, so
is the block of a property the widget declares as `node` or `nodes`; every other block inside a node is a map.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import tess_dl

from tess_ui.spec import marker
from tess_ui.spec import widgets as registry
from tess_ui.spec.nodes import LoadError, PMap, PSeq, Position, _near
from tess_ui.spec.widgets import WidgetDecl

__all__ = ["load_marked_tdl", "load_tdl_file", "title_case", "snake_case"]

_BOM = "\ufeff"

# -- the stand-in for slots ------------------------------------------------------------------------------------------------
# The pinned `tess_dl` reads slots as `{{ expr }}`, not yet as `<| expr |>`. This section is the whole of what stands in: `_parse_document` hands
# it the text with every `<| x |>` written `{{ x }}` (the same width, so every column stays true) and braces, quotes and backslashes inside the
# expression hidden, `_slot_text` shows them again. When `tess_dl` reads `<| |>` itself: delete `_standin_rewrite`, `_standin_words` and the mask
# tables, make `_parse_document` call `tess_dl.loads` on the text and `_slot_text` return `slot.text`.

_MASK = str.maketrans({"{": "\ue000", "}": "\ue001", "'": "\ue002", '"': "\ue003", "\\": "\ue004"})
_UNMASK = str.maketrans({"\ue000": "{", "\ue001": "}", "\ue002": "'", "\ue003": '"', "\ue004": "\\"})


def _standin_rewrite(text: str, file: str) -> str:
    """`text` with each slot `<| x |>` as `{{ x }}`. A slot is not read inside a quoted string or a comment."""
    out: list[str] = []
    i, n, prev = 0, len(text), ""  # prev: the last character that was not whitespace ("s" after a string)
    while i < n:
        c = text[i]
        if text.startswith("<|", i):
            eol = text.find("\n", i)
            eol = n if eol < 0 else eol
            end = text.find("|>", i + 2, eol)
            if end < 0:
                line, column = text.count("\n", 0, i) + 1, i - (text.rfind("\n", 0, i) + 1)
                raise LoadError("this '<|' has no '|>' on its line", file=file, line=line, column=column, hint="close the slot on the same line", text=text)
            out.append("{{" + text[i + 2:end].translate(_MASK) + "}}")
            i, prev = end + 2, "}"
        elif c in "\"'" and prev in (":", "[", ",", "(", "s"):
            j = i + 1
            while j < n and text[j] != c and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n) if j < n and text[j] == c else j
            out.append(text[i:j])
            i, prev = j, "s"
        elif c == "#" and (i == 0 or text[i - 1] in " \t\r\n"):
            eol = text.find("\n", i)
            eol = n if eol < 0 else eol
            out.append(text[i:eol])
            i = eol
        else:
            out.append(c)
            i += 1
            if not c.isspace():
                prev = c
    return "".join(out)


def _standin_words(message: str) -> str:
    """`tess_dl` names a slot `{{ }}` in its messages: say `<| |>`."""
    return message.replace("{{", "<|").replace("}}", "|>")


def _slot_text(slot: tess_dl.Slot) -> str:
    """What lies between the delimiters of `slot`, nothing trimmed."""
    return slot.text.translate(_UNMASK)


def _parse_document(text: str, file: str) -> tess_dl.Document:
    """Reads `text` with `tess_dl`; a syntax error becomes a `LoadError` at the same line and column."""
    try:
        return tess_dl.loads(_standin_rewrite(text, file), path=file)
    except tess_dl.TDLSyntaxError as exc:
        hint = _standin_words(exc.hint)
        line = text.splitlines()[exc.origin.line - 1] if 1 <= exc.origin.line <= len(text.splitlines()) else ""
        if re.match(r"\s*For\s+\w+\s*,", line):
            hint = "a For takes one variable: the pair form (`i, item`) is not supported yet"
        raise LoadError(_standin_words(exc.message), file=file, line=exc.origin.line, column=exc.origin.column - 1, hint=hint, text=text) from None


# -- keys ------------------------------------------------------------------------------------------------------------------

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ACTION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WORDS = {"true": True, "false": False, "null": None}
#: The metadata keys a view file may have (`TDL` and `Name` are `tess_dl`'s, `Tesserae` is the release series).
_METADATA = ("TDL", "Name", "Tesserae")


def title_case(snake: str) -> str:
    """`typography_role` -> `Typography_Role`, `a11y` -> `A11y`."""
    return "_".join(part[:1].upper() + part[1:] for part in snake.split("_"))


def snake_case(key: str) -> str | None:
    """`Typography_Role` -> `typography_role`; `None` when `key` is not `Title_Case` (it would not come back as written)."""
    snake = key.lower()
    return snake if title_case(snake) == key else None


class _Front:
    def __init__(self, text: str, file: str, resolver: Callable[[str], WidgetDecl | None] | None) -> None:
        self.text, self.file, self.resolver = text, file, resolver

    # errors and positions

    @staticmethod
    def pos(where: Any) -> Position:
        """`(line, column)`, line 1-based and column 0-based as `LoadError` and the YAML position maps have them."""
        if isinstance(where, tuple):
            return where
        origin = where if isinstance(where, tess_dl.Origin) else where.origin
        return origin.line, origin.column - 1

    def fail(self, where: Any, message: str, hint: str | None = None) -> LoadError:
        line, column = self.pos(where)
        return LoadError(message, file=self.file, line=line, column=column, hint=hint, text=self.text)

    def key(self, text: str, where: Any) -> str:
        """The mapping key for the `Title_Case` key `text`."""
        snake = snake_case(text)
        if snake is None:
            suggestion = title_case(_CAMEL.sub("_", text).lower())
            raise self.fail(where, f"'{text}' is not a Title_Case key", f"write '{suggestion}'")
        return snake

    def decl(self, widget: str) -> WidgetDecl | None:
        found = registry.lookup(widget)
        return found if found is not None or self.resolver is None else self.resolver(widget)

    @staticmethod
    def new_map(where: Position) -> PMap:
        m = PMap()
        m.at, m.key_at, m.val_at = where, {}, {}
        return m

    def put(self, m: PMap, key: str, value: Any, key_at: Position, val_at: Position) -> None:
        if key in m:
            raise self.fail(key_at, f"duplicate key '{key}'")
        m[key] = value
        m.key_at[key], m.val_at[key] = key_at, val_at

    # values

    def value(self, v: tess_dl.Value) -> tuple[Any, Position]:
        """A value and where it is: a quoted string's text starts after its quote, a slot's `{{` is where its delimiter is."""
        at = self.pos(v)
        if isinstance(v, tess_dl.Word):
            return _WORDS.get(v.text, v.text), at
        if isinstance(v, tess_dl.String):
            return v.value, (at[0], at[1] + 1)
        if isinstance(v, tess_dl.Number):
            return v.value, at
        if isinstance(v, tess_dl.Percent):
            return v.text, at
        if isinstance(v, tess_dl.Slot):
            return "{{" + _slot_text(v) + "}}", at
        if isinstance(v, tess_dl.Template):
            return "".join(p if isinstance(p, str) else "{{" + _slot_text(p) + "}}" for p in v.parts), at
        if isinstance(v, tess_dl.List):
            seq = PSeq()
            seq.at, seq.item_at = at, []
            for item in v.items:
                made, item_at = self.value(item)
                seq.append(made)
                seq.item_at.append(item_at)
            return seq, at
        raise self.fail(at, f"'{v.name}(...)' is not a value a view takes", "write the value as text or a number")  # a Call

    def expr(self, slot: tess_dl.Slot) -> tuple[str, Position]:
        """The expression text of a condition, a loop or a step (trimmed) and where its first character is."""
        raw = _slot_text(slot)
        line, column = self.pos(slot.text_origin)
        return raw.strip(), (line, column + len(raw) - len(raw.lstrip()))

    # nodes

    def node_entry(self, entry: Any, depth: int = 0) -> PMap:
        """A node: a block headed by its widget, in any number of `For`/`If` wrappers (a `For` outside an `If`, one of each at most)."""
        wrappers: list[Any] = []
        while isinstance(entry, (tess_dl.If, tess_dl.For)):
            if isinstance(entry, tess_dl.If) and entry.else_body is not None:
                raise self.fail(entry, "an If around a node has no Else", "put the other node in its own If")
            body = [e for e in entry.body if not isinstance(e, tess_dl.Comment)]
            if len(body) != 1 or not isinstance(body[0], (tess_dl.Block, tess_dl.If, tess_dl.For)):
                kind = "an If" if isinstance(entry, tess_dl.If) else "a For"
                raise self.fail(entry, f"{kind} holds exactly one node")
            wrappers.append(entry)
            entry = body[0]
        kinds = ["If" if isinstance(w, tess_dl.If) else "For" for w in wrappers]
        if kinds not in ([], ["If"], ["For"], ["For", "If"]):
            raise self.fail(wrappers[1], "one node has at most one For and one If, a For outside the If",
                            "the If is tested for each item: write For ... { If ... { Node { } } }")
        node = self.node_block(entry, depth)
        for wrapper in reversed(wrappers):
            if isinstance(wrapper, tess_dl.If):
                text, at = self.expr(wrapper.condition)
                self.put(node, "if", text, self.pos(wrapper), at)
            else:
                items, items_at = self.expr(wrapper.items)
                prefix = f"{wrapper.variable} in "
                self.put(node, "for", prefix + items, self.pos(wrapper), (items_at[0], items_at[1] - len(prefix)))
                key, key_at = self.expr(wrapper.key)
                if key != "None":  # a For must write a Key; `None` is how a node without one says so
                    keyword = self.text.find("Key", wrapper.items.end, wrapper.key.start)
                    self.put(node, "key", key, self.keyword_at(keyword, key_at), key_at)
        return node

    def keyword_at(self, offset: int, fallback: Position) -> Position:
        if offset < 0:
            return fallback
        return self.text.count("\n", 0, offset) + 1, offset - (self.text.rfind("\n", 0, offset) + 1)

    def node_block(self, block: Any, depth: int) -> PMap:
        if not isinstance(block, tess_dl.Block):  # unreachable through node_entry
            raise self.fail(block, "a node is a block headed by its widget")
        at = self.pos(block)
        m = self.new_map(at)
        self.put(m, "widget", block.type, at, at)
        decl = self.decl(block.type)
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                kind = "an If" if isinstance(entry, tess_dl.If) else "a For"
                raise self.fail(entry, f"{kind} wraps a node: it goes inside Children, not among a node's properties")
            if isinstance(entry, tess_dl.Property):
                key = self.key(entry.key, entry.key_origin)
                value, value_at = self.value(entry.value)
                self.put(m, key, value, self.pos(entry.key_origin), value_at)
                continue
            key = self.key(entry.type, entry)
            prop = decl.properties.get(key) if decl is not None else None
            if key == "children":
                value = self.children(entry)
            elif key == "handlers":
                value = self.handlers(entry)
            elif prop is not None and prop.type == "node":
                value = self.only_node(entry)
            elif prop is not None and prop.type == "nodes":
                value = self.children(entry)
            else:
                value = self.block_value(entry)
            self.put(m, key, value, self.pos(entry), self.pos(entry))
        return m

    def only_node(self, block: tess_dl.Block) -> PMap:
        found = [e for e in block.entries if not isinstance(e, tess_dl.Comment)]
        if len(found) != 1 or isinstance(found[0], tess_dl.Property):
            raise self.fail(block, f"'{block.type}' holds one node")
        return self.node_entry(found[0])

    def children(self, block: tess_dl.Block) -> PSeq:
        seq = PSeq()
        seq.at, seq.item_at = self.pos(block), []
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, tess_dl.Property):
                raise self.fail(entry, f"'{block.type}' holds nodes, and '{entry.key}:' is a property",
                                "a node is a block headed by its widget: Text { Text: hello }")
            node = self.node_entry(entry)
            seq.append(node)
            seq.item_at.append(node.at)
        return seq

    # maps

    def block_value(self, block: tess_dl.Block) -> Any:
        """A block that is a map; or a list of maps when it holds nothing but `Item` blocks (a map with only an `item` key is not expressible)."""
        entries = [e for e in block.entries if not isinstance(e, tess_dl.Comment)]
        items = [e for e in entries if isinstance(e, tess_dl.Block) and e.type == "Item"]
        if entries and len(items) == len(entries):
            seq = PSeq()
            seq.at, seq.item_at = self.pos(block), []
            for item in items:
                seq.append(self.mapping(item))
                seq.item_at.append(self.pos(item))
            return seq
        return self.mapping(block)

    def mapping(self, block: tess_dl.Block) -> PMap:
        m = self.new_map(self.pos(block))
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                kind = "an If" if isinstance(entry, tess_dl.If) else "a For"
                raise self.fail(entry, f"{kind} wraps a node, and '{block.type}' holds a map", "nodes go inside Children")
            if isinstance(entry, tess_dl.Property):
                key = self.key(entry.key, entry.key_origin)
                value, value_at = self.value(entry.value)
                self.put(m, key, value, self.pos(entry.key_origin), value_at)
                continue
            key = self.key(entry.type, entry)
            if key.startswith("on_") and self.is_steps(entry):
                value = self.steps_text(entry)
            else:
                value = self.block_value(entry)
            self.put(m, key, value, self.pos(entry), self.pos(entry))
        return m

    # handlers

    @staticmethod
    def is_steps(block: tess_dl.Block) -> bool:
        entries = [e for e in block.entries if not isinstance(e, tess_dl.Comment)]
        return bool(entries) and all(isinstance(e, tess_dl.Block) and e.type in ("Set", "Call") for e in entries)

    def handlers(self, block: tess_dl.Block) -> PMap:
        m = self.new_map(self.pos(block))
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if isinstance(entry, (tess_dl.If, tess_dl.For)):
                raise self.fail(entry, "Handlers hold events, not If or For")
            if isinstance(entry, tess_dl.Property):  # an event whose handler is an action name
                event = self.key(entry.key, entry.key_origin)
                value, value_at = self.value(entry.value)
                self.put(m, event, value, self.pos(entry.key_origin), value_at)
                continue
            event = self.key(entry.type, entry)
            self.put(m, event, self.steps_text(entry), self.pos(entry), self.pos(entry))
        return m

    def steps_text(self, block: tess_dl.Block) -> str:
        """The handler text for the `Set` and `Call` steps of `block`: statements joined with `; `, each seeing the writes before it."""
        out: list[str] = []
        for entry in block.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if not isinstance(entry, tess_dl.Block) or entry.type not in ("Set", "Call"):
                head = entry.type if isinstance(entry, tess_dl.Block) else type(entry).__name__ if not isinstance(entry, tess_dl.Property) else f"{entry.key}:"
                raise self.fail(entry, f"a handler is made of Set and Call steps, got '{head}'", _near(head, ("Set", "Call")))
            props = self.step_properties(entry)
            out.append(self.set_step(entry, props) if entry.type == "Set" else self.call_step(entry, props))
        if not out:
            raise self.fail(block, "a handler needs at least one step", 'write Call { Action: "name" } or Set { Target: name, Value: <| expression |> }')
        return "; ".join(out)

    def step_properties(self, step: tess_dl.Block) -> dict[str, tess_dl.Property]:
        props: dict[str, tess_dl.Property] = {}
        for entry in step.entries:
            if isinstance(entry, tess_dl.Comment):
                continue
            if not isinstance(entry, tess_dl.Property):
                raise self.fail(entry, f"a {step.type} step holds properties, not blocks")
            props[entry.key] = entry
        return props

    def slot_of(self, prop: tess_dl.Property, what: str) -> str:
        if not isinstance(prop.value, tess_dl.Slot):
            raise self.fail(prop.value, f"'{prop.key}:' takes one expression", f"write {prop.key}: <| {what} |>")
        return self.expr(prop.value)[0]

    def set_step(self, step: tess_dl.Block, props: dict[str, tess_dl.Property]) -> str:
        for key, prop in props.items():
            if key not in ("Target", "Value"):
                raise self.fail(prop.key_origin, f"a Set has a Target and a Value, not '{key}'", _near(key, ("Target", "Value")))
        for needed in ("Target", "Value"):
            if needed not in props:
                raise self.fail(step, f"a Set needs a {needed}", "write Set { Target: name, Value: <| expression |> }")
        target = props["Target"].value
        name = target.text if isinstance(target, tess_dl.Word) else target.value if isinstance(target, tess_dl.String) else None
        if name is None or not _IDENT.match(name):
            shown = self.text[target.start:target.end] if hasattr(target, "start") else ""
            raise self.fail(target, f"a Set's Target is one plain name, got '{shown}'", "write the name of a state, a param or a view model field")
        return f"{name} = {self.slot_of(props['Value'], 'expression')}"

    def call_step(self, step: tess_dl.Block, props: dict[str, tess_dl.Property]) -> str:
        if "Action" not in props:
            raise self.fail(step, "a Call needs an Action", 'write Call { Action: "name" }')
        action = props["Action"].value
        name = action.text if isinstance(action, tess_dl.Word) else action.value if isinstance(action, tess_dl.String) else None
        if name is None or not _ACTION.match(name):
            raise self.fail(action, "a Call's Action is an action name such as save or navigate.back", 'write Action: "name"')
        args: list[str] = []
        if "Args" in props:
            given = props["Args"].value
            if not isinstance(given, tess_dl.List) or not all(isinstance(a, tess_dl.Slot) for a in given.items):
                raise self.fail(given, "'Args:' is a list of expressions", "write Args: [<| a |>, <| b |>]")
            args = [self.expr(a)[0] for a in given.items if isinstance(a, tess_dl.Slot)]
        for key, prop in props.items():
            if key in ("Action", "Args"):
                continue
            snake = self.key(key, prop.key_origin)
            args.append(f"{snake}={self.slot_of(prop, 'expression')}")
        return f"{name}({', '.join(args)})"

    # the file

    def metadata(self, doc: tess_dl.Document) -> None:
        for entry in doc.metadata.entries:
            if not isinstance(entry, tess_dl.Property):
                continue
            if entry.key not in _METADATA:
                raise self.fail(entry.key_origin, f"no metadata key '{entry.key}'", _near(entry.key, _METADATA))
            if entry.key == "Tesserae":
                value = entry.value
                assert isinstance(value, tess_dl.Word | tess_dl.String)  # tess_dl reads metadata values as words and strings
                scanned = marker.scan(f"tesserae: {value.text if isinstance(value, tess_dl.Word) else value.value}")
                if scanned.problem:
                    raise self.fail(value, scanned.problem.replace("`tesserae:", "`Tesserae:"))


def load_marked_tdl(text: str, file: str = "<view>", *, resolver: Callable[[str], WidgetDecl | None] | None = None) -> PMap:
    """Reads the TDL view in `text` into the mapping with positions that `nodes.load_marked` makes of YAML, for `nodes.parse_data`.
    A syntax error, a key that is not `Title_Case`, a misplaced block or a bad step is a `LoadError` at its line and column in the file.
    `resolver` is as `parse_view`'s: it declares a widget that is not built in, so its `node` and `nodes` properties are read as nodes."""
    text = text.removeprefix(_BOM)
    document = _parse_document(text, file)
    front = _Front(text, file, resolver)
    front.metadata(document)
    return front.node_entry(document.root)


def load_tdl_file(path: str | Path, *, resolver: Callable[[str], WidgetDecl | None] | None = None) -> PMap:
    """`load_marked_tdl` for a file: UTF-8 (a byte order mark and CRLF lines are fine); errors name the file by its name."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise LoadError(f"the file is not UTF-8: {exc.reason}", file=path.name) from None
    return load_marked_tdl(text, path.name, resolver=resolver)
