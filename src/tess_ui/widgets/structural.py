"""Tesserae's own namespace for the Cards, Lists, Chips & Structural Rows
category -- `card`, `list_`, `list_item`, `chip`, `badge`, `divider`,
`link`, `accordion_header`, `tree_node` -- built by Tesserae from their
fragments. `list_` (trailing underscore) avoids shadowing the
builtin `list`.
"""

from __future__ import annotations

import math
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Callable

from tess_ui import a11y
from tess_ui.behavior import ChangeEvent, Gate, GatedSignal, caused_by
from tess_ui.reactive import Effect, Signal
from tess_ui.typeahead import TypeAhead
from tess_ui.widgets._composed import Widget
from tess_ui.widgets._views import Call
from tess_ui.widgets.buttons import _border, _hex, _variant

if TYPE_CHECKING:
    from tess_ui.theme import Theme
    from tess_re import Window


_CARDS = {"elevated": "elevated", "filled": "filled", "outlined": "outlined"}


def card(
    window: "Window",
    width: float,
    height: float,
    variant: str = "elevated",
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
) -> Widget:
    """MD3's card: elevated, filled or
    outlined. Content-free: add to `.node`. `on_click` makes it an
    actionable card, with MD3's feedback."""
    call = Call("Card", props={"variant": _variant("card", variant, _CARDS), "bare": True, "actionable": on_click is not None},
                style={"width": width, "height": height, **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: f"card.{variant}"}, theme=theme, x=x, y=y, name="card")
    if on_click is not None:
        widget.on_click(on_click)
    return widget


def list_(
    window: "Window",
    items: list[Any],
    width: float = 360.0,
    x: float | None = None,
    y: float | None = None,
    *,
    theme: "Theme | None" = None,
    selectable: str | None = None,
    selected: int | list[int] | None = None,
    announce: str | None = "{count} selected",
) -> Widget:
    """Lays out `list_item(...)`s (or any nodes) as MD3's list: a column
    `width` wide. The items move into it. An empty list is an error, as
    `tess_re`'s was.

    With `selectable="single"` the list is a listbox of options: one Tab
    stop for the list (the selected row, else the first), the arrows, Home
    and End move between rows, and a click, Enter or Space selects one.
    `.selected` is a `GatedSignal` of the selected row's index (or `None`),
    which `selected` starts at: the rows should be `list_item`s, which show
    the selection. `.on_before_change(fn)` and `.on_change(fn)` hear a
    user's selection (`reason` `pointer` or `keyboard`, `detail`
    `select`), and `event.cancel()` refuses it.

    With `selectable="multiple"` the engine's container selection does it:
    click chooses one, Ctrl+click toggles, Shift+click and Shift+Arrow
    choose a range from the anchor, Space toggles, Ctrl+A chooses all; the arrows, Home and End move
    the focus between the rows. `.selection`
    is a `Signal` of the chosen rows' indices, ascending (a tuple; write it to
    choose rows from code), `selected=` starts it with a list, and `announce`
    is what assistive technology reads as it changes (`{count}` is how many;
    `None` is silent). Only `.on_change(fn)` hears it (`reason` `pointer`,
    `keyboard` or `api`; `detail` `select`, `toggle` (Ctrl+click, Space), `range` (Shift), `all` (Ctrl+A) or `clear` (a click on the empty part), as the Selection pattern names them): the engine makes the change, so
    there is nothing to refuse beforehand."""
    if not items:
        raise ValueError("a list needs at least one item")
    if selectable not in (None, "single", "multiple"):
        raise ValueError(f"list_: selectable is None, 'single' or 'multiple', got {selectable!r}")
    widget = Widget(window, spec={"id": "list", "kind": "Container",
                                  "style": {"width": width, "flex_direction": "vertical"}},
                    theme=theme, x=x, y=y, name="list")
    a11y.describe(widget.node, role="listbox" if selectable else "list")
    nodes = []
    for item in items:
        node = getattr(item, "node", item)
        node.set(width=float(width))
        widget.node.add_child(node)
        action = getattr(getattr(item, "actionable", None), "get", lambda: False)()
        if selectable or not action:  # a plain list's row that has an action stays the button it is
            a11y.describe(node, role="option" if selectable else "listitem")
        nodes.append(node)
    if selectable == "multiple":
        _multiple(widget, items, nodes, selected if isinstance(selected, list) else [] if selected is None else [selected], announce)
    elif selectable:
        _selectable(widget, items, nodes, selected if not isinstance(selected, list) else (selected[0] if selected else None))
    return widget


def _hear(listeners: list[Callable[[Any], None]], fn: Callable[[Any], None]) -> Callable[[], None]:
    """Adds `fn` to `listeners`; returns the function that removes it."""
    listeners.append(fn)
    return lambda: listeners.remove(fn) if fn in listeners else None


def _multiple(widget: Widget, items: list[Any], nodes: list[Any], start: list[int], announce: str | None) -> None:
    """The multiple-selection list: the engine's container selection chooses (clicks, Shift, Ctrl, Space, Ctrl+A); this styles the rows, keeps
    `.selection` in step both ways, keeps the roving Tab stop and the type-ahead."""
    box = widget.node
    box.set(selection_mode="multiple", select_all_key=True)
    if announce is not None:
        box.set(selection_announce=announce)
    gate = Gate(detail_of=lambda source: "select")
    chosen = Signal(tuple(sorted({i for i in start if 0 <= i < len(nodes)})))
    active = [chosen.get()[0] if chosen.get() else 0]
    heard = [chosen.get()]  # the last set `on_change` was told of
    index_of = {node: i for i, node in enumerate(nodes)}

    def reassert() -> None:
        for node in nodes:
            with suppress(ValueError, RuntimeError):  # the list may have been taken down before this ran
                a11y.describe(node, role="option")

    def show() -> None:
        picked = set(chosen.get())
        for i, (item, node) in enumerate(zip(items, nodes)):
            if hasattr(item, "selected"):
                item.selected.set(i in picked)
            a11y.describe(node, role="option", **({} if hasattr(item, "pickable") else {"selected": i in picked}))
            node.set(tab_index=0 if i == active[0] else -1)
        # a row's own view patches its role back to listitem when its state changes, in the same wave: say option again once it has
        widget.window.after(0, reassert)

    def push(indices: tuple[int, ...]) -> None:
        """Signal -> engine, when they differ (a write from code)."""
        if tuple(index_of[node] for node in box.get("selection")) != indices:
            box.set(selection=[nodes[i] for i in indices])

    last: list[Any] = [None]  # the input the engine is about to act on: (what, event), set by the box's listeners, which run before the engine's own handling

    def pointed(event: Any) -> None:
        last[0] = ("pointer", event)

    def detail_of(event: Any, now: tuple[int, ...]) -> str:
        """What the standard calls the change (Selection, SPEC 2.5b): select, toggle, range, all or clear."""
        source = getattr(event, "selection_source", None)
        kind, trigger = last[0] or (None, None)
        if source == "api" or kind is None:
            return "select"
        ctrl, shift = bool(getattr(trigger, "ctrl", False)), bool(getattr(trigger, "shift", False))
        if kind == "pointer":
            if shift:
                return "range"
            if ctrl:
                return "toggle"
            return "clear" if not now and getattr(trigger, "target", None) == box else "select"
        key = getattr(trigger, "key", "")
        if key == "space":
            return "toggle"
        if ctrl and key == "a":
            return "all"
        return "range" if shift and key in ("arrow_down", "arrow_up", "home", "end") else "select"

    def changed(event: Any) -> None:
        """Engine -> Signal: the chosen rows, and who made the change."""
        previous = heard[0]
        now = tuple(sorted(index_of[node] for node in box.get("selection")))
        if now == previous:
            return
        heard[0] = now
        chosen.set(now)
        if gate.after:
            done = ChangeEvent("change", previous, now, getattr(event, "selection_source", None) or "api", detail_of(event, now))
            for listener in list(gate.after):
                listener(done)

    def rove(i: int) -> Callable[[Any], None]:
        def moved(event: Any) -> None:
            active[0] = i
            for j, node in enumerate(nodes):
                node.set(tab_index=0 if j == i else -1)
        return moved

    ahead = TypeAhead()
    labels = [str(node.get("label") or "") for node in nodes]

    def typed(event: Any) -> None:
        """Type-ahead, heard on the list itself: a listener on a row would keep the row's keys from the engine's selection."""
        last[0] = ("key", event)
        i = index_of.get(event.target)
        target = {"arrow_down": min((i or 0) + 1, len(nodes) - 1), "arrow_up": max((i or 0) - 1, 0), "home": 0, "end": len(nodes) - 1}.get(event.key)
        if i is not None and target is not None:  # the container has no arrow-key focus of its own: move it (Shift: after the engine's range, which starts from the row that had it)
            if target != i:
                widget.window.after(0, nodes[target].focus) if getattr(event, "shift", False) else nodes[target].focus()
            return
        if i is not None and len(event.key) == 1 and event.key.isprintable() and event.key != " " and not (getattr(event, "ctrl", False) or getattr(event, "meta", False)):
            found = ahead.find(event.key, i, labels)
            if found is not None and found != i:
                nodes[found].focus()

    for i, node in enumerate(nodes):
        if hasattr(items[i], "actionable"):
            items[i].actionable.set(True)
        if hasattr(items[i], "pickable"):
            items[i].pickable.set(True)  # the row tells assistive technology whether it is selected
        node.set(focusable=True, item_selectable=True)
        widget._undo.append(widget.view._listen(node, "focus", rove(i)))
    widget._undo.append(widget.view._listen(box, "key_down", typed))
    widget._undo.append(widget.view._listen(box, "pointer_down", pointed))
    widget._undo.append(widget.view._listen(box, "selection_change", changed))
    box.set(selection=[nodes[i] for i in chosen.get()])
    widget_any: Any = widget
    widget_any.selection = chosen
    widget_any.on_change = lambda fn: _hear(gate.after, fn)
    widget._undo.append(Effect(lambda: push(chosen.get())).dispose)
    widget._undo.append(Effect(show).dispose)


def _selectable(widget: Widget, items: list[Any], nodes: list[Any], start: int | None) -> None:
    """The single-selection list: selection in a `GatedSignal`, the roving Tab stop, the keys."""
    gate = Gate(detail_of=lambda source: "select")
    chosen = GatedSignal(start if start is not None and 0 <= start < len(nodes) else None, gate)
    active = [chosen.get() or 0]  # the row that holds the Tab stop

    def show() -> None:
        index = chosen.get()
        for i, (item, node) in enumerate(zip(items, nodes)):
            if hasattr(item, "selected"):
                item.selected.set(i == index)  # the row's own look (secondary container)
            a11y.describe(node, role="option", selected=(i == index))  # after the row's own view patched it back to listitem
            node.set(tab_index=0 if i == active[0] else -1)

    def pick(i: int, reason: str) -> None:
        with caused_by(reason, "select"):
            chosen.set(i)
        active[0] = i
        show()

    def rove(i: int) -> Callable[[Any], None]:
        def moved(event: Any) -> None:
            active[0] = i
            for j, node in enumerate(nodes):
                node.set(tab_index=0 if j == i else -1)
        return moved

    ahead = TypeAhead()
    labels = [str(node.get("label") or "") for node in nodes]  # the rows' names (a `list_item`'s headline)

    def key(i: int) -> Callable[[Any], None]:
        def pressed(event: Any) -> None:
            target = {"arrow_down": min(i + 1, len(nodes) - 1), "arrow_up": max(i - 1, 0), "home": 0, "end": len(nodes) - 1}.get(event.key)
            if target is not None and target != i:
                nodes[target].focus()
            elif event.key in ("enter", "space"):
                pick(i, "keyboard")
            elif target is None and len(event.key) == 1 and event.key.isprintable() and event.key != " ":
                found = ahead.find(event.key, i, labels)  # type-ahead: the next row whose name starts with what was typed (the focus groups' search)
                if found is not None and found != i:
                    nodes[found].focus()
        return pressed

    def clicked(i: int) -> Callable[[Any], None]:
        return lambda event: pick(i, "pointer" if getattr(event, "button", None) else "keyboard")  # no button: Enter or Space activated it

    for i, node in enumerate(nodes):
        if hasattr(items[i], "actionable"):
            items[i].actionable.set(True)  # a selectable list's rows are what the user picks
        node.set(focusable=True)
        widget._undo.append(widget.view._listen(node, "focus", rove(i)))
        widget._undo.append(widget.view._listen(node, "key_down", key(i)))
        widget._undo.append(widget.view._listen(node, "click", clicked(i)))
    widget.selected = chosen  # type: ignore[attr-defined]
    widget_any: Any = widget
    widget_any.on_before_change = lambda fn: _hear(gate.before, fn)
    widget_any.on_change = lambda fn: _hear(gate.after, fn)
    widget._undo.append(Effect(show).dispose)


def list_item(
    window: "Window",
    headline: str,
    leading_icon: str | None = None,
    trailing_icon: str | None = None,
    supporting_text: str | None = None,
    width: float = 360.0,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
    selected: bool = False,
) -> Widget:
    """One MD3 list row: a `body_large`
    headline, 56 px tall, or 72 with `supporting_text` (`body_medium`,
    `on_surface_variant`) under it; 24 px `on_surface_variant` icons either
    side. Parts: `headline`, `supporting`, `leading`, `trailing`. `.selected`
    is a `Signal`: while true the row is a secondary container (`list_`
    drives it in a selectable list)."""
    selected_signal = Signal(bool(selected))
    pickable_signal = Signal(False)
    actionable_signal = Signal(on_click is not None)  # a row that does something is a Tab stop; one that only shows something is not
    call = Call("ListItem", props={"headline": headline, "supporting": supporting_text, "leading_icon": leading_icon, "trailing_icon": trailing_icon,
                                   "selected": selected_signal, "actionable": actionable_signal, "pickable": pickable_signal},
                style={"width": width, **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: "list_item"},
                    parts={"headline": "text.headline", "supporting": "text.supporting", "leading": "leading_icon", "trailing": "trailing_icon"},
                    theme=theme, x=x, y=y, name="list_item")
    widget.selected = selected_signal  # type: ignore[attr-defined]
    widget.actionable = actionable_signal  # type: ignore[attr-defined]
    widget.pickable = pickable_signal  # type: ignore[attr-defined]
    if on_click is not None:
        widget.on_click(on_click)
    return widget


def _icon_spec(node_id: str, name: str, size: float = 24.0, foreground: str = "on_surface_variant") -> dict[str, Any]:
    return {"id": node_id, "kind": "Icon", "icon": {"name": name},
            "style": {"width": size, "height": size, "foreground": foreground}}


_CHIPS = {"assist": "assist", "filter": "filter", "input": "input", "suggestion": "suggestion"}


def chip(
    window: "Window",
    label: str,
    width: float,
    variant: str = "assist",
    icon: str | None = None,
    selected: bool = False,
    removable: bool = False,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
    on_remove: Callable[[], Any] | None = None,
) -> Widget:
    """MD3's chip: assist, filter, input or
    suggestion, 32 px tall, with an optional leading `icon`.

    A filter chip toggles when clicked: `.selected` is a `Signal`, and
    selected it's `secondary_container` with a check and no border. An
    input chip with `removable=True` has a trailing close button that calls
    `on_remove`. The chip itself is a button (a filter chip a checkbox)."""
    shipped = _variant("chip", variant, _CHIPS)
    selected_signal = Signal(bool(selected))
    # the state layer is the label's colour (the shipped sheet's): `on_surface_variant` on a filter or input chip, `on_surface` on the others
    call = Call("Chip", props={"label": label, "variant": shipped, "icon": icon, "selected": selected_signal, "removable": removable or None},
                interaction="on_surface_variant" if variant in ("filter", "input") else "on_surface",
                style={"width": width, "align_content": "left", **_border(border_color, border_width)})  # a width of the caller's: the content starts at the left padding
    widget = Widget(window, call=call, components={None: f"chip.{variant}"},
                    parts={"check": "icon", "remove": "close", "remove.icon": "close.close_icon"}, theme=theme, x=x, y=y, name="chip")
    widget.selected = selected_signal  # the view's own `selected`: a filter chip flips it when pressed
    if variant == "filter":
        widget.on_click(lambda: None, role="checkbox")  # focusable, and a checkbox to a screen reader; the view does the toggling
    if on_click is not None:
        widget.on_click(on_click, role="checkbox" if variant == "filter" else "button")
    if removable:
        a11y.describe(widget.part("remove"), label=f"Remove {label}")
        widget.on_click(on_remove or (lambda: None), part="remove")
    return widget


def badge(
    window: "Window",
    label: str | None = None,
    width: float | None = None,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> Widget:
    """MD3's badge: a 6 px `error` dot when
    `label=None`, otherwise a 16 px pill with a `label_small` `on_error`
    label (`width` defaults to fit it)."""
    call = Call("Badge", props={"value": "" if label is None else label, "flat": True},
                style={"width": width, **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: "badge.dot" if label is None else "badge.labeled"}, parts={"label": "flat_label"},
                    theme=theme, x=x, y=y, name="badge")
    return widget


def divider(
    window: "Window",
    length: float,
    orientation: str = "horizontal",
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> Widget:
    """MD3's divider: a 1 px `outline_variant`
    line `length` long. `border_color`/`border_width` recolour or thicken it."""
    if orientation not in ("horizontal", "vertical"):
        raise ValueError(f"a divider's orientation is 'horizontal' or 'vertical', got {orientation!r}")
    thickness = float(border_width) if border_width is not None else 1.0
    size = (length, thickness) if orientation == "horizontal" else (thickness, length)

    call = Call("Divider", props={"orientation": orientation, "thickness": thickness},
                style={"width": size[0], "height": size[1], "background": None if border_color is None else _hex(border_color)})
    widget = Widget(window, call=call, components={None: "divider"}, theme=theme, x=x, y=y, name="divider")
    a11y.describe(widget.node, hidden=True)
    return widget


def link(
    window: "Window",
    content: str,
    width: float,
    x: float | None = None,
    y: float | None = None,
    *,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
) -> Widget:
    """A link: `body_large` text in
    `primary`, `role="link"`, a Tab stop that Enter follows (`on_click`)."""
    call = Call("Link", props={"text": content, "typography_role": "body_large", "wrap": "none", "overflow": "ellipsis"},
                style={"width": width, "height": 24, "foreground": "primary"})
    widget = Widget(window, call=call, components={None: "link"}, theme=theme, x=x, y=y, name="link")
    if on_click is not None:
        widget.on_click(on_click, role="link")
    return widget


def text(
    window: "Window",
    content: str,
    typography_role: str = "body_medium",
    color: str = "on_surface",
    width: float | None = None,
    x: float | None = None,
    y: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> Widget:
    """Plain text in a type role and a colour of the theme: `color` is a colour role (`on_surface` by default)
    or any colour string. `.content` is a `Signal`; setting it re-measures
    the text in its resolved font, keeping `width` when one was given.
    It follows the app's theme like the other widgets."""
    content_signal = Signal(content)
    call = Call("Text", props={"text": content_signal, "typography_role": typography_role, "wrap": "word", "overflow": "clip"},
                style={"foreground": color, "width": None if width is None else float(width)})
    widget = Widget(window, call=call, components={None: "text"}, theme=theme, x=x, y=y, name="text")
    widget.content = content_signal  # the view's own `text`: setting it re-measures the text in its resolved font
    return widget


class _Expandable:
    """The expanded state of an accordion header or tree node: `widget.expanded`, the `Signal` the view shows (its chevron turns with it), set by a click,
    Enter or Space, the arrow keys (a tree node's) and assistive technology's expand/collapse. `on_change(fn)` hears what the user does, not what the
    program sets. `toggles` says whether the view flips it on a press itself (an accordion's does; a tree node's does not)."""

    def __init__(self, widget: Widget, expanded: Signal, part: str | None, *, toggles: bool, arrows: bool) -> None:
        widget.expanded = expanded
        self.expanded = expanded
        self.changes: list[Callable[[bool], Any]] = []
        widget.on_change = lambda fn: (self.changes.append(fn), lambda: self.changes.remove(fn) if fn in self.changes else None)[1]
        node = widget.part(part)

        def user_set(value: bool) -> None:
            if expanded.get() != value:
                expanded.set(value)
                self.heard()

        self.user_set = user_set
        if not toggles:
            widget.on_click(lambda: user_set(not expanded.get()), part=part, role=node.get("role") or "button")
        widget._undo.append(a11y.on_action(node, {"expand": lambda e: user_set(True), "collapse": lambda e: user_set(False)},
                                           listen=widget.view._listen))
        if arrows:
            keys = {"arrow_right": True, "arrow_left": False}
            widget._undo.append(widget.view._listen(node, "key_down", lambda e: user_set(keys[e.key]) if e.key in keys else None))

    def heard(self) -> None:
        for fn in list(self.changes):
            fn(self.expanded.get())


def accordion_header(
    window: "Window",
    title: str,
    expanded: bool = False,
    width: float = 360.0,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> Widget:
    """An accordion header: a title and a
    chevron that turns over when `.expanded` (a `Signal`) is on. A click,
    Enter or Space toggles it; `.on_change(fn)` hears the user's toggles.
    Show and hide the content yourself, from `.expanded`."""
    state = Signal(bool(expanded))
    holder: list[_Expandable] = []
    call = Call("Accordion", props={"title": title, "expanded": state}, handlers={"on_toggle": lambda: holder[0].heard()},
                style={"width": width, **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: "accordion_header"}, parts={"title": "header.title", "chevron": "header.chevron"},
                    theme=theme, x=x, y=y, name="accordion_header")
    holder.append(_Expandable(widget, state, "header", toggles=True, arrows=False))
    return widget


def tree_node(
    window: "Window",
    title: str,
    depth: int = 0,
    expanded: bool = False,
    leaf: bool = False,
    width: float = 360.0,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> Widget:
    """A tree row, indented by its `depth`, `role="treeitem"` at `level` `depth + 1`. A branch has a
    chevron (pointing right, down when `.expanded`), toggled by a click,
    Enter or Space, and set by the right and left arrows. Build the tree's
    structure yourself, from `.expanded`."""
    state = None if leaf else Signal(bool(expanded))
    call = Call("TreeNode", props={"label": title, "level": int(depth), "branch": None if leaf else True, "expanded": state},
                style={"width": width, **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: "tree_node"}, parts={"title": "label"}, theme=theme, x=x, y=y, name="tree_node")
    if state is None:
        widget.expanded = None
        widget.node.set(focusable=True)
    else:
        _Expandable(widget, state, None, toggles=False, arrows=True)
    return widget
