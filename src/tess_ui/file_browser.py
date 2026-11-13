"""The state and the rules of the file dialog, apart from how it looks: `FileBrowser`.

One `FileBrowser` is one dialog's whole mind. It knows the folder it is showing (`path`) and the rows in it (`rows`: folders first, then files, each sorted by name
without regard to case, after the hidden-file switch and the type filter), the rows picked (`selection`) and the one the keyboard is on (`cursor`), the history
that Back and Forward walk, the name typed for a save (`name`), and the last thing that went wrong (`message`; a folder that cannot be read is a message, never an
exception). What it does is a method each: `navigate`, `up`, `back`, `forward`, `home`, `refresh`, `submit_path`, `click`, `activate`, `press` (a key), `make_folder`.
`valid`, `target` and `exists` say what pressing OK would give now.

It reads the file system only through `tess_ui.filesystem`, a folder at a time and never below it, so a directory of ten thousand entries costs one listing when it
is entered; the dialog's `VirtualList` builds only the rows in view. A `root` confines it: nothing above it can be entered, by the path bar, Up, Back, Home or a
symlink inside it that leads out.

The view (`FileDialog`) drives one of these through the `FileBrowser` control (`tess_ui.file_controls`); a program can drive one directly, and it has no window.
"""

from __future__ import annotations

import fnmatch
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from tess_ui import filesystem
from tess_ui.filesystem import Entry, FileSystem, FileSystemError

__all__ = ["FileBrowser", "Filter", "MODES", "read_filters"]

MODES = ("open", "save", "folder")
Row = dict[str, Any]
_WILD = set("*?[")


@dataclass(frozen=True, slots=True)
class Filter:
    """A choice in the type list: a `label` and the glob `patterns` a file's name must match (case does not count) to be shown."""

    label: str
    patterns: tuple[str, ...]

    def matches(self, name: str) -> bool:
        """Whether a file called `name` is of this type."""
        folded = name.casefold()
        return any(fnmatch.fnmatchcase(folded, p.casefold()) for p in self.patterns)

    @property
    def extension(self) -> str:
        """The extension a file saved under this filter gets when its name has none: the first pattern written `*.ext` with nothing wild in `ext`, else empty."""
        for pattern in self.patterns:
            if pattern.startswith("*.") and len(pattern) > 2 and not _WILD & set(pattern[1:]):
                return pattern[1:]
        return ""


ALL_FILES = Filter("All files", ("*",))


def read_filters(filters: Iterable[Any] | None) -> list[Filter]:
    """The filters a dialog is given (`{label, patterns}` mappings, `(label, patterns)` pairs or `Filter`s), then `All files` unless one already shows everything."""
    found: list[Filter] = []
    for item in filters or ():
        if isinstance(item, Filter):
            found.append(item)
            continue
        if isinstance(item, dict):
            label, patterns = item.get("label"), item.get("patterns")
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            label, patterns = item
        else:
            raise ValueError(f"a filter is {{label: ..., patterns: [...]}}, got {item!r}")
        if isinstance(patterns, str):
            patterns = [patterns]
        if not isinstance(label, str) or not label or not isinstance(patterns, (list, tuple)) or not patterns or not all(isinstance(p, str) and p for p in patterns):
            raise ValueError(f"a filter has a label and a list of patterns such as ['*.tdl'], got {item!r}")
        found.append(Filter(label, tuple(patterns)))
    if not any("*" in f.patterns for f in found):
        found.append(ALL_FILES)
    return found


def size_text(size: int | None) -> str:
    """`1.5 KB`: a file's size as a person reads it (empty for a folder)."""
    if size is None:
        return ""
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1024
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if value >= 10 else f"{value:.1f} {unit}"
    raise AssertionError("unreachable")


def time_text(seconds: float | None) -> str:
    """`2026-11-13 09:30`, in local time (empty when the time is not known or not one a calendar has)."""
    if seconds is None:
        return ""
    try:
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(seconds))
    except (OverflowError, OSError, ValueError):
        return ""


def _row(entry: Entry) -> Row:
    return {"name": entry.name, "path": entry.path, "dir": entry.is_dir, "icon": "folder" if entry.is_dir else "file",
            "size": size_text(entry.size), "modified": time_text(entry.modified), "hidden": entry.hidden}


class FileBrowser:
    """One file dialog's state. See the module's note."""

    #: Two clicks on one row within this many seconds are a double click.
    DOUBLE_CLICK = 0.4
    #: A pause this long (seconds) in typing starts a new type-ahead word.
    TYPE_AHEAD = 1.0

    def __init__(self, fs: FileSystem | None = None, *, mode: str = "open", multiple: bool = False, start: str = "", root: str = "",
                 filters: Iterable[Any] | None = None, filter_index: int = 0, show_hidden: bool = False, name: str = "",
                 clock: Callable[[], float] = time.monotonic) -> None:
        if mode not in MODES:
            raise ValueError(f"mode is one of {', '.join(MODES)}, got {mode!r}")
        self.fs: FileSystem = fs if fs is not None else filesystem.default()
        self.mode = mode
        self.multiple = bool(multiple)
        self.filters = read_filters(filters)
        self.filter_index = max(0, min(int(filter_index), len(self.filters) - 1))
        self.show_hidden = bool(show_hidden)
        self.name = name
        #: how many rows the list shows at once and how tall a row is: what `reveal` and Page Up and Page Down need.
        self.page_rows = 8
        self.row_height = 40.0
        self.message = ""
        self.selection: list[str] = []
        self.cursor = -1
        self.rows: list[Row] = []
        self.path = ""
        self._readable = False  # the folder shown could be read: a folder dialog with none has nothing it can give
        self._clock = clock
        self._all: list[Row] = []
        self._by_path: dict[str, Row] = {}
        self._back: list[str] = []
        self._forward: list[str] = []
        self._anchor = -1
        self._last_click: tuple[int, float] | None = None
        self._typed = ""
        self._typed_at = 0.0
        self._listeners: list[Callable[[], None]] = []
        self.root = self._normal(self._tilde(root)) if root else ""
        self._start(start)

    # -- listening ---------------------------------------------------------------------------------------------------------------

    def on_change(self, fn: Callable[[], None]) -> Callable[[], None]:
        """Calls `fn()` after each operation that may have changed anything. Returns the function that stops it."""
        self._listeners.append(fn)
        return lambda: self._listeners.remove(fn) if fn in self._listeners else None

    def _changed(self) -> None:
        for fn in list(self._listeners):
            fn()

    # -- places --------------------------------------------------------------------------------------------------------------------

    @staticmethod
    def _normal(path: str) -> str:
        return os.path.normpath(os.path.abspath(path))

    def _tilde(self, text: str) -> str:
        """`~` and `~/x` read as the person's home, which the file system says (so a test never reads the real one)."""
        if text == "~" or text.startswith(("~/", "~" + os.sep)):
            return self.fs.home() + text[1:]
        return text

    def _resolve(self, text: str) -> str:
        text = self._tilde(text.strip())
        base = self.path or self.fs.cwd()
        return os.path.normpath(os.path.join(base, text)) if text else base

    def _inside(self, path: str) -> bool:
        """Whether `path` is the root or under it, by its name and by where it really leads."""
        if not self.root:
            return True

        def under(inner: str, outer: str) -> bool:
            try:
                return os.path.commonpath([inner, outer]) == outer
            except ValueError:  # another drive
                return False

        if not under(path, self.root):
            return False
        try:
            return under(self.fs.real_path(path), self.fs.real_path(self.root))
        except OSError:
            return False

    def _start(self, start: str) -> None:
        """Opens the first folder: `start`, else the root, else the working folder; one that cannot be opened gives way to the nearest folder above it that can,
        and the message says what went wrong with the first."""
        wanted = self._normal(self._tilde(start)) if start else (self.root or self._normal(self.fs.cwd()))
        if self.root and not self._inside(wanted):
            wanted = self.root
        failure = ""
        candidate = wanted
        while True:
            if self._load(candidate):
                self.message = failure
                return
            failure = failure or self.message
            parent = os.path.dirname(candidate)
            if parent == candidate or (self.root and candidate == self.root):
                break
            candidate = parent
        self.path = wanted  # nothing could be read: show the empty place and what went wrong
        self._readable = False
        self._set_rows([])
        self.message = failure

    def _load(self, path: str) -> bool:
        """Reads the folder `path` and makes it the current one; false, with `message` set, when it cannot be."""
        try:
            if not self.fs.is_dir(path):
                self.message = (f"{path} is not a folder" if self.fs.exists(path) else f"There is no folder {path}")
                return False
            entries = self.fs.list_dir(path)
        except FileSystemError as error:
            self.message = str(error)
            return False
        self.path = path
        self._readable = True
        self._all = [_row(e) for e in sorted(entries, key=lambda e: (not e.is_dir, e.name.casefold(), e.name))]
        self._by_path = {r["path"]: r for r in self._all}
        self.selection = []
        self.cursor = self._anchor = -1
        self._last_click = None
        self._filter()
        self.message = ""
        return True

    # -- what is shown ------------------------------------------------------------------------------------------------------------

    def _visible(self, row: Row) -> bool:
        if row["hidden"] and not self.show_hidden:
            return False
        if row["dir"]:
            return True  # a filter never hides a folder
        return self.mode != "folder" and self.current_filter.matches(row["name"])

    @property
    def current_filter(self) -> Filter:
        """The file type in use."""
        return self.filters[self.filter_index]

    def _filter(self) -> None:
        cursor_at = self.rows[self.cursor]["path"] if 0 <= self.cursor < len(self.rows) else None
        self.rows = [r for r in self._all if self._visible(r)]
        shown = {r["path"] for r in self.rows}
        self.selection = [p for p in self.selection if p in shown or p not in self._by_path]  # a path typed in that the listing does not hold stays
        self.cursor = self._anchor = next((i for i, r in enumerate(self.rows) if r["path"] == cursor_at), -1)

    def _set_rows(self, rows: list[Row]) -> None:
        self._all, self.rows, self._by_path = rows, rows, {r["path"]: r for r in rows}
        self.selection, self.cursor, self._anchor = [], -1, -1

    def set_filter(self, index: int) -> None:
        """Chooses the type filter `index`; a file it hides stops being selected."""
        self.filter_index = max(0, min(int(index), len(self.filters) - 1))
        self._filter()
        self._changed()

    def set_show_hidden(self, shown: bool) -> None:
        """Shows or hides the entries whose names start with a dot."""
        self.show_hidden = bool(shown)
        self._filter()
        self._changed()

    @property
    def crumbs(self) -> list[dict[str, str]]:
        """The path as a trail: from the root (or the file system's own, `/` or a drive) to the current folder, each `{name, path}`."""
        if self.root:
            base, rest = self.root, os.path.relpath(self.path, self.root) if self.path != self.root else ""
            first = os.path.basename(base) or base
        else:
            drive, root, tail = os.path.splitroot(self.path)
            base, rest, first = drive + root, tail, drive + root
        trail = [{"name": first, "path": base}]
        current = base
        for part in [p for p in rest.split(os.sep) if p and p != os.curdir]:
            current = os.path.join(current, part)
            trail.append({"name": part, "path": current})
        return trail

    # -- moving about -------------------------------------------------------------------------------------------------------------

    def navigate(self, target: str) -> bool:
        """Goes to the folder `target` (`~` is home; a relative one is read from the current folder). False, with `message`, when it is not a folder, cannot
        be read, or is outside the root; the dialog stays where it was."""
        before = self.path
        ok = self._go(target)
        if ok and self.path != before:
            self._back.append(before)
            self._forward.clear()
        self._changed()
        return ok

    def _go(self, target: str) -> bool:
        path = self._resolve(target)
        if not self._inside(path):
            self.message = f"{path} is outside {self.root}"
            return False
        return self._load(path)

    @property
    def can_up(self) -> bool:
        """Whether there is a folder above (not at the top of the file system, nor at the root)."""
        return bool(self.path) and os.path.dirname(self.path) != self.path and self.path != self.root

    @property
    def can_back(self) -> bool:
        """Whether there is a folder to go back to."""
        return bool(self._back)

    @property
    def can_forward(self) -> bool:
        """Whether there is a folder to go forward to (after a Back)."""
        return bool(self._forward)

    def up(self) -> bool:
        """Goes to the folder above, unless this is the top (the file system's, or the root)."""
        if not self.can_up:
            return False
        return self.navigate(os.path.dirname(self.path))

    def home(self) -> bool:
        """Goes to the person's home folder, or to the root when home is outside it."""
        home = self.fs.home()
        if self.root and not self._inside(self._normal(home)):
            home = self.root
        return self.navigate(home)

    def back(self) -> bool:
        """Goes back to the folder before this one."""
        if not self._back:
            return False
        before = self.path
        ok = self._go(self._back[-1])
        if ok:
            self._back.pop()
            self._forward.append(before)
        self._changed()
        return ok

    def forward(self) -> bool:
        """Goes forward again after a Back."""
        if not self._forward:
            return False
        before = self.path
        ok = self._go(self._forward[-1])
        if ok:
            self._forward.pop()
            self._back.append(before)
        self._changed()
        return ok

    def refresh(self) -> bool:
        """Reads the current folder again, keeping what is selected that is still there."""
        kept = list(self.selection)
        ok = self._load(self.path)
        if ok:
            self.selection = [p for p in kept if p in self._by_path]
            self.cursor = next((i for i, r in enumerate(self.rows) if r["path"] in self.selection), -1)
        else:
            self._readable = False
            self._set_rows([])  # the folder has gone or cannot be read now: nothing to show, and the message says why
        self._changed()
        return ok

    def submit_path(self, text: str) -> bool:
        """What Enter in the path bar does: a folder is entered; an existing file is selected, in its own folder (an open dialog) or has its name taken (a save).
        Anything else is a message."""
        if not text.strip():
            return False
        wanted = self._resolve(text)
        if self.fs.exists(wanted) and not self.fs.is_dir(wanted):
            if not self._inside(wanted):
                self.message = f"{wanted} is outside {self.root}"
                self._changed()
                return False
            if self.mode == "folder":
                self.message = f"{wanted} is not a folder"
                self._changed()
                return False
            if not self._go(os.path.dirname(wanted)):
                self._changed()
                return False
            self.selection = [wanted]
            if self.mode == "save":
                self.name = os.path.basename(wanted)
            self.cursor = next((i for i, r in enumerate(self.rows) if r["path"] == wanted), -1)
            self._anchor = self.cursor
            self._changed()
            return True
        return self.navigate(text)

    # -- picking ------------------------------------------------------------------------------------------------------------------

    def _pick(self, paths: list[str], cursor: int) -> None:
        self.selection = paths
        self.cursor = cursor
        if self.mode == "save" and len(paths) == 1 and paths[0] in self._by_path and not self._by_path[paths[0]]["dir"]:
            self.name = self._by_path[paths[0]]["name"]  # picking a file to overwrite names the save after it

    def click(self, index: int, *, ctrl: bool = False, shift: bool = False) -> str:
        """A press on row `index`. A plain press selects it; with Ctrl (several allowed) it flips it; with Shift (several allowed) it extends from the row
        pressed last. A second plain press on the same row within `DOUBLE_CLICK` seconds is `activate`. Returns what `activate` does, else `""`."""
        if not 0 <= index < len(self.rows):
            return ""
        now = self._clock()
        double = (self._last_click is not None and self._last_click[0] == index and now - self._last_click[1] <= self.DOUBLE_CLICK
                  and not ctrl and not shift)
        self._last_click = (index, now)
        if double:
            self._last_click = None
            return self.activate(index)
        row = self.rows[index]
        if self.multiple and shift:
            low, high = sorted((index, self._anchor if self._anchor >= 0 else index))
            self._pick([r["path"] for r in self.rows[low:high + 1] if self._selectable(r)], index)
        elif self.multiple and ctrl:
            kept = [p for p in self.selection if p != row["path"]]
            self._pick(kept if len(kept) != len(self.selection) else kept + ([row["path"]] if self._selectable(row) else []), index)
            self._anchor = index
        else:
            self._pick([row["path"]] if self._selectable(row) else [], index)
            self._anchor = index
        self._changed()
        return ""

    def _selectable(self, row: Row) -> bool:
        """A folder dialog picks folders and the others pick files; the cursor still goes over the rest, to enter a folder."""
        return row["dir"] == (self.mode == "folder")

    def activate(self, index: int) -> str:
        """Opens the row: a folder is entered (returns `"entered"`), a file is chosen (returns `"accept"`, for the dialog to finish with it)."""
        if not 0 <= index < len(self.rows):
            return ""
        row = self.rows[index]
        if row["dir"]:
            self.navigate(row["path"])
            return "entered"
        self._pick([row["path"]], index)
        self._anchor = index
        self._changed()
        return "accept"

    def move(self, to: int, *, extend: bool = False) -> None:
        """Puts the keyboard on row `to` (held to the rows there are) and selects it; `extend` (several allowed) keeps the rows from the anchor to it."""
        if not self.rows:
            return
        to = max(0, min(to, len(self.rows) - 1))
        if self.multiple and extend:
            low, high = sorted((to, self._anchor if self._anchor >= 0 else to))
            self._pick([r["path"] for r in self.rows[low:high + 1] if self._selectable(r)], to)
        else:
            self._pick([self.rows[to]["path"]] if self._selectable(self.rows[to]) else [], to)
            self._anchor = to
        self._changed()

    def select_all(self) -> None:
        """Every selectable row (several allowed)."""
        if self.multiple:
            self.selection = [r["path"] for r in self.rows if self._selectable(r)]
            self._changed()

    def press(self, key: str, *, shift: bool = False, ctrl: bool = False, alt: bool = False) -> str:
        """A key pressed in the list (`key` as the engine names it: `arrow_up`, `page_down`, `enter`, `a`). The arrows, Page Up and Page Down, Home and End
        move the cursor; Enter opens the row it is on (or, with none, is `accept`); Backspace and Alt+Left, Alt+Right are Up, Back and Forward; Ctrl+A selects
        all (several allowed); a letter jumps to the next name that starts with what has been typed. Returns `"accept"` when the dialog should finish, else `""`."""
        page = max(1, self.page_rows - 1)
        key = key.lower() if len(key) > 1 else key  # `enter` and `Enter` are one key
        if alt:
            if key == "arrow_left":
                self.back()
            elif key == "arrow_right":
                self.forward()
            elif key == "arrow_up":
                self.up()
            return ""
        if ctrl:
            if key.lower() == "a":
                self.select_all()
            return ""
        if key == "arrow_down":
            self.move(self.cursor + 1, extend=shift)
        elif key == "arrow_up":
            self.move(self.cursor - 1 if self.cursor > 0 else 0, extend=shift)
        elif key == "page_down":
            self.move(self.cursor + page, extend=shift)
        elif key == "page_up":
            self.move(self.cursor - page, extend=shift)
        elif key == "home":
            self.move(0, extend=shift)
        elif key == "end":
            self.move(len(self.rows) - 1, extend=shift)
        elif key == "backspace":
            self.up()
        elif key == "enter":
            if self.cursor >= 0:
                return self.activate(self.cursor)
            return "accept" if self.valid else ""
        elif len(key) == 1 and key.isprintable() and key != " ":
            self._type(key)
        return ""

    def _type(self, char: str) -> None:
        """Type-ahead: a letter goes to the next name from the cursor that starts with it (the same letter again goes on to the one after); more letters within
        `TYPE_AHEAD` seconds make a longer start, which may stay on the row the cursor is on."""
        now = self._clock()
        if now - self._typed_at > self.TYPE_AHEAD:
            self._typed = ""
        self._typed_at = now
        self._typed += char.casefold()
        names = [r["name"].casefold() for r in self.rows]
        stepping = len(set(self._typed)) == 1  # `a`, `aa`, `aaa`: the next name that starts with `a`
        probe = self._typed[0] if stepping else self._typed
        begin = self.cursor + 1 if stepping else max(self.cursor, 0)
        for i in [*range(begin, len(names)), *range(min(begin, len(names)))]:
            if names[i].startswith(probe):
                self.move(i)
                return

    def reveal(self, offset: float) -> float:
        """The scroll offset (pixels) that shows the cursor row, starting from `offset`: unchanged when it is in view already."""
        if self.cursor < 0:
            return offset
        view = self.page_rows * self.row_height
        top = self.cursor * self.row_height
        if top < offset:
            return top
        if top + self.row_height > offset + view:
            return top + self.row_height - view
        return offset

    # -- new folder -------------------------------------------------------------------------------------------------------------

    def make_folder(self, name: str) -> bool:
        """Makes the folder `name` in the current one and selects it. False, with `message`, for a name that is empty, has a separator, is taken, or a place
        that will not take it."""
        problem = self._name_problem(name)
        if problem:
            self.message = problem
            self._changed()
            return False
        made = os.path.join(self.path, name.strip())
        if self.fs.exists(made):
            self.message = f"{name.strip()} already exists"
            self._changed()
            return False
        try:
            self.fs.make_dir(made)
        except FileSystemError as error:
            self.message = str(error)
            self._changed()
            return False
        if self._load(self.path):
            self._pick([made], next((i for i, r in enumerate(self.rows) if r["path"] == made), -1))
            self._anchor = self.cursor
        self._changed()
        return True

    @staticmethod
    def _name_problem(name: str) -> str:
        text = name.strip()
        if not text:
            return "Type a name"
        if text in (".", "..") or any(c in text for c in ("/", "\\", "\0")) or (os.sep in text):
            return f"{text} is not a name: it cannot hold / or \\"
        return ""

    # -- the answer -----------------------------------------------------------------------------------------------------------------

    def filename(self) -> str:
        """The save name as it will be written: what was typed, and the extension of the filter when the name has none."""
        text = self.name.strip()
        if text and not os.path.splitext(text)[1] and not text.endswith("."):
            return text + self.current_filter.extension
        return text

    def _is_dir(self, path: str) -> bool:
        row = self._by_path.get(path)
        return row["dir"] if row is not None else self.fs.is_dir(path)

    @property
    def target(self) -> list[str]:
        """The paths OK would give now (empty when there is nothing valid to give)."""
        if self.mode == "save":
            name = self.filename()
            return [os.path.join(self.path, name)] if name and not self._name_problem(name) else []
        if self.mode == "folder":
            chosen = [p for p in self.selection if self._is_dir(p)]
            return chosen if chosen else ([self.path] if self._readable else [])
        files = [p for p in self.selection if not self._is_dir(p)]
        return files if files and len(files) == len(self.selection) and (self.multiple or len(files) == 1) else []

    @property
    def problem(self) -> str:
        """Why a save name will not do (empty when it will, or when none is typed yet)."""
        if self.mode != "save" or not self.name.strip():
            return ""
        problem = self._name_problem(self.filename())
        if problem:
            return problem
        if self._is_dir(os.path.join(self.path, self.filename())) and self.fs.exists(os.path.join(self.path, self.filename())):
            return f"{self.filename()} is a folder"
        return ""

    @property
    def valid(self) -> bool:
        """Whether OK may be pressed."""
        return bool(self.target) and not self.problem

    @property
    def exists(self) -> bool:
        """A save whose file is there already, which wants the person's yes before it is written over."""
        return self.mode == "save" and self.valid and self.fs.exists(self.target[0])

    def result(self) -> list[str] | None:
        """The answer, or `None` while `valid` is false."""
        return list(self.target) if self.valid else None
