"""Tesserae's own namespace for the Search category -- `search_bar` and
`search_view` (an overlay), built by Tesserae."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from tess_ui.reactive import Signal
from tess_ui.widgets._composed import Widget
from tess_ui.widgets._views import Call
from tess_ui.widgets.buttons import _border

if TYPE_CHECKING:
    from tess_ui.overlays import SearchView
    from tess_ui.theme import Theme
    from tess_re import Window


def search_bar(
    window: "Window",
    placeholder: str,
    width: float,
    leading_icon: str | None = "search",
    trailing_icons: list[str] | None = None,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> Widget:
    """MD3's search bar: a 56 px
    `surface_container_high` pill with elevation, a leading icon
    (`on_surface`), a `body_large` field whose `placeholder` is hint text
    in `on_surface_variant`, and trailing icon buttons
    (`on_surface_variant`). `.query` is a `Signal` of what's typed;
    `.on_query(fn)` hears each change. Parts: `field` (the `text_input`),
    `leading`, `trailing0`, ..."""
    query = Signal("")
    call = Call("SearchBar", props={"placeholder": placeholder, "query": query, "leading_icon": leading_icon or "",
                                    "trailing_icons": list(trailing_icons or [])},
                style={"width": width, **_border(border_color, border_width)})
    parts = {"field": "input", "leading.icon": "leading.leading_glyph"}
    for i in range(len(trailing_icons or [])):
        parts[f"trailing{i}"] = f"trailing_item[{i}]"
        parts[f"trailing{i}.icon"] = f"trailing_item[{i}].trailing_item_glyph"
    widget = Widget(window, call=call, components={None: "search_bar"}, parts=parts, theme=theme, x=x, y=y, name="search_bar")
    for i in range(len(trailing_icons or [])):
        widget.part(f"trailing{i}").set(focusable=True, cursor="pointer")
    widget.query = query  # the view's own `query`: what is typed in the field
    field = widget.part("field")
    queries: list[Callable[[str], Any]] = []

    def typed(event: Any) -> None:
        text = field.get("text") or ""
        for fn in list(queries):
            fn(text)

    widget._undo.append(widget.view._listen(field, "change", typed))
    widget.on_query = lambda fn: (queries.append(fn), lambda: queries.remove(fn) if fn in queries else None)[1]
    return widget


def search_view(
    window: "Window",
    width: float,
    height: float,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    bar: Widget | None = None,
    results: list[tuple[str, Optional[Callable[[], Any]]]] | None = None,
    theme: "Theme | None" = None,
) -> "SearchView":
    """MD3's docked search view (`tess_ui.overlays.SearchView`): the
    results panel under a `search_bar`, `height` its most. Give it the
    `bar` and it opens and closes with it; `set_results([(text, fn)])`."""
    from tess_ui.overlays import SearchView

    view = SearchView(window, bar=bar, width=width, max_height=height, results=results, theme=theme)
    if border_color is not None or border_width is not None:
        view.node.set(**({"stroke_color": tuple(border_color)} if border_color else {}),
                      **({"stroke_width": float(border_width)} if border_width is not None else {}))
    return view
