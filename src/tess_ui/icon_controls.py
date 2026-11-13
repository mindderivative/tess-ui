"""`IconBrowser`, the model and the control behind the icon picker: the curated icons of `tess_ui.icons`, and the SVG and PNG files of an optional folder, as a searchable grid.

`IconBrowser` has no window: it lists, searches, keeps a cursor in the grid and answers keys. `IconBrowserControl` is `widget: IconBrowser` in `IconPickerPanel_View.yaml` and
`IconPicker_View.yaml`, a control that draws nothing (see `tess_ui.mind`): it holds a browser, hands the view the grid as rows of cells, and reads the previews of the files
that are in view (and no others) when the view scrolls to them.

The grid is a list of rows `{key, cells}` (the key changes with each search, so a view makes new rows rather than patching old ones); a cell is `{index, name, kind, icon, svg, frame}`: `kind` is `glyph` (`icon` names a built-in icon), `svg` (`svg` is the file's text), `png` (`frame` is `(rgba, width, height)`) or `file` (a
file that has not been read yet, or cannot be: `icon` names a plain file glyph). A file's `name` is its file name with the extension (`logo.svg`); a built-in icon's is its name.
The folder is read through `tess_ui.filesystem`, and a folder that cannot be read is a `message`, never an error.
"""

from __future__ import annotations

import io
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from tess_ui import filesystem, icons
from tess_ui.filesystem import FileSystem, FileSystemError
from tess_ui.mind import Mind
from tess_ui.reactive import Signal

__all__ = ["IconBrowser", "IconBrowserControl", "IconEntry"]

#: The file extensions a folder's icons may have, and what each is drawn as.
_KINDS = {".svg": "svg", ".png": "png"}
_SVG_LIMIT = 256 * 1024
_PNG_LIMIT = 1024 * 1024
_PNG_SIDE = 96  # a preview is drawn at most this many pixels on a side
_FILE_GLYPH = "file" if "file" in icons.ICONS else "circle"
#: What a cell holds in `svg` while it is not a picture, and in `icon` while it is not a glyph: a view may work out a node's values a moment before it drops the node, and an empty one is refused.
_BLANK_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"/>'
_SPLIT = re.compile(r"[\s_\-.]+")
_SVG_ROOT = re.compile(r"<svg[\s>]")


@dataclass(frozen=True, slots=True)
class IconEntry:
    """One icon: its `name` (what `value` holds), its `kind` (`glyph`, `svg` or `png`) and the `path` of its file (empty for a built-in one)."""

    name: str
    kind: str
    path: str = ""


def _words(text: str) -> str:
    """`arrow_back` and `Arrow-Back.svg` both as `arrow back svg`-style words: lowercase, `_`, `-`, `.` and spaces as one space."""
    return " ".join(w for w in _SPLIT.split(text.lower()) if w)


class IconBrowser:
    """The icons, a search and a cursor. `folder` is read once, here (and again by `refresh`); `columns` and `page_rows` shape the keys."""

    def __init__(self, fs: FileSystem, folder: str = "", columns: int = 8, page_rows: int = 6, builtin: Iterable[str] | None = None) -> None:
        self.fs, self.folder, self.columns, self.page_rows = fs, folder, max(1, int(columns)), max(1, int(page_rows))
        self._builtin = sorted(builtin if builtin is not None else icons.ICONS, key=str.lower)
        self.message = ""
        self.query = ""
        self.cursor = -1
        self.version = 0  # counts the times `results` was made again
        self.entries: list[IconEntry] = []
        self.results: list[IconEntry] = []
        self.refresh()

    # -- listing and searching ---------------------------------------------------------------------------------------------------

    def refresh(self) -> None:
        """Reads the folder again (the files first, then the built-in icons, each by name without regard to case) and searches again."""
        files: list[IconEntry] = []
        self.message = ""
        if self.folder:
            try:
                for item in self.fs.list_dir(self.folder):
                    kind = _KINDS.get(item.name[item.name.rfind("."):].lower()) if "." in item.name else None
                    if kind and not item.is_dir and not item.hidden:
                        files.append(IconEntry(item.name, kind, item.path))
            except FileSystemError as error:
                self.message = str(error)
        files.sort(key=lambda e: e.name.lower())
        self.entries = [*files, *(IconEntry(name, "glyph") for name in self._builtin)]
        self.set_query(self.query)

    def set_query(self, query: str) -> None:
        """Keeps the icons whose name has every word of `query` in it (`arrow back` finds `arrow_back`), the ones whose name starts with the first word first; the cursor goes to the first."""
        self.query = query
        self.version += 1
        words = _words(query).split()
        if not words:
            self.results = list(self.entries)
        else:
            found = [e for e in self.entries if all(w in _words(e.name) for w in words)]
            self.results = sorted(found, key=lambda e: not _words(e.name).startswith(words[0]))  # stable: the order by name is kept inside each group
        self.cursor = 0 if self.results else -1

    def index_of(self, name: str) -> int:
        """The place of the icon `name` in the results, or -1."""
        for i, entry in enumerate(self.results):
            if entry.name == name:
                return i
        return -1

    def entry_named(self, name: str) -> IconEntry | None:
        """The icon `name` among all of them (not only the results), or `None`."""
        return next((e for e in self.entries if e.name == name), None)

    @property
    def rows(self) -> list[list[IconEntry]]:
        """The results in rows of `columns`."""
        return [self.results[i:i + self.columns] for i in range(0, len(self.results), self.columns)]

    # -- the cursor --------------------------------------------------------------------------------------------------------------

    def move(self, to: int) -> None:
        """Puts the cursor on `to`, kept inside the results."""
        if self.results:
            self.cursor = max(0, min(len(self.results) - 1, to))

    def press(self, key: str, *, ctrl: bool = False, in_field: bool = False) -> str | None:
        """A key. Returns `"pick"` when it chose the icon under the cursor. In the grid the arrows move by one and by a row, Home and End go to the start and the end of the row (with Ctrl, of
        the grid), Page Up and Page Down go `page_rows` rows, and Enter and Space pick. In the search field only Up, Down, Page Up and Page Down act (the others are the text's) and Enter picks."""
        if not self.results:
            return None
        here = max(self.cursor, 0) if self.cursor >= 0 else 0
        if self.cursor < 0:
            self.cursor = 0
            if key in ("arrow_down", "arrow_right", "page_down", "home", "end", "arrow_up", "arrow_left", "page_up"):
                return None
        cols, last = self.columns, len(self.results) - 1
        moves: dict[str, int] = {"arrow_up": here - cols, "arrow_down": here + cols, "page_up": here - cols * self.page_rows, "page_down": here + cols * self.page_rows}
        if not in_field:
            moves.update({"arrow_left": here - 1, "arrow_right": here + 1,
                          "home": 0 if ctrl else here - here % cols, "end": last if ctrl else min(last, here - here % cols + cols - 1)})
        if key in moves:
            self.move(moves[key])
            return None
        if key == "enter" or (key in (" ", "space") and not in_field):
            return "pick"
        return None

    def click(self, index: int) -> str | None:
        """A press on cell `index`: it is picked."""
        if 0 <= index < len(self.results):
            self.cursor = index
            return "pick"
        return None

    @property
    def picked(self) -> IconEntry | None:
        """The icon under the cursor."""
        return self.results[self.cursor] if 0 <= self.cursor < len(self.results) else None

    def reveal(self, offset: float, row_height: float, rows: int | None = None) -> float:
        """The scroll offset that keeps the cursor's row in a window of `rows` rows (`page_rows` when not given), as near to `offset` as it can be."""
        if self.cursor < 0:
            return offset
        shown = rows if rows is not None else self.page_rows
        row = self.cursor // self.columns
        top = offset / row_height
        if row < top:
            return row * row_height
        if row + 1 > top + shown:
            return (row + 1 - shown) * row_height
        return offset


def decode_png(data: bytes) -> tuple[bytes, int, int] | None:
    """`(rgba, width, height)` for PNG bytes, no larger than `_PNG_SIDE` on a side, or `None` when they are not a picture."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(data)) as opened:
            if opened.width * opened.height > 4_000_000:
                return None
            image = opened.convert("RGBA")
            image.thumbnail((_PNG_SIDE, _PNG_SIDE))
            return image.tobytes(), image.width, image.height
    except (OSError, ValueError, ImportError):
        return None


def clean_svg(data: bytes) -> str | None:
    """The text of an SVG file, or `None` when it is not one the picker will hand the engine: not UTF-8, with no `<svg` element, or with a document type or entity declaration."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    if "<!ENTITY" in text or "<!DOCTYPE" in text:
        return None
    return text if _SVG_ROOT.search(text) else None


class IconBrowserControl(Mind):
    """See the module's note. Made by the view builder for `widget: IconBrowser`; `values` are the node's properties.

    Two-way: `value` (the icon the view holds; a pick writes it) and `scroll` (the grid's scroll offset: a key that moves the cursor writes the offset that shows it).
    Read: `query`, `folder`, `columns`, `rows`, `row_height`, `command`, and `open` (the grid is listed only while it is true; `current` is kept either way)."""

    TWO_WAY = ("value", "scroll")
    READ = ("query", "folder", "columns", "rows", "row_height")
    OVERSCAN = 2

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Any = None, listen: Any = None, fs: FileSystem | None = None) -> None:
        super().__init__(window, values, theme=theme, listen=listen)
        self.fs = fs
        self.browser: IconBrowser | None = None
        self.value = Signal(str(values.get("value") or ""))
        self.scroll = Signal(float(values.get("scroll") or 0.0))
        self.grid = Signal([])
        self.cursor = Signal(-1)
        self.count = Signal(0)
        self.current = Signal({"kind": "none", "name": "", "icon": _FILE_GLYPH, "svg": _BLANK_SVG, "frame": None})
        self.message = Signal("")
        self._previews: dict[str, dict[str, Any]] = {}
        self._shown: tuple[Any, ...] | None = None
        self._columns, self._rows, self._row_height, self._folder = 8, 6, 48.0, ""
        self.start_soon()

    # -- the view's edits --------------------------------------------------------------------------------------------------------

    def _filesystem(self) -> FileSystem:
        return self.fs if self.fs is not None else filesystem.default()

    def _read_settings(self, values: dict[str, Any]) -> None:
        self._columns = max(1, int(values.get("columns") or 8))
        self._rows = max(1, int(values.get("rows") or 6))
        self._row_height = float(values.get("row_height") or 48.0)
        self._folder = str(values.get("folder") or "")

    def _begin(self, values: dict[str, Any]) -> None:
        self._read_settings(values)
        self.browser = IconBrowser(self._filesystem(), self._folder, self._columns, self._rows)
        self._previews.clear()
        self._shown = None
        self.value.set(str(values.get("value") or ""))
        self.browser.set_query(str(values.get("query") or ""))
        self._cursor_to_value()
        self.scroll.set(self.browser.reveal(0.0, self._row_height))
        self._sync()

    def _cursor_to_value(self) -> None:
        browser = self.browser
        assert browser is not None
        at = browser.index_of(self.value.get())
        browser.cursor = at if at >= 0 else (0 if browser.results else -1)

    def _follow(self, values: dict[str, Any], edited: Callable[[str], bool]) -> bool:
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
        if self._folder != browser.folder:
            browser.folder = self._folder
            browser.refresh()
            self._previews.clear()
            self._cursor_to_value()
            changed = True
        if (self._columns, self._rows) != (browser.columns, browser.page_rows):
            browser.columns, browser.page_rows = self._columns, self._rows
            changed = True
        if edited("query") and str(values.get("query") or "") != browser.query:
            browser.set_query(str(values.get("query") or ""))
            self.scroll.set(0.0)
            changed = True
        if edited("scroll") and float(values.get("scroll") or 0.0) != self.scroll.get():
            self.scroll.set(float(values.get("scroll") or 0.0))
            changed = True
        return changed

    # -- commands ----------------------------------------------------------------------------------------------------------------

    def _run(self, word: str, rest: str) -> None:
        browser = self.browser
        if browser is None:
            return
        picked: str | None = None
        if word == "key":
            parts = rest.split(" ")
            picked = browser.press(parts[0] if parts[0] else " ", ctrl="ctrl" in parts[1:], in_field="field" in parts[1:])
        elif word == "click":
            if rest.strip().lstrip("-").isdigit():
                picked = browser.click(int(rest))
        elif word == "refresh":
            browser.refresh()
            self._previews.clear()
        if picked == "pick" and browser.picked is not None:
            name = browser.picked.name
            self.value.set(name)
            self._finish(name)
        self.scroll.set(browser.reveal(self.scroll.get(), self._row_height))

    # -- telling the view --------------------------------------------------------------------------------------------------------

    def _preview(self, entry: IconEntry) -> dict[str, Any]:
        """What a file's cell shows, read once: its text or its pixels, or `{}` for a file that cannot be."""
        found = self._previews.get(entry.path)
        if found is not None:
            return found
        found = {}
        try:
            if entry.kind == "svg":
                text = clean_svg(self._filesystem().read_bytes(entry.path, _SVG_LIMIT))
                if text is not None:
                    found = {"svg": text}
            else:
                frame = decode_png(self._filesystem().read_bytes(entry.path, _PNG_LIMIT))
                if frame is not None:
                    found = {"frame": frame}
        except (FileSystemError, AttributeError):
            found = {}
        self._previews[entry.path] = found
        return found

    def _cell(self, entry: IconEntry, index: int, *, load: bool) -> dict[str, Any]:
        cell: dict[str, Any] = {"index": index, "name": entry.name, "kind": entry.kind, "icon": entry.name if entry.kind == "glyph" else _FILE_GLYPH, "svg": _BLANK_SVG, "frame": None}
        if entry.kind != "glyph":
            seen = self._previews.get(entry.path)
            seen = self._preview(entry) if load and seen is None else (seen or {})
            if "svg" in seen:
                cell["svg"] = seen["svg"]
            elif "frame" in seen:
                cell["frame"] = seen["frame"]
            else:
                cell["kind"] = "file"
        return cell

    def _sync(self) -> None:
        browser = self.browser
        value = self.value.get()
        if browser is not None and self._active:
            first = max(0, int(self.scroll.get() // self._row_height) - self.OVERSCAN)
            last = int(self.scroll.get() // self._row_height) + self._rows + self.OVERSCAN
            columns = browser.columns
            lo, hi = first * columns, (last + 1) * columns
            if (browser.version, columns, len(self._previews), lo, hi) != self._shown:
                cells = [self._cell(e, i, load=lo <= i < hi) for i, e in enumerate(browser.results)]
                self._shown = (browser.version, columns, len(self._previews), lo, hi)  # loading may have added previews
                # a row's key holds the version of the search, so a new search builds its rows afresh (a view patches a hundred cells far slower than it makes them)
                self.grid.set([{"key": f"{browser.version}:{i // columns}", "cells": cells[i:i + columns]} for i in range(0, len(cells), columns)])
            self.cursor.set(browser.cursor)
            self.count.set(len(browser.results))
            self.message.set(browser.message)
            entry = browser.entry_named(value)
        else:
            entry = IconEntry(value, "glyph") if value in icons.ICONS else self._file_entry(value)
        if entry is None:
            now = {"kind": "none", "name": value, "icon": _FILE_GLYPH, "svg": _BLANK_SVG, "frame": None}
        else:
            now = self._cell(entry, -1, load=True)
        if now != self.current.get():
            self.current.set(now)

    def _file_entry(self, value: str) -> IconEntry | None:
        """The icon `value` when it is a file in the folder (found without listing it), for the swatch of a closed picker."""
        if not value or not self._folder:
            return None
        kind = _KINDS.get(value[value.rfind("."):].lower()) if "." in value else None
        if kind is None or "/" in value or "\\" in value:
            return None
        return IconEntry(value, kind, self._folder.rstrip("/\\") + "/" + value)
