"""Density on every node: the cascade (ADR-0029, "Density on every element").

A node may say `Density: compact` (`default`, `compact` or `dense`), and so may a stylesheet rule. A node that says nothing takes the density of
its nearest ancestor that says one, and at the top the application's (`App(density=)`; `""` there is the components' own Material sizes).
Order of resolution for one node: its own `Density` key, then the `Density` of the stylesheet rules that match it (a more specific or later rule
over a less specific one), then its parent's resolved density, then the application's. A number written on the node (`Height: 50`) is
not part of this: a node's inline style lies over what its stylesheet rules give, and the density only reaches a size through those rules.

Expressions read the result as the name `density` (a string: `""`, `default`, `compact` or `dense`), where they used to call `app_density()`.
"""

from __future__ import annotations

from typing import Any, Optional

from tess_ui import tel
from tess_ui.reactive import Computed, Signal, untrack

LEVELS = ("default", "compact", "dense")


def check_level(value: Any) -> Optional[str]:
    """A problem with a written density, or `None`: it is one of the three levels, in lower case."""
    if isinstance(value, str) and value in LEVELS:
        return None
    return f"density is one of {', '.join(LEVELS)}, got {value!r}"


class DensityNode:
    """One node's density: what it says itself, what its stylesheet rules say, and the resolved value, which follows the parent's.
    `resolved` is a `Computed`, so an expression that reads `density` follows a change of any of them."""

    def __init__(self, own: Optional[str] = None) -> None:
        self.own = Signal(own or None)
        #: the `Computed` of the density the stylesheet rules that match this node give (`None` while it has none)
        self.ruled_source: Signal = Signal(None)
        self.parent: Signal = Signal(None)
        self.resolved: Computed = Computed(self._resolve)

    def _resolve(self) -> str:
        source = self.ruled_source.get()
        level = self.own.get() or (source.get() if source is not None else None)
        if level:
            return str(level)
        parent: Optional[DensityNode] = self.parent.get()
        return parent.resolved.get() if parent is not None else str(tel._app_density.get())

    def attach(self, parent: Optional["DensityNode"]) -> None:
        """Make `parent` the node whose density this one takes when it says none."""
        if untrack(self.parent.get) is not parent:
            self.parent.set(parent)
