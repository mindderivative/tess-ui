"""`FontBrowser`, the model and the control behind the font list: the installed font families (see `tess_ui.font_families`), searchable, with a cursor.

`FontBrowser` has no window: it keeps the families, the search and the cursor, and answers keys. `FontBrowserControl` is `widget: FontBrowser` in `FontListPanel_View.yaml` and
`FontList_View.yaml`, a control that draws nothing (see `tess_ui.mind`). It asks `tess_ui.font_families` once, when the view first builds it, and tells the view:
`mode` (`""` until the control has asked, then `list`, or `text` when the families cannot be listed, so the view shows a text field instead, and `message` says why), `entries` (the rows: `{family, loadable}`, where
`loadable` says whether the engine can draw text in that family, which `tess_ui.fonts.available_families` knows, so the view can show each name in its own face only then),
`cursor_name`, `count` and `current` (the row of `value`, for the closed popup's button).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tess_ui import font_families, fonts
from tess_ui.mind import Mind
from tess_ui.reactive import Signal

__all__ = ["FontBrowser", "FontBrowserControl"]


class FontBrowser:
    """The families, a search and a cursor. `families` must be sorted already (`tess_ui.font_families.families()` is); `page_rows` shapes Page Up and Page Down."""

    def __init__(self, families: list[str], page_rows: int = 8) -> None:
        self.families = list(families)
        self.page_rows = max(1, int(page_rows))
        self.query = ""
        self.cursor = -1
        self.results: list[str] = []
        self.version = 0  # counts the times `results` was made again
        self.set_query("")

    def set_query(self, query: str) -> None:
        """Keeps the families that have every word of `query` in them (without regard to case), the ones that start with the first word first; the cursor goes to the first."""
        self.query = query
        self.version += 1
        words = query.casefold().split()
        if not words:
            self.results = list(self.families)
        else:
            found = [f for f in self.families if all(w in f.casefold() for w in words)]
            self.results = sorted(found, key=lambda f: not f.casefold().startswith(words[0]))  # stable: the order by name is kept inside each group
        self.cursor = 0 if self.results else -1

    def index_of(self, family: str) -> int:
        """The place of `family` in the results, or -1."""
        try:
            return self.results.index(family)
        except ValueError:
            return -1

    def move(self, to: int) -> None:
        """Puts the cursor on `to`, kept inside the results."""
        if self.results:
            self.cursor = max(0, min(len(self.results) - 1, to))

    def press(self, key: str, *, in_field: bool = False) -> str | None:
        """A key. Returns `"pick"` when it chose the family under the cursor. In the list Up and Down move by one, Page Up and Page Down by `page_rows`, Home and End go to the ends, and Enter
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
        if key == "enter" or (key in (" ", "space") and not in_field):
            return "pick"
        return None

    def click(self, index: int) -> str | None:
        """A press on row `index` (-1 is none): it is picked."""
        if 0 <= index < len(self.results):
            self.cursor = index
            return "pick"
        return None

    @property
    def picked(self) -> str | None:
        """The family under the cursor."""
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


class FontBrowserControl(Mind):
    """See the module's note. Made by the view builder for `widget: FontBrowser`; `values` are the node's properties.

    Two-way: `value` (the family the view holds; a pick writes it) and `scroll`. Read: `query`, `rows`, `row_height`, `command`, and `open` (the list is built only while it is true;
    `mode` and `current` are kept either way)."""

    TWO_WAY = ("value", "scroll")
    READ = ("query", "rows", "row_height")

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Any = None, listen: Any = None) -> None:
        super().__init__(window, values, theme=theme, listen=listen)
        self.browser: FontBrowser | None = None
        self._families: list[str] | None = None
        self.value = Signal(str(values.get("value") or ""))
        self.scroll = Signal(float(values.get("scroll") or 0.0))
        self.entries = Signal([])
        self.cursor_name = Signal("")
        self.count = Signal(0)
        self.mode = Signal("")
        self.message = Signal("")
        self.current = Signal({"family": "", "loadable": False})
        self._rows, self._row_height = 8, 40.0
        self._shown: tuple[Any, ...] | None = None
        self.start_soon()

    def _load(self) -> None:
        """Asks `tess_ui.font_families` once; a machine that cannot list its fonts leaves the control in `text` mode with no list."""
        if self._families is not None:
            return
        try:
            self._families = font_families.families()
            self.mode.set("list")
        except font_families.FontListError as error:
            self._families = []
            self.mode.set("text")
            self.message.set(f"The installed fonts cannot be listed ({error}): type the family's name.")

    def _read_settings(self, values: dict[str, Any]) -> None:
        self._rows = max(1, int(values.get("rows") or 8))
        self._row_height = float(values.get("row_height") or 40.0)

    def _begin(self, values: dict[str, Any]) -> None:
        self._read_settings(values)
        self._load()
        self.value.set(str(values.get("value") or ""))
        self.browser = FontBrowser(self._families or [], self._rows)
        self.browser.set_query(str(values.get("query") or ""))
        self._cursor_to_value()
        self.scroll.set(self.browser.reveal(0.0, self._row_height))
        self._shown = None
        self._sync()

    def _cursor_to_value(self) -> None:
        browser = self.browser
        assert browser is not None
        at = browser.index_of(self.value.get())
        browser.cursor = at if at >= 0 else (0 if browser.results else -1)

    def _follow(self, values: dict[str, Any], edited: Callable[[str], bool]) -> bool:
        self._load()
        self._read_settings(values)
        changed = False
        if edited("value") and str(values.get("value") or "") != self.value.get():
            self.value.set(str(values.get("value") or ""))
            changed = True
            if self.browser is not None and self._active:
                self._cursor_to_value()
                self.scroll.set(self.browser.reveal(self.scroll.get(), self._row_height))
        if not self._active or self.browser is None:
            return changed
        browser = self.browser
        if self._rows != browser.page_rows:
            browser.page_rows = self._rows
            changed = True
        if edited("query") and str(values.get("query") or "") != browser.query:
            browser.set_query(str(values.get("query") or ""))
            self.scroll.set(0.0)
            changed = True
        if edited("scroll") and float(values.get("scroll") or 0.0) != self.scroll.get():
            self.scroll.set(float(values.get("scroll") or 0.0))
            changed = True
        return changed

    def _run(self, word: str, rest: str) -> None:
        browser = self.browser
        if browser is None:
            return
        picked: str | None = None
        if word == "key":
            parts = rest.split(" ")
            picked = browser.press(parts[0] if parts[0] else " ", in_field="field" in parts[1:])
        elif word == "click":
            picked = browser.click(browser.index_of(rest))  # by name: a row does not know its place, which a search changes
        if picked == "pick" and browser.picked is not None:
            self.value.set(browser.picked)
            self._finish(browser.picked)
        self.scroll.set(browser.reveal(self.scroll.get(), self._row_height))

    def _sync(self) -> None:
        browser = self.browser
        value = self.value.get()
        loadable = fonts.available_families()
        if browser is not None and self._active:
            if (browser.version, loadable) != self._shown:
                self._shown = (browser.version, loadable)
                self.entries.set([{"family": f, "loadable": f in loadable} for f in browser.results])
            self.cursor_name.set(browser.picked or "")
            self.count.set(len(browser.results))
        now = {"family": value, "loadable": value in loadable}
        if now != self.current.get():
            self.current.set(now)
