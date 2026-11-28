"""The combo box's mind (`Combobox`, the control of the `Autocomplete` view; ux spec Autocomplete, tess-behavior SPEC 2.5d).

`ComboboxModel` is the behaviour, with no window: the options, the text in the field, the value, whether the list is open, which row is active and what each key and each leaving of the field does. The field keeps the
keyboard focus all the time (the active row is the *active descendant*, not a focused row), so everything is decided here from keys the field hears.

- Options are `{value, label}` and optionally `{hint, disabled, swatch, icon, font}` (the row templates: a colour swatch, an icon, or the label set in a font). Matching is by containing text, case-insensitively, and keeps the order of the options. The matched part of a label is given as `runs`.
- *Strict*: the value is always one of the options; text that is not one is only a query, and leaving the field puts the last value back. *Free*: the text may be the value; the list only suggests.
- Keys (the field's own Home, End and letters are the text's): Down opens the list (the selected row, or the first enabled row, active; with Alt it opens and makes no row active) and then moves to the next enabled row and stops
  at the last; Up opens with the last enabled row, then moves up, and from the first row makes none active; Page Down and Page Up move a page; Enter picks the active row (with none: Strict closes and puts the value back, Free takes the text
  as the value); Escape closes the list and keeps the text, and with the list already closed Strict puts the value back (`changed` says whether anything happened: a caller that can stop the key stops it only then); Tab (`leave`)
  picks an active row that an arrow key chose, else Strict picks an option whose label equals the text (case aside) or puts the value back, and Free keeps the text.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tess_ui.mind import Mind
from tess_ui.reactive import Signal

__all__ = ["ComboboxControl", "ComboboxModel"]


def _runs(label: str, start: int, length: int) -> list[Any]:
    """The label as the runs of a `Text`, the matched characters in weight 500 (emphasis is the weight, not the colour alone)."""
    if length <= 0:
        return [label]
    return [piece for piece in (label[:start], {"text": label[start:start + length], "weight": 500}, label[start + length:]) if piece != ""]


class ComboboxModel:
    """See the module's note."""

    def __init__(self, options: list[dict[str, Any]] | None = None, *, strict: bool = True, value: Any = "", page_rows: int = 8) -> None:
        self.options: list[dict[str, Any]] = []
        self.strict = strict
        self.page_rows = page_rows
        self.value: Any = value
        self.text = ""
        self.query = ""  # what the person typed since the last pick: empty shows every option
        self.open = False
        self.active = -1
        self.by_arrow = False  # the active row was chosen by an arrow key (Tab may pick it)
        self.results: list[dict[str, Any]] = []
        self.version = 0
        self.picked: dict[str, Any] | None = None
        self.set_options(options or [])
        self.text = self.label_of(value)

    # -- reading ---------------------------------------------------------------------------------------------------------------

    def label_of(self, value: Any) -> str:
        """The label of the option whose value is `value` (empty when there is none)."""
        return next((str(o["label"]) for o in self.options if o["value"] == value), "")

    def row_enabled(self, index: int) -> bool:
        """Whether row `index` of the results exists and can be picked."""
        return 0 <= index < len(self.results) and not self.results[index].get("disabled", False)

    def _enabled(self) -> list[int]:
        return [i for i in range(len(self.results)) if self.row_enabled(i)]

    # -- what changes the options and the text ----------------------------------------------------------------------------------

    def set_options(self, options: list[dict[str, Any]]) -> None:
        """The options are now these (a row without a `value` and a `label` is left out); the list is filtered again."""
        self.options = [dict(o) for o in options if isinstance(o, dict) and "value" in o and "label" in o]
        self._filter()

    def set_value(self, value: Any) -> None:
        """The view's own change of the value: the field shows its label."""
        self.value = value
        self.text, self.query = self.label_of(value), ""
        self._filter()

    def _filter(self) -> None:
        words = self.query.casefold()
        rows = []
        for option in self.options:
            label = str(option["label"])
            at = label.casefold().find(words) if words else 0
            if words and at < 0:
                continue
            rows.append({"value": option["value"], "label": label, "hint": str(option.get("hint", "")), "disabled": bool(option.get("disabled", False)),
                         "runs": _runs(label, at, len(words)) if words else [label], "selected": option["value"] == self.value,
                         "swatch": str(option.get("swatch", "")), "icon": str(option.get("icon", "")), "font": str(option.get("font", ""))})
        self.results = rows
        self.active, self.by_arrow = -1, False
        self.version += 1

    def type(self, text: str) -> None:
        """The person edited the text: the list narrows at once and opens, and no row is active."""
        if text == self.text:
            return
        self.text, self.query, self.open = text, text, True
        self._filter()

    # -- keys ------------------------------------------------------------------------------------------------------------------

    def key(self, name: str, *, alt: bool = False) -> bool:
        """A key the field heard. Returns whether the model used it (Home, End and the letters are the text's)."""
        name = name.casefold()
        enabled = self._enabled()
        if name == "arrow_down":
            if not self.open:
                self.open = True
                if not alt:
                    self._activate(next((i for i in enabled if self.results[i]["selected"]), enabled[0] if enabled else -1))
                return True
            self._activate(next((i for i in enabled if i > self.active), self.active))
            return True
        if name == "arrow_up":
            if not self.open:
                self.open = True
                self._activate(enabled[-1] if enabled else -1)
                return True
            before = [i for i in enabled if i < self.active]
            self.active, self.by_arrow = (before[-1] if before else -1), bool(before)
            return True
        if name in ("page_down", "page_up") and self.open:
            step = self.page_rows if name == "page_down" else -self.page_rows
            target = max(0, min(len(self.results) - 1, max(self.active, 0) + step)) if self.results else -1
            nearest = sorted(enabled, key=lambda i: (abs(i - target), i))
            if nearest:
                self._activate(nearest[0])
            return True
        if name == "enter":
            if self.active >= 0 and self.row_enabled(self.active):
                self.pick(self.active)
            elif self.strict:
                self.revert()
            else:
                self._commit_text()
            return True
        if name == "escape":
            return self.escape()
        return False

    def _activate(self, index: int) -> None:
        self.active, self.by_arrow = index, index >= 0

    def escape(self) -> bool:
        """Escape: close the list and keep the text; closed already, Strict puts the value back. Returns whether anything changed."""
        if self.open:
            self.open, self.active, self.by_arrow = False, -1, False
            return True
        if self.strict and self.text != self.label_of(self.value):
            self.revert()
            return True
        return False

    def leave(self) -> None:
        """The field loses the focus (Tab): see the module's note."""
        if self.by_arrow and self.row_enabled(self.active):
            self.pick(self.active)
            return
        if self.strict:
            exact = next((o for o in self.options if str(o["label"]).casefold() == self.text.casefold() and not o.get("disabled")), None)
            if exact is not None and exact["value"] != self.value:
                self.picked = exact
                self.value = exact["value"]
            self.revert()
        else:
            self._commit_text()

    def revert(self) -> None:
        """Strict: the text goes back to the label of the value, the list closes."""
        self.text, self.query, self.open = self.label_of(self.value), "", False
        self._filter()

    def _commit_text(self) -> None:
        """Free: the text is the value."""
        self.open = False
        if self.text != self.value:
            self.value = self.text
            self.picked = {"value": self.text, "label": self.text}
        self.query = ""
        self._filter()

    def pick(self, index: int) -> bool:
        """Pick row `index` (a press on it, or Enter): the value is its value, the field shows its label, the list closes."""
        if not self.row_enabled(index):
            return False
        row = self.results[index]
        self.picked = row
        self.value, self.text, self.query, self.open = row["value"], row["label"], "", False
        self._filter()
        return True

    def reveal(self, offset: float, row_height: float) -> float:
        """The scroll offset that keeps the active row among `page_rows` rows."""
        if self.active < 0:
            return offset
        top = offset / row_height
        if self.active < top:
            return self.active * row_height
        if self.active + 1 > top + self.page_rows:
            return (self.active + 1 - self.page_rows) * row_height
        return offset


class ComboboxControl(Mind):
    """The control of the widget kind `Combobox` (made by the view builder; `values` are the node's properties).

    Two-way: `value`, `text` (the field's text: the view's field writes it as the person types), `expanded` (the popup is open), `scroll`. Read: `options`, `strict`, `rows`, `row_height`, `command`. Out: `entries` (the rows that match, each
    {value, label, hint, disabled, runs, selected, swatch, icon, font}), `active` (the active row's place, -1 none), `count`."""

    TWO_WAY = ("value", "text", "scroll", "expanded")
    READ = ("options", "strict", "rows", "row_height")

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Any = None, listen: Any = None) -> None:
        super().__init__(window, values, theme=theme, listen=listen)
        self.model = ComboboxModel(list(values.get("options") or []), strict=values.get("strict") is not False, value=values.get("value", ""))
        self.value = Signal(values.get("value", ""))
        self.text = Signal(self.model.text)
        self.expanded = Signal(False)
        self.scroll = Signal(0.0)
        self.entries = Signal(list(self.model.results))
        self.active = Signal(-1)
        self.count = Signal(len(self.model.results))
        self._row_height = float(values.get("row_height") or 32.0)
        self.start_soon()

    def _begin(self, values: dict[str, Any]) -> None:
        self._follow(values, lambda key: False)  # nothing the view has written yet is an edit: the field shows the label of its value
        self._sync()

    def _follow(self, values: dict[str, Any], edited: Callable[[str], bool]) -> bool:
        model, changed = self.model, False
        model.strict = values.get("strict") is not False
        model.page_rows = max(1, int(values.get("rows") or 8))
        self._row_height = float(values.get("row_height") or 32.0)
        options = list(values.get("options") or [])
        if options != model.options and [dict(o) for o in options if isinstance(o, dict)] != [{k: v for k, v in o.items() if k not in ("runs", "selected")} for o in model.options]:
            model.set_options(options)
            changed = True
        if edited("value") and values.get("value", "") != model.value:
            model.set_value(values.get("value", ""))
            changed = True
        if edited("text") and str(values.get("text") or "") != model.text:
            model.type(str(values.get("text") or ""))
            changed = True
        if edited("expanded") and bool(values.get("expanded")) != model.open:
            model.open = bool(values.get("expanded"))  # the popup closed itself: Escape or a press outside
            changed = True
        if edited("scroll") and float(values.get("scroll") or 0.0) != self.scroll.get():
            self.scroll.set(float(values.get("scroll") or 0.0))
        return changed

    def _run(self, word: str, rest: str) -> None:
        model = self.model
        if word == "key":
            parts = rest.split(" ")
            model.key(parts[0], alt="alt" in parts[1:])
        elif word == "click":
            model.pick(int(rest)) if rest.lstrip("-").isdigit() else None
        elif word == "leave":
            model.leave()
        elif word == "toggle":
            model.open = not model.open
        elif word == "open":
            model.open = True
        self.scroll.set(model.reveal(self.scroll.get(), self._row_height))
        if model.picked is not None:
            picked, model.picked = model.picked, None
            self.value.set(picked["value"])
            self._finish(picked["value"])

    def _sync(self) -> None:
        model = self.model
        self.entries.set(list(model.results))
        self.active.set(model.active)
        self.count.set(len(model.results))
        self.text.set(model.text)
        self.expanded.set(model.open)
        if self.value.get() != model.value:
            self.value.set(model.value)
