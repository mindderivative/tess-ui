"""Small helpers over `tess_dl`: parse without raising, the entries of a node as the index paths count them, a block's properties."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import tess_dl
from tess_dl import Block, Document, For, If, Property

__all__ = ["IndexPath", "OrdPath", "ordinals", "from_ordinals", "is_node", "dedented_source", "Node", "Mark", "Parsed", "parse_text", "child_entries", "properties_of", "child_named", "node_type", "node_source", "walk"]

type IndexPath = tuple[int, ...]
#: A place in the tree counted in blocks, `If`s and `For`s only (the entry numbers of an index path also count properties and comments, and an edit can take a comment away with a block).
type OrdPath = tuple[int, ...]
#: What a selection points at: a block, or an `If` or `For` node.
type Node = Block | If | For


@dataclass(frozen=True)
class Mark:
    """One syntax error, for the text view and the problems list: 1-based `line` and `column`, the stable `code`, what is wrong and what to write."""

    line: int
    column: int
    code: str
    message: str
    hint: str

    def __str__(self) -> str:
        return f"{self.line}:{self.column}: {self.message}" + (f" ({self.hint})" if self.hint else "")


@dataclass(frozen=True)
class Parsed:
    """A text read by `tess_dl`. `document` is set only when the text parses with no error; otherwise `errors` say what is wrong and there is no tree to edit."""

    text: str
    document: Document | None
    errors: tuple[Mark, ...]

    @property
    def valid(self) -> bool:
        return self.document is not None


def parse_text(text: str, path: str | None = None) -> Parsed:
    """Parse `text`. Never raises for a syntax error: an editor keeps the text it cannot yet read."""
    try:
        result = tess_dl.parse(text, path=path)
    except tess_dl.TDLError as error:  # a limit stops the file before any tree exists
        return Parsed(text, None, (_mark(error),))
    if result.errors or result.document is None:
        return Parsed(text, None, tuple(_mark(e) for e in result.errors) or (Mark(1, 1, "tdl-no-tree", "The file has no metadata block or root block.", ""),))
    return Parsed(text, result.document, ())


def _mark(error: tess_dl.TDLError) -> Mark:
    origin = getattr(error, "origin", None)
    return Mark(line=getattr(origin, "line", 1) or 1, column=getattr(origin, "column", 1) or 1, code=str(getattr(error, "code", "")),
                message=str(getattr(error, "message", error)), hint=str(getattr(error, "hint", "") or ""))


def child_entries(node: Node) -> tuple[object, ...]:
    """The entries of `node` in the order its index paths count them: a block's entries; an `If`'s body, then its else body; a `For`'s body."""
    if isinstance(node, Block):
        return tuple(node.entries)
    if isinstance(node, If):
        return (*node.body, *(node.else_body or ()))
    return tuple(node.body)


def properties_of(block: Block) -> dict[str, Property]:
    """The block's own properties by key (a repeated key is an error in the language, so the first is the only one)."""
    found: dict[str, Property] = {}
    for entry in block.entries:
        if isinstance(entry, Property):
            found.setdefault(entry.key, entry)
    return found


def child_named(block: Block, name: str) -> Block | None:
    """The first block directly inside `block` whose type is `name`, compared without regard to case (a theme's `Color` block, a token group `color`)."""
    wanted = name.lower()
    return next((e for e in block.entries if isinstance(e, Block) and e.type.lower() == wanted), None)


def node_type(node: Node) -> str:
    """The word before the brace: a block's type, `If` or `For`."""
    return node.type if isinstance(node, Block) else type(node).__name__


def node_source(document: Document, node: Node) -> str:
    """The text of `node` exactly as it is written in the document."""
    return document.text[node.start:node.end]


def walk(node: Node) -> Iterator[Node]:
    """`node` and every block, `If` and `For` below it, in order."""
    yield node
    for entry in child_entries(node):
        if isinstance(entry, (Block, If, For)):
            yield from walk(entry)


def is_node(entry: object) -> bool:
    """Whether an entry is a block, an `If` or a `For` (a place in the structure tree), not a property or a comment."""
    return isinstance(entry, (Block, If, For))


def ordinals(document: Document, path: IndexPath) -> OrdPath:
    """`path` counted in blocks, `If`s and `For`s: `(0, 3, 4)` for the block that is the 5th entry of a block whose ordinal is 1 (an entry before it that is a property or a comment is not counted)."""
    node: Node = document.root
    found: list[int] = []
    for i in path:
        entries = child_entries(node)
        found.append(sum(1 for e in entries[:i] if is_node(e)))
        node = entries[i]  # type: ignore[assignment]
    return tuple(found)


def from_ordinals(document: Document, ords: OrdPath) -> IndexPath | None:
    """The index path of the node whose ordinal path is `ords`, or `None` when there is none."""
    node: Node = document.root
    found: list[int] = []
    for o in ords:
        places = [i for i, e in enumerate(child_entries(node)) if is_node(e)]
        if not 0 <= o < len(places):
            return None
        found.append(places[o])
        node = child_entries(node)[places[o]]  # type: ignore[assignment]
    return tuple(found)


def dedented_source(document: Document, node: Node) -> str:
    """`node_source` with the indentation of the line the node starts on taken off every later line, so `Block.with_child` (which adds the new place's indentation to every line) lays it out as it was."""
    text = document.text
    line_start = text.rfind("\n", 0, node.start) + 1
    indent = text[line_start:node.start]
    indent = indent if not indent.strip() else ""
    source = text[node.start:node.end]
    if not indent:
        return source
    first, *rest = source.split("\n")
    return "\n".join([first, *(line[len(indent):] if line.startswith(indent) else line.lstrip(" \t") for line in rest)])
