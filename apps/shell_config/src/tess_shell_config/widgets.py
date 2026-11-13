"""The widget registry: which widget edits a key of which schema kind, and how it reads and writes TDL.

A `Widget` is made for one key (`factory(key, context)`). It does three things and knows no key by name:

- `empty()`: what the cell shows while the key is absent (the schema's default, as TDL text, is the placeholder);
- `read(value, text)`: what the cell shows for a value that is in the file, or `None` when this widget cannot show it (a call, a list it does not understand, a token reference): the form then shows
  the value as TDL text and never rewrites it unless the person edits it;
- `write(edit)`: the TDL text of the value the person made, `None` to remove the property, or `Refused` (with the message to show) when the value is not allowed and nothing is written.

`ui` is the cell shape the window's view draws (`switch`, `choice`, `field`, `length`, `sides`, `colour`). The registry maps a schema kind to a widget factory; a kind with no entry (a kind a higher schema
minor version adds) and a kind with no widget yet get the generic TDL text field, and the form reports which keys did (`Widget.reason`). A widget of another branch (the icon picker, the font list, the key-chord recorder, the list
editor) plugs in with one line: `registry.register("icon", IconPickerWidget)`, plus the `ui` branch its cell needs in `Views/Main_View.yaml`.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

from tess_dl import List, Number, Percent, String, Value, Word

from tess_shell_config.schema import KeyInfo, Schema
from tess_shell_config.values import colour_text, format_number, is_reference, normal_colour, parse_number, quote

__all__ = ["Refused", "Context", "Widget", "WidgetFactory", "WidgetRegistry", "TdlWidget", "SwitchWidget", "ChoiceWidget", "NumberWidget", "LengthWidget", "SidesWidget", "ColourWidget",
           "TextWidget", "PathWidget", "fallback", "default_registry"]


class Refused(Exception):
    """A value the key does not allow; `str(error)` says why and what is allowed. Nothing is written."""


@dataclass(frozen=True)
class Context:
    """What a widget may need beyond its key: the schema (enums, tokens) and the folder of the open file (a path widget's start and relative paths)."""

    schema: Schema
    file_dir: Path | None = None
    folder: Path | None = None


type WidgetFactory = Callable[[KeyInfo, Context], "Widget"]


def _label(key: KeyInfo) -> str:
    return key.name.replace("_", " ")


class Widget:
    """The base: a generic TDL text field. `reason` is set on a widget the registry used because the kind has no widget of its own."""

    ui = "field"
    reason: str | None = None

    def __init__(self, key: KeyInfo, context: Context) -> None:
        self.key = key
        self.context = context

    @property
    def default(self) -> str:
        """The schema's default, as TDL text, shown as the placeholder ('' when the schema has none)."""
        return self.key.default or ""

    def empty(self) -> dict[str, Any]:
        """The cell's own properties for an absent key."""
        return {"field": "", "placeholder": self.default}

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        """The cell's own properties for the value `value` whose TDL text is `text`; `None` when this widget cannot show it."""
        return {"field": text, "placeholder": self.default}

    def write(self, edit: Mapping[str, Any]) -> str | None:
        """The TDL text of the edit (`edit["text"]` for a field); `None` removes the property. Raises `Refused`."""
        text = str(edit.get("text", "")).strip()
        return text or None

    def sample_edit(self) -> dict[str, Any]:
        """An edit this widget writes without refusing it, for a test that walks the schema: the schema's default as text when it is one value, else an empty string."""
        default = self.default
        return {"text": default if default and "{" not in default and "\n" not in default else '""'}


class TdlWidget(Widget):
    """The generic field: the value as TDL text, written as typed (`tess_dl` refuses text that is not one value)."""

    def __init__(self, key: KeyInfo, context: Context, reason: str | None = None) -> None:
        super().__init__(key, context)
        self.reason = reason


def fallback(reason: str) -> WidgetFactory:
    """A factory for a kind that has no widget of its own: the generic TDL field, with the reason the form reports."""
    return lambda key, context: TdlWidget(key, context, reason)


# -- switch ------------------------------------------------------------------------------------------------------------------------

class SwitchWidget(Widget):
    ui = "switch"

    def empty(self) -> dict[str, Any]:
        return {"checked": self.default.strip().lower() == "true", "placeholder": self.default}

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        if isinstance(value, Word) and value.text in ("true", "false"):
            return {"checked": value.text == "true", "placeholder": self.default}
        return None

    def write(self, edit: Mapping[str, Any]) -> str | None:
        return "true" if edit.get("checked") else "false"

    def sample_edit(self) -> dict[str, Any]:
        return {"checked": True}


# -- choice ------------------------------------------------------------------------------------------------------------------------

class ChoiceWidget(Widget):
    ui = "choice"

    @property
    def choices(self) -> tuple[str, ...]:
        found = [str(c) for c in self.key.choices] if self.key.choices else []
        if not found and self.key.enum:
            found = list(self.context.schema.enums.get(self.key.enum, ()))
        return tuple(found)

    def _options(self) -> list[dict[str, str]]:
        docs = self.key.extra.get("choice_docs") or {}
        return [{"value": c, "label": c, "doc": str(docs.get(c, ""))} for c in self.choices]

    def empty(self) -> dict[str, Any]:
        return {"choices": self._options(), "current": "", "shown": self.default or "choose", "placeholder": self.default}

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        if isinstance(value, Word) and value.text in self.choices:
            return {"choices": self._options(), "current": value.text, "shown": value.text, "placeholder": self.default}
        return None

    def write(self, edit: Mapping[str, Any]) -> str | None:
        chosen = str(edit.get("value", ""))
        if chosen not in self.choices:
            raise Refused(f"{_label(self.key)} takes one of: {', '.join(self.choices)}.")
        return chosen

    def sample_edit(self) -> dict[str, Any]:
        return {"value": self.choices[0] if self.choices else ""}


# -- numbers -----------------------------------------------------------------------------------------------------------------------

class NumberWidget(Widget):
    """number, whole, duration and percent: a number field with the schema's minimum, maximum, step and unit; a value outside them is refused with the range."""

    def __init__(self, key: KeyInfo, context: Context) -> None:
        super().__init__(key, context)
        self.whole = key.kind == "whole"
        self.percent = key.kind == "percent"
        self.suffix = "%" if self.percent else str(key.unit or "")
        self.exclusive = bool(key.extra.get("min_exclusive"))

    @property
    def range_text(self) -> str:
        low, high = self.key.minimum, self.key.maximum
        unit = f" {self.suffix}" if self.suffix else ""
        if low is not None and high is not None:
            return f"from {format_number(Decimal(str(low)))} to {format_number(Decimal(str(high)))}{unit}"
        if low is not None:
            return (f"more than {format_number(Decimal(str(low)))}" if self.exclusive else f"at least {format_number(Decimal(str(low)))}") + unit
        if high is not None:
            return f"at most {format_number(Decimal(str(high)))}{unit}"
        return ""

    def _hint(self) -> str:
        return ("a whole number " if self.whole else "") + self.range_text

    def empty(self) -> dict[str, Any]:
        return {"field": "", "placeholder": self.default, "suffix": self.suffix, "hint": self._hint(), "stepping": True}

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        if isinstance(value, Number) or (isinstance(value, Percent) and self.percent):
            shown = text[:-1] if isinstance(value, Percent) else text
            return {"field": shown, "placeholder": self.default, "suffix": self.suffix, "hint": self._hint(), "stepping": True}
        return None

    def check(self, number: Decimal) -> None:
        name = _label(self.key)
        if self.whole and number != number.to_integral_value():
            raise Refused(f"{name} takes a whole number" + (f", {self.range_text}" if self.range_text else "") + ".")
        low, high = self.key.minimum, self.key.maximum
        below = low is not None and (number <= Decimal(str(low)) if self.exclusive else number < Decimal(str(low)))
        if below or (high is not None and number > Decimal(str(high))):
            raise Refused(f"{name} must be {self.range_text}.")

    def write(self, edit: Mapping[str, Any]) -> str | None:
        text = str(edit.get("text", "")).strip()
        if not text:
            return None
        if self.key.tokens and is_reference(text):
            return text
        if self.percent and text.endswith("%"):
            text = text[:-1].strip()
        number = parse_number(text)
        if number is None:
            raise Refused(f"{_label(self.key)} takes a number" + (f", {self.range_text}" if self.range_text else "") + f"; {text!r} is not one.")
        self.check(number)
        return format_number(number) + ("%" if self.percent else "")

    def step(self, text: str, direction: int) -> str | None:
        """The text one step up (`direction` 1) or down (-1) from `text` (the default when the field is empty), kept inside the range; `None` when there is nothing to step from."""
        step = Decimal(str(self.key.step)) if self.key.step else Decimal(1)
        number = parse_number(text) if text.strip() else parse_number(self.default.rstrip("%"))
        if number is None:
            number = Decimal(str(self.key.minimum)) if self.key.minimum is not None else Decimal(0)
            direction = 0
        moved = number + step * direction
        low, high = self.key.minimum, self.key.maximum
        if low is not None:
            moved = max(moved, Decimal(str(low)) + (step if self.exclusive and moved <= Decimal(str(low)) else 0))
        if high is not None:
            moved = min(moved, Decimal(str(high)))
        return format_number(moved)

    def sample_edit(self) -> dict[str, Any]:
        low, step = self.key.minimum, Decimal(str(self.key.step)) if self.key.step else Decimal(1)
        number = (Decimal(str(low)) + (step if self.exclusive else 0)) if low is not None else Decimal(1)
        if self.key.maximum is not None:
            number = min(number, Decimal(str(self.key.maximum)))
        return {"text": format_number(number)}


class LengthWidget(Widget):
    """A number and a unit: pixels (a whole number), a percentage, or one of the words the key allows (`AUTO`, `EXPAND`)."""

    ui = "length"

    def __init__(self, key: KeyInfo, context: Context) -> None:
        super().__init__(key, context)
        self.units = key.units or ("px", "%")
        self.words = tuple(u for u in self.units if u not in ("px", "%"))
        self.negative = bool(key.extra.get("negative"))

    def _units(self) -> list[dict[str, str]]:
        return [{"value": u, "label": u} for u in self.units]

    def _props(self, number: str, unit: str) -> dict[str, Any]:
        return {"field": number, "unit": unit, "units": self._units(), "number_enabled": unit in ("px", "%"), "placeholder": self.default,
                "hint": "a whole number of pixels, or a percentage" + (f", or {' or '.join(self.words)}" if self.words else "")}

    def empty(self) -> dict[str, Any]:
        default = self.default
        unit = default if default in self.words else "%" if default.endswith("%") else "px"
        return self._props("", unit)

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        if isinstance(value, Percent):
            return self._props(text[:-1], "%")
        if isinstance(value, Number):
            return self._props(text, "px")
        if isinstance(value, Word) and value.text in self.words:
            return self._props("", value.text)
        return None

    def write(self, edit: Mapping[str, Any]) -> str | None:
        unit = str(edit.get("unit") or "px")
        text = str(edit.get("text", "")).strip()
        name = _label(self.key)
        if unit in self.words:
            return unit
        if not text:
            return None
        if self.key.tokens and is_reference(text):
            return text
        number = parse_number(text)
        if number is None:
            raise Refused(f"{name} takes a number of {'pixels' if unit == 'px' else 'percent'}; {text!r} is not a number.")
        if unit == "px" and number != number.to_integral_value():
            raise Refused(f"{name} in pixels takes a whole number.")
        if number < 0 and not self.negative:
            raise Refused(f"{name} cannot be negative.")
        return format_number(number) + ("%" if unit == "%" else "")

    def sample_edit(self) -> dict[str, Any]:
        return {"text": "10", "unit": "px"}


class SidesWidget(Widget):
    """One number for all four sides, or four in the schema's order (left, top, right, bottom; a corner key lists its own corners)."""

    ui = "sides"

    def __init__(self, key: KeyInfo, context: Context) -> None:
        super().__init__(key, context)
        arity = key.extra.get("arity") or (1, 4)
        self.arity = tuple(int(a) for a in arity)
        self.order = tuple(str(o).replace("_", " ") for o in (key.extra.get("order") or ("1", "2", "3", "4")))
        self.negative = bool(key.extra.get("negative"))
        self.auto = bool(key.extra.get("auto"))

    @property
    def can_link(self) -> bool:
        return 1 in self.arity and 4 in self.arity

    def _props(self, fields: list[str], linked: bool) -> dict[str, Any]:
        return {"fields": fields, "linked": linked, "can_link": self.can_link, "labels": list(self.order), "placeholder": self.default, "unit": str(self.key.extra.get("unit") or "")}

    def empty(self) -> dict[str, Any]:
        linked = 1 in self.arity
        return self._props([""] if linked else ["", "", "", ""], linked)

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        if isinstance(value, Number) and 1 in self.arity:
            return self._props([text], True)
        if isinstance(value, List) and len(value.items) == 4 and 4 in self.arity and all(isinstance(i, Number) or (isinstance(i, Word) and self.auto and i.text == "AUTO") for i in value.items):
            return self._props([i.text for i in value.items], False)
        return None

    def _side(self, text: str, position: int) -> str:
        name = self.order[position] if position < len(self.order) else str(position + 1)
        text = text.strip() or "0"
        if self.auto and text == "AUTO":
            return text
        number = parse_number(text)
        if number is None:
            raise Refused(f"{self.key.name.replace('_', ' ')}: the {name} side takes a number; {text!r} is not one.")
        if number < 0 and not self.negative:
            raise Refused(f"{self.key.name.replace('_', ' ')}: the {name} side cannot be negative.")
        return format_number(number)

    def write(self, edit: Mapping[str, Any]) -> str | None:
        fields = [str(f) for f in (edit.get("fields") or [])]
        linked = bool(edit.get("linked")) and 1 in self.arity or 4 not in self.arity
        if not any(f.strip() for f in fields):
            return None
        if linked:
            return self._side(fields[0], 0)
        fields = (fields + [""] * 4)[:4]
        return "[" + ", ".join(self._side(f, i) for i, f in enumerate(fields)) + "]"

    def sample_edit(self) -> dict[str, Any]:
        return {"fields": ["4"], "linked": True}


# -- colour ------------------------------------------------------------------------------------------------------------------------

class ColourWidget(Widget):
    """The shipped ColourPicker, with alpha when the key allows it."""

    ui = "colour"

    def _props(self, colour: str) -> dict[str, Any]:
        return {"colour": colour, "alpha": bool(self.key.extra.get("alpha")), "placeholder": self.default}

    def empty(self) -> dict[str, Any]:
        default = self.default.strip()
        shown = normal_colour(default[1:-1]) if len(default) > 1 and default[0] == default[-1] == '"' else None
        return self._props(shown or "#808080")

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        if isinstance(value, String):
            shown = normal_colour(value.value)
            if shown is not None and (len(shown) == 7 or self.key.extra.get("alpha")):
                return self._props(shown)
        return None

    def write(self, edit: Mapping[str, Any]) -> str | None:
        picked = str(edit.get("value", "")).strip()
        shown = normal_colour(picked)
        if shown is None:
            raise Refused(f"{_label(self.key)} takes a colour such as #4682B4; {picked!r} is not one.")
        if len(shown) == 9 and not self.key.extra.get("alpha"):
            raise Refused(f"{_label(self.key)} takes no alpha: choose an opaque colour.")
        return colour_text(shown)

    def sample_edit(self) -> dict[str, Any]:
        return {"value": "#336699"}


# -- text and paths ----------------------------------------------------------------------------------------------------------------

_BARE = ("name", "name_ref")


class TextWidget(Widget):
    """string, text, name, name_ref and the kinds that read as text: a text field; a `pattern` in the schema is checked before anything is written."""

    def empty(self) -> dict[str, Any]:
        return {"field": "", "placeholder": self.default}

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        if isinstance(value, String):
            return {"field": value.value, "placeholder": self.default}
        if isinstance(value, (Word, Number, Percent)) and not (isinstance(value, Word) and value.text.startswith("$")):
            return {"field": text, "placeholder": self.default}
        return None

    def _check_pattern(self, text: str) -> None:
        pattern = self.key.extra.get("pattern")
        if pattern and not re.fullmatch(str(pattern), text):
            raise Refused(f"{_label(self.key)} must match {pattern}; {text!r} does not.")

    def write(self, edit: Mapping[str, Any]) -> str | None:
        text = str(edit.get("text", ""))
        if not text.strip():
            return None
        if self.key.tokens and is_reference(text):
            return text.strip()
        if self.key.kind in _BARE:
            text = text.strip()
            self._check_pattern(text)
            return text
        self._check_pattern(text)
        if self.key.kind in ("text_or_number", "monitor_index"):
            if parse_number(text) is not None:
                low = self.key.minimum
                if low is not None and parse_number(text) < Decimal(str(low)):  # type: ignore[operator]
                    raise Refused(f"{_label(self.key)} must be at least {low}.")
                return text.strip()
            if self.key.kind == "monitor_index":
                word = self.key.extra.get("word")
                if text.strip() != word:
                    raise Refused(f"{_label(self.key)} takes a whole number or the word {word}.")
                return text.strip()
        return quote(text)

    def sample_edit(self) -> dict[str, Any]:
        if self.key.kind in _BARE:
            return {"text": "Sample_Name"}
        if self.key.kind == "monitor_index":
            return {"text": "0"}
        return {"text": "sample"}


class PathWidget(TextWidget):
    """A text field with a Browse button that opens the shipped FileDialog in the key's mode and filters."""

    def empty(self) -> dict[str, Any]:
        return {**super().empty(), **self._dialog()}

    def read(self, value: Value, text: str) -> dict[str, Any] | None:
        shown = super().read(value, text)
        return None if shown is None else {**shown, **self._dialog()}

    def _dialog(self) -> dict[str, Any]:
        filters = self.key.extra.get("filters") or []
        return {"browse": True, "mode": str(self.key.extra.get("mode") or "open"), "filters": [{"label": " ".join(filters), "patterns": list(filters)}] if filters else []}

    def from_dialog(self, chosen: str) -> str:
        """The path the dialog gave, as the text a field commits: relative to the open file's folder when it lies under it (a path in a shell file is relative to that file), unless the key is absolute."""
        if self.key.extra.get("absolute") or self.context.file_dir is None:
            return chosen
        try:
            return Path(chosen).relative_to(self.context.file_dir).as_posix()
        except ValueError:
            return chosen

    def sample_edit(self) -> dict[str, Any]:
        return {"text": "sample.file"}


# -- the registry ------------------------------------------------------------------------------------------------------------------

@dataclass
class WidgetRegistry:
    """Schema kind -> widget factory. `create` never fails: a kind with no entry gets the generic TDL field and a reason."""

    factories: dict[str, WidgetFactory] = field(default_factory=dict)

    def register(self, kind: str, factory: WidgetFactory) -> None:
        """One line to plug a widget in: `registry.register("icon", IconPickerWidget)`."""
        self.factories[kind] = factory

    def create(self, key: KeyInfo, context: Context) -> Widget:
        if key.kind is None or key.kind == "":
            return TdlWidget(key, context, "the schema gives this key no kind (a key that is not built)")
        factory = self.factories.get(key.kind)
        if factory is None:
            return TdlWidget(key, context, f"the kind {key.kind!r} is not one this application knows (a newer schema minor version); shown with the generic TDL field")
        return factory(key, context)


def default_registry() -> WidgetRegistry:
    """The kinds of schema 1.1 and the widgets they get."""
    registry = WidgetRegistry()
    for kind in ("bool", "enabled"):
        registry.register(kind, SwitchWidget)
    for kind in ("enum", "input_region"):
        registry.register(kind, ChoiceWidget)
    for kind in ("number", "whole", "percent", "duration"):
        registry.register(kind, NumberWidget)
    registry.register("length", LengthWidget)
    for kind in ("sides", "radius"):
        registry.register(kind, SidesWidget)
    registry.register("color", ColourWidget)
    for kind in ("string", "text", "name", "name_ref", "text_or_number", "monitor_index", "token_ref"):
        registry.register(kind, TextWidget)
    registry.register("path", PathWidget)
    composite = "a composite value (a block or a token reference): edited as TDL text"
    for kind in ("shadows", "block", "tooltip"):
        registry.register(kind, fallback(composite))
    pending = {"icon": "icon picker (branch feat/icon-picker)", "font": "font list (branch feat/font-list)", "key_chord": "key-chord recorder (branch feat/key-chord)", "list": "list editor (branch feat/list-editor)"}
    for kind, widget in pending.items():
        registry.register(kind, fallback(f"the {widget} is not merged yet: edited as TDL text"))
    registry.register("expression", fallback("an expression is TDL text"))
    return registry
