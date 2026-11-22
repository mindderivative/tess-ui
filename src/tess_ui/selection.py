"""What the engine's container selection leaves unsaid: which input made a change. The engine says `selection_source` (`pointer`, `keyboard`, `api`);
the Selection pattern (the behavior standard's SPEC 2.5b) names the change too: `select`, `toggle`, `range`, `all` or `clear`. A container's listeners
note the last pointer press or key, which run before the engine acts on it, and `detail` reads the change against it."""

from __future__ import annotations

from typing import Any


class InputNote:
    """The last pointer press or key a container with a `selection_mode` saw."""

    def __init__(self) -> None:
        self.kind: str | None = None
        self.event: Any = None

    def pointer(self, event: Any) -> None:
        self.kind, self.event = "pointer", event

    def key(self, event: Any) -> None:
        self.kind, self.event = "key", event

    @property
    def plain_press(self) -> bool:
        """The last input was a pointer press with no Ctrl, Shift or Meta (it chooses only the row pressed)."""
        return self.kind == "pointer" and not any(getattr(self.event, name, False) for name in ("ctrl", "shift", "meta"))

    def detail(self, source: str | None, now_empty: bool, container: Any) -> str:
        """The name of the change just made: `select` for a write from code and for anything not named below."""
        if source == "api" or self.kind is None:
            return "select"
        ctrl, shift = bool(getattr(self.event, "ctrl", False)), bool(getattr(self.event, "shift", False))
        if self.kind == "pointer":
            if shift:
                return "range"
            if ctrl:
                return "toggle"
            return "clear" if now_empty and getattr(self.event, "target", None) == container else "select"
        key = getattr(self.event, "key", "")
        if key == "space":
            return "toggle"
        if ctrl and key == "a":
            return "all"
        return "range" if shift and key in ("arrow_down", "arrow_up", "home", "end") else "select"
