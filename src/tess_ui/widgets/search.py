"""Tesserae's own namespace for the Search category -- `search_bar` and
`search_view` (an overlay), built by Tesserae."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from tess_ui.behavior import Gate, GatedSignal, caused_by, current
from tess_ui.reactive import Effect, Signal
from tess_ui.widgets._composed import Widget
from tess_ui.widgets._views import Call
from tess_ui.widgets.buttons import _border

if TYPE_CHECKING:
    from tess_ui.overlays import SearchView
    from tess_ui.theme import Theme
    from tess_re import Window


#: What a change of the query is called, by the part that made it (the behavior standard's `detail`).
_DETAILS = {"input": "typing", "clear": "clear", "escape": "escape"}


def _inside(root: Any, node: Any) -> bool:
    """Whether `node` is `root` or below it."""
    while node is not None:
        if node == root:
            return True
        node = node.parent()
    return False


def _hear(listeners: list[Callable[[Any], None]], fn: Callable[[Any], None]) -> Callable[[], None]:
    """Adds `fn` to `listeners`; returns the function that removes it."""
    listeners.append(fn)
    return lambda: listeners.remove(fn) if fn in listeners else None


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
    controlled: bool = False,
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
    technology. `.active` is a `Signal`: the bar was pressed or typed in, until its back arrow or a third Escape (the first closes the open view, the
    second clears the query, the third deactivates the bar and gives the focus back to the control that had it). `.on_before_change(fn)` and `.on_change(fn)` hear each change of the query a user makes (`event.previous`, `.value`, `.reason`
    `pointer` or `keyboard`, `.detail` `typing`, `clear` or `escape`); `event.cancel()` in the first refuses it. With `controlled` the widget
    never writes the query itself: a change is a request, and it is made only when a `before_change` listener calls `event.accept()`; the host
    writes `.query` itself for anything else (an `api` change, never asked about)."""
    gate = Gate(controlled=controlled, detail_of=lambda source: _DETAILS.get(source.rsplit(".", 1)[-1], source))
    query = GatedSignal("", gate)
    active = Signal(False)  # the view's own `active`: pressed or typed in, until the back arrow or the third Escape
    call = Call("SearchBar", props={"placeholder": placeholder, "query": query, "leading_icon": leading_icon or "",
                                    "trailing_icons": list(trailing_icons or []), "disabled": disabled,
                                    "clear_label": clear_label, "active": active},
                style={"width": width, **_border(border_color, border_width)})
    parts = {"field": "input", "leading.icon": "leading.leading_glyph"}
    for i in range(len(trailing_icons or [])):
        parts[f"trailing{i}"] = f"trailing_item[{i}]"
        parts[f"trailing{i}.icon"] = f"trailing_item[{i}].trailing_item_glyph"
    widget = Widget(window, call=call, components={None: "search_bar"}, parts=parts, theme=theme, x=x, y=y, name="search_bar")
    for i in range(len(trailing_icons or [])):
        widget.part(f"trailing{i}").set(focusable=True, cursor="pointer")
    widget_any: Any = widget
    widget_any.on_before_change = lambda fn: _hear(gate.before, fn)
    widget_any.on_change = lambda fn: _hear(gate.after, fn)
    widget.active = active  # type: ignore[attr-defined]
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
            with caused_by("keyboard", "escape"):
                query.set("")
        else:  # nothing left to close or clear: the bar is deactivated and focus goes back to where it was (AC-SRB-5)
            active.set(False)
            back = came_from[0]
            if back is not None:
                back.focus()

    came_from: list[Any] = [None]  # the control that had the focus before the field took it

    def took_focus(event: Any) -> None:
        before = getattr(event, "related_target", None)
        if before is not None and before != field and not _inside(widget.node, before):
            came_from[0] = before

    widget._undo.append(widget.view._listen(field, "focus", took_focus))

    widget._undo.append(widget.view._listen(field, "key_down", escape))
    typed_before = [""]

    def recover() -> None:
        """The clear button goes when the query empties, and it does not hold the focus (a press on it does not take it): the field takes the focus
        after a press on it, by pointer or keyboard, so it is not lost (AC-SRB-4, Press Focus: input)."""
        text, before = query.get(), typed_before[0]
        typed_before[0] = text
        cause = current()
        if not text and before and cause is not None and cause[1].rsplit(".", 1)[-1] == "clear":
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
