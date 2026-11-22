"""Behavior events for a widget (the Tesserae behavior standard, SPEC.md section 4): a state change from input is proposed as a `before_change`
that a listener can veto, then made and reported as a `change`, each with the `reason` that caused it (`pointer`, `keyboard`) and a `detail`
word for the cause inside the widget (`typing`, `clear`, `escape`).

A widget opts in by holding its state in a `GatedSignal`. Nothing changes for code that writes the Signal itself (a host, a test, a ViewModel):
a write that no handler or key is running is `api`, is never asked about and is made at once. A widget with no listener and not `controlled`
pays one attribute check per write.

**Controlled.** A controlled gate never writes the Signal by itself: the change is a request, and the value is written only when a listener
answers `event.accept()`, from its handler, synchronously. An uncontrolled gate writes unless a listener calls `event.cancel()`."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from tess_ui.reactive import Signal, _schedule_notify

__all__ = ["ChangeEvent", "Gate", "GatedSignal", "caused_by", "reason_of"]

REASONS = ("pointer", "keyboard", "api")


@dataclass
class ChangeEvent:
    """A change of a widget's state: `previous` and `value`, why (`reason`) and what for (`detail`). A `before_change` can be answered by its
    listener: `cancel()` (a cancelled change leaves the state as it was), and in a controlled gate `accept()` (the host passes the value)."""

    name: str
    previous: Any
    value: Any
    reason: str
    detail: str
    cancelled: bool = False
    accepted: bool = False

    def cancel(self) -> None:
        self.cancelled = True

    def accept(self) -> None:
        self.accepted = True


@dataclass
class Gate:
    """The listeners of one gated state and whether the host owns the value (`controlled`). `detail_of(source)` names the cause of a change made
    by the handler of the instance `source` (a widget part such as `clear`); it is the widget's own table."""

    controlled: bool = False
    detail_of: Callable[[str], str] = lambda source: source
    before: list[Callable[[ChangeEvent], None]] = field(default_factory=list)
    after: list[Callable[[ChangeEvent], None]] = field(default_factory=list)

    @property
    def active(self) -> bool:
        return self.controlled or bool(self.before) or bool(self.after)


_cause: list[tuple[str, str]] = []


@contextmanager
def caused_by(reason: str, source: str) -> Iterator[None]:
    """While the body runs, a write to a `GatedSignal` is a change `reason` made by `source` (a part of the widget, or a detail word of its own)."""
    _cause.append((reason, source))
    try:
        yield
    finally:
        _cause.pop()


def reason_of(event: str, payload: Any) -> str:
    """The reason of a handler run for `event`: a press that has a button was a pointer's, one without (Enter or Space on a focused control) a
    key's; key and text events are the keyboard's; anything else is `api`."""
    if event in ("on_click", "on_press"):
        return "pointer" if getattr(payload, "button", None) else "keyboard"
    if event in ("on_key", "on_submit", "on_change", "on_input"):
        return "keyboard"
    return "api"


class GatedSignal(Signal):
    """A `Signal` whose writes made while something caused them (a handler, a key) go through its `Gate`."""

    def __init__(self, value: Any, gate: Gate | None = None) -> None:
        super().__init__(value)
        self.gate = gate or Gate()

    def set(self, value: Any) -> None:
        if value == self._value or not _cause or not self.gate.active:
            super().set(value)  # nothing to ask: no change, a write nothing caused (api), or no listener and not controlled
            return
        self._ask(value)

    def _ask(self, value: Any) -> None:
        reason, source = _cause[-1]
        gate = self.gate
        event = ChangeEvent("before_change", self._value, value, reason, gate.detail_of(source))
        for listener in list(gate.before):
            listener(event)
        if event.cancelled or (gate.controlled and not event.accepted):
            _schedule_notify(self)  # the view shows the value it had: a typed character that was refused goes
            return
        previous = self._value
        super().set(value)
        done = ChangeEvent("change", previous, value, reason, event.detail)
        for listener in list(gate.after):
            listener(done)
