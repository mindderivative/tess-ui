"""What a block may hold and what a new block is written as, both from the schema.

`children_of(schema, type)` is the "Add" menu of a block: the `allowed_children` its schema entry names, then (for a block that takes module calls) every shipped module. `new_block_text` is the TDL of a
new block: its type and the keys the schema marks `required`, each with the schema's default when it has a one-line one, else a value its widget writes without refusing it; a `Name` gets a name no
other block of the file has. `tess_dl.format_block` lays it out, so the new block is written the way the formatter writes it. No block type or key name is written in this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import tess_dl

from tess_shell_config.form import file_name, key_of_param
from tess_shell_config.model import DocumentModel, block_names
from tess_shell_config.schema import KeyInfo, Schema
from tess_shell_config.tdl import IndexPath
from tess_shell_config.widgets import Context, Refused, WidgetRegistry, default_registry

__all__ = ["HOLDER", "holder_of", "has_layout", "is_surface", "is_layout", "holder_text", "add_child", "module_layout", "Child", "MODES", "children_of", "file_children", "mode_names", "accepts", "required_keys", "new_block_text"]

#: The key that names a block (the TDL language's, not the schema's: `Block.name` reads it).
NAME = "Name"
#: The key that selects what a stylesheet rule styles, and what a new rule selects: a class nothing has yet. A sample word would be taken for a block name and refused by the real checker ("unknown block in a selector").
SELECTOR = "Selector"
NEW_SELECTOR = '".new_rule"'


#: The block a surface or a container keeps its blocks in (the TDL language's word, as `Name` is): `Monitor { Children { Bar { } } }`. The schema's `allowed_children` of such a block are the blocks its `Children` holds.
HOLDER = "Children"


def holder_of(schema: Schema, node_type: str) -> str:
    """`HOLDER` when a block of `node_type` keeps the blocks it holds inside a `Children` block (the real checker refuses them written straight in it: "unknown block in Monitor Bar"); `""` when they go straight in
    (a Module offers `Children` itself among its allowed children, so its layout may be written in it or beside its `Params`; a Shell holds Monitors, a Stylesheet its Rules, a Style its classes and defaults).
    The schema does not say so in one field; it is read from what it does say: the block takes module calls, or one of the blocks it may hold is a root that does (a Monitor holds Bars)."""
    info = schema.block(node_type)
    if info is None or HOLDER in info.allowed_children or not info.allowed_children:
        return ""
    if info.module_calls:
        return HOLDER
    return HOLDER if any((root := schema.roots.get(name)) is not None and root.module_calls for name in info.allowed_children) else ""


def is_layout(schema: Schema, parent_type: str, child_type: str) -> bool:
    """Whether `child_type`, added to a `parent_type` block that holds its layout beside its other parts (a module's root), is its layout: a drawn block or a module call (not `Params`, `Style` or `Children`)."""
    info = schema.block(parent_type)
    return info is not None and HOLDER in info.allowed_children and (child_type in schema.blocks or child_type in schema.modules)


def has_layout(schema: Schema, node: tess_dl.Block) -> bool:
    """Whether a module root already has its layout: a drawn block or module call in it, or a `Children` block holding one. A module has exactly one (the real checker: "a module has one layout root")."""
    for entry in node.entries:
        if isinstance(entry, tess_dl.Block) and (is_layout(schema, node.type, entry.type) or (entry.type == HOLDER and any(isinstance(e, tess_dl.Block) for e in entry.entries))):
            return True
    return False


def is_surface(schema: Schema, node_type: str) -> bool:
    """Whether a block of `node_type` is a surface: one of the blocks a block that keeps its blocks in `Children` holds, itself a root (a Monitor holds Bar, Panel, Popup, Frame). The real checker refuses a surface's style
    keys written on it ("unknown key in Bar Background"): they go in its `Style { }`, where a drawn block (a Box) takes them either way."""
    return node_type in schema.roots and any(holder_of(schema, name) and node_type in info.allowed_children for name, info in schema.roots.items())


def holder_text(block_text: str) -> str:
    """A `Children` block holding the block written in `block_text`, as the formatter writes it."""
    return tess_dl.format_block(f"{HOLDER} {{ {block_text} }}")


@dataclass(frozen=True)
class Child:
    """One entry of an Add menu: the block `type` to write, its one-line `doc`, and whether it is a module call."""

    type: str
    doc: str
    module: bool = False
    unique: bool = False


def children_of(schema: Schema, node_type: str, parent_type: str = "") -> list[Child]:
    """The blocks the block called `node_type` may hold: its `allowed_children`, then the shipped modules where it takes module calls. A block the schema does not know holds none. A `Children` block (`node_type`
    is `HOLDER`) holds what its parent (`parent_type`) holds, but not the parent's own parts (a module's `Params`, `Style`: those go beside it, not in it)."""
    if node_type == HOLDER:
        wanted = holder_of(schema, parent_type) == HOLDER
        return [c for c in children_of(schema, parent_type) if c.type != HOLDER and (wanted or schema.roots.get(c.type) is None)] if parent_type else []
    info = schema.block(node_type)
    if info is None:
        return file_children(schema, node_type)
    found = []
    for name in info.allowed_children:
        child = schema.block(name)
        found.append(Child(name, child.doc if child is not None else ""))
    if info.module_calls:
        found += [Child(name, module.doc, True) for name, module in schema.modules.items() if all(name != c.type for c in found)]
    return found


#: The modes a theme file may define, besides the base (the Style Schema's "Modes inside one theme"; a mode the schema's tokens name is added to these).
MODES = ("Light", "Dark", "High_Contrast", "Reduced_Motion")
#: The block of a theme file that holds its modes.
MODES_BLOCK = "Modes"


def mode_names(schema: Schema) -> tuple[str, ...]:
    """The modes a theme may define: `MODES`, then any other mode the schema's tokens say they override in."""
    named = [file_name(mode) for group in schema.tokens.values() for token in group.values() for mode in token.modes]
    return (*MODES, *dict.fromkeys(m for m in named if m not in MODES))


def file_children(schema: Schema, node_type: str) -> list[Child]:
    """What a block the schema has no entry for may hold: the files of the theme and settings types have no root entry in the schema, but their shape is in its tables. A `Theme` holds its token groups (`schema.tokens`) and
    `Modes`; `Modes` holds the modes (a mode is one column of the token forms); a mode holds the token groups; `Settings` holds its sections (`schema.settings`). Each may be there once."""
    lower = node_type.lower()
    groups = [Child(file_name(group), f"The {group} tokens of the theme.", unique=True) for group in schema.tokens]
    if lower == "theme":
        return [*groups, Child(MODES_BLOCK, "The tokens that differ in a mode: one block for each mode, one column for each in the token forms.", unique=True)]
    if lower == MODES_BLOCK.lower():
        return [Child(mode, f"What the {mode.replace('_', ' ')} mode overrides: a column of its own in every token form.", unique=True) for mode in mode_names(schema)]
    if lower in {mode.lower() for mode in mode_names(schema)}:
        return groups
    if lower == "settings":
        return [Child(section, f"The {section} section of settings.tdl.", unique=True) for section in schema.settings if section.lower() != lower]
    return []


def module_layout(schema: Schema) -> str:
    """The block a new module's layout starts with: the first block the schema lets the root of a module file hold that is a drawn block (a module needs exactly one; `Params`, `Children` and `Style` are not). `""` when the schema has no such root."""
    root = schema.roots.get("Module")
    return next((name for name in root.allowed_children if name in schema.blocks), "") if root is not None else ""


def accepts(schema: Schema, parent_type: str, child_type: str) -> bool:
    """Whether the schema lets a `parent_type` block hold a `child_type` block."""
    return any(c.type == child_type for c in children_of(schema, parent_type))


def _alternative(keys: dict[str, KeyInfo], group: tuple[str, ...]) -> KeyInfo | None:
    """The key to write for one set of alternatives: the first, but not one that names a file (`path`) while another does not: a file that is not there is an error in the real checker, a name is not."""
    present = [keys[name] for name in group if name in keys]
    return next((k for k in present if k.kind != "path"), present[0] if present else None)


def required_keys(schema: Schema, type_name: str) -> list[KeyInfo]:
    """The keys a block must have: the schema's `required` sets of its entry (each a list of keys of which one is needed: a size or a depth; see `_alternative`), and the keys marked `required`; a module's required params."""
    info = schema.block(type_name)
    if info is not None:
        keys = info.all_keys()
        found = [pick for group in info.required if (pick := _alternative(keys, group)) is not None]
        return [*found, *(k for k in keys.values() if k.required and k not in found)]
    module = schema.modules.get(type_name)
    return [key_of_param(p) for p in module.params.values() if p.required] if module is not None else []


def new_block_text(schema: Schema, type_name: str, taken: set[str], registry: WidgetRegistry | None = None, *, bare: bool = False) -> str:
    """The new block as the formatter writes it: `type_name` with its required keys (`bare`: with none: a per-type default in a `Style` sets style keys, and the keys that make a block are not among them). `taken` is every name in the file, lower case; a `Name` is the type and a number that no block has."""
    registry = registry if registry is not None else default_registry()
    context = Context(schema)
    parts = []
    for key in [] if bare else required_keys(schema, type_name):
        if key.name == SELECTOR:
            parts.append(f"{SELECTOR}: {NEW_SELECTOR}")
            continue
        if key.name == NAME:
            number = 1
            while f"{type_name}_{number}".lower() in taken:
                number += 1
            parts.append(f"{NAME}: {type_name}_{number}")
            continue
        parts.append(f"{key.name}: {_value(key, registry, context)}")
    text = f"{type_name} {{ {', '.join(parts)} }}" if parts else f"{type_name} {{ }}"
    return tess_dl.format_block(text)


def _value(key: KeyInfo, registry: WidgetRegistry, context: Context) -> str:
    """The schema's default when it is one value on one line; else the value the key's widget writes for its sample edit."""
    default = (key.default or "").strip()
    if default and "{" not in default and "\n" not in default:
        return default
    widget = registry.create(key, context)
    try:
        written = widget.write(widget.sample_edit())
    except Refused:  # a sample the widget refuses is a bug in the widget: the block is still written, the key is left for the person
        written = None
    return written or '""'


def add_child(model: DocumentModel, schema: Schema, parent: IndexPath, type_name: str) -> IndexPath:
    """Add a new block of `type_name`, written with its required keys, last in the block at `parent`: in its `Children` block when it keeps its blocks there (made with the first). Returns its index path. One edit."""
    document = model.document
    node = model.node_at(parent)
    assert document is not None and isinstance(node, tess_dl.Block)
    info = schema.block(node.type)
    defaults = info is not None and HOLDER not in info.allowed_children and not info.module_calls and type_name in schema.blocks  # a Style's `Text { }`: defaults for a type
    text = new_block_text(schema, type_name, block_names(document), bare=defaults)
    if not holder_of(schema, node.type):
        return model.add_block(parent, text)
    held = next((i for i, e in enumerate(node.entries) if isinstance(e, tess_dl.Block) and e.type == HOLDER), None)
    if held is None:
        return (*model.add_block(parent, holder_text(text)), 0)
    return model.add_block((*parent, held), text)
