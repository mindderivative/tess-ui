"""`FileBrowser`, the control behind the file dialog: a `widget: FileBrowser` in `FileDialog_View.yaml` that draws nothing and is the dialog's mind.

A view cannot keep a folder, its history, a selection and a listing in step by itself (a called view has no ViewModel, and an expression cannot read a disk), so
this control holds one `tess_ui.file_browser.FileBrowser` and talks to the view the way the colour picker's parts do: through properties bound to names the view owns.
What the view hands it (`mode`, `multiple`, `start`, `root`, `filters`, `open`, `initial`, `rows`, `row_height`) is read when the dialog opens; `path` (the text typed in the
path bar), `filename`, `hidden`, `filter`, `scroll` and `confirm` are two-way; and `command` is how the view asks it to do something: text that starts with a number
that is new each time (a view cannot write to a name it is being told about, so the control does not clear it: it does a command once, when its text differs from the last
it did) and goes on with a word and its arguments, such as `7 click 3 ctrl`, `8 key arrow_down`, `9 up`, `10 goto`, `11 accept`, `12 new_folder Name` or `13 confirmed`. What it
knows (`entries`, `selection`, `cursor`, `folder`, `crumbs`, `message`, `valid`, `target`, `chosen`, `exists`, `problem`, `can_back`, `can_forward`, `can_up`, `filter_items`)
is written to the names the view bound.

The control reads no disk until the dialog opens (`open` going true builds a fresh `FileBrowser`, so each opening starts at `start` with the folder as it is now), and
`on_input` is called when the user has chosen something to finish with, once it needs no confirmation: the view's `on_input` handler then writes `value` and closes.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from tess_ui import filesystem
from tess_ui.file_browser import FileBrowser
from tess_ui.filesystem import FileSystem
from tess_ui.reactive import Signal, batch
from tess_ui.theme import Theme

__all__ = ["FileBrowserControl"]

#: The properties the view and the control both write.
_TWO_WAY = ("path", "filename", "hidden", "filter", "scroll", "confirm")


class FileBrowserControl:
    """See the module's note. Made by the view builder for `widget: FileBrowser`; `values` are the node's properties."""

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Theme | None = None, listen: Any = None, fs: FileSystem | None = None) -> None:
        self.window = window
        self.theme = theme
        self.fs = fs
        self.disabled = Signal(False)
        self.node = window.create("box", width=0.0, height=0.0, position="absolute", hit_testable=False, a11y_hidden=True)
        self.browser: FileBrowser | None = None
        self.entries = Signal([])
        self.selection = Signal([])
        self.cursor = Signal(-1)
        self.folder = Signal("")
        self.crumbs = Signal([])
        self.message = Signal("")
        self.valid = Signal(False)
        self.target = Signal([])
        self.chosen = Signal("")
        self.exists = Signal(False)
        self.problem = Signal("")
        self.can_back = Signal(False)
        self.can_forward = Signal(False)
        self.can_up = Signal(False)
        self.filter_items = Signal([])
        self.path = Signal(str(values.get("path") or ""))
        self.filename = Signal(str(values.get("filename") or ""))
        self.hidden = Signal(bool(values.get("hidden")))
        self.filter = Signal(int(values.get("filter") or 0))
        self.scroll = Signal(float(values.get("scroll") or 0.0))
        self.confirm = Signal(False)
        self._live: list[Callable[[Any], None]] = []
        self._changes: list[Callable[[Any], None]] = []
        self._open = False
        self._dead = False
        self._pending = False
        self._finishing: list[str] | None = None
        self._seen: dict[str, Any] = {}
        self.rows = 8
        self._pushed: list[Any] | None = None
        self._done = str(values.get("command") or "")  # the last command run: a command in the view when it was made was run by an earlier opening
        self._unlisten: Callable[[], None] | None = None
        self._values = values
        if values.get("open"):  # built open: the view's builder makes a throw-away copy of every control to check a change, so nothing is read before the real one has been kept
            window.after(0, self._start)

    def _start(self) -> None:
        if not self._dead and not self._open:
            self.follow(self._values)

    # -- for the view ----------------------------------------------------------------------------------------------------------

    def on_input(self, fn: Callable[[Any], None]) -> Callable[[], None]:
        """Calls `fn(paths)` when the dialog has something to finish with: an accepted choice that needs no confirmation. Returns the function that stops it."""
        self._live.append(fn)
        return lambda: self._live.remove(fn) if fn in self._live else None

    def on_change(self, fn: Callable[[Any], None]) -> Callable[[], None]:
        """Calls `fn(None)` after the control has changed what it holds. Returns the function that stops it."""
        self._changes.append(fn)
        return lambda: self._changes.remove(fn) if fn in self._changes else None

    def follow(self, values: dict[str, Any]) -> None:
        """Takes what the view's bindings now hold: opens or closes, then the edits the person made, then the command. A value counts as an edit when it differs from
        the one the last call saw, so a value the control has set and not yet told the view of is not taken for the view's own."""
        self._values = values
        seen, self._seen = self._seen, {key: values.get(key) for key in (*_TWO_WAY, "command")}

        def edited(key: str) -> bool:
            return values.get(key) != seen.get(key)

        opening = bool(values.get("open"))
        if opening and not self._open:
            self._open = True
            self._begin(values)
            return
        self._open = opening
        browser = self.browser
        if not opening or browser is None:
            return
        browser.page_rows, browser.row_height = max(1, int(values.get("rows") or browser.page_rows)), float(values.get("row_height") or browser.row_height)
        changed = False
        if edited("filename"):
            browser.name = str(values.get("filename") or "")
            changed = True
        if edited("hidden") and bool(values.get("hidden")) != browser.show_hidden:
            browser.show_hidden = bool(values.get("hidden"))
            browser._filter()
            changed = True
        if edited("filter"):
            index = max(0, min(int(values.get("filter") or 0), len(browser.filters) - 1))
            if index != browser.filter_index:
                browser.filter_index = index
                browser._filter()
                changed = True
        if edited("path"):
            self.path.set(str(values.get("path") or ""))
        if edited("scroll"):
            self.scroll.set(float(values.get("scroll") or 0.0))
        if edited("confirm") and not values.get("confirm") and self.confirm.get():
            self.confirm.set(False)
            changed = True
        command = str(values.get("command") or "")
        if command and command != self._done:
            self._done = command
            self._run(command.partition(" ")[2])
        elif changed:
            self._sync()
            self._tell()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme

    def dispose(self) -> None:
        """Stops the control: nothing more is read or told."""
        self._dead = True
        self._unbind()

    def _unbind(self) -> None:
        if self._unlisten is not None:
            self._unlisten()
            self._unlisten = None

    def destroy(self) -> None:
        self.dispose()
        self.node.destroy()

    # -- opening -----------------------------------------------------------------------------------------------------------------

    def _begin(self, values: dict[str, Any]) -> None:
        """A dialog has opened: a new `FileBrowser` at the start, with what the view says."""
        self._unbind()
        mode = str(values.get("mode") or "open")
        self.browser = browser = FileBrowser(
            self.fs if self.fs is not None else filesystem.default(), mode=mode, multiple=bool(values.get("multiple")), start=str(values.get("start") or ""),
            root=str(values.get("root") or ""), filters=values.get("filters") or [], filter_index=int(values.get("filter") or 0),
            show_hidden=bool(values.get("hidden")), name=str(values.get("initial") or ""))
        self.rows = max(1, int(values.get("rows") or 8))
        browser.page_rows, browser.row_height = self.rows, float(values.get("row_height") or 40.0)
        self.filter_items.set([{"value": i, "label": f.label} for i, f in enumerate(browser.filters)])
        self.confirm.set(False)
        self.scroll.set(0.0)
        self._done = str(values.get("command") or "")
        self._pushed = None
        self._unlisten = browser.on_change(self._on_browser)
        self._sync()
        self._tell()

    def _on_browser(self) -> None:
        self._sync()

    # -- commands ----------------------------------------------------------------------------------------------------------------

    def _run(self, command: str) -> None:
        browser = self.browser
        assert browser is not None
        word, _, rest = command.partition(" ")
        finish = False
        if word == "click":
            parts = rest.split()
            if parts and parts[0].lstrip("-").isdigit():
                finish = browser.click(int(parts[0]), ctrl="ctrl" in parts[1:], shift="shift" in parts[1:]) == "accept"
        elif word == "key":
            parts = rest.split(" ")
            finish = browser.press(parts[0] if parts[0] else " ", shift="shift" in parts[1:], ctrl="ctrl" in parts[1:], alt="alt" in parts[1:]) == "accept"
        elif word == "up":
            browser.up()
        elif word == "back":
            browser.back()
        elif word == "forward":
            browser.forward()
        elif word == "home":
            browser.home()
        elif word == "refresh":
            browser.refresh()
        elif word == "goto":
            browser.submit_path(rest if rest else self.path.get())
        elif word == "open":
            if rest.lstrip("-").isdigit():
                finish = browser.activate(int(rest)) == "accept"
        elif word == "enter":
            finish = browser.press("enter") == "accept"
        elif word == "new_folder":
            browser.make_folder(rest)
        elif word == "accept":
            finish = True
        elif word == "confirmed":
            self.confirm.set(False)
            self._finish()
            return
        if finish:
            if browser.valid and browser.exists:
                self._sync()
                self.confirm.set(True)
                self._tell()
                return
            if browser.valid:
                self._finish()
                return
        self._sync()
        self.scroll.set(browser.reveal(self.scroll.get()))
        self._tell()

    # -- telling the view --------------------------------------------------------------------------------------------------------

    def _sync(self) -> None:
        """Copies what the browser knows into the signals."""
        browser = self.browser
        assert browser is not None
        if self._pushed is not browser.rows:
            self._pushed = browser.rows
            self.entries.set(browser.rows)
        self.selection.set(list(browser.selection))
        self.cursor.set(browser.cursor)
        if self.folder.get() != browser.path:
            self.folder.set(browser.path)
            self.path.set(browser.path)  # the path bar follows where the dialog is
            self.scroll.set(0.0)
        self.crumbs.set(browser.crumbs)
        self.message.set(browser.message)
        self.valid.set(browser.valid)
        self.target.set(list(browser.target))
        self.chosen.set(os.path.basename(browser.target[0]) if browser.target else "")
        self.exists.set(browser.exists)
        self.problem.set(browser.problem)
        self.can_back.set(browser.can_back)
        self.can_forward.set(browser.can_forward)
        self.can_up.set(browser.can_up)
        self.filename.set(browser.name)
        self.hidden.set(browser.show_hidden)
        self.filter.set(browser.filter_index)

    def _tell(self) -> None:
        """Has the listeners the view wired write each bound name, in one batch, on the window's next turn: the view is part way through patching its nodes when this
        control hears of a change, and a second patch started now would find them half done."""
        if self._pending or self._dead:
            return
        self._pending = True
        self.window.after(0, self._flush)

    def _flush(self) -> None:
        self._pending = False
        if self._dead:
            return
        finishing, self._finishing = self._finishing, None
        listeners = [*self._changes, *(self._live if finishing is not None else [])]
        batch(lambda: [fn(finishing) for fn in list(listeners)])

    def _finish(self) -> None:
        browser = self.browser
        assert browser is not None
        self._sync()
        self._finishing = browser.result() or []
        self._tell()
