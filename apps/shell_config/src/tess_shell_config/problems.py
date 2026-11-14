"""The problems list: the findings of `check`, as rows for the window, and the way from a finding to the block and key it points at.

A finding is a file, a line and a column (1-based, columns count characters: `tess_dl`'s own origins). `locate` finds the deepest block, `If` or `For` of the open document that holds that place,
and the key (the property, or a part of an `If` or `For`) when the place is inside one, so a click can select the block and show the key. Nothing here knows a key name of the shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tess_dl import Block, Document, For, If, Property

from tess_shell_config.shell import CheckResult
from tess_shell_config.tdl import IndexPath, Node

__all__ = ["Place", "locate", "relative_to_folder", "rows_for", "failure_rows", "SEVERITY_ICONS", "title_for"]

#: The icon and the word for a severity: a row says it in both (an icon alone is not enough).
SEVERITY_ICONS = {"error": ("error", "Error"), "warning": ("alert", "Warning"), "info": ("information", "Note")}


@dataclass(frozen=True)
class Place:
    """Where a finding points in a document: the node (`path`, from `node.index_path`), and the `key` inside it when there is one (a property's name, or `condition`, `items`, `key` of an `If` or `For`)."""

    path: IndexPath
    key: str | None = None


def _inside(node: Any, line: int, column: int) -> bool:
    origin = node.origin
    if origin is None:
        return False
    return (origin.line, origin.column) <= (line, column) < (origin.end_line, origin.end_column)


def locate(document: Document, line: int, column: int) -> Place | None:
    """The deepest block, `If` or `For` of `document` that holds `line:column`, with the key at that place. `None` when the place is outside every block (a metadata line, a place past the end)."""
    root = document.root
    if not _inside(root, line, column):
        return None
    found: Node = root
    while True:
        child = next((e for e in _entries(found) if isinstance(e, (Block, If, For)) and _inside(e, line, column)), None)
        if child is None:
            break
        found = child
    key = _key_at(found, line, column)
    if isinstance(found, Block) and found is not root and found.type.lower() == "style":  # a style key written inside `Style { }` belongs to the block that holds the `Style`
        return Place(tuple(found.index_path)[:-1], key)
    return Place(tuple(found.index_path), key)


def _entries(node: Node) -> tuple[Any, ...]:
    if isinstance(node, Block):
        return tuple(node.entries)
    if isinstance(node, If):
        return (*node.body, *(node.else_body or ()))
    return tuple(node.body)


def _key_at(node: Node, line: int, column: int) -> str | None:
    if isinstance(node, Block):
        for entry in node.entries:
            if isinstance(entry, Property) and _inside(entry, line, column):
                return entry.key
        return None
    if isinstance(node, If):
        return "condition" if _inside(node.condition, line, column) else None
    if _inside(node.items, line, column):
        return "items"
    return "key" if _inside(node.key, line, column) else None


def relative_to_folder(name: str, folder: Path) -> str:
    """The finding's `file` as the path from the configuration folder, written with `/` (the shell names it that way; an absolute name under `folder` is made relative)."""
    path = Path(name)
    if path.is_absolute():
        try:
            return path.relative_to(folder).as_posix()
        except ValueError:
            return path.as_posix()
    text = name.replace("\\", "/")
    return text[2:] if text.startswith("./") else text


def rows_for(result: CheckResult) -> list[dict[str, Any]]:
    """The findings as the window's rows: an icon and a word, the place, the message and its hint. A row with a `file` can be clicked."""
    rows = []
    for index, finding in enumerate(result.findings):
        icon, word = SEVERITY_ICONS.get(finding.severity, SEVERITY_ICONS["error"] if not finding.severity else ("information", finding.severity.capitalize()))
        place = f"{finding.file}:{finding.line}:{finding.column}" if finding.line else finding.file
        rows.append({"id": f"p:{index}", "index": index, "icon": icon, "severity": word, "where": place, "message": finding.message, "hint": finding.hint, "rule": finding.rule,
                     "clickable": bool(finding.file)})
    if result.omitted:
        rows.append({"id": "p:omitted", "index": -1, "icon": "information", "severity": "Note", "where": "", "message": f"{result.omitted} more finding(s) were left out by check.", "hint": "", "rule": "", "clickable": False})
    return rows


def failure_rows(message: str) -> list[dict[str, Any]]:
    """The one row of a check that could not give an answer (it did not run, or timed out): editing goes on."""
    return [{"id": "p:failed", "index": -1, "icon": "error", "severity": "Check", "where": "", "message": message, "hint": "", "rule": "", "clickable": False}]


def title_for(result: CheckResult | None, failed: bool, running: bool) -> str:
    """The heading of the list."""
    if running:
        return "Problems: checking..."
    if failed:
        return "Problems: the check did not run"
    if result is None:
        return "Problems: not checked yet"
    if not result.findings:
        return f"Problems: none ({result.files} file{'s' if result.files != 1 else ''} checked)"
    count = len(result.findings) + result.omitted
    return f"Problems: {count} finding{'s' if count != 1 else ''} in {result.files} file{'s' if result.files != 1 else ''}"
