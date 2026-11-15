"""Small helpers shared by tests."""

from collections.abc import Callable, Iterable, Mapping
from typing import Any, Optional

from tess_ui import tokens
from tess_ui.reactive import Signal


def window_unthemed(window) -> bool:
    """Whether `tess_re`'s window has no theme of its own (M42 Phase 7).
    `tess_re` 0.3.5 removes `Window.theme` altogether, which is unthemed too."""
    try:
        theme = window.theme
    except AttributeError:
        return True
    return not theme.is_set()


def elevation(node) -> float:
    """A node's MD3 elevation level. A Tesserae-built node carries it as
    `shadows` (0.3.4 nodes have no `elevation`); a node from one of
    `tess_re`'s legacy factories still has its own `elevation`."""
    shadows = node.get("shadows")
    if not shadows:
        try:  # a legacy node's own level, while `tess_re` 0.3.4 has one
            return node.get("elevation")
        except (AttributeError, ValueError):  # 0.3.5 has no `elevation` (its shim raised AttributeError,
            return 0.0                         # the release ValueError); no shadows is level 0
    for level in range(6):
        if shadows == tokens.elevation_shadows(level):
            return float(level)
    raise AssertionError(f"shadows {shadows!r} aren't an MD3 elevation level")


def view_from(spec, **kwargs):
    """A Tesserae `View` built from a kind-tree (the form the Python widget factories' hand-built widgets use), or from
    a view's TDL text (it starts with the `---` metadata block)."""
    from tess_ui import View

    if isinstance(spec, str):
        from tess_ui.spec.tdl import load_marked_tdl
        from tess_ui.spec.tdl_theme import plain

        spec = plain(load_marked_tdl(spec, "T_View.tdl"))
    return View(spec, **kwargs)


class MapScope:
    """A scope over a dict, for tests of expressions and handlers. `reactive` names read as reactive, `writable` names can be assigned in a handler,
    `actions` maps a dotted name (`window.close`, `save`) to a function a handler may call."""

    def __init__(self, values: Optional[Mapping[str, Any]] = None, *, reactive: Iterable[str] = (), writable: Iterable[str] = (),
                 actions: Optional[Mapping[str, Callable[..., Any]]] = None) -> None:
        self.values = dict(values or {})
        self.reactive = set(reactive)
        self.writable = set(writable)
        self.actions = dict(actions or {})

    def lookup(self, name: str) -> Any:
        return self.values[name]

    def names(self) -> list[str]:
        return list(self.values)

    def is_reactive(self, name: str) -> bool:
        return name in self.reactive

    def assign(self, name: str, value: Any) -> None:
        if name not in self.writable:
            raise KeyError(name)
        current = self.values.get(name)
        if isinstance(current, Signal):
            current.set(value)
        else:
            self.values[name] = value

    def is_action(self, path: str) -> bool:
        return path in self.actions

    def call_action(self, path: str, args: list[Any], kwargs: dict[str, Any]) -> Any:
        return self.actions[path](*args, **kwargs)
