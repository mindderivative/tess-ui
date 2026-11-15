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
                 children: Optional[list["Call"]] = None, *, interaction: Optional[str] = None) -> None:
        self.widget = widget
        self.name = name
        self.props = {key: value for key, value in (props or {}).items() if value is not None}
        self.style = {key: value for key, value in (style or {}).items() if value is not None}
        self.children = list(children or [])
        self.interaction = interaction
        for key in (widget, name or "x", interaction or "x", *self.props, *self.style):
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
            params[attr := f"{path}__{key}"] = value
            lines.append(f"{pad}  {_title(key)}: <| {attr} |>")
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
    by node id: the widget's own root, and the roots of the views it calls."""

    def __init__(self, handle: ViewHandle, *, components: Optional[dict[str, str]] = None, **kwargs: Any) -> None:
        self._components = dict(components or {})
        self._tagged: dict[str, tuple[dict[str, Any], list[Any], dict[str, Any]]] = {}  # a node's id -> the lowered node, its children as tagged, the result
        self._after_sync: list[Callable[[], None]] = []
        super().__init__(handle, **kwargs)

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
        return (self._tag(spec) if self._components else spec), frames

    def _use_scheme(self, scheme: Any) -> None:
        """A widget is re-coloured for its theme at once (`Widget.set_theme`), whatever its style eases when it changes state."""
        with transition.at_once():
            super()._use_scheme(scheme)

    def _tag(self, node: dict[str, Any]) -> dict[str, Any]:
        """`node` with `component_of` on the nodes `components` names. A node that did not change, and nothing under it, is given back as it was
        (the same dict, which `reconcile` goes by)."""
        children = node.get("children") or []
        tagged = [self._tag(child) for child in children]
        key = self._components.get(node["id"])
        if key is None and all(a is b for a, b in zip(children, tagged)):
            return node
        kept = self._tagged.get(node["id"])
        if kept is not None and kept[0] is node and len(kept[1]) == len(tagged) and all(a is b for a, b in zip(kept[1], tagged)):
            return kept[2]
        result = {**node, **({"children": tagged} if children else {}), **({"component_of": key} if key is not None else {})}
        self._tagged[node["id"]] = (node, tagged, result)
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
