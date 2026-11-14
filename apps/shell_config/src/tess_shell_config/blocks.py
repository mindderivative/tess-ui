"""What a block may hold and what a new block is written as, both from the schema.

`children_of(schema, type)` is the "Add" menu of a block: the `allowed_children` its schema entry names, then (for a block that takes module calls) every shipped module. `new_block_text` is the TDL of a
new block: its type and the keys the schema marks `required`, each with the schema's default when it has a one-line one, else a value its widget writes without refusing it; a `Name` gets a name no
other block of the file has. `tess_dl.format_block` lays it out, so the new block is written the way the formatter writes it. No block type or key name is written in this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import tess_dl

from tess_shell_config.form import file_name, key_of_param
from tess_shell_config.schema import KeyInfo, Schema
from tess_shell_config.widgets import Context, Refused, WidgetRegistry, default_registry

__all__ = ["Child", "MODES", "children_of", "file_children", "mode_names", "accepts", "required_keys", "new_block_text"]

#: The key that names a block (the TDL language's, not the schema's: `Block.name` reads it).
NAME = "Name"


@dataclass(frozen=True)
class Child:
    """One entry of an Add menu: the block `type` to write, its one-line `doc`, and whether it is a module call."""

    type: str
    doc: str
    module: bool = False
    unique: bool = False


def children_of(schema: Schema, node_type: str) -> list[Child]:
    """The blocks the block called `node_type` may hold: its `allowed_children`, then the shipped modules where it takes module calls. A block the schema does not know holds none."""
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
