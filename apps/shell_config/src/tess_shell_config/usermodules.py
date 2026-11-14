"""The user's own modules: the `Params` block of every module file in the configuration folder's `Modules/` folder, read as the schema reads a shipped module.

A module file is `Module { Params { who { Type: string, Default: "world" } } ... }`. Its params have a name (the block's type, or the `Name` of a `Param { }` block), a `Type` word and optionally a `Default`.
Nothing documents them, so a param shows its name and type and no doc line. The result is a `ModuleInfo` for each module, so the Add menu and the form treat a user module like a shipped one;
a shipped module is never replaced by a user module of the same name.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from tess_dl import Block

from tess_shell_config.schema import ModuleInfo, ParamInfo, Schema
from tess_shell_config.tdl import child_named, parse_text, properties_of

__all__ = ["MODULES_FOLDER", "UserParam", "UserModule", "read_module", "module_info", "user_modules"]

#: The folder of the configuration folder that holds the user's modules.
MODULES_FOLDER = "Modules"

#: A `Type` word that is not a schema kind, read as the kind that has the widget for it.
_TYPE_KINDS = {"boolean": "bool", "int": "whole", "integer": "whole", "float": "number", "colour": "color", "str": "string"}
#: The layout block a module with no recognisable layout is rooted in.
_FALLBACK_ROOT = "Box"
_NOT_LAYOUT = ("Params", "Children", "Style")


@dataclass(frozen=True)
class UserParam:
    """A param as the file writes it: its name, `Type` word (`""` when it has none) and `Default` as TDL text (`None` when it has none)."""

    name: str
    type: str
    default: str | None


@dataclass(frozen=True)
class UserModule:
    """A module file: the module's `name` (the file's metadata `Name`, else its file name), where it is (`rel`), its params and the first block of its layout."""

    name: str
    rel: str
    params: tuple[UserParam, ...]
    layout: str


def read_module(rel: str, text: str, fallback_name: str) -> UserModule | None:
    """Read one module file's `Params` with `tess_dl`. A file that does not parse, or is not a module, is `None`."""
    parsed = parse_text(text, rel)
    document = parsed.document
    if document is None or document.root.type != "Module":
        return None
    name_value = document.metadata.get("Name")
    name = str(getattr(name_value, "text", None) or fallback_name)
    params: list[UserParam] = []
    block = child_named(document.root, "Params")
    if block is not None:
        for entry in (e for e in block.entries if isinstance(e, Block)):
            found = properties_of(entry)
            param_name = (entry.name or "") if entry.type == "Param" else entry.type
            if not param_name:
                continue
            kind = found.get("Type")
            default = found.get("Default")
            params.append(UserParam(param_name, document.text[kind.value.start:kind.value.end].strip('"') if kind is not None else "",
                                    document.text[default.value.start:default.value.end] if default is not None else None))
    layout = next((e.type for e in document.root.entries if isinstance(e, Block) and e.type not in _NOT_LAYOUT), _FALLBACK_ROOT)
    return UserModule(name, rel, tuple(params), layout)


def module_info(module: UserModule, schema: Schema) -> ModuleInfo:
    """A user module as the schema describes a shipped one: params with their types, the layout block it is rooted in (when the schema knows it), and the keys every shipped module takes."""
    params = {}
    for p in module.params:
        word = p.type.lower()
        kind = word if word in schema.kinds else _TYPE_KINDS.get(word, "")
        params[p.name] = ParamInfo(name=p.name, type=p.type, kind=kind, doc="", default=p.default, required=False, extra={"user_module": True, "type": p.type})
    shipped = [m.common_keys for m in schema.modules.values()]
    common = tuple(k for k in shipped[0] if all(k in keys for keys in shipped)) if shipped else ()
    root = module.layout if schema.block(module.layout) is not None else _FALLBACK_ROOT
    return ModuleInfo(name=module.name, doc=f"Your module, from {module.rel}.", params=params, root_block=root, events=(), common_keys=common, actions=(), extra={"user_module": True})


def user_modules(files: Iterable[tuple[str, str, str]], schema: Schema) -> Mapping[str, ModuleInfo]:
    """The user modules among `files` (`(rel, text, fallback name)`): those under `Modules/` that parse and are modules. The first of two files that give one name wins."""
    found: dict[str, ModuleInfo] = {}
    for rel, text, fallback in files:
        if not rel.startswith(MODULES_FOLDER + "/"):
            continue
        module = read_module(rel, text, fallback)
        if module is not None and module.name not in found:
            found[module.name] = module_info(module, schema)
    return found
