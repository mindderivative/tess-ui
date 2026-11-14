"""The shell's exported schema, read into typed classes.

`tesserae-shell schema --json` says what can be written: every root block, block, setting, module, token, event and action, with each key's
kind, choices, default (as TDL text), doc and range. This module reads that JSON and nothing else: **no key name, enum value or default
is written in this application's code**; a form, an "add" menu or a default is looked up here.

Versions. `schema_version` is `major.minor`. A major version the application does not know is refused (`UnsupportedSchemaVersion`, naming
both versions); a higher minor is read, and what it adds is kept in each class's `extra` so a later form can show it with the generic
widget of its kind.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from typing import Any

__all__ = [
    "SUPPORTED_MAJOR", "SchemaError", "UnsupportedSchemaVersion", "Schema", "KindInfo", "KeyInfo", "BlockInfo", "TokenInfo", "ModuleInfo", "ParamInfo", "PopupInfo",
    "EventInfo", "ActionInfo", "ActionArg", "parse_version", "load_schema",
]

#: The one major version of the schema this application reads.
SUPPORTED_MAJOR = 1


class SchemaError(ValueError):
    """The schema is not the shape this application reads."""


class UnsupportedSchemaVersion(SchemaError):
    """The schema's major version is not the one this application knows."""

    def __init__(self, found: str, supported_major: int = SUPPORTED_MAJOR) -> None:
        self.found = found
        self.supported_major = supported_major
        super().__init__(f"The shell exports schema {found}; this application reads schema {supported_major}.x. Update the application or use a shell that exports schema {supported_major}.x.")


def parse_version(text: Any) -> tuple[int, int]:
    """`"1.1"` -> `(1, 1)`; a bare `"2"` is `(2, 0)`. Raises `SchemaError` for anything else."""
    try:
        parts = str(text).strip().split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        raise SchemaError(f"The schema's version {text!r} is not major.minor.") from None
    return major, minor


def _tuple(value: Any) -> tuple[Any, ...]:
    return tuple(value) if isinstance(value, (list, tuple)) else ()


def _strings(value: Any) -> tuple[str, ...]:
    return tuple(str(v) for v in value) if isinstance(value, (list, tuple)) else ()


def _kind(raw: Mapping[str, Any]) -> str:
    """A record's kind: `string` when the record names none at all, `""` when the schema says `null` (a key that is not built has no kind)."""
    kind = raw.get("kind", "string")
    return "" if kind is None else str(kind)


def _mapping(value: Any, what: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaError(f"The schema's {what} is not a table.")
    return value


#: The fields every record reads itself; anything else lands in `extra`.
_KEY_FIELDS = ("kind", "choices", "enum", "default", "doc", "slot", "required", "built", "group", "tokens", "preferred_tokens")


@dataclass(frozen=True)
class KindInfo:
    """One entry of the `kinds` table: the widget family (`ui`) a key of this kind gets, with a note and the shell's own kinds it covers."""

    name: str
    ui: str
    note: str
    model_kinds: tuple[str, ...]
    extra: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class KeyInfo:
    """A key of a root block, block, style, setting or module param. `extra` holds the optional hints (range, units, arity, ...) by their schema names."""

    name: str
    kind: str
    doc: str
    default: str | None
    choices: tuple[Any, ...] | None
    enum: str | None
    slot: bool
    required: bool
    built: bool
    group: str | None
    tokens: tuple[str, ...]
    preferred_tokens: tuple[str, ...]
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def minimum(self) -> float | None:
        return self.extra.get("min")

    @property
    def maximum(self) -> float | None:
        return self.extra.get("max")

    @property
    def step(self) -> float | None:
        return self.extra.get("step")

    @property
    def unit(self) -> str | None:
        return self.extra.get("unit")

    @property
    def units(self) -> tuple[str, ...]:
        return _strings(self.extra.get("units"))

    @classmethod
    def read(cls, name: str, raw: Mapping[str, Any]) -> KeyInfo:
        raw = _mapping(raw, f"key {name}")
        choices = raw.get("choices")
        return cls(
            name=name, kind=_kind(raw), doc=str(raw.get("doc") or ""),
            default=None if raw.get("default") is None else str(raw["default"]),
            choices=tuple(choices) if isinstance(choices, (list, tuple)) else None,
            enum=None if raw.get("enum") is None else str(raw["enum"]),
            slot=bool(raw.get("slot", False)), required=bool(raw.get("required", False)), built=bool(raw.get("built", True)),
            group=None if raw.get("group") is None else str(raw["group"]),
            tokens=_strings(raw.get("tokens")), preferred_tokens=_strings(raw.get("preferred_tokens")),
            extra={k: v for k, v in raw.items() if k not in _KEY_FIELDS})


@dataclass(frozen=True)
class ParamInfo:
    """A param of a shipped module: its declared `type` and `kind` (the widget family), default text and doc."""

    name: str
    type: str
    kind: str
    doc: str
    default: str | None
    required: bool
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def minimum(self) -> float | None:
        return self.extra.get("min")

    @property
    def maximum(self) -> float | None:
        return self.extra.get("max")

    @property
    def step(self) -> float | None:
        return self.extra.get("step")

    @property
    def unit(self) -> str | None:
        return self.extra.get("unit")

    @classmethod
    def read(cls, name: str, raw: Mapping[str, Any]) -> ParamInfo:
        raw = _mapping(raw, f"param {name}")
        return cls(name=name, type=str(raw.get("type", "")), kind=_kind(raw), doc=str(raw.get("doc") or ""),
                   default=None if raw.get("default") is None else str(raw["default"]), required=bool(raw.get("required", False)),
                   extra={k: v for k, v in raw.items() if k not in ("type", "kind", "doc", "default", "required")})


@dataclass(frozen=True)
class BlockInfo:
    """A root block or a block: its head words, keys, style keys, events, the sets of keys of which one set is required (`required`), the blocks it may hold."""

    name: str
    doc: str
    heads: tuple[str, ...]
    keys: Mapping[str, KeyInfo]
    style: Mapping[str, KeyInfo]
    events: tuple[str, ...]
    required: tuple[tuple[str, ...], ...]
    repeatable: bool
    allowed_children: tuple[str, ...]
    module_calls: bool
    example: str
    not_built: tuple[str, ...]
    extra: Mapping[str, Any] = field(default_factory=dict)

    def all_keys(self) -> dict[str, KeyInfo]:
        """The keys, then the style keys (a style key is a key of the block's `Style` block)."""
        return {**self.keys, **self.style}

    @classmethod
    def read(cls, name: str, raw: Mapping[str, Any]) -> BlockInfo:
        raw = _mapping(raw, f"block {name}")
        known = ("doc", "heads", "keys", "style", "events", "required", "repeatable", "allowed_children", "module_calls", "example", "not_built")
        return cls(
            name=name, doc=str(raw.get("doc") or ""), heads=_strings(raw.get("heads")),
            keys={k: KeyInfo.read(k, v) for k, v in _mapping(raw.get("keys") or {}, f"{name} keys").items()},
            style={k: KeyInfo.read(k, v) for k, v in _mapping(raw.get("style") or {}, f"{name} style").items()},
            events=_strings(raw.get("events")), required=tuple(_strings(group) for group in _tuple(raw.get("required"))),
            repeatable=bool(raw.get("repeatable", False)), allowed_children=_strings(raw.get("allowed_children")),
            module_calls=bool(raw.get("module_calls", False)), example=str(raw.get("example") or ""), not_built=_strings(raw.get("not_built")),
            extra={k: v for k, v in raw.items() if k not in known})


@dataclass(frozen=True)
class TokenInfo:
    """A theme token: `group` and `name` make the reference `ref` (`$group.name`); `modes` are the modes that override it in the shell's own theme."""

    group: str
    name: str
    kind: str
    ref: str
    default: str | None
    doc: str
    modes: tuple[str, ...]
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def minimum(self) -> float | None:
        return self.extra.get("min")

    @property
    def maximum(self) -> float | None:
        return self.extra.get("max")

    @classmethod
    def read(cls, group: str, name: str, raw: Mapping[str, Any]) -> TokenInfo:
        raw = _mapping(raw, f"token {group}.{name}")
        return cls(group=group, name=name, kind=_kind(raw), ref=str(raw.get("ref") or f"${group}.{name}"),
                   default=None if raw.get("default") is None else str(raw["default"]), doc=str(raw.get("doc") or ""), modes=_strings(raw.get("modes")),
                   extra={k: v for k, v in raw.items() if k not in ("kind", "ref", "default", "doc", "modes")})


@dataclass(frozen=True)
class PopupInfo:
    """One popup a module opens by default (schema 1.2 `popups`): the module that shows it, the block it holds, and its placement. `values` are the defaults by the schema's own
    names (the keys of the `Popup` root block, in lower case), a `max_height` as written: `{"value": 60.0, "unit": "%"}`."""

    name: str
    shown_by: str
    content: str
    doc: str
    values: Mapping[str, Any]

    @classmethod
    def read(cls, name: str, raw: Mapping[str, Any]) -> PopupInfo:
        raw = _mapping(raw, f"popup {name}")
        return cls(name=name, shown_by=str(raw.get("shown_by") or ""), content=str(raw.get("content") or ""), doc=str(raw.get("doc") or ""),
                   values={k: v for k, v in raw.items() if k not in ("shown_by", "content", "doc")})


@dataclass(frozen=True)
class ModuleInfo:
    """A shipped module: its params, the block it is rooted in, the events it raises, the common keys of a call and the actions it takes."""

    name: str
    doc: str
    params: Mapping[str, ParamInfo]
    root_block: str
    events: tuple[str, ...]
    common_keys: tuple[str, ...]
    actions: tuple[Any, ...]
    extra: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def read(cls, name: str, raw: Mapping[str, Any]) -> ModuleInfo:
        raw = _mapping(raw, f"module {name}")
        known = ("doc", "params", "root_block", "events", "common_keys", "actions")
        return cls(name=name, doc=str(raw.get("doc") or ""),
                   params={k: ParamInfo.read(k, v) for k, v in _mapping(raw.get("params") or {}, f"{name} params").items()},
                   root_block=str(raw.get("root_block") or ""), events=_strings(raw.get("events")), common_keys=_strings(raw.get("common_keys")),
                   actions=_tuple(raw.get("actions")), extra={k: v for k, v in raw.items() if k not in known})


@dataclass(frozen=True)
class EventInfo:
    name: str
    doc: str
    module_only: bool
    needs: tuple[str, ...]
    raised_by: tuple[str, ...]
    extra: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def read(cls, name: str, raw: Mapping[str, Any]) -> EventInfo:
        raw = _mapping(raw, f"event {name}")
        return cls(name=name, doc=str(raw.get("doc") or ""), module_only=bool(raw.get("module_only", False)), needs=_strings(raw.get("needs")),
                   raised_by=_strings(raw.get("raised_by")), extra={k: v for k, v in raw.items() if k not in ("doc", "module_only", "needs", "raised_by")})


@dataclass(frozen=True)
class ActionArg:
    name: str
    kind: str
    required: bool
    doc: str


@dataclass(frozen=True)
class ActionInfo:
    name: str
    doc: str
    args: tuple[ActionArg, ...]
    built: bool

    @classmethod
    def read(cls, raw: Mapping[str, Any]) -> ActionInfo:
        raw = _mapping(raw, "action")
        args = tuple(ActionArg(str(a.get("name", "")), str(a.get("kind", "string")), bool(a.get("required", False)), str(a.get("doc") or ""))
                     for a in _tuple(raw.get("args")) if isinstance(a, Mapping))
        return cls(name=str(raw.get("name", "")), doc=str(raw.get("doc") or ""), args=args, built=bool(raw.get("built", True)))


_KNOWN_TOP = ("schema_version", "shell_version", "kinds", "roots", "blocks", "settings", "events", "actions", "enums", "tokens", "modules")
_OPTIONAL_TOP = ("popups",)


@dataclass(frozen=True)
class Schema:
    """The whole schema. Tables keep the shell's order."""

    version: tuple[int, int]
    shell_version: str
    kinds: Mapping[str, KindInfo]
    roots: Mapping[str, BlockInfo]
    blocks: Mapping[str, BlockInfo]
    settings: Mapping[str, Mapping[str, KeyInfo]]
    events: Mapping[str, EventInfo]
    actions: tuple[ActionInfo, ...]
    enums: Mapping[str, tuple[str, ...]]
    tokens: Mapping[str, Mapping[str, TokenInfo]]
    modules: Mapping[str, ModuleInfo]
    extra: Mapping[str, Any] = field(default_factory=dict)
    #: Schema 1.2: the popups the modules open by default; empty for a 1.1 schema.
    popups: Mapping[str, PopupInfo] = field(default_factory=dict)
    #: Schema 1.2: how those popups reach the monitors, in words (empty for 1.1).
    popup_note: str = ""

    @property
    def version_text(self) -> str:
        return f"{self.version[0]}.{self.version[1]}"

    @classmethod
    def from_data(cls, data: Any) -> Schema:
        """Read a decoded schema. Raises `UnsupportedSchemaVersion` for a major version this application does not know, `SchemaError` for a missing or misshapen part."""
        data = _mapping(data, "document")
        if "schema_version" not in data:
            raise SchemaError("The shell's answer has no schema_version, so it is not a schema.")
        version = parse_version(data["schema_version"])
        if version[0] != SUPPORTED_MAJOR:
            raise UnsupportedSchemaVersion(str(data["schema_version"]))
        missing = [name for name in _KNOWN_TOP[2:] if name not in data]
        if missing:
            raise SchemaError("The schema lacks " + ", ".join(missing) + ".")
        settings = {section: {k: KeyInfo.read(k, v) for k, v in _mapping(keys, f"settings {section}").items()}
                    for section, keys in _mapping(data["settings"], "settings").items()}
        tokens = {group: {k: TokenInfo.read(group, k, v) for k, v in _mapping(entries, f"tokens {group}").items()}
                  for group, entries in _mapping(data["tokens"], "tokens").items()}
        popup_table = data.get("popups")
        popup_table = _mapping(popup_table, "popups") if popup_table is not None else {}
        listed = popup_table.get("popups")
        return cls(
            popups={k: PopupInfo.read(k, v) for k, v in _mapping(listed, "popups list").items()} if listed is not None else {},
            popup_note=str(popup_table.get("monitors") or ""),
            version=version, shell_version=str(data.get("shell_version", "")),
            kinds={k: KindInfo(k, str(v.get("ui", "text")), str(v.get("note") or ""), _strings(v.get("model_kinds")),
                               {a: b for a, b in v.items() if a not in ("ui", "note", "model_kinds")})
                   for k, v in _mapping(data["kinds"], "kinds").items()},
            roots={k: BlockInfo.read(k, v) for k, v in _mapping(data["roots"], "roots").items()},
            blocks={k: BlockInfo.read(k, v) for k, v in _mapping(data["blocks"], "blocks").items()},
            settings=settings, events={k: EventInfo.read(k, v) for k, v in _mapping(data["events"], "events").items()},
            actions=tuple(ActionInfo.read(a) for a in _tuple(data["actions"])),
            enums={k: _strings(v) for k, v in _mapping(data["enums"], "enums").items()}, tokens=tokens,
            modules={k: ModuleInfo.read(k, v) for k, v in _mapping(data["modules"], "modules").items()},
            extra={k: v for k, v in data.items() if k not in _KNOWN_TOP and k not in _OPTIONAL_TOP})

    @classmethod
    def from_json(cls, text: str | bytes) -> Schema:
        try:
            data = json.loads(text)
        except ValueError as error:
            raise SchemaError(f"The shell's schema is not JSON: {error}") from None
        return cls.from_data(data)

    # -- lookups -----------------------------------------------------------------------------------------------------------------

    def kind(self, name: str) -> KindInfo:
        """The kind called `name`. A kind a higher minor version adds, which this table does not have, reads as the generic text kind."""
        found = self.kinds.get(name)
        return found if found is not None else KindInfo(name, "text", "", ())

    def block(self, name: str) -> BlockInfo | None:
        """The root block or block with the head word `name`, or `None`."""
        return self.roots.get(name) or self.blocks.get(name) or next((b for b in (*self.roots.values(), *self.blocks.values()) if name in b.heads), None)

    def is_root(self, name: str) -> bool:
        return name in self.roots

    def token_groups(self) -> tuple[str, ...]:
        return tuple(self.tokens)

    def tokens_for(self, key: KeyInfo) -> list[TokenInfo]:
        """The tokens a key accepts: those of the groups its `tokens` names, the ones its `preferred_tokens` name first. A preferred entry is a group (`color`), one token (`elevation.max`) or a pattern
        over the dotted name (`type.*.font_weight`)."""
        found = [t for group in key.tokens for t in self.tokens.get(group, {}).values()]
        none = len(key.preferred_tokens)

        def rank(token: TokenInfo) -> int:
            dotted = f"{token.group}.{token.name}"
            return next((i for i, p in enumerate(key.preferred_tokens) if p == token.group or fnmatchcase(dotted, p)), none)

        return sorted(found, key=rank)

    def preferred_refs(self, key: KeyInfo) -> list[str]:
        """The refs of the tokens `key` prefers, in the order `tokens_for` lists them (the ones the token button puts first)."""
        none = len(key.preferred_tokens)
        found = []
        for token in self.tokens_for(key):
            dotted = f"{token.group}.{token.name}"
            if any(p == token.group or fnmatchcase(dotted, p) for p in key.preferred_tokens):
                found.append(token.ref)
        return found if none else []

    def module_names(self) -> tuple[str, ...]:
        return tuple(self.modules)

    def walk_keys(self) -> Iterable[tuple[str, KeyInfo]]:
        """Every key of every root block, block, setting section and module param, as `(where, key)`: the walk a coverage test makes."""
        for table in (self.roots, self.blocks):
            for block in table.values():
                for key in block.all_keys().values():
                    yield block.name, key
        for section, keys in self.settings.items():
            for key in keys.values():
                yield section, key

    def walk_popups(self) -> Iterable[tuple[str, str, KeyInfo | None]]:
        """Every default a popup states, as `(popup, field, key)`: `key` is the `Popup` root block's key it sets (found without regard to case), or `None` when the root has none."""
        keys = {name.lower(): key for name, key in (self.roots["Popup"].all_keys().items() if "Popup" in self.roots else ())}
        for popup in self.popups.values():
            for name in popup.values:
                yield popup.name, name, keys.get(name.lower())


def load_schema(text: str | bytes) -> Schema:
    """`Schema.from_json`, under the name a caller reads."""
    return Schema.from_json(text)
