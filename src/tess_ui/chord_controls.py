"""`ChordRecorder`, the control behind the key-chord field: it draws nothing, records a key press as a chord, and reads a chord that was typed.

It is `widget: ChordRecorder` in `KeyChordField_View.yaml` (see `tess_ui.mind`). The view holds a button that has the keyboard focus while a chord is being recorded and sends each key it
hears as the command `key <name> <modifiers>`; a text field holds the chord as text (`draft`) and sends `typed <text>` when the person commits it. What the control does:

- Not recording, Enter and Space start recording (the view's button also starts it by a press, writing `recording`).
- Recording, a key press that is not a modifier on its own ends the recording with that chord as `value`; Escape alone cancels (`value` as it was) and Backspace alone clears it (an empty `value`); a bare
  modifier (Shift, Control, Alt, Meta, a lock) changes only `preview`, the modifiers held so far (`Ctrl+Shift+`), and does not end it. A key that no chord can have (`print_screen`) says so in `message`
  and the recording goes on.
- A typed text is read with `tess_ui.key_chords.normalise` (any case; `Control+Return` is `Ctrl+Enter`): a chord becomes `value` and `draft` in the canonical form, an empty text clears `value`, and
  anything else leaves `value` as it was and sets `invalid` with a `message`.
- A `value` the view sets is shown as it is, never rewritten: a hand-written `ctrl+shift+f1` stays so until the person edits it. `invalid` is true for one that is not a chord.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tess_ui import key_chords
from tess_ui.mind import Mind
from tess_ui.reactive import Signal

__all__ = ["ChordRecorder"]

_MODIFIER_FLAGS = ("ctrl", "alt", "shift", "meta")


class ChordRecorder(Mind):
    """See the module's note. Made by the view builder for `widget: ChordRecorder`; `values` are the node's properties.

    Two-way: `value`, `draft` (the text of the field) and `recording`. Outputs: `preview`, `invalid`, `message`. Read: `command`."""

    TWO_WAY = ("value", "draft", "recording")

    def __init__(self, window: Any, values: dict[str, Any], *, theme: Any = None, listen: Any = None) -> None:
        super().__init__(window, values, theme=theme, listen=listen)
        self.value = Signal(str(values.get("value") or ""))
        self.draft = Signal(str(values.get("draft") or values.get("value") or ""))
        self.recording = Signal(bool(values.get("recording")))
        self.preview = Signal("")
        self.invalid = Signal(False)
        self.message = Signal("")
        self.start_soon()

    def _follow(self, values: dict[str, Any], edited: Callable[[str], bool]) -> bool:
        changed = False
        if edited("value") and str(values.get("value") or "") != self.value.get():
            self._show(str(values.get("value") or ""))
            changed = True
        if edited("recording") and bool(values.get("recording")) != self.recording.get():
            self.recording.set(bool(values.get("recording")))
            self.preview.set("")
            self.message.set("")
            changed = True
        if edited("draft") and str(values.get("draft") or "") != self.draft.get():
            self.draft.set(str(values.get("draft") or ""))  # typed in the field: nothing is committed until `typed`
        return changed

    def _begin(self, values: dict[str, Any]) -> None:
        self._show(str(values.get("value") or ""))

    def _show(self, value: str) -> None:
        """The view holds `value`: show it as it is. One that is not a chord is `invalid`; the empty one is a shortcut that is not set."""
        self.value.set(value)
        self.draft.set(value)
        bad = value != "" and key_chords.normalise(value) is None
        self.invalid.set(bad)
        self.message.set(f"{value} is not a key chord" if bad else "")

    def _set(self, chord: str) -> None:
        """The person made `chord` (or the empty one): it is the value, written in its canonical form, and the field shows it."""
        self.value.set(chord)
        self.draft.set(chord)
        self.invalid.set(False)
        self.message.set("")
        self._finish(chord)

    def _run(self, word: str, rest: str) -> None:
        if word == "key":
            parts = rest.split(" ")
            self._key(parts[0] if parts[0] else " ", {m: m in parts[1:] for m in _MODIFIER_FLAGS})
        elif word == "typed":
            self._typed(rest)
        elif word == "record":
            self.recording.set(True)
            self.preview.set("")
            self.message.set("")
        elif word == "stop":
            self.recording.set(False)
            self.preview.set("")

    def _key(self, name: str, held: dict[str, bool]) -> None:
        """A key the button heard."""
        bare = not any(held.values())
        if not self.recording.get():
            if bare and name in ("enter", "Enter", " ", "space"):
                self.recording.set(True)
                self.preview.set("")
                self.message.set("")
            return
        if key_chords.is_modifier_key(name):
            now = {m for m, flag in (("Ctrl", held["ctrl"]), ("Alt", held["alt"]), ("Shift", held["shift"]), ("Meta", held["meta"])) if flag}
            now.add(key_chords.modifier_of(name) or "")  # the key itself counts, whether or not the engine sets its flag on its own press
            self.preview.set("".join(f"{m}+" for m in key_chords.MODIFIERS if m in now))
            return
        if name == "escape" and bare:
            self.recording.set(False)
            self.preview.set("")
            self.message.set("")
            return
        if name == "backspace" and bare:
            self.recording.set(False)
            self.preview.set("")
            self._set("")
            return
        chord = key_chords.from_event(name, ctrl=held["ctrl"], alt=held["alt"], shift=held["shift"], meta=held["meta"])
        if chord is None:
            self.message.set(f"{name} cannot be part of a key chord")
            return
        self.recording.set(False)
        self.preview.set("")
        self._set(chord)

    def _typed(self, text: str) -> None:
        """The person has committed `text` in the field."""
        text = text.strip()
        if text == "":
            if self.value.get() != "" or self.invalid.get():
                self._set("")
            return
        chord = key_chords.normalise(text)
        if chord is None:
            self.draft.set(text)
            self.invalid.set(True)
            self.message.set(f"{text} is not a key chord: write the modifiers (Ctrl, Alt, Shift, Meta) and one key, joined by +, such as Ctrl+Shift+F1")
            return
        if chord != self.value.get() or self.invalid.get() or text != chord:
            self._set(chord)

    def _sync(self) -> None:
        """Nothing to derive: the signals are set where they change."""
