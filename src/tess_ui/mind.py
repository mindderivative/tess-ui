"""The base of the controls that draw nothing and are a view's mind: `IconBrowser`, `FontBrowser`, `ChordRecorder`, `ListModel` and `TokenList`.

A view cannot keep a search, a cursor, a list that is cut to fit it and a chord in step by itself (a called view has no ViewModel, and an expression cannot call a
method or read a disk), so each of these widgets is a shipped view of ordinary nodes plus one of these controls, which holds the state in Python and talks to the view
the way the file dialog's `FileBrowser` does (`tess_ui.file_controls`), through properties bound to names the view owns:

- what the view hands it is read in `follow(values)`, which the builder calls whenever the view is patched;
- the names that both write (`TWO_WAY`) count as an edit of the view's only when they differ from what the last call saw, so a value the control has set and not yet
  told the view of is not taken for the view's own;
- `command` is how the view asks it to do something: text that starts with a number that is new each time (a view cannot write to a name it is being told about, so
  the control does not clear it: it does a command once, when its text differs from the last it did) and goes on with a word and its arguments, such as `7 key arrow_down shift`;
- what it knows is written to the names the view bound, in one `batch`, on the window's next turn (the view is part way through patching its nodes when a control hears
  of a change, and a second patch started then would find them half done); `on_input` is called for the changes the person has made, `on_change` for every change.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

from tess_ui.reactive import Signal, batch
from tess_ui.theme import Theme

__all__ = ["KINDS", "Mind", "control_class"]

#: The widget kinds that are one of these controls, and where each one lives (`module:Class`; imported when one is built).
KINDS: dict[str, str] = {
    "IconBrowser": "tess_ui.icon_controls:IconBrowserControl",
    "FontBrowser": "tess_ui.font_controls:FontBrowserControl",
    "ChordRecorder": "tess_ui.chord_controls:ChordRecorder",
    "TokenList": "tess_ui.token_controls:TokenListControl",
}


def control_class(kind: str) -> type[Mind]:
    """The control class for the widget kind `kind` (one of `KINDS`)."""
    module, _, name = KINDS[kind].partition(":")
    return getattr(importlib.import_module(module), name)


class Mind:
    """See the module's note. Subclasses set `TWO_WAY` and write `_follow` (the edits the view made), `_run` (a command), `_begin` (it has become active) and `_sync`
    (copy what they know to the signals). `values` are the node's properties."""

    #: The properties both the view and the control write.
    TWO_WAY: tuple[str, ...] = ()
    #: The properties only the view writes and the control wants to hear of when they change (besides `command`).
    READ: tuple[str, ...] = ()

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Theme | None = None, listen: Any = None) -> None:
        self.window = window
        self.theme = theme
        self.disabled = Signal(False)
        self.node = window.create("box", width=0.0, height=0.0, position="absolute", hit_testable=False, a11y_hidden=True)
        self._live: list[Callable[[Any], None]] = []
        self._changes: list[Callable[[Any], None]] = []
        self._active = False
        self._dead = False
        self._pending = False
        self._finishing: Any = None
        self._finished = False
        self._seen: dict[str, Any] = {}
        self._values = values
        self._done = str(values.get("command") or "")  # the last command run: one in the view when it was made was run by an earlier control

    # -- for the view ----------------------------------------------------------------------------------------------------------

    def on_input(self, fn: Callable[[Any], None]) -> Callable[[], None]:
        """Calls `fn(result)` when the person has finished something (a pick). Returns the function that stops it."""
        self._live.append(fn)
        return lambda: self._live.remove(fn) if fn in self._live else None

    def on_change(self, fn: Callable[[Any], None]) -> Callable[[], None]:
        """Calls `fn(None)` after the control has changed what it holds. Returns the function that stops it."""
        self._changes.append(fn)
        return lambda: self._changes.remove(fn) if fn in self._changes else None

    def follow(self, values: dict[str, Any]) -> None:
        """Takes what the view's bindings now hold: whether it is active (`open`, true when the view does not say), then the edits made in the view, then the command (an inactive control does no command)."""
        self._values = values
        seen, self._seen = self._seen, {key: values.get(key) for key in (*self.TWO_WAY, *self.READ, "command")}

        def edited(key: str) -> bool:
            return values.get(key) != seen.get(key)

        active = bool(values.get("open", True))
        if active and not self._active:
            self._active = True
            self._begin(values)
            self._flush_soon()
            return
        self._active = active
        changed = self._follow(values, edited) or not seen  # the first call always shows what there is
        command = str(values.get("command") or "")
        if active and command and command != self._done:
            self._done = command
            if not self.disabled.get():  # a disabled control is deaf (the builder sets `disabled` before it follows the view)
                self._run(*command.partition(" ")[2].partition(" ")[::2])
                changed = True
        if changed:
            self._sync()
            self._flush_soon()

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme

    def dispose(self) -> None:
        """Stops the control: nothing more is read or told."""
        self._dead = True

    def destroy(self) -> None:
        self.dispose()
        self.node.destroy()

    def start(self) -> None:
        """Takes the view's first values, on the window's next turn after it was built, unless a patch has already done so (the builder makes a throw-away copy of every
        control to check a change, so a constructor reads nothing)."""
        if not self._dead and not self._seen:
            self.follow(self._values)

    def start_soon(self) -> None:
        """For a subclass constructor: take the first values on the window's next turn."""
        self.window.after(0, self.start)

    # -- for subclasses ---------------------------------------------------------------------------------------------------------

    def _begin(self, values: dict[str, Any]) -> None:
        """The control has become active: read what it needs and set the signals."""

    def _follow(self, values: dict[str, Any], edited: Callable[[str], bool]) -> bool:
        """Takes the view's edits (called whether or not the control is active, which `self._active` says); true when something changed that the signals must show."""
        return False

    def _run(self, word: str, rest: str) -> None:
        """A command from the view: `word` and the text after it."""

    def _sync(self) -> None:
        """Copy what is known into the signals."""

    def _finish(self, result: Any = True) -> None:
        """The person has finished something (a pick): `on_input` is told, with `result`, once the signals are current (the caller's `_sync` follows)."""
        self._finishing, self._finished = result, True
        self._flush_soon()

    def _flush_soon(self) -> None:
        if self._pending or self._dead:
            return
        self._pending = True
        self.window.after(0, self._flush)

    def _flush(self) -> None:
        self._pending = False
        if self._dead:
            return
        finished, result, self._finished, self._finishing = self._finished, self._finishing, False, None
        listeners = [*self._changes, *(self._live if finished else [])]
        batch(lambda: [fn(result) for fn in list(listeners)])
