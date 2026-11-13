"""The form generator: the keys of the selected block (or setting, module call, token group) as rows, built from the schema and nothing else.

`Form.build(model)` reads the selected block of the open file and makes `FormView`: the schema's groups, each key one row (label, a cell with the key's widget, the token button, the expression toggle and
the reset button), with the value the file has or the schema's default as the placeholder. A row's cell is a plain dict (`Cell.view`) that the window's view draws; every action (`commit`, `reset`,
`toggle_expression`, `use_token`) is one `DocumentModel` edit, so only that line of the file changes. No key name, enum value or default is written here: the registry (`widgets.py`) maps a schema kind
to a widget, and the schema says everything else. The coverage report (`coverage`) walks the whole schema and says which keys got the generic TDL text field and why.

What a row can be:

- a **key** of a root block, block, setting section or module call (a call's params, then the keys every module takes): the property of the selected block;
- a **token** of a theme group, with one cell for the base and one for each mode the file defines: the property of the nested block `Group { Name { Key: value } }` (and the same under `Modes { Mode { ... } }`).
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from tess_dl import Block, Document, Property, Slot, Value

from tess_shell_config.model import DocumentModel, EditError
from tess_shell_config.schema import KeyInfo, ModuleInfo, ParamInfo, Schema, TokenInfo
from tess_shell_config.tdl import IndexPath, child_named, properties_of
from tess_shell_config.values import EXPRESSION_STUB, key_problem, normal_colour, value_text
from tess_shell_config.widgets import Context, PathWidget, Refused, TdlWidget, Widget, WidgetRegistry, default_registry

__all__ = ["Outcome", "Fallback", "Coverage", "Cell", "Row", "FormView", "Form", "coverage", "key_of_param", "key_of_token", "file_name"]

NOT_BUILT = "Not built"
NOT_IN_SCHEMA = "Not in the schema"
PARAMS = "Parameters"
COMMON = "Common to every module"


@dataclass(frozen=True)
class Outcome:
    """What an action did: `changed` (the file's text changed), and the message for the status line (`ok` false for a refusal or an edit `tess_dl` would not make)."""

    changed: bool = False
    message: str = ""
    ok: bool = True


@dataclass(frozen=True)
class Fallback:
    """A key that got the generic TDL text field, and why."""

    where: str
    key: str
    kind: str
    reason: str


def key_of_param(param: ParamInfo) -> KeyInfo:
    """A module param as a key: the same record the schema keeps for a block's key, so one widget code path serves both."""
    return KeyInfo(name=param.name, kind=param.kind, doc=param.doc, default=param.default, choices=param.extra.get("choices"), enum=None, slot=False, required=param.required, built=True,
                   group=PARAMS, tokens=(), preferred_tokens=(), extra=param.extra)


def key_of_token(token: TokenInfo) -> KeyInfo:
    """A theme token as a key, named by its dotted path (`type.body.font_size`)."""
    return KeyInfo(name=token.name, kind=token.kind, doc=token.doc, default=token.default, choices=None, enum=None, slot=False, required=False, built=True, group=token.group, tokens=(),
                   preferred_tokens=(), extra=token.extra)


def file_name(part: str) -> str:
    """How the files write a name part: `surface_raised` -> `Surface_Raised`."""
    return "_".join(word.capitalize() for word in part.split("_"))


# -- where a value lives ----------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Found:
    """What the file has for a cell: a `value`, or a child `block` of the key's name (a composite value), or neither."""

    value: Value | None = None
    block: Block | None = None
    key: str = ""


class Store:
    """Where one cell's value is in the file, and how to change it."""

    def read(self, document: Document) -> Found:
        raise NotImplementedError

    def write(self, model: DocumentModel, text: str) -> None:
        raise NotImplementedError

    def remove(self, model: DocumentModel) -> None:
        raise NotImplementedError


@dataclass(frozen=True)
class PropertyStore(Store):
    """The property `key` of the block at `path`."""

    path: IndexPath
    key: str

    def _block(self, document: Document) -> Block | None:
        try:
            found = document.at(self.path)
        except (IndexError, ValueError):
            return None
        return found if isinstance(found, Block) else None

    def read(self, document: Document) -> Found:
        block = self._block(document)
        if block is None:
            return Found()
        prop = properties_of(block).get(self.key)
        if prop is not None:
            return Found(value=prop.value, key=self.key)
        return Found(block=child_named(block, self.key), key=self.key)

    def write(self, model: DocumentModel, text: str) -> None:
        model.set_value(self.path, self.key, text)

    def remove(self, model: DocumentModel) -> None:
        model.clear_value(self.path, self.key)


@dataclass(frozen=True)
class StyleKeyStore(PropertyStore):
    """A style key: written on the block (the shorthand) or inside the block's `Style { }`. A key that is already in the `Style` block is read and changed there, because writing it in both places is an
    error in the shell (Block Reference, R2); a key that is in neither is added on the block."""

    def _style(self, document: Document) -> Block | None:
        block = self._block(document)
        return child_named(block, "Style") if block is not None else None

    def _in_style(self, document: Document | None) -> bool:
        if document is None:
            return False
        direct = PropertyStore.read(self, document)
        style = self._style(document)
        return direct.value is None and direct.block is None and style is not None and (self.key in properties_of(style) or child_named(style, self.key) is not None)

    def read(self, document: Document) -> Found:
        if not self._in_style(document):
            return PropertyStore.read(self, document)
        style = self._style(document)
        assert style is not None
        prop = properties_of(style).get(self.key)
        return Found(value=prop.value, key=self.key) if prop is not None else Found(block=child_named(style, self.key), key=self.key)

    def write(self, model: DocumentModel, text: str) -> None:
        if self._in_style(model.document):
            model.set_nested_value(self.path, ("Style",), self.key, text)
        else:
            model.set_value(self.path, self.key, text)

    def remove(self, model: DocumentModel) -> None:
        if self._in_style(model.document):
            model.clear_nested_value(self.path, ("Style",), self.key)
        else:
            model.clear_value(self.path, self.key)

@dataclass(frozen=True)
class TokenStore(Store):
    """The property `leaf` of the block reached from the block at `path` through the child blocks `chain` (names compared without regard to case)."""

    path: IndexPath
    chain: tuple[str, ...]
    leaf: str

    def _walk(self, document: Document) -> Block | None:
        try:
            block = document.at(self.path)
        except (IndexError, ValueError):
            return None
        if not isinstance(block, Block):
            return None
        for name in self.chain:
            block = child_named(block, name)  # type: ignore[assignment]
            if block is None:
                return None
        return block

    def read(self, document: Document) -> Found:
        block = self._walk(document)
        if block is None:
            return Found()
        wanted = self.leaf.lower()
        for prop in (e for e in block.entries if isinstance(e, Property)):
            if prop.key.lower() == wanted:
                return Found(value=prop.value, key=prop.key)
        return Found(block=child_named(block, self.leaf), key=self.leaf)

    def write(self, model: DocumentModel, text: str) -> None:
        document = model.document
        found = self.read(document) if document is not None else Found()
        model.set_nested_value(self.path, self.chain, found.key if found.value is not None else file_name(self.leaf), text)

    def remove(self, model: DocumentModel) -> None:
        document = model.document
        found = self.read(document) if document is not None else Found()
        model.clear_nested_value(self.path, self.chain, found.key or self.leaf)


# -- cells and rows ---------------------------------------------------------------------------------------------------------------

@dataclass(eq=False)
class Cell:
    """One value slot of a row: a key's value, or a token's value in one mode (`column`)."""

    id: str
    widget: Widget
    store: Store | None
    column: str = ""
    present: bool = False
    text: str = ""
    shown: dict[str, Any] = field(default_factory=dict)
    tdl: bool = False
    is_slot: bool = False
    readonly: bool = False
    note: str = ""
    error: str = ""
    expression: bool = False
    slot: bool = False
    tokens: bool = False

    def view(self) -> dict[str, Any]:
        """The cell as the window's view draws it."""
        ui = "field" if (self.tdl or self.expression or self.readonly) else self.widget.ui
        data: dict[str, Any] = {
            "id": self.id, "ui": ui, "column": self.column, "present": self.present, "text": self.text, "default": self.widget.default, "error": self.error, "expression": self.expression,
            "slot": self.slot, "tokens": self.tokens, "readonly": self.readonly, "note": self.note, "fallback": self.widget.reason is not None, "stepping": False, "browse": False, "suffix": "",
            "hint": "", "mono": False, "placeholder": self.widget.default,
        }
        data.update(self.shown)
        if self.expression:
            data.update(field=self.text if self.is_slot else EXPRESSION_STUB, placeholder="{{ expression }}", suffix="", stepping=False, browse=False, mono=True)
        elif self.tdl or self.readonly:
            data.update(field=self.text, mono=True, stepping=False, browse=False, suffix="")
        return data


@dataclass(eq=False)
class Row:
    """One key (or token): a label, its doc, and its cells."""

    id: str
    label: str
    doc: str
    cells: list[Cell]
    group: str = ""
    key: KeyInfo | None = None
    required: bool = False
    markers: list[str] = field(default_factory=list)

    @property
    def missing(self) -> bool:
        """A required key that is absent."""
        return self.required and not any(c.present for c in self.cells)

    def view(self) -> dict[str, Any]:
        error = next((c.error for c in self.cells if c.error), "")
        return {"type": "row", "id": self.id, "label": self.label, "doc": self.doc, "required": self.required, "missing": self.missing, "markers": list(self.markers),
                "error": error, "cells": [c.view() for c in self.cells], "columns": [c.column for c in self.cells], "many": len(self.cells) > 1}


@dataclass(eq=False)
class FormView:
    """The form of one selected block: its rows in the schema's groups, notes about the block, and the view's flat list of items."""

    title: str = ""
    rows: list[Row] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    items: list[dict[str, Any]] = field(default_factory=list)

    @property
    def groups(self) -> dict[str, list[Row]]:
        found: dict[str, list[Row]] = {}
        for row in self.rows:
            found.setdefault(row.group, []).append(row)
        return found

    def row(self, key: str) -> Row:
        """The row of the key (or token) called `key`."""
        for row in self.rows:
            if row.key is not None and row.key.name == key or row.id == key:
                return row
        raise KeyError(key)

    def cell(self, key: str, column: str = "") -> Cell:
        return next(c for c in self.row(key).cells if c.column == column)

    def fallbacks(self) -> list[Fallback]:
        """The rows of this form whose widget is the generic TDL field because the kind has none of its own."""
        return [Fallback(r.group, r.key.name, r.key.kind, r.cells[0].widget.reason or "") for r in self.rows if r.key is not None and r.cells and r.cells[0].widget.reason]


# -- the form ---------------------------------------------------------------------------------------------------------------------

class Form:
    """Builds the form for the selected block and applies the edits made in it. One per window; it holds what the form remembers between builds (the cells switched to an expression field,
    the text of a value that was refused, the token chooser's cell)."""

    def __init__(self, schema: Schema, registry: WidgetRegistry | None = None) -> None:
        self.schema = schema
        self.registry = registry if registry is not None else default_registry()
        self.expressions: set[str] = set()
        self.opened: set[str] = set()
        self.closed: set[str] = set()
        self.drafts: dict[str, Mapping[str, Any]] = {}
        self.errors: dict[str, str] = {}
        self.view: FormView = FormView()
        self._model: DocumentModel | None = None
        self._cells: dict[str, Cell] = {}
        self._scope: tuple[str, IndexPath | None] = ("", None)
        self._seen: dict[str, tuple[Any, int]] = {}
        self._folder: Path | None = None

    # -- building ----------------------------------------------------------------------------------------------------------------

    def build(self, model: DocumentModel | None, folder: Path | None = None) -> FormView:
        """The form for what `model` has selected. With no file, no tree or no block selected (an `If` or `For` has no keys of its own) the form is empty, with a note that says why."""
        self._model, self._folder = model, folder
        view = FormView()
        self._cells = {}
        if model is None:
            self.view = view
            return view
        scope = (model.relative, model.selection)
        if scope != self._scope:
            self.errors.clear()
            self.drafts.clear()
            self.expressions.clear()
            self._scope = scope
        document, node = model.document, model.selected
        if document is None:
            view.notes.append("This file has syntax errors: fix them in the text view and the form returns.")
        elif not isinstance(node, Block):
            view.notes.append("Select a block in the structure: an If or For holds blocks but has no keys of its own." if node is not None else "Select a block in the structure to edit its keys.")
        else:
            self._fill(view, document, node, tuple(model.selection or ()))
        for row in view.rows:
            for cell in row.cells:
                self._cells[cell.id] = cell
        view.items = self._items(view)
        self.view = view
        return view

    def _context(self) -> Context:
        model = self._model
        file_dir = model.path.parent if model is not None and model.path is not None else None
        return Context(self.schema, file_dir, self._folder)

    def _fill(self, view: FormView, document: Document, block: Block, path: IndexPath) -> None:
        schema = self.schema
        root = document.root
        view.title = f"{block.type}  {block.name}" if block.name else block.type
        context = self._context()
        if root.type.lower() == "theme" and self._token_group(document, path) is not None:
            self._fill_tokens(view, document, block, path, context)
            return
        if root.type == "Settings" or (root.type.lower() == "settings" and block.type in schema.settings):
            section = schema.settings.get(block.type)
            if section is not None:
                self._fill_keys(view, document, block, path, context, list(section.values()))
                view.notes.append(f"The {block.type} section of settings.tdl.")
                return
        module = schema.modules.get(block.type)
        info = schema.block(block.type)
        if module is not None and info is None:
            root_info = schema.block(module.root_block)
            self._fill_keys(view, document, block, path, context, self._module_keys(module), set(root_info.style) if root_info is not None else ())
            view.notes.append(module.doc)
            return
        if info is None:
            if root.type.lower() == "theme":
                view.notes.append("A theme: choose one of its token groups (Color, Type, Shape, Space, Elevation, Motion) to edit the tokens.")
            else:
                view.notes.append(f"The schema has no entry for a {block.type} block, so there are no keys to show. Its text is in the text view.")
            self._fill_unknown(view, document, block, path, context, ())
            return
        keys = list(info.all_keys().values())
        self._fill_keys(view, document, block, path, context, keys, set(info.style))
        if info.doc:
            view.notes.append(info.doc)
        satisfied = [group for group in info.required if all(self._has(block, name) for name in group)]
        if info.required and not satisfied:
            view.notes.append("Needs one of: " + "; ".join(" and ".join(group) for group in info.required) + ".")

    @staticmethod
    def _has(block: Block, name: str) -> bool:
        return name in properties_of(block) or child_named(block, name) is not None

    def _module_keys(self, module: ModuleInfo) -> list[KeyInfo]:
        keys = [key_of_param(p) for p in module.params.values()]
        root = self.schema.block(module.root_block)
        known = root.all_keys() if root is not None else {}
        for name in module.common_keys:
            found = known.get(name)
            keys.append(_regrouped(found, COMMON) if found is not None else KeyInfo(name, "", "", None, None, None, False, False, True, COMMON, (), ()))
        return keys

    def _fill_keys(self, view: FormView, document: Document, block: Block, path: IndexPath, context: Context, keys: Sequence[KeyInfo], style: Collection[str] = ()) -> None:
        for key in keys:
            row = self._key_row(document, path, key, context, key.name in style)
            view.rows.append(row)
        self._fill_unknown(view, document, block, path, context, [k.name for k in keys])
        order: dict[str, int] = {}
        for row in view.rows:
            order.setdefault(row.group, len(order))
        trailing = {NOT_BUILT: 1, NOT_IN_SCHEMA: 2}
        view.rows.sort(key=lambda r: (trailing.get(r.group, 0), order[r.group]))

    def _fill_unknown(self, view: FormView, document: Document, block: Block, path: IndexPath, context: Context, known: Sequence[str]) -> None:
        """Properties the file has that the schema does not name: shown as TDL text, so nothing the person wrote is hidden."""
        names = set(known)
        for name in properties_of(block):
            if name in names:
                continue
            key = KeyInfo(name, "", "Not named in the schema of this shell version.", None, None, None, False, False, True, NOT_IN_SCHEMA, (), ())
            cell = self._cell(f"k:{name}|", TdlWidget(key, context, "the schema does not name this key"), PropertyStore(path, name), document, "", key)
            view.rows.append(Row(f"k:{name}", name.replace("_", " "), key.doc, [cell], NOT_IN_SCHEMA, key))

    def _key_row(self, document: Document | None, path: IndexPath, key: KeyInfo, context: Context, styled: bool = False) -> Row:
        widget = self.registry.create(key, context)
        group = NOT_BUILT if not key.built else (key.group or "Other")
        store = StyleKeyStore(path, key.name) if styled else PropertyStore(path, key.name)
        cell = self._cell(f"k:{key.name}|", widget, store, document, "", key)
        markers = []
        if not key.built:
            markers.append("not built in this shell version")
        if key.extra.get("refused"):
            markers.append("the shell refuses this key")
            cell.readonly = True
        if key.extra.get("module_only"):
            markers.append("set by a module")
        problem = key_problem(key.name)
        if problem:  # a word the language reserves cannot be written as a property by `tess_dl`'s edits: the row says so instead of offering a field that always fails
            markers.append("cannot be written here")
            cell.readonly, cell.note = True, f"tess_dl: {problem}. Write it in the text view."
        return Row(f"k:{key.name}", key.name.replace("_", " "), key.doc, [cell], group, key, key.required, markers)

    def _cell(self, cell_id: str, widget: Widget, store: Store | None, document: Document | None, column: str, key: KeyInfo) -> Cell:
        cell = Cell(cell_id, widget, store, column, slot=key.slot, tokens=bool(key.tokens))
        found = store.read(document) if store is not None and document is not None else Found()
        if found.value is not None:
            cell.present, cell.text = True, value_text(document, found.value)  # type: ignore[arg-type]
            cell.is_slot = isinstance(found.value, Slot)
            shown = None if cell.is_slot else widget.read(found.value, cell.text)
            if shown is None:
                cell.tdl = True
                cell.note = "an expression" if cell.is_slot else "shown as TDL text: this widget cannot show it"
                shown = {}
            cell.shown = shown
        elif found.block is not None:
            cell.present, cell.readonly = True, True
            cell.text = document.text[found.block.start:found.block.end]  # type: ignore[union-attr]
            cell.note = "a block: edit it in the structure"
        else:
            cell.shown = widget.empty()
        cell.expression = cell.is_slot or cell.id in self.expressions
        cell.error = self.errors.get(cell.id, "")
        draft = self.drafts.get(cell.id)
        if draft is not None and not cell.expression:
            cell.shown = {**cell.shown, **_overlay(draft)}
        return cell

    # -- tokens ------------------------------------------------------------------------------------------------------------------

    def _token_group(self, document: Document, path: IndexPath) -> tuple[str, int] | None:
        """The token group the block at `path` is in (a group block of the theme, or a block inside one) and the depth of that group block in `path`."""
        blocks = self._chain(document, path)
        for depth, block in enumerate(blocks[1:], start=1):
            if block.type.lower() in self.schema.tokens:
                return block.type.lower(), depth
        return None

    @staticmethod
    def _chain(document: Document, path: IndexPath) -> list[Block]:
        found: list[Block] = [document.root]
        for i in range(1, len(path) + 1):
            node = document.at(path[:i])
            if not isinstance(node, Block):
                break
            found.append(node)
        return found

    def _fill_tokens(self, view: FormView, document: Document, block: Block, path: IndexPath, context: Context) -> None:
        group, depth = self._token_group(document, path)  # type: ignore[misc]
        chain = self._chain(document, path)
        prefix = [b.type.lower() for b in chain[depth + 1:]]
        group_path = path[:depth]
        columns: list[tuple[str, IndexPath, tuple[str, ...]]] = []
        group_block = chain[depth]
        if depth == 1:  # a group block directly under the theme: the base, then one column per mode the file defines
            columns.append(("base", group_path, ()))
            modes = child_named(document.root, "Modes")
            if modes is not None:
                for mode in (e for e in modes.entries if isinstance(e, Block)):
                    columns.append((mode.type, (), ("Modes", mode.type, group_block.type)))
        else:
            columns.append((chain[depth - 1].type if depth > 1 else "base", group_path, ()))
        view.notes.append(f"The {group} tokens: one column for the base" + (" and one for each mode this theme defines." if len(columns) > 1 else "."))
        for token in self.schema.tokens[group].values():
            parts = token.name.split(".")
            if parts[: len(prefix)] != prefix:
                continue
            rest = parts[len(prefix):]
            key = key_of_token(token)
            widget = self.registry.create(key, context)
            cells = []
            for column, base, names in columns:
                folders = tuple(file_name(p) for p in parts[:-1])
                store: Store = TokenStore(base, (*names, *folders), parts[-1])
                cells.append(self._cell(f"t:{token.name}|{column}", widget, store, document, column, key))
            view.rows.append(Row(f"t:{token.name}", ".".join(rest), token.doc, cells, group, key))

    # -- the flat list the view draws -----------------------------------------------------------------------------------------------

    def is_open(self, view: FormView, group: str) -> bool:
        """Whether a group shows its rows: the ones the person opened, the first group, and a group with a required key that is absent or a refused value, unless the person closed it."""
        if group in self.opened:
            return True
        if group in self.closed:
            return False
        rows = view.groups.get(group, [])
        first = next(iter(view.groups), None) == group
        return first or any(r.missing or any(c.error for c in r.cells) for r in rows)

    def toggle_group(self, group: str) -> None:
        """Open a closed group or close an open one (what the person chose is remembered by the group's name, from block to block)."""
        if self.is_open(self.view, group):
            self.opened.discard(group)
            self.closed.add(group)
        else:
            self.closed.discard(group)
            self.opened.add(group)
        self.view.items = self._items(self.view)

    def _items(self, view: FormView) -> list[dict[str, Any]]:
        """Each group is a header; only an open group builds its rows, which keeps the window light (every row is a dozen nodes the toolkit lays out again after any change)."""
        items: list[dict[str, Any]] = []
        seen: dict[str, tuple[Any, int]] = {}
        for group, rows in view.groups.items():
            opened = self.is_open(view, group)
            items.append(self._stamped({"type": "group", "id": f"g:{group}", "label": group, "open": opened, "count": len(rows), "present": sum(1 for r in rows if any(c.present for c in r.cells))}, seen))
            if opened:
                items.extend(self._stamped(row.view(), seen) for row in rows)
        self._seen = seen
        return items

    def _stamped(self, item: dict[str, Any], seen: dict[str, tuple[Any, int]]) -> dict[str, Any]:
        """Gives the item its `key` for the view's `for:`: the same while the item is unchanged, new when it changed, so a row whose value changed is built again (its field starts from the file)."""
        before = self._seen.get(item["id"])
        stamp = 0 if before is None else before[1] + (0 if before[0] == item else 1)
        seen[item["id"]] = (item, stamp)
        return {**item, "key": f"{item['id']}#{stamp}"}

    # -- the edits ----------------------------------------------------------------------------------------------------------------

    def cell(self, cell_id: str) -> Cell:
        try:
            return self._cells[cell_id]
        except KeyError:
            raise KeyError(f"The form has no cell {cell_id!r}.") from None

    def commit(self, cell_id: str, edit: Mapping[str, Any]) -> Outcome:
        """Write what the person made in a cell. A refused value (out of range, not a number, a pattern) writes nothing, says why, and keeps the typed text in the field."""
        cell = self.cell(cell_id)
        try:
            text = self._text_of(cell, edit)
        except _Skip:
            return Outcome()
        except Refused as error:
            self.errors[cell_id] = str(error)
            self.drafts[cell_id] = dict(edit)
            self._rebuild()
            return Outcome(False, str(error), False)
        return self._apply(cell, text)

    def _text_of(self, cell: Cell, edit: Mapping[str, Any]) -> str | None:
        if cell.readonly:
            raise Refused(cell.note or "This value cannot be edited here.")
        raw = str(edit.get("text", "")).strip()
        if cell.expression:
            if not raw or raw.replace(" ", "") == "{{}}":
                raise _Skip
            if not (raw.startswith("{{") and raw.endswith("}}")):
                raise Refused("An expression is written {{ ... }}.")
            return raw
        if cell.tdl and "text" in edit:
            return raw or None
        return cell.widget.write(edit)

    def _apply(self, cell: Cell, text: str | None) -> Outcome:
        model = self._model
        assert model is not None and cell.store is not None
        self.errors.pop(cell.id, None)
        self.drafts.pop(cell.id, None)
        try:
            if text is None:
                if cell.present:
                    cell.store.remove(model)
                    self.expressions.discard(cell.id)
                else:
                    self._rebuild()
                    return Outcome()
            elif cell.present and text == cell.text:  # unchanged: nothing is written
                self._rebuild()
                return Outcome()
            else:
                cell.store.write(model, text)
                if text.startswith("{{"):
                    self.expressions.add(cell.id)
                else:
                    self.expressions.discard(cell.id)
        except EditError as error:
            self.errors[cell.id] = str(error)
            self._rebuild()
            return Outcome(False, str(error), False)
        self._rebuild()
        return Outcome(True, "")

    def reset(self, cell_id: str) -> Outcome:
        """Reset to the default: remove the property (an absent key gives the schema's default)."""
        cell = self.cell(cell_id)
        if not cell.present:
            return Outcome()
        self.drafts.pop(cell_id, None)
        return self._apply(cell, None)

    def toggle_expression(self, cell_id: str) -> Outcome:
        """Swap the cell between its widget and an expression field holding `{{ ... }}`. Switching an expression that is in the file back to the widget removes it (the property goes back to its default)."""
        cell = self.cell(cell_id)
        if not cell.slot:
            return Outcome(False, "This key does not take an expression.", False)
        if cell.is_slot:
            return self._apply(cell, None)
        if cell_id in self.expressions:
            self.expressions.discard(cell_id)
        else:
            self.expressions.add(cell_id)
        self._rebuild()
        return Outcome()

    def tokens_for(self, cell_id: str) -> list[dict[str, Any]]:
        """The tokens the key accepts for the token list: `{group, name, ref, value, colour, doc}`, the preferred ones first, a colour's swatch in `colour`."""
        cell = self.cell(cell_id)
        key = cell.widget.key
        found = self.schema.tokens_for(key)
        return [{"group": t.group, "name": t.name, "ref": t.ref, "value": (t.default or ""), "doc": t.doc, "colour": _swatch(t), "label": f"{t.group}.{t.name}"} for t in found]

    def use_token(self, cell_id: str, ref: str) -> Outcome:
        """Write `$group.name` for the cell (a reference is a plain word, written as it is)."""
        cell = self.cell(cell_id)
        if not cell.tokens:
            return Outcome(False, "This key takes no theme token.", False)
        self.expressions.discard(cell_id)
        return self._apply(cell, ref)

    def use_path(self, cell_id: str, chosen: str) -> Outcome:
        """The file dialog's answer for a path cell: written as a path relative to the open file's folder when it lies under it."""
        cell = self.cell(cell_id)
        if not isinstance(cell.widget, PathWidget):
            return Outcome(False, "This key is not a path.", False)
        return self.commit(cell_id, {"text": cell.widget.from_dialog(chosen)})

    def step(self, cell_id: str, direction: int, text: str) -> Outcome:
        """Up or down in a number field: one step of the schema's `step`, kept inside its range."""
        cell = self.cell(cell_id)
        stepper: Callable[[str, int], str | None] | None = getattr(cell.widget, "step", None)
        if stepper is None or cell.expression or cell.tdl:
            return Outcome()
        moved = stepper(text, direction)
        return self.commit(cell_id, {"text": moved or ""})

    def _rebuild(self) -> None:
        self.build(self._model, self._folder)


class _Skip(Exception):
    """An edit that asks for nothing (an empty expression): nothing is written and nothing is said."""


def _regrouped(key: KeyInfo, group: str) -> KeyInfo:
    return replace(key, group=group)


def _overlay(edit: Mapping[str, Any]) -> dict[str, Any]:
    """What a refused edit shows again: the typed text, unit and sides, so the person corrects it instead of retyping it."""
    shown: dict[str, Any] = {}
    if "text" in edit:
        shown["field"] = str(edit["text"])
    if "unit" in edit:
        shown["unit"] = str(edit["unit"])
        shown["number_enabled"] = shown["unit"] in ("px", "%")
    if "fields" in edit:
        shown["fields"] = [str(f) for f in edit["fields"]]
    if "linked" in edit:
        shown["linked"] = bool(edit["linked"])
    return shown


def _swatch(token: TokenInfo) -> str:
    """A colour token's colour for the token list's swatch (`#rrggbb`), or ''."""
    default = (token.default or "").strip()
    if token.kind == "color" and len(default) > 1 and default[0] == default[-1] == '"':
        return normal_colour(default[1:-1]) or ""
    return ""


# -- the coverage report ----------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Coverage:
    """Every key the schema has (root blocks, blocks, settings, module params, tokens), with the widget it gets. `fallbacks` are those that got the generic TDL text field, each with its reason."""

    entries: tuple[tuple[str, KeyInfo, Widget], ...]

    @property
    def fallbacks(self) -> list[Fallback]:
        return [Fallback(where, key.name, key.kind, widget.reason or "") for where, key, widget in self.entries if widget.reason]


def coverage(schema: Schema, registry: WidgetRegistry | None = None) -> Coverage:
    """Walk the whole schema and make a widget for every key. Nothing is read from a file."""
    registry = registry if registry is not None else default_registry()
    context = Context(schema)
    entries: list[tuple[str, KeyInfo, Widget]] = []
    for where, key in schema.walk_keys():
        entries.append((where, key, registry.create(key, context)))
    for name, module in schema.modules.items():
        for param in module.params.values():
            key = key_of_param(param)
            entries.append((f"module {name}", key, registry.create(key, context)))
    for group, tokens in schema.tokens.items():
        for token in tokens.values():
            key = key_of_token(token)
            entries.append((f"tokens {group}", key, registry.create(key, context)))
    return Coverage(tuple(entries))
