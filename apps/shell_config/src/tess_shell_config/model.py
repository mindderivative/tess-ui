"""The document model: one open file, its text, its lossless tree, its history and its selection.

`DocumentModel` holds the file as a stack of snapshots (text, tree or the errors that stop one, the selection). Every edit is one `tess_dl` call on the
lossless tree and pushes a new snapshot; `undo` and `redo` step through the snapshots, so they restore earlier and later bytes exactly. The selection
is an index path (`Block.index_path`) and is found again in the new tree with `Document.at`, so it stays on the same block across an edit.

A file with syntax errors has no tree: only `set_text` (the text view) works until it parses, and every structure edit says so.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import tess_dl
from tess_dl import Block, Document, For, If
from tess_shell_config.files import display_text, encode, is_utf8
from tess_shell_config.tdl import (
    IndexPath,
    Mark,
    Node,
    Parsed,
    child_entries,
    child_named,
    node_source,
    parse_text,
)

__all__ = ["EditError", "Snapshot", "DocumentModel"]


class EditError(Exception):
    """An edit that cannot be made. The file is not changed; `str(error)` is the message for the person."""


@dataclass(frozen=True)
class Snapshot:
    """One state of the file: its text, the tree when the text parses (else the errors), the selection, and what made it (`kind`: open, text, edit, format)."""

    text: str
    document: Document | None
    errors: tuple[Mark, ...]
    selection: IndexPath | None
    kind: str


class DocumentModel:
    """One open file. `path` is where it lives (a model with no path is a scratch text, for tests and for a new file before its first save)."""

    def __init__(self, text: str, path: str | Path | None = None, *, relative: str | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.relative = relative or (self.path.name if self.path else "")
        self.utf8 = is_utf8(encode(text))
        parsed = parse_text(text, self.relative or None)
        self._history: list[Snapshot] = [Snapshot(text, parsed.document, parsed.errors, () if parsed.valid else None, "open")]
        self._at = 0
        self._saved = text

    @classmethod
    def from_bytes(cls, raw: bytes, path: str | Path | None = None, *, relative: str | None = None) -> DocumentModel:
        from tess_shell_config.files import decode

        return cls(decode(raw), path, relative=relative)

    # -- the current state -------------------------------------------------------------------------------------------------------

    @property
    def snapshot(self) -> Snapshot:
        return self._history[self._at]

    @property
    def text(self) -> str:
        return self.snapshot.text

    @property
    def display_text(self) -> str:
        """`text` for a screen: the same unless the file holds bytes that are not UTF-8."""
        return self.text if self.utf8 else display_text(self.text)

    @property
    def data(self) -> bytes:
        """What a save writes: the text as the bytes it was read from, byte for byte when nothing changed."""
        return encode(self.text)

    @property
    def document(self) -> Document | None:
        return self.snapshot.document

    @property
    def errors(self) -> tuple[Mark, ...]:
        return self.snapshot.errors

    @property
    def valid(self) -> bool:
        """The text parses: there is a tree to show and edit."""
        return self.snapshot.document is not None

    @property
    def dirty(self) -> bool:
        return self.text != self._saved

    @property
    def can_undo(self) -> bool:
        return self._at > 0

    @property
    def can_redo(self) -> bool:
        return self._at < len(self._history) - 1

    @property
    def selection(self) -> IndexPath | None:
        return self.snapshot.selection

    @property
    def selected(self) -> Node | None:
        """The selected block, `If` or `For`; `None` with no selection or no tree."""
        document, path = self.document, self.selection
        return self._at_path(document, path) if document is not None and path is not None else None

    def node_at(self, path: IndexPath) -> Node:
        """The node at `path` in the current tree. Raises `EditError` when there is none (or no tree)."""
        return self._need_at(self._need_document(), path)

    def mark_saved(self) -> None:
        """The text now on disk is the current text."""
        self._saved = self.text

    def adopt_disk(self, raw: bytes) -> None:
        """The file was changed on disk and the person chose to reload: its bytes are the new first state. The history starts over."""
        from tess_shell_config.files import decode

        text = decode(raw)
        parsed = parse_text(text, self.relative or None)
        self.utf8 = is_utf8(raw)
        self._history = [Snapshot(text, parsed.document, parsed.errors, () if parsed.valid else None, "open")]
        self._at = 0
        self._saved = text

    # -- selection ---------------------------------------------------------------------------------------------------------------

    def select(self, path: IndexPath | None) -> None:
        """Select the block, `If` or `For` at `path`, or nothing. Selecting is not an edit: it is not undone, and it is remembered in the current state."""
        if path is not None:
            self._need_at(self._need_document(), tuple(path))
            path = tuple(path)
        self._history[self._at] = replace(self.snapshot, selection=path)

    # -- the text view -----------------------------------------------------------------------------------------------------------

    def set_text(self, text: str) -> None:
        """The text view changed the whole text. The tree follows when it parses; the selection stays where it still points at a node. Typing is one undo step: a run of text
        edits is one snapshot until something else is done."""
        if not self.utf8:
            raise EditError(f"{self.relative or 'This file'} holds bytes that are not UTF-8, so it cannot be edited here.")
        if text == self.text:
            return
        parsed = parse_text(text, self.relative or None)
        selection = self._kept(parsed, self.selection)
        snapshot = Snapshot(text, parsed.document, parsed.errors, selection, "text")
        if self.snapshot.kind == "text" and self._at == len(self._history) - 1 and self._at > 0:
            self._history[self._at] = snapshot
        else:
            self._push(snapshot)

    # -- the structure edits (one `tess_dl` call each) -------------------------------------------------------------------------------

    def set_value(self, path: IndexPath, key: str, value_text: str) -> None:
        """Set (or add) the property `key` of the block at `path` to `value_text`, the TDL of one value on one line. Only that line changes."""
        block = self._need_block(path)
        self._edit(lambda: block.with_property(key, value_text), selection=tuple(path))

    def clear_value(self, path: IndexPath, key: str) -> None:
        """Remove the property `key` of the block at `path` (the key goes back to the schema's default)."""
        block = self._need_block(path)
        self._edit(lambda: block.without_property(key), selection=tuple(path))

    def set_nested_value(self, path: IndexPath, chain: tuple[str, ...], key: str, value_text: str) -> None:
        """Set the property `key` of the block reached from the block at `path` through the child blocks named in `chain` (compared without regard to case), adding each block that is not there yet
        (written `Name { }`, after the last entry). It is one edit, so one undo step: a theme token whose group and name blocks are missing is written in a single step."""
        root = self._need_block(path)

        def make() -> Document:
            block: Block = root
            for name in chain:
                found = child_named(block, name)
                if found is None:
                    _, found = block.with_child(f"{name} {{ }}")
                block = found
            return block.with_property(key, value_text)

        self._edit(make, selection=self.selection)  # the block that is edited is not the one that is selected (a mode's block of a theme): the selection stays where it was

    def clear_nested_value(self, path: IndexPath, chain: tuple[str, ...], key: str) -> None:
        """Remove the property `key` of the block reached through `chain` (see `set_nested_value`); the blocks stay."""
        block = self._need_block(path)
        for name in chain:
            found = child_named(block, name)
            if found is None:
                raise EditError(f"There is no {name} block to remove {key} from.")
            block = found
        target = block
        self._edit(lambda: target.without_property(key), selection=self.selection)

    def add_block(self, parent: IndexPath, block_text: str, index: int | None = None, *, select: bool = False) -> IndexPath:
        """Add the block written in `block_text` to the block at `parent`, at entry `index` (`None`: last). Returns the new block's index path. The selection stays on the block
        that was selected, followed to its new path when the new block lands before it; `select=True` selects the new block instead."""
        block = self._need_block(parent)
        parent = tuple(parent)
        results: list[IndexPath] = []

        def make() -> Document:
            document, added = block.with_child(block_text, index)
            results.append(added.index_path)
            return document

        selection = self.selection
        self._edit(make, selection=None)
        new = results[0]
        self._history[self._at] = replace(self.snapshot, selection=new if select else _after_insert(selection, new))
        return new

    def remove_block(self, path: IndexPath) -> IndexPath:
        """Remove the block, `If` or `For` at `path`. A selection on it (or below it) moves to its parent; any other selection stays on its block. Returns the parent's path."""
        path = tuple(path)
        if not path:
            raise EditError("The root block cannot be removed.")
        document = self._need_document()
        parent = self._need_at(document, path[:-1])
        if not isinstance(parent, Block):
            raise EditError("A block inside an If or For is removed in the text view; the structure edits work on the blocks of a block.")
        child = self._need_at(document, path)
        self._edit(lambda: parent.without_child(child), selection=_after_remove(self.selection, path))
        return path[:-1]

    def move_block(self, path: IndexPath, to_parent: IndexPath | None = None, index: int | None = None, *, select: bool = False) -> IndexPath:
        """Move the block at `path` to entry `index` of the block at `to_parent` (`None`: its own parent; `index` `None`: last). Within one parent this is `Block.move_child`; to
        another parent the block is removed and added again (an `If` or `For` cannot change parent). The selection follows its block to the new place (`select=True` selects the
        moved block instead). Returns the moved block's new path."""
        path = tuple(path)
        if not path:
            raise EditError("The root block cannot be moved.")
        document = self._need_document()
        parent_path = path[:-1]
        target_path = parent_path if to_parent is None else tuple(to_parent)
        parent = self._need_block(parent_path)
        child = self._need_at(document, path)
        selection = self.selection
        new_path: list[IndexPath] = []
        if target_path == parent_path:
            entries = child_entries(parent)
            to = len(entries) - 1 if index is None else index
            if not 0 <= to < len(entries):
                raise EditError(f"There is no place {to} in {tuple(parent_path) or 'the root block'} to move it to.")

            def within() -> Document:
                new_path.append((*parent_path, to))
                return parent.move_child(child, to)

            self._edit(within, selection=None)
            followed = _after_reorder(selection, path, to)
        else:
            if target_path[: len(path)] == path:
                raise EditError("A block cannot be moved into itself.")
            if not isinstance(child, Block):
                raise EditError("An If or For can be moved only inside its own block.")
            self._need_block(target_path)
            source = node_source(document, child)
            shifted = _after_remove(target_path, path)  # the target's own path once the block has left its old place

            def across() -> Document:
                without = parent.without_child(child)
                added_document, added = without.at(tuple(shifted or ())).with_child(source, index)  # type: ignore[union-attr]
                new_path.append(added.index_path)
                return added_document

            self._edit(across, selection=None)
            moved = new_path[0]
            if selection is not None and selection[: len(path)] == path:
                followed = (*moved, *selection[len(path):])  # a selection in the moved block goes with it
            else:
                followed = _after_insert(_after_remove(selection, path), moved)
        self._history[self._at] = replace(self.snapshot, selection=new_path[0] if select else self._kept(Parsed(self.text, self.document, ()), followed))
        return new_path[0]

    def set_metadata(self, key: str, value_text: str) -> None:
        """Set a metadata key (the block between the `---` lines)."""
        document = self._need_document()
        self._edit(lambda: document.with_metadata(key, value_text), selection=self.selection)

    def clear_metadata(self, key: str) -> None:
        document = self._need_document()
        self._edit(lambda: document.without_metadata(key), selection=self.selection)

    def format_file(self) -> None:
        """Run `tess_dl.format` on the file. Never done unless asked."""
        document = self._need_document()
        self._edit(lambda: tess_dl.format(document), selection=self.selection, kind="format")

    # -- history -----------------------------------------------------------------------------------------------------------------

    def undo(self) -> bool:
        """Step back to the state before the last edit; the selection is the one that state had. Returns whether there was one."""
        if not self.can_undo:
            return False
        self._at -= 1
        return True

    def redo(self) -> bool:
        if not self.can_redo:
            return False
        self._at += 1
        return True

    # -- the inside --------------------------------------------------------------------------------------------------------------

    def _push(self, snapshot: Snapshot) -> None:
        del self._history[self._at + 1:]
        self._history.append(snapshot)
        self._at += 1

    def _edit(self, make: Any, *, selection: IndexPath | None, kind: str = "edit") -> None:
        """Run one `tess_dl` edit; on success push its result as a new state. A refusal leaves the file as it was."""
        try:
            document = make()
        except tess_dl.TDLError as error:
            raise EditError(_why(error)) from error
        except (ValueError, KeyError, IndexError) as error:
            raise EditError(str(error.args[0]) if error.args else str(error)) from error
        kept = self._kept(Parsed(document.text, document, ()), selection)
        self._push(Snapshot(document.text, document, (), kept, kind))

    def _need_document(self) -> Document:
        document = self.document
        if document is None:
            first = self.errors[0] if self.errors else None
            where = f" Line {first.line}: {first.message}" if first else ""
            raise EditError(f"{self.relative or 'The file'} has syntax errors, so only the text view can change it until it parses.{where}")
        return document

    @staticmethod
    def _at_path(document: Document, path: IndexPath | None) -> Node | None:
        if path is None:
            return None
        try:
            found = document.at(tuple(path))
        except (IndexError, ValueError):
            return None
        return found if isinstance(found, (Block, If, For)) else None

    def _need_at(self, document: Document, path: IndexPath) -> Node:
        found = self._at_path(document, tuple(path))
        if found is None:
            raise EditError(f"There is no block at {tuple(path)}.")
        return found

    def _need_block(self, path: IndexPath) -> Block:
        found = self._need_at(self._need_document(), tuple(path))
        if not isinstance(found, Block):
            raise EditError("That is an If or For, which holds blocks but has no keys of its own.")
        return found

    def _kept(self, parsed: Parsed, selection: IndexPath | None) -> IndexPath | None:
        """`selection` in the new tree: the same path when it still points at a node, else the nearest ancestor that does; `None` without a tree."""
        if parsed.document is None:
            return None
        if selection is None:
            return ()
        path = tuple(selection)
        while path and self._at_path(parsed.document, path) is None:
            path = path[:-1]
        return path


def _after_insert(selection: IndexPath | None, new: IndexPath) -> IndexPath | None:
    """`selection` once a block was inserted at `new`: a selection below a later (or the same) entry of that parent moves down one."""
    if selection is None:
        return None
    at = len(new) - 1
    if len(selection) > at and selection[:at] == new[:at] and selection[at] >= new[at]:
        return (*selection[:at], selection[at] + 1, *selection[at + 1:])
    return selection


def _after_remove(selection: IndexPath | None, removed: IndexPath) -> IndexPath | None:
    """`selection` once the entry at `removed` is gone: on it or below it, the parent; below a later entry of that parent, up one; otherwise unchanged."""
    if selection is None:
        return None
    if selection[: len(removed)] == removed:
        return removed[:-1]
    at = len(removed) - 1
    if len(selection) > at and selection[:at] == removed[:at] and selection[at] > removed[at]:
        return (*selection[:at], selection[at] - 1, *selection[at + 1:])
    return selection


def _after_reorder(selection: IndexPath | None, old: IndexPath, to: int) -> IndexPath | None:
    """`selection` once the entry at `old` moved to index `to` of the same parent (as `list.insert` after `list.pop`): the entries between shift by one, the moved one and what is below it follow."""
    if selection is None:
        return None
    at = len(old) - 1
    if len(selection) <= at or selection[:at] != old[:at]:
        return selection
    start, here = old[at], selection[at]
    if here == start:
        shifted = to
    elif start < here <= to:
        shifted = here - 1
    elif to <= here < start:
        shifted = here + 1
    else:
        shifted = here
    return (*selection[:at], shifted, *selection[at + 1:])


def _why(error: tess_dl.TDLError) -> str:
    origin = getattr(error, "origin", None)
    where = f" (line {origin.line} of the new block)" if origin is not None and getattr(origin, "file", "") == "<block_text>" else ""
    hint = getattr(error, "hint", "")
    return f"{getattr(error, 'message', error)}{where}" + (f" {hint}." if hint else "")
