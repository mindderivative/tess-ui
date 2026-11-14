"""The selector of a stylesheet `Rule`: read it into its parts, write it back, and the rows of the builder.

A selector is the string of a rule's `Selector:` (Style Schema, "Stylesheet Selectors"): a block or module name (`Text`, `Clock`), a class (`.warning`), a unique name (`#clock_label`), then optionally
a part of a module (`Slider::track`) and a state (`:hovered`). The builder shows those as four rows (what the rule applies to, its target, a part, a state); each change writes the whole selector as one
`Selector:` edit. A selector that does not read in this grammar (a descendant, a state the shell does not know) is not offered to the builder: the form says so and shows the raw text with the union of style keys.

The grammar is the shell's own documentation's, not the schema's (the schema says `Selector` is a string); the six states are the ones its `Block Reference` names.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from tess_shell_config.form import Cell, PropertyStore, Row, Store
from tess_shell_config.model import DocumentModel, EditError
from tess_shell_config.schema import KeyInfo
from tess_shell_config.values import quote
from tess_shell_config.widgets import ChoiceWidget, Context, Refused, TextWidget

__all__ = ["STATES", "BASES", "Selector", "parse_selector", "SelectorStore", "selector_rows"]

#: The states a selector may end in.
STATES = ("hovered", "pressed", "disabled", "selected", "checked", "focused")
#: What a selector applies to: a block or module name, a class (`.`), a unique name (`#`).
BASES = ("Block or module", "A class", "A name")
_PREFIX = {"Block or module": "", "A class": ".", "A name": "#"}
_WORD = r"[A-Za-z_][A-Za-z0-9_]*"
_PATTERN = re.compile(rf"^(?P<prefix>[.#]?)(?P<target>{_WORD})(?:::(?P<part>{_WORD}))?(?::(?P<state>{_WORD}))?$")
GROUP = "Selector builder"


@dataclass(frozen=True)
class Selector:
    """A selector in its parts: what it applies to (`base`, one of `BASES`), the `target` word, an optional `part` and an optional `state`."""

    base: str
    target: str
    part: str = ""
    state: str = ""

    def text(self) -> str:
        return _PREFIX[self.base] + self.target + (f"::{self.part}" if self.part else "") + (f":{self.state}" if self.state else "")


def parse_selector(text: str) -> Selector | None:
    """The parts of a selector, or `None` when it is not in the grammar (a descendant, an unknown state, a part on a class or a name, which the shell does not build)."""
    found = _PATTERN.match(text.strip())
    if found is None:
        return None
    base = next(name for name, prefix in _PREFIX.items() if prefix == found["prefix"])
    state = found["state"] or ""
    if state and state not in STATES:
        return None
    if found["part"] and base != "Block or module":
        return None
    return Selector(base, found["target"], found["part"] or "", state)


@dataclass(frozen=True)
class SelectorStore(Store):
    """One part of the selector of the rule at `path`. A write changes that part and writes the whole `Selector:`; a removal of the target removes the property, of the part or the state only that."""

    path: tuple[int, ...]
    field: str
    key: str = "Selector"

    def _current(self, model: DocumentModel) -> Selector | None:
        document = model.document
        if document is None:
            return None
        value = PropertyStore(self.path, self.key).read(document).value
        return parse_selector(document.text[value.start:value.end].strip().strip('"')) if value is not None else None

    def write(self, model: DocumentModel, text: str) -> None:
        current = self._current(model)
        if current is None:
            if self.field != "target":
                raise EditError("Write the Target first: the selector has none yet.")
            current = Selector("Block or module", text)
        elif self.field == "base":
            current = Selector(text, current.target, current.part if text == "Block or module" else "", current.state)
        elif self.field == "target":
            current = Selector(current.base, text, current.part, current.state)
        elif self.field == "part":
            if current.base != "Block or module":
                raise EditError("A part goes with a module name (Slider::track): .class::part and #name::part are not built.")
            current = Selector(current.base, current.target, text, current.state)
        else:
            current = Selector(current.base, current.target, current.part, text)
        model.set_value(self.path, self.key, quote(current.text()))

    def remove(self, model: DocumentModel) -> None:
        current = self._current(model)
        if self.field in ("target", "base") or current is None:
            model.clear_value(self.path, self.key)
            return
        changed = Selector(current.base, current.target, "" if self.field == "part" else current.part, "" if self.field == "state" else current.state)
        model.set_value(self.path, self.key, quote(changed.text()))

    def read(self, document: Any) -> Any:  # the builder's cells are filled from the parsed selector, not through a store read
        raise NotImplementedError


class _PartWidget(TextWidget):
    """A text field for the target or part word: a bare word, no quotes."""

    def write(self, edit: Mapping[str, Any]) -> str | None:
        text = str(edit.get("text", "")).strip()
        if not text:
            return None
        if not re.fullmatch(_WORD, text):
            raise Refused(f"{self.key.name} is one word of letters, digits and _, starting with a letter; {text!r} is not.")
        return text


def _key(name: str, kind: str, doc: str, choices: tuple[str, ...] | None = None) -> KeyInfo:
    return KeyInfo(name, kind, doc, None, choices, None, False, False, True, GROUP, (), ())


def selector_rows(path: tuple[int, ...], selector: Selector | None, context: Context, errors: Mapping[str, str], drafts: Mapping[str, Mapping[str, Any]]) -> list[Row]:
    """The builder's four rows for the rule at `path`, filled from `selector` (`None`: the rule has no selector yet)."""
    specs = (
        ("base", _key("Applies to", "enum", "What the rule styles: a block or module name, a class set with Class:, or one unique Name:.", BASES), ChoiceWidget),
        ("target", _key("Target", "name", "The block or module name, the class or the name (without the . or #).", None), _PartWidget),
        ("part", _key("Part", "name", "A named part of a module (Module::part), set with Part: on a block of its layout. Only for a module name.", None), _PartWidget),
        ("state", _key("State", "enum", "The state the rule applies in.", tuple(STATES)), ChoiceWidget),
    )
    rows = []
    for field_name, key, factory in specs:
        widget = factory(key, context)
        value = getattr(selector, field_name, "") if selector is not None else ""
        cell_id = f"s:{field_name}|"
        cell = Cell(cell_id, widget, SelectorStore(path, field_name))
        cell.present = bool(value) and (field_name != "base" or selector is not None)
        cell.text = value
        if isinstance(widget, ChoiceWidget):
            cell.shown = {"choices": widget._options(), "current": value, "shown": value or "choose", "placeholder": ""}
        else:
            cell.shown = {"field": value, "placeholder": ""}
        cell.error = errors.get(cell_id, "")
        draft = drafts.get(cell_id)
        if draft is not None and "text" in draft:
            cell.shown = {**cell.shown, "field": str(draft["text"])}
        rows.append(Row(f"s:{field_name}", key.name, key.doc, [cell], GROUP, key, field_name == "target"))
    return rows
