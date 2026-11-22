"""Type-ahead: typing the start of an item's name moves to the next item whose name starts with it. One search for the focus groups of a view and
for lists: a pause of `RESET` seconds starts over, and the same letter typed again and again goes on to the next item that starts with it."""

from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Optional

__all__ = ["RESET", "TypeAhead"]

#: A pause this long (seconds) in typing starts a new type-ahead search.
RESET = 1.0


class TypeAhead:
    """What has been typed so far, and the search over a list of names."""

    def __init__(self) -> None:
        self._typed: tuple[str, float] = ("", 0.0)

    def find(self, key: str, current: int, labels: Sequence[str]) -> Optional[int]:
        """The index of the item whose name starts with what has been typed (`key` is the newest letter), searching on from `current`; `None`
        when none does."""
        typed, when = self._typed
        now = time.monotonic()
        text = (typed if now - when < RESET else "") + key.lower()
        self._typed = (text, now)
        names = [label.lower() for label in labels]
        repeated = len(text) > 1 and len(set(text)) == 1
        wanted = text[0] if repeated else text
        start = current + 1 if repeated else current
        for step in range(len(names)):
            index = (start + step) % len(names)
            if names[index].startswith(wanted):
                return index
        return None
