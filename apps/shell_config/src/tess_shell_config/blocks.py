"""What a block may hold and what a new block is written as, both from the schema.

`children_of(schema, type)` is the "Add" menu of a block: the `allowed_children` its schema entry names, then (for a block that takes module calls) every shipped module. `new_block_text` is the TDL of a
new block: its type and the keys the schema marks `required`, each with the schema's default when it has a one-line one, else a value its widget writes without refusing it; a `Name` gets a name no
other block of the file has. `tess_dl.format_block` lays it out, so the new block is written the way the formatter writes it. No block type or key name is written in this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import tess_dl

from tess_shell_config.form import key_of_param
from tess_shell_config.schema import KeyInfo, Schema
from tess_shell_config.widgets import Context, Refused, WidgetRegistry, default_registry

__all__ = ["Child", "children_of", "accepts", "required_keys", "new_block_text"]

#: The key that names a block (the TDL language's, not the schema's: `Block.name` reads it).
NAME = "Name"


@dataclass(frozen=True)
class Child:
    """One entry of an Add menu: the block `type` to write, its one-line `doc`, and whether it is a module call."""

    type: str
    doc: str
    module: bool = False


def children_of(schema: Schema, node_type: str) -> list[Child]:
    """The blocks the block called `node_type` may hold: its `allowed_children`, then the shipped modules where it takes module calls. A block the schema does not know holds none."""
    info = schema.block(node_type)
    if info is None:
        return []
    found = []
    for name in info.allowed_children:
        child = schema.block(name)
        found.append(Child(name, child.doc if child is not None else ""))
    if info.module_calls:
        found += [Child(name, module.doc, True) for name, module in schema.modules.items() if all(name != c.type for c in found)]
    return found


def accepts(schema: Schema, parent_type: str, child_type: str) -> bool:
    """Whether the schema lets a `parent_type` block hold a `child_type` block."""
    return any(c.type == child_type for c in children_of(schema, parent_type))


def required_keys(schema: Schema, type_name: str) -> list[KeyInfo]:
    """The keys a block of this type must have: those the schema marks `required` (a module's required params)."""
    info = schema.block(type_name)
    if info is not None:
        return [k for k in info.all_keys().values() if k.required]
    module = schema.modules.get(type_name)
    return [key_of_param(p) for p in module.params.values() if p.required] if module is not None else []


def new_block_text(schema: Schema, type_name: str, taken: set[str], registry: WidgetRegistry | None = None) -> str:
    """The new block as the formatter writes it: `type_name` with its required keys. `taken` is every name in the file, lower case; a `Name` is the type and a number that no block has."""
    registry = registry if registry is not None else default_registry()
    context = Context(schema)
    parts = []
    for key in required_keys(schema, type_name):
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
