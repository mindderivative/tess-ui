"""The structure view's data: the open file's blocks as the nodes of the toolkit's `Tree`, with `If` and `For` as labelled nodes.

A node is `{value, label, children}`, the shape `widget: Tree` takes. A node's `value` is its index path written as text (`r` for the root, `r.2.0` for the
first entry of the third entry of the root), so a tree row and `Block.index_path` name the same place. An `If` that has an `Else` shows the else body under an
`Else` node (its value is the `If`'s path with `:else`, and choosing it selects the `If`).
"""

from __future__ import annotations

from typing import Any

from tess_dl import Block, Document, For, If, String

from tess_shell_config.tdl import IndexPath, Node, properties_of

__all__ = ["ROOT", "value_of", "path_of", "label_of", "nodes_for", "ancestors"]

ROOT = "r"
ELSE = ":else"
_LABEL_LIMIT = 48


def value_of(path: IndexPath, *, else_branch: bool = False) -> str:
    """The tree value of an index path: `()` -> `r`, `(2, 0)` -> `r.2.0`."""
    return ".".join([ROOT, *(str(i) for i in path)]) + (ELSE if else_branch else "")


def path_of(value: str) -> IndexPath:
    """The index path of a tree value (an `Else` node's value gives its `If`'s path). Raises `ValueError` for text that is not a value of this tree."""
    head = value.removesuffix(ELSE)
    parts = head.split(".")
    if parts[0] != ROOT:
        raise ValueError(f"{value!r} is not a place in the structure tree")
    return tuple(int(p) for p in parts[1:])


def _clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _LABEL_LIMIT else text[: _LABEL_LIMIT - 1] + "…"


def label_of(node: Node) -> str:
    """What a row says: a block's type and its `Name` (`Bar  Top_Bar`), or its `Selector` for a block with no name (`Rule  Text:hovered`: the rules of a stylesheet are told apart by it); `If {{ condition }}`; `For item In {{ items }}`."""
    if isinstance(node, Block):
        if node.name:
            return f"{node.type}  {node.name}"
        selector = properties_of(node).get("Selector")
        if selector is not None and isinstance(selector.value, String):
            return f"{node.type}  {_clip(selector.value.value)}"
        return node.type
    if isinstance(node, If):
        return f"If {{{{ {_clip(node.condition.text)} }}}}"
    assert isinstance(node, For)
    return f"For {node.variable} In {{{{ {_clip(node.items.text)} }}}}"


def _entries(node: Node, path: IndexPath) -> list[dict[str, Any]]:
    """The child rows of a node: its blocks, `If`s and `For`s (properties and comments have none), each with the index path the entry really has."""
    rows: list[dict[str, Any]] = []
    if isinstance(node, Block):
        for i, entry in enumerate(node.entries):
            if isinstance(entry, (Block, If, For)):
                rows.append(_row(entry, (*path, i)))
        return rows
    body = list(node.body)
    for i, entry in enumerate(body):
        if isinstance(entry, (Block, If, For)):
            rows.append(_row(entry, (*path, i)))
    if isinstance(node, If) and node.else_body is not None:
        other = [_row(entry, (*path, len(body) + i)) for i, entry in enumerate(node.else_body) if isinstance(entry, (Block, If, For))]
        rows.append({"value": value_of(path, else_branch=True), "label": "Else", "children": other})
    return rows


def _row(node: Node, path: IndexPath) -> dict[str, Any]:
    row: dict[str, Any] = {"value": value_of(path), "label": label_of(node)}
    children = _entries(node, path)
    if children:
        row["children"] = children
    return row


def nodes_for(document: Document | None) -> list[dict[str, Any]]:
    """The tree for a document: one top row, the root block. No document (the text has errors): no rows."""
    if document is None:
        return []
    return [_row(document.root, ())]


def ancestors(path: IndexPath) -> list[str]:
    """The values of every row above `path`, outermost first: the branches to open so that `path` shows."""
    return [value_of(path[:n]) for n in range(len(path))]

