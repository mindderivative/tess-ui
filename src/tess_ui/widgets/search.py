"""Tesserae's own namespace for the Search category -- `search_bar` and
`search_view` (an overlay), built by Tesserae."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from tess_ui.reactive import Effect, Signal
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
    disabled: bool = False,
    clear_label: str = "Clear",
    theme: "Theme | None" = None,
) -> Widget:
    """MD3's search bar: a 56 px
    `surface_container_high` pill with elevation, a leading icon
    (`on_surface`), a `body_large` field whose `placeholder` is hint text
    in `on_surface_variant`, and trailing icon buttons
    (`on_surface_variant`). `.query` is a `Signal` of what's typed;
    `.on_query(fn)` hears each change. Parts: `field` (the `text_input`),
    `leading`, `trailing0`, ... `disabled` dims it, makes the field read-only
    and hides the clear button; `clear_label` names that button for assistive
    technology."""
    query = Signal("")
    call = Call("SearchBar", props={"placeholder": placeholder, "query": query, "leading_icon": leading_icon or "",
                                    "trailing_icons": list(trailing_icons or []), "disabled": disabled,
                                    "clear_label": clear_label},
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
    held: Any = widget  # the widget the view registers itself on: `search_view(bar=...)` sets `search_view`
    held.search_view = None

    def escape(event: Any) -> None:
        """Escape: with the view open it closes and the query stays; otherwise a typed query clears (Search, Keyboard)."""
        if event.key != "escape":
            return
        shown = held.search_view
        if shown is not None and shown.is_open:
            shown.close()
        elif query.get():
            query.set("")

    widget._undo.append(widget.view._listen(field, "key_down", escape))
    typed_before = [""]

    def recover() -> None:
        """Focus recovery: the clear button goes when the query empties, and if it held the focus the field takes it (a press on it, by pointer or
        keyboard, or the query emptied some other way): focus is not lost to the window (AC-SRB-4)."""
        text, before = query.get(), typed_before[0]
        typed_before[0] = text
        if text or not before:
            return
        try:
            clear = widget.part("clear")
        except ValueError:
            return
        if clear.get("focused"):
            field.focus()

    widget._undo.append(Effect(recover).dispose)
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
