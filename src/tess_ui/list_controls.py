"""`ListModel`, the model and the control behind the list editor: a list of items of one kind that rows add to, change, remove and move.

`ListModel` has no window: it holds the items, each with an identity that stays with it when it is moved (so a view keeps its row), and does the edits. `ListModelControl` is `widget: ListModel` in
`ListEditor_View.yaml` (see `tess_ui.mind`), a control that draws nothing. The view builds a row for each of `rows` with the widget of the item kind and sends what a row does as a command:
`set <place> <text>` (the new value of the item, as text), `add`, `remove <place>`, `up <place>` and `down <place>`. Each command that changes the list writes the new list to `value` and
tells `on_input`.

The kinds are `text` (a string), `number` (an int when the number is whole and `step` is, else a float; kept between `least` and `most` when given), `bool`, `enum` (one of `choices`: strings, or
`{value, label}`) and `colour` (`'#rrggbb'` or `'#rrggbbaa'` text, as `tess_ui.colour` has it). An item of the list the view holds that does not fit its kind is shown as the kind's nearest value (a
number that is not one as 0, an enum that is not a choice as the first choice) and is left exactly as it was in the list until the person changes that row: the list is only rewritten where it is edited,
and a list the app sets is never normalised.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tess_ui import colour
from tess_ui.mind import Mind
from tess_ui.reactive import Signal

__all__ = ["KINDS", "ListModel", "ListModelControl", "choices_of"]

#: The kinds of item a list editor edits.
KINDS = ("text", "number", "bool", "enum", "colour")


def choices_of(raw: Any) -> list[tuple[Any, str]]:
    """The `(value, label)` pairs of `choices`: each a plain value (its label is its text) or a mapping with `value` and optionally `label`."""
    found: list[tuple[Any, str]] = []
    for choice in raw or []:
        if isinstance(choice, dict) and "value" in choice:
            found.append((choice["value"], str(choice.get("label", choice["value"]))))
        elif not isinstance(choice, dict):
            found.append((choice, str(choice)))
    return found


@dataclass(slots=True)
class _Item:
    uid: int
    raw: Any


class ListModel:
    """The items of one kind, and the edits. `least`, `most` and `step` bound a number; `choices` are an enum's; `min_items` and `max_items` (0 for none) bound the length."""

    def __init__(self, kind: str = "text", values: list[Any] | None = None, *, choices: Any = None, least: float | None = None, most: float | None = None,
                 step: float | None = None, min_items: int = 0, max_items: int = 0) -> None:
        if kind not in KINDS:
            raise ValueError(f"an item kind is one of {', '.join(KINDS)}, not {kind!r}")
        self.kind = kind
        self.choices = choices_of(choices)
        self.least, self.most, self.step = least, most, step
        self.min_items, self.max_items = max(0, int(min_items)), max(0, int(max_items))
        self._next = 0
        self.items: list[_Item] = []
        self.set_values(values or [])

    def set_values(self, values: list[Any]) -> None:
        """Takes `values` as the list (the app's): every item is a new one."""
        self.items = [self._new(v) for v in values]

    def _new(self, raw: Any) -> _Item:
        self._next += 1
        return _Item(self._next, raw)

    @property
    def values(self) -> list[Any]:
        """The list: each item as it was set or as the person made it."""
        return [item.raw for item in self.items]

    def shown(self, raw: Any) -> Any:
        """What a row shows for `raw`: the item as its kind has it, or the kind's nearest value."""
        if self.kind == "text":
            return "" if raw is None else str(raw)
        if self.kind == "number":
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                return 0.0
            return float(raw)
        if self.kind == "bool":
            return bool(raw)
        if self.kind == "enum":
            values = [v for v, _ in self.choices]
            return raw if raw in values else (values[0] if values else "")
        return raw.lower() if isinstance(raw, str) and colour.is_valid(raw) else "#000000"

    @property
    def rows(self) -> list[dict[str, Any]]:
        """For the view: each item as `{uid, value}`, the value as `shown` has it."""
        return [{"uid": f"i{item.uid}", "value": self.shown(item.raw)} for item in self.items]

    @property
    def can_add(self) -> bool:
        """Whether `add` would add: the list is below `max_items` (or has no bound)."""
        return not self.max_items or len(self.items) < self.max_items

    @property
    def can_remove(self) -> bool:
        """Whether `remove` would remove: the list is above `min_items`."""
        return len(self.items) > self.min_items

    def default(self) -> Any:
        """The item `add` makes: empty text, the least number (or 0), false, the first choice, black."""
        if self.kind == "text":
            return ""
        if self.kind == "number":
            return self._number(self.least if self.least is not None else 0)
        if self.kind == "bool":
            return False
        if self.kind == "enum":
            return self.choices[0][0] if self.choices else ""
        return "#000000"

    def _number(self, value: float) -> int | float:
        low = -float("inf") if self.least is None else self.least
        high = float("inf") if self.most is None else self.most
        value = max(low, min(high, value))
        whole = float(value).is_integer() and (self.step is None or float(self.step).is_integer())
        return int(value) if whole else float(value)

    def parse(self, text: str) -> Any:
        """The item `text` stands for (the text a row sends), or raises `ValueError`."""
        if self.kind == "text":
            return text
        if self.kind == "number":
            return self._number(float(text))
        if self.kind == "bool":
            if text.lower() not in ("true", "false"):
                raise ValueError(f"a bool is true or false, not {text!r}")
            return text.lower() == "true"
        if self.kind == "enum":
            for value, _ in self.choices:
                if str(value) == text:
                    return value
            raise ValueError(f"{text!r} is not one of the choices")
        if not colour.is_valid(text):
            raise ValueError(f"a colour is written #rrggbb or #rrggbbaa, not {text!r}")
        return text.lower()

    # -- the edits: each returns whether the list changed -------------------------------------------------------------------------

    def set(self, place: int, text: str) -> bool:
        """Changes item `place` to the item `text` stands for. A text that is not one for the kind changes nothing."""
        if not 0 <= place < len(self.items):
            return False
        try:
            value = self.parse(text)
        except ValueError:
            return False
        if value == self.items[place].raw and type(value) is type(self.items[place].raw):
            return False
        self.items[place].raw = value
        return True

    def add(self) -> bool:
        """Appends the default item of the kind; does nothing at `max_items`."""
        if not self.can_add:
            return False
        self.items.append(self._new(self.default()))
        return True

    def remove(self, place: int) -> bool:
        """Takes item `place` out; does nothing at `min_items` or for a place that is not there."""
        if not 0 <= place < len(self.items) or not self.can_remove:
            return False
        del self.items[place]
        return True

    def move(self, place: int, by: int) -> bool:
        """Moves item `place` by `by` places (kept inside the list); the item keeps its identity."""
        target = place + by
        if not (0 <= place < len(self.items) and 0 <= target < len(self.items)) or by == 0:
            return False
        self.items.insert(target, self.items.pop(place))
        return True


class ListModelControl(Mind):
    """See the module's note. Made by the view builder for `widget: ListModel`; `values` are the node's properties.

    Two-way: `value` (the list). Read: `item_kind`, `choices`, `least`, `most`, `step`, `min_items`, `max_items`, `command`. Outputs: `rows`, `options`, `count`, `can_add`, `can_remove`, `message`."""

    TWO_WAY = ("value",)
    READ = ("item_kind", "choices", "least", "most", "step", "min_items", "max_items")

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Any = None, listen: Any = None) -> None:
        super().__init__(window, values, theme=theme, listen=listen)
        self.model: ListModel | None = None
        self._settings: tuple[Any, ...] | None = None
        self.value = Signal(list(values.get("value") or []))
        self.rows = Signal([])
        self.options = Signal([])
        self.count = Signal(0)
        self.can_add = Signal(True)
        self.can_remove = Signal(True)
        self.message = Signal("")
        self.start_soon()

    def _make(self, values: dict[str, Any]) -> bool:
        """Builds the model when there is none or its settings changed (the list is kept); returns whether it did."""
        settings = (values.get("item_kind") or "text", repr(values.get("choices")), values.get("least"), values.get("most"), values.get("step"),
                    values.get("min_items"), values.get("max_items"))
        if self.model is not None and settings == self._settings:
            return False
        self._settings = settings
        kind = str(values.get("item_kind") or "text")
        if kind not in KINDS:
            self.message.set(f"item_kind is one of {', '.join(KINDS)}, not {kind!r}")
            kind = "text"
        else:
            self.message.set("")
        held = list(self.model.values) if self.model is not None else _as_list(values.get("value"))
        self.model = ListModel(kind, held, choices=values.get("choices"), least=_number(values.get("least")), most=_number(values.get("most")),
                               step=_number(values.get("step")), min_items=int(values.get("min_items") or 0), max_items=int(values.get("max_items") or 0))
        return True

    def _begin(self, values: dict[str, Any]) -> None:
        self._make(values)
        assert self.model is not None
        self.model.set_values(_as_list(values.get("value")))
        self.value.set(self.model.values)
        self._sync()

    def _follow(self, values: dict[str, Any], edited: Callable[[str], bool]) -> bool:
        changed = self._make(values)
        model = self.model
        assert model is not None
        held = _as_list(values.get("value"))
        if edited("value") and held != model.values:
            model.set_values(held)  # the app's list: new rows
            self.value.set(held)
            changed = True
        return changed

    def _run(self, word: str, rest: str) -> None:
        model = self.model
        if model is None:
            return
        place, _, text = rest.partition(" ")
        number = int(place) if place.lstrip("-").isdigit() else -1
        changed = False
        if word == "set":
            changed = model.set(number, text)
        elif word == "add":
            changed = model.add()
        elif word == "remove":
            changed = model.remove(number)
            if not changed and number >= 0 and not model.can_remove:
                self.message.set(f"The list needs at least {model.min_items} item{'s' if model.min_items != 1 else ''}.")
        elif word == "up":
            changed = model.move(number, -1)
        elif word == "down":
            changed = model.move(number, 1)
        if changed:
            self.message.set("")
            self.value.set(model.values)
            self._finish(model.values)

    def _sync(self) -> None:
        model = self.model
        if model is None:
            return
        rows = model.rows
        if rows != self.rows.get():
            self.rows.set(rows)
        options = [{"value": value, "label": label} for value, label in model.choices]
        if options != self.options.get():
            self.options.set(options)
        self.count.set(len(model.items))
        self.can_add.set(model.can_add)
        self.can_remove.set(model.can_remove)


def _as_list(raw: Any) -> list[Any]:
    return list(raw) if isinstance(raw, (list, tuple)) else []


def _number(raw: Any) -> float | None:
    return None if raw is None or isinstance(raw, bool) or not isinstance(raw, (int, float)) else float(raw)
