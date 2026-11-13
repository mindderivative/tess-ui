"""`TokenList`, the model and the control behind the token button: a list of theme tokens given as data, searchable, with a cursor.

`TokenList` has no window: it keeps the tokens, the search and the cursor, and answers keys. `TokenListControl` is `widget: TokenList` in `TokenButton_View.yaml`, a control that draws nothing (see
`tess_ui.mind`). The tokens are data the app hands over, each a mapping `{name, ref, kind, value, doc}`: `name` is what a person looks for (`color.primary`), `ref` is the text a pick writes
(`$color.primary`; `$` and the name when it is left out), `kind` says what the value is (`colour` or `color` for a colour, anything else for text), `value` is the token's value and `doc` a line about
it. `groups` is the same tokens in named sets, `[{name, tokens}]`, which come after the plain ones and give each token a `group`; `preferred` names (or refs) are listed first, in that order.
A token with no name, or with the `ref` of an earlier one, is left out.

The control tells the view: `entries` (the rows that match the search: `{ref, name, kind, value, shown, doc, group, detail, swatch, label}`, where `swatch` is a colour token's value as `'#rrggbb'` or
`'#rrggbbaa'` text when it is one, and empty for any other token, whose `shown` text the row then shows), `cursor_ref`, `count` and `current` (the row of `value`, for the button).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tess_ui import colour
from tess_ui.mind import Mind
from tess_ui.reactive import Signal

__all__ = ["TokenList", "TokenListControl", "rows_of"]


def _text(raw: Any) -> str:
    return "" if raw is None else str(raw)


def _row(token: Any, group: str) -> dict[str, Any] | None:
    """One token as a row, or `None` when it has no name."""
    if not isinstance(token, dict):
        return None
    name = _text(token.get("name")).strip()
    if not name:
        return None
    ref = _text(token.get("ref")).strip() or "$" + name
    kind = _text(token.get("kind")).strip()
    value = token.get("value")
    shown = _text(value)
    swatch = ""
    if kind.casefold() in ("colour", "color") and isinstance(value, str) and colour.is_valid(value):
        swatch = value.lower()
    doc = _text(token.get("doc")).strip()
    detail = f"{group} · {doc}" if group and doc else (group or doc)
    return {"ref": ref, "name": name, "kind": kind, "value": value, "shown": shown, "doc": doc, "group": group, "detail": detail, "swatch": swatch,
            "label": f"{name}: {shown}" if shown else name}


def rows_of(tokens: Any = None, groups: Any = None, preferred: Any = None) -> list[dict[str, Any]]:
    """The rows for `tokens` and `groups` (see the module's note): the preferred first, in the order of `preferred`, then the rest in the order given."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()

    def take(token: Any, group: str) -> None:
        row = _row(token, group)
        if row is not None and row["ref"] not in seen:
            seen.add(row["ref"])
            found.append(row)

    for token in tokens if isinstance(tokens, (list, tuple)) else []:
        take(token, "")
    for group in groups if isinstance(groups, (list, tuple)) else []:
        if isinstance(group, dict):
            title = _text(group.get("name") or group.get("title") or group.get("group")).strip()
            members = group.get("tokens")
            for token in members if isinstance(members, (list, tuple)) else []:
                take(token, title)
    wanted = [_text(p).strip() for p in (preferred if isinstance(preferred, (list, tuple)) else [])]

    def rank(row: dict[str, Any]) -> int:
        for place, name in enumerate(wanted):
            if name in (row["name"], row["ref"]):
                return place
        return len(wanted)

    return sorted(found, key=rank)  # stable: the order given is kept inside the preferred ones and inside the rest


class TokenList:
    """The tokens, a search and a cursor. `page_rows` shapes Page Up and Page Down."""

    def __init__(self, tokens: Any = None, groups: Any = None, preferred: Any = None, page_rows: int = 7) -> None:
        self.rows = rows_of(tokens, groups, preferred)
        self.page_rows = max(1, int(page_rows))
        self.query = ""
        self.cursor = -1
        self.results: list[dict[str, Any]] = []
        self.version = 0  # counts the times `results` was made again
        self.set_query("")

    def set_query(self, query: str) -> None:
        """Keeps the tokens that have every word of `query` in their name, ref, group or doc (without regard to case), the ones whose name starts with the first word first; the cursor goes to the first."""
        self.query = query
        self.version += 1
        words = query.casefold().split()
        if not words:
            self.results = list(self.rows)
        else:
            found = [r for r in self.rows if all(w in f"{r['name']} {r['ref']} {r['group']} {r['doc']}".casefold() for w in words)]
            self.results = sorted(found, key=lambda r: not r["name"].casefold().startswith(words[0]))  # stable: preferred first, then the order given, inside each group
        self.cursor = 0 if self.results else -1

    def row_of(self, ref: str) -> dict[str, Any] | None:
        """The token with the ref `ref`, whether or not the search keeps it."""
        for row in self.rows:
            if row["ref"] == ref:
                return row
        return None

    def index_of(self, ref: str) -> int:
        """The place of `ref` in the results, or -1."""
        for place, row in enumerate(self.results):
            if row["ref"] == ref:
                return place
        return -1

    def move(self, to: int) -> None:
        """Puts the cursor on `to`, kept inside the results."""
        if self.results:
            self.cursor = max(0, min(len(self.results) - 1, to))

    def press(self, key: str, *, in_field: bool = False) -> str | None:
        """A key. Returns `"pick"` when it chose the token under the cursor. In the list Up and Down move by one, Page Up and Page Down by `page_rows`, Home and End go to the ends, and Enter
        and Space pick. In the search field only Up, Down, Page Up and Page Down act (the others are the text's) and Enter picks."""
        if not self.results:
            return None
        if self.cursor < 0:
            self.cursor = 0
            return None
        moves = {"arrow_up": self.cursor - 1, "arrow_down": self.cursor + 1, "page_up": self.cursor - self.page_rows, "page_down": self.cursor + self.page_rows}
        if not in_field:
            moves.update({"home": 0, "end": len(self.results) - 1})
        if key in moves:
            self.move(moves[key])
            return None
        if key.casefold() == "enter" or (key in (" ", "space") and not in_field):
            return "pick"
        return None

    def click(self, index: int) -> str | None:
        """A press on row `index` (-1 is none): it is picked."""
        if 0 <= index < len(self.results):
            self.cursor = index
            return "pick"
        return None

    @property
    def picked(self) -> dict[str, Any] | None:
        """The token under the cursor."""
        return self.results[self.cursor] if 0 <= self.cursor < len(self.results) else None

    def reveal(self, offset: float, row_height: float, rows: int | None = None) -> float:
        """The scroll offset that keeps the cursor's row in a window of `rows` rows (`page_rows` when not given), as near to `offset` as it can be."""
        if self.cursor < 0:
            return offset
        shown = rows if rows is not None else self.page_rows
        top = offset / row_height
        if self.cursor < top:
            return self.cursor * row_height
        if self.cursor + 1 > top + shown:
            return (self.cursor + 1 - shown) * row_height
        return offset


class TokenListControl(Mind):
    """See the module's note. Made by the view builder for `widget: TokenList`; `values` are the node's properties.

    Two-way: `value` (the ref the view holds; a pick writes it), `query` (the search text; it is empty each time the list opens) and `scroll`. Read: `tokens`, `groups`, `preferred`, `rows`, `row_height`, `command`, and `open` (the list is built only while
    it is true; `current` is kept either way)."""

    TWO_WAY = ("value", "query", "scroll")
    READ = ("tokens", "groups", "preferred", "rows", "row_height")

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Any = None, listen: Any = None) -> None:
        super().__init__(window, values, theme=theme, listen=listen)
        self.model: TokenList | None = None
        self._data: tuple[Any, ...] | None = None
        self.value = Signal(str(values.get("value") or ""))
        self.query = Signal(str(values.get("query") or ""))
        self.scroll = Signal(float(values.get("scroll") or 0.0))
        self.entries = Signal([])
        self.cursor_ref = Signal("")
        self.count = Signal(0)
        self.current = Signal(_unknown(str(values.get("value") or "")))
        self._rows, self._row_height = 7, 56.0
        self._shown: int | None = None  # the `version` of the results `entries` holds
        self.start_soon()

    def _read_settings(self, values: dict[str, Any]) -> None:
        self._rows = max(1, int(values.get("rows") or 7))
        self._row_height = float(values.get("row_height") or 56.0)

    def _make(self, values: dict[str, Any]) -> bool:
        """Builds the model when there is none or the tokens, groups or preferred names changed (the search and the cursor are kept); returns whether it did."""
        data = (values.get("tokens"), values.get("groups"), values.get("preferred"))
        if self.model is not None and data == self._data:
            return False
        self._data = data
        query = self.model.query if self.model is not None else str(values.get("query") or "")
        self.model = TokenList(*data, page_rows=self._rows)
        self.model.set_query(query)
        self._cursor_to_value()
        self._shown = None
        return True

    def _begin(self, values: dict[str, Any]) -> None:
        self._read_settings(values)
        self._make(values)
        model = self.model
        assert model is not None
        self.value.set(str(values.get("value") or ""))
        self.query.set("")
        model.set_query("")
        self._cursor_to_value()
        self.scroll.set(model.reveal(0.0, self._row_height))
        self._shown = None
        self._sync()

    def _cursor_to_value(self) -> None:
        model = self.model
        if model is None:
            return
        at = model.index_of(self.value.get())
        model.cursor = at if at >= 0 else (0 if model.results else -1)

    def _follow(self, values: dict[str, Any], edited: Callable[[str], bool]) -> bool:
        self._read_settings(values)
        changed = self._make(values)
        if edited("value") and str(values.get("value") or "") != self.value.get():
            self.value.set(str(values.get("value") or ""))
            changed = True
            self._cursor_to_value()
            if self._active and self.model is not None:
                self.scroll.set(self.model.reveal(self.scroll.get(), self._row_height))
        model = self.model
        if not self._active or model is None:
            return changed
        if self._rows != model.page_rows:
            model.page_rows = self._rows
            changed = True
        if edited("query") and str(values.get("query") or "") != model.query:
            self.query.set(str(values.get("query") or ""))
            model.set_query(self.query.get())
            self.scroll.set(0.0)
            changed = True
        if edited("scroll") and float(values.get("scroll") or 0.0) != self.scroll.get():
            self.scroll.set(float(values.get("scroll") or 0.0))
            changed = True
        return changed

    def _run(self, word: str, rest: str) -> None:
        model = self.model
        if model is None:
            return
        picked: str | None = None
        if word == "key":
            parts = rest.split(" ")
            picked = model.press(parts[0] if parts[0] else " ", in_field="field" in parts[1:])
        elif word == "click":
            picked = model.click(model.index_of(rest))  # by ref: a row does not know its place, which a search changes
        if picked == "pick" and model.picked is not None:
            self.value.set(model.picked["ref"])
            self._finish(model.picked["ref"])
        self.scroll.set(model.reveal(self.scroll.get(), self._row_height))

    def _sync(self) -> None:
        model = self.model
        if model is None:
            return
        if self._active:
            if model.version != self._shown:
                self._shown = model.version
                self.entries.set(list(model.results))
            picked = model.picked
            self.cursor_ref.set(picked["ref"] if picked else "")
            self.count.set(len(model.results))
        value = self.value.get()
        row = model.row_of(value)
        now = _current(row) if row is not None else _unknown(value)
        if now != self.current.get():
            self.current.set(now)


def _current(row: dict[str, Any]) -> dict[str, Any]:
    return {"ref": row["ref"], "name": row["name"], "kind": row["kind"], "swatch": row["swatch"], "shown": row["shown"], "known": True}


def _unknown(ref: str) -> dict[str, Any]:
    return {"ref": ref, "name": "", "kind": "", "swatch": "", "shown": "", "known": False}
