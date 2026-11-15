"""The shipped views, called from Python: how a widget factory (`tess_ui.widgets.button()`, ...) is built from `src/tess_ui/views/*_View.tdl`.

A factory describes what it wants as a `Call` tree: a widget (a shipped view such as `Button`, or a built-in such as `Container`), a name, props, style
and children. The tree renders to TDL text that holds only names (`Label: <| label |>`); every value, a number, a string or a `Signal` the factory
keeps hold of, is an attribute of the object the view is composed against, so nothing a caller passes is ever written into TDL (no escaping) and the
text, and so the parsed `ViewDoc`, is the same for every call of the same shape. The result is a `FactoryView`: a `ComposedView` with no ViewModel,
whose root is called what the factory named it, with the stylesheets the shipped views bring.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Optional

from tess_ui import tokens
from tess_ui.composed import ComposedView
from tess_ui.shipped import ViewLibrary
from tess_ui.spec import transition
from tess_ui.spec.compose import Composer
from tess_ui.spec.nodes import ViewDoc, parse_view
from tess_ui.viewmodel import ViewHandle

__all__ = ["Call", "FactoryView", "open_factory_view"]

_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
#: The props whose value is a choice a view reads once (a variant, a size), written into the TDL as itself: a name the view reads in a place that cannot change
#: while it is open (a `Role:`, an `Interaction:`) must not come from the params object, which may hold a Signal.
_LITERAL_KEYS = frozenset({"variant", "size", "orientation", "mode", "shape", "width_kind", "period"})
_HEADER = '---\nTDL: 0.2\nName: Factory\nTesserae: "0.6"\n---\n'
_DOCS: dict[str, tuple[ViewDoc, list[Any]]] = {}
_LIBRARY: list[ViewLibrary] = []


def _title(key: str) -> str:
    """`corner_radius` as TDL writes it: `Corner_Radius`."""
    return "_".join(part.capitalize() for part in key.split("_"))


class Call:
    """One node of what a factory builds: `widget` (a shipped view or a built-in), its `name`, its `props` and `style` (a value of `None` is left out,
    so the view's own default stands), its `children` (`Call`s) and `interaction`, the colour role of its state layer and ripple (the shipped views
    tint them `on_surface`; MD3 tints them in the colour of the content, which the factory knows)."""

    def __init__(self, widget: str, name: Optional[str] = None, props: Optional[Mapping[str, Any]] = None, style: Optional[Mapping[str, Any]] = None,
                 children: Optional[list["Call"]] = None, *, interaction: Optional[str] = None, handlers: Optional[Mapping[str, Any]] = None) -> None:
        self.widget = widget
        self.name = name
        self.props = {key: value for key, value in (props or {}).items() if value is not None}
        self.style = {key: value for key, value in (style or {}).items() if value is not None}
        self.children = list(children or [])
        self.interaction = interaction
        self.handlers = dict(handlers or {})  # a view's handler-type params (`on_toggle`) and the Python functions they call
        for key in (widget, name or "x", interaction or "x", *self.props, *self.style, *self.handlers):
            if not _NAME.match(key):
                raise ValueError(f"a call's names are plain identifiers, got {key!r}")

    def render(self, params: dict[str, Any], path: str = "c", depth: int = 0) -> list[str]:
        """The TDL lines of this call, with its values put in `params` under the names the lines use."""
        pad = "  " * depth
        lines = [f"{pad}{self.widget} {{"]
        if self.name is not None:
            lines.append(f"{pad}  Name: {self.name}")
        if self.interaction is not None:
            lines.append(f"{pad}  Interaction: {self.interaction}")
        for key, value in self.props.items():
            if isinstance(value, bool) or (isinstance(value, str) and key in _LITERAL_KEYS and _NAME.match(value)):
                lines.append(f"{pad}  {_title(key)}: {str(value).lower() if isinstance(value, bool) else value}")  # a choice or a switch the view reads once, as a constant
                continue
            params[attr := f"{path}__{key}"] = value
            lines.append(f"{pad}  {_title(key)}: <| {attr} |>")
        for key, fn in self.handlers.items():  # the action's name is the params object's attribute that holds the function
            params[attr := f"{path}__h_{key}"] = fn
            lines.append(f"{pad}  {_title(key)}: {attr}")
        if self.style:
            lines.append(f"{pad}  Style {{")
            for key, value in self.style.items():
                params[attr := f"{path}__s_{key}"] = value
                lines.append(f"{pad}    {_title(key)}: <| {attr} |>")
            lines.append(f"{pad}  }}")
        if self.children:
            lines.append(f"{pad}  Children {{")
            for index, child in enumerate(self.children):
                lines.extend(child.render(params, f"{path}_{index}", depth + 2))
            lines.append(f"{pad}  }}")
        lines.append(f"{pad}}}")
        return lines


class _Params:
    """What a factory's view is composed against: its values, as attributes."""

    def __init__(self, values: Mapping[str, Any]) -> None:
        self.__dict__.update(values)


class FactoryView(ComposedView):
    """A factory's view. `components` says which theme `components:` entries (as `cascade.component_key` takes them: `fab.small`) the roots of its nodes read,
    by node id: the widget's own root, and the roots of the views it calls. `patch(id, ...)` puts keys on a lowered node (feedback a factory gives a part the
    view does not: they are part of what the view is lowered to, so a sync does not take them off)."""

    def __init__(self, handle: ViewHandle, *, components: Optional[dict[str, str]] = None, **kwargs: Any) -> None:
        self._patches: dict[str, dict[str, Any]] = {node_id: {"component_of": key} for node_id, key in (components or {}).items()}
        self._version = 0
        self._tagged: dict[str, tuple[int, dict[str, Any], list[Any], dict[str, Any]]] = {}  # a node's id -> the version, the lowered node, its children as patched, the result
        self._after_sync: list[Callable[[], None]] = []
        super().__init__(handle, **kwargs)

    def patch(self, node_id: str, **keys: Any) -> None:
        """Gives the lowered node `node_id` these keys from now on, and brings the view up to date."""
        self._patches.setdefault(node_id, {}).update(keys)
        self._version += 1
        self._sync()

    def after_sync(self, fn: Callable[[], None]) -> Callable[[], None]:
        """Calls `fn()` after each time the view has been brought up to date with its values (what a factory puts on the built nodes itself, such as the feedback's
        clip following a part's corners, is put back there). Returns the function that stops it."""
        self._after_sync.append(fn)
        return lambda: self._after_sync.remove(fn) if fn in self._after_sync else None

    def _sync(self) -> None:
        super()._sync()
        for fn in list(self._after_sync):
            fn()

    def _lowered(self) -> tuple[dict[str, Any], dict[str, tuple[bytes, int, int]]]:
        spec, frames = super()._lowered()
        return (self._patched(spec) if self._patches else spec), frames

    def _use_scheme(self, scheme: Any) -> None:
        """A widget is re-coloured for its theme at once (`Widget.set_theme`), whatever its style eases when it changes state."""
        with transition.at_once():
            super()._use_scheme(scheme)

    def _patched(self, node: dict[str, Any]) -> dict[str, Any]:
        """`node` with the patches on the nodes they name. A node that did not change, and nothing under it, is given back as it was
        (the same dict, which `reconcile` goes by)."""
        children = node.get("children") or []
        patched = [self._patched(child) for child in children]
        keys = self._patches.get(node["id"])
        if keys is None and all(a is b for a, b in zip(children, patched, strict=True)):
            return node
        kept = self._tagged.get(node["id"])
        if kept is not None and kept[0] == self._version and kept[1] is node and len(kept[2]) == len(patched) and all(a is b for a, b in zip(kept[2], patched, strict=True)):
            return kept[3]
        result = {**node, **({"children": patched} if children else {}), **(keys or {})}
        self._tagged[node["id"]] = (self._version, node, patched, result)
        return result


def _library() -> ViewLibrary:
    """The shipped views and no others: a project's own `Button_View.tdl` is for its own views, not for a factory's widgets."""
    if not _LIBRARY:
        _LIBRARY.append(ViewLibrary())
    return _LIBRARY[0]


def open_factory_view(call: Call, window: Any, *, root_id: str, components: Optional[dict[str, str]] = None) -> FactoryView:
    """Composes `call` and builds it in `window`; its root is `root_id`, its parts `root_id.<name>`."""
    params: dict[str, Any] = {}
    text = _HEADER + "\n".join(call.render(params)) + "\n"
    library = _library()
    if text not in _DOCS:
        doc = parse_view(text, f"<{call.widget} call>", resolver=library.decl)
        _DOCS[text] = (doc, library.sheets_of(library.used(doc))[0])
    doc, rules = _DOCS[text]
    values = _Params(params)
    composition = Composer(library.doc, values, rules=rules).compose(doc, root_id)
    handle = ViewHandle(None, composition, values, None, doc)
    return FactoryView(handle, components=components, window=window, theme_seed=tokens.BASELINE["primary"])
