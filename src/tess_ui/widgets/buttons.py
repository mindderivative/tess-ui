"""Tesserae's own namespace for the Buttons & Actions category --
`button`, `icon_button`, `fab`, `extended_fab`, `split_button`,
`button_group` and `segmented_button`.

`button`, `icon_button`, `fab`, `extended_fab`, `split_button` and `button_group` are calls of the shipped views `Button`, `IconButton` and `Fab` (see
`tess_ui.widgets._views`), with MD3's feedback in the content's colour; `segmented_button` is still built by hand. The split button's hover and the
button group's press morph the corners and widths as Signals in the call's style (the view eases them) and the feedback's clip follows each sync, which
`tess_re`'s own factories did in Rust with no public Python API.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Callable, Optional

from tess_ui.widgets._composed import Widget
from tess_ui.widgets._views import Call
from tess_ui import motion
from tess_ui.reactive import Signal, batch

if TYPE_CHECKING:
    from tess_ui.theme import Theme
    from tess_re import Window


#: `button`'s variants, and the shipped `Button`'s name for each. A button's label colour, and its feedback's, are the shipped sheet's.
_BUTTONS = {"elevated": "elevated", "filled": "filled", "filled_tonal": "tonal", "outlined": "outlined", "text": "text"}
#: The colour role of each variant's label, which is the tint of its state layer and ripple (MD3).
_BUTTON_INK = {"elevated": "primary", "filled": "on_primary", "filled_tonal": "on_secondary_container", "outlined": "primary", "text": "primary"}
_ICON_BUTTON_INK = {"standard": "on_surface_variant", "filled": "on_primary", "filled_tonal": "on_secondary_container", "outlined": "on_surface_variant"}
_FAB_INK = {"surface": "primary", "primary": "on_primary_container", "secondary": "on_secondary_container", "tertiary": "on_tertiary_container"}


def _border(border_color: tuple[int, int, int, int] | None, border_width: float | None) -> dict[str, Any]:
    """The call-site style that gives a widget the caller's border."""
    return {"border_color": None if border_color is None else _hex(border_color),
            "border_width": None if border_width is None else float(border_width)}


_PADDING_12 = {"left": 12, "right": 12, "top": 0, "bottom": 0}
_SIZES = {32.0: "xs", 40.0: "s", 56.0: "m", 96.0: "l", 136.0: "xl"}  # the shipped sizes (`Size`), by their height


def _size(pixels: float) -> str:
    """The shipped `Size` nearest `pixels` (its type, icon and gap); the pixels themselves are the call's `Style`."""
    return _SIZES[min(_SIZES, key=lambda height: abs(height - float(pixels)))]


def _corners(top_left: float, top_right: float, bottom_right: float, bottom_left: float) -> dict[str, float]:
    """Four corner radii as a style takes them."""
    return {"top_left": top_left, "top_right": top_right, "bottom_right": bottom_right, "bottom_left": bottom_left}


def _hex(color: tuple[int, int, int, int]) -> str:
    return "#" + "".join(f"{c:02X}" for c in color)


def button(
    window: "Window",
    label: str,
    width: float,
    height: float,
    variant: str = "filled",
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    corner_radius: float | None = None,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
) -> Widget:
    """MD3's button. `variant`: elevated,
    filled, filled_tonal, outlined or text. It's a pill (`corner_radius`
    half the height) unless told otherwise. `on_click` makes it a focusable
    button that Enter and Space activate, with MD3's feedback."""
    variant_name = _variant("button", variant, _BUTTONS)
    radius = float(height) / 2 if corner_radius is None else float(corner_radius)
    call = Call("Button", props={"label": label, "variant": variant_name, "size": "s"}, interaction=_BUTTON_INK[variant],
                style={"width": width, "height": height, "corner_radius": radius, "padding": _PADDING_12,
                       **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: f"button.{variant}"}, theme=theme, x=x, y=y, name="button")
    if on_click is not None:
        widget.on_click(on_click)
    return widget


def _borders(parts: list[str | None], border_color, border_width) -> Callable[[dict[str, Any]], None] | None:
    """An `edit` giving `parts` of a widget's spec the caller's border."""
    if border_color is None and border_width is None:
        return None

    def edit(spec: dict[str, Any]) -> None:
        for part in parts:
            node = spec if part is None else next(c for c in spec["children"] if c["id"].endswith("." + part))
            style = node.setdefault("style", {})
            if border_color is not None:
                style["border_color"] = _hex(border_color)
            if border_width is not None:
                style["border_width"] = float(border_width)
    return edit


def _variant(kind: str, variant: str, table: dict[str, str]) -> str:
    if variant not in table:
        raise ValueError(f"unknown {kind} variant {variant!r}; expected one of {sorted(table)}")
    return table[variant]


_ICON_BUTTONS = {"standard": "standard", "filled": "filled", "filled_tonal": "tonal", "outlined": "outlined"}


def icon_button(
    window: "Window",
    icon: str,
    size: float = 40.0,
    variant: str = "standard",
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    label: str | None = None,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
) -> Widget:
    """MD3's icon button. `variant`:
    standard, filled, filled_tonal or outlined. A circle `size` across.
    Give `label=` so a screen reader can name it."""
    pixels = float(size)
    call = Call("IconButton", props={"icon": icon, "variant": _variant("icon button", variant, _ICON_BUTTONS), "size": _size(pixels)},
                interaction=_ICON_BUTTON_INK[variant],
                style={"width": pixels, "height": pixels, "corner_radius": pixels / 2, **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: f"icon_button.{variant}"}, theme=theme, label=label, x=x, y=y,
                    name="icon_button")
    if on_click is not None:
        widget.on_click(on_click)
    return widget


_FABS = {"surface": "surface", "primary": "primary", "secondary": "secondary", "tertiary": "tertiary"}
#: `fab`'s sizes, and the shipped `Fab`'s name for each.
_FAB_SIZES = {"small": "small", "default": "medium", "large": "large"}


def fab(
    window: "Window",
    icon: str,
    size: str = "default",
    variant: str = "surface",
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    label: str | None = None,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
) -> Widget:
    """MD3's floating action button.
    `size`: small (40), default (56) or large (96, with a 36 px icon).
    `variant`: surface, primary, secondary or tertiary."""
    if size not in _FAB_SIZES:
        raise ValueError(f"unknown FAB size {size!r}; expected one of {sorted(_FAB_SIZES)}")
    call = Call("Fab", props={"icon": icon, "variant": _variant("FAB", variant, _FABS), "size": _FAB_SIZES[size]}, interaction=_FAB_INK[variant],
                style=_border(border_color, border_width))
    widget = Widget(window, call=call, components={None: f"fab.{size}"}, theme=theme, label=label, x=x, y=y, name="fab")
    if on_click is not None:
        widget.on_click(on_click)
    return widget


_EXTENDED_FABS = {"surface": "surface", "primary": "primary", "secondary": "secondary", "tertiary": "tertiary"}


def extended_fab(
    window: "Window",
    label: str,
    width: float,
    icon: str | None = None,
    variant: str = "primary",
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
) -> Widget:
    """MD3's extended FAB: an optional
    leading icon and a label, 56 px tall."""
    # a width of the caller's: with an icon the content starts at the left padding (16), without one it is centred with 20 px either side
    call = Call("Fab", props={"label": label, "icon": icon, "variant": _variant("extended FAB", variant, _EXTENDED_FABS), "size": "medium"},
                interaction=_FAB_INK[variant],
                style={"width": width, "align_content": "left" if icon else None,
                       "padding": None if icon else {"left": 20, "right": 20, "top": 0, "bottom": 0},
                       **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: "extended_fab"}, theme=theme, x=x, y=y, name="extended_fab")
    if on_click is not None:
        widget.on_click(on_click)
    return widget


_SPLIT_BUTTONS = {"elevated": "elevated", "filled": "filled", "filled_tonal": "tonal", "outlined": "outlined", "text": "text"}
#: `tess_re`'s split button: the facing corners tighten to this on hover, over 100 ms.
SPLIT_TIGHTENED = 8.0
MORPH_MS = 100


def split_button(
    window: "Window",
    label: str,
    width: float,
    height: float,
    variant: str = "filled",
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
    on_click: Callable[[], Any] | None = None,
    on_menu: Callable[[], Any] | None = None,
) -> Widget:
    """MD3's split button: a `leading`
    action and a `trailing` chevron, parts of the returned `Widget`. While
    it's hovered, the corners where the two meet tighten, as `tess_re`'s did.
    `on_click` is the action, `on_menu` the chevron."""
    rest = float(height) / 2
    shipped = _variant("split button", variant, _SPLIT_BUTTONS)
    border = _border(border_color, border_width)
    # the corners are the view's own style, a Signal each: a hover re-styles the parts (the shipped rules), so a corner set by hand would be put back
    radii = {part: Signal(_corners(rest, rest, rest, rest)) for part in ("leading", "trailing")}
    easing = {"corner_radius": MORPH_MS, "elevation": 200, "background": 150}
    call = Call("Container", style={"flex_direction": "horizontal", "gap": 2}, children=[
        Call("Button", "leading", {"label": label, "variant": shipped, "size": "s"},
             {"width": width, "height": height, "corner_radius": radii["leading"], "padding": _PADDING_12, "transition": easing, **border},
             interaction=_BUTTON_INK[variant]),
        Call("Button", "trailing", {"icon": "chevron_down", "variant": shipped, "size": "s"},
             {"width": height, "height": height, "corner_radius": radii["trailing"], "padding": 0, "transition": easing, **border},
             interaction=_BUTTON_INK[variant])])
    widget = Widget(window, call=call, components={None: f"split_button.{variant}"}, parts={"label": "leading.label", "chevron": "trailing.icon"},
                    theme=theme, x=x, y=y, name="split_button")
    tight = (widget.theme.shape("split_button", "tightened") if widget.theme.is_set else None) or SPLIT_TIGHTENED
    corners = {  # (top_left, top_right, bottom_right, bottom_left)
        "leading": ((rest,) * 4, (rest, tight, tight, rest)),
        "trailing": ((rest,) * 4, (tight, rest, rest, tight)),
    }

    def morph(hovered: bool) -> None:
        def write() -> None:
            for part, (resting, tightened) in corners.items():
                radii[part].set(_corners(*(tightened if hovered else resting)))

        batch(write)

    def follow() -> None:  # the feedback's clip takes the part's corners (the view eases the part itself)
        for part in corners:
            widget.interaction(part).clip.animate("corner_radius", tuple(radii[part].get().values()), motion.duration(window, MORPH_MS))

    widget._undo.append(widget.view.after_sync(follow))

    widget._undo.append(widget.view._listen(widget.node, "pointer_enter", lambda e: morph(True)))
    widget._undo.append(widget.view._listen(widget.node, "pointer_leave", lambda e: morph(False)))
    if on_click is not None:
        widget.on_click(on_click, part="leading")
    if on_menu is not None:
        widget.on_click(on_menu, part="trailing")
    return widget


#: The pressed child's corners in a button group, by its height (`tess_re`'s):
#: 8 up to 38 px, 12 up to 44, else 16.
def _group_tightened(height: float) -> float:
    return 8.0 if height <= 38 else 12.0 if height <= 44 else 16.0


#: How much wider a pressed group child grows; its neighbours share the loss.
GROUP_GROWTH = 12.0


def button_group(
    window: "Window",
    labels: list[str],
    width: float,
    height: float,
    variant: str = "filled",
    x: float | None = None,
    y: float | None = None,
    *,
    theme: "Theme | None" = None,
    on_click: Callable[[int], Any] | None = None,
) -> Widget:
    """MD3's button group: one button per label, `width`x`height`,
    8 px apart; parts `b0`, `b1`, ... While one is pressed, its corners
    tighten and it grows 12 px, its neighbours sharing the loss, and it
    all comes back on release -- the intent of `tess_re`'s, whose reflow
    compounded and never restored. `on_click(index)` hears each."""
    shipped = _variant("button group", variant, _BUTTONS)
    rest = float(height) / 2
    name = "button_group"
    count = len(labels)
    # each button's width and corners are the view's own style, a Signal each (see `split_button`)
    widths = [Signal(float(width)) for _ in range(count)]
    radii = [Signal(rest) for _ in range(count)]
    easing = {"corner_radius": MORPH_MS, "elevation": 200, "background": 150}
    call = Call("Container", style={"flex_direction": "horizontal", "gap": 8}, children=[
        Call("Button", f"b{i}", {"label": text, "variant": shipped, "size": "s"},
             {"width": widths[i], "height": height, "corner_radius": radii[i], "padding": _PADDING_12, "transition": easing},
             interaction=_BUTTON_INK[variant])
        for i, text in enumerate(labels)])
    widget = Widget(window, call=call, components={None: "button_group", **{f"b{i}": f"button.{variant}" for i in range(count)}},
                    theme=theme, x=x, y=y, name=name)
    tight = (widget.theme.shape("button_group", "tightened") if widget.theme.is_set else None) or _group_tightened(
        float(height))
    pressed: list[int] = []

    def follow() -> None:  # the feedback's clip takes the button's corners (the view eases the button itself)
        for i in range(count):
            widget.interaction(f"b{i}").clip.animate("corner_radius", radii[i].get(), motion.duration(window, MORPH_MS))

    widget._undo.append(widget.view.after_sync(follow))

    def press(index: int) -> None:
        release()
        pressed.append(index)
        neighbours = [n for n in (index - 1, index + 1) if 0 <= n < count]
        grown = {index: float(width) + GROUP_GROWTH}
        for n in neighbours:
            grown[n] = max(0.0, float(width) - GROUP_GROWTH / len(neighbours))

        def write() -> None:
            for i, w in grown.items():
                widths[i].set(w)
            radii[index].set(tight)

        batch(write)

    def reset(index: int) -> None:
        for i in range(count):
            widths[i].set(float(width))
        radii[index].set(rest)

    def reset_one(index: int) -> Callable[[], None]:
        def run() -> None:
            reset(index)

        return run

    def release() -> None:
        while pressed:
            index = pressed.pop()
            batch(reset_one(index))

    for i in range(count):
        part = widget.part(f"b{i}")
        widget._undo.append(widget.view._listen(part, "pointer_down", lambda e, i=i: press(i)))
        widget._undo.append(widget.view._listen(part, "pointer_up", lambda e: release()))
        widget._undo.append(widget.view._listen(part, "pointer_cancel", lambda e: release()))  # 0.3.0 M2
        widget._undo.append(widget.view._listen(part, "pointer_leave", lambda e: release()))
        if on_click is not None:
            widget.on_click(lambda i=i: on_click(i), part=f"b{i}")
    return widget


#: A segmented button's check, and the gap after it (MD3).
SEGMENT_CHECK = 18.0
SEGMENT_GAP = 8.0


def segmented_button(
    window: "Window",
    labels: list[str],
    width: float | None = None,
    height: float = 40.0,
    selected: "int | list[int] | None" = None,
    multi: bool = False,
    x: float | None = None,
    y: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> Widget:
    """MD3's outlined segmented button: equal segments in one 1 px
    `outline` pill, 1 px dividers between them, `label_large` labels in
    `on_surface`. A selected segment is `secondary_container` with an 18 px
    check before its `on_secondary_container` label. Single-select (a
    click selects; one Tab stop, the arrows move the selection, as radio
    buttons do) or `multi=True` (a click toggles; each segment a Tab stop,
    the arrows move focus). `.selected` is a `Signal`: an index or `None`,
    or a `frozenset` of indices with `multi`; `.on_change(fn)` hears the
    user's changes. Without `width`, segments fit the widest label. Parts
    `s0`, `s1`, ... with `label`/`check`."""
    from tess_ui import a11y
    from tess_ui.reactive import Effect, Signal

    count = len(labels)
    if count < 2:
        raise ValueError(f"a segmented button needs at least 2 labels, got {count}")
    chosen = _segments_selected(selected, multi, count)
    height = float(height)
    inner = height - 2.0  # inside the 1 px outline
    if width is None:  # MD3: 12 px padding, the check and its gap, the label
        widest = max(window.measure_text(text, font_size=14.0, font_weight=500.0)[0] for text in labels)
        width = 2.0 + math.ceil(max(48.0, 24.0 + SEGMENT_CHECK + SEGMENT_GAP + widest)) * count + (count - 1)
    width = float(width)
    segment = (width - 2.0 - (count - 1)) / count
    name = "segmented_button"
    children: list[dict[str, Any]] = []
    for i, text in enumerate(labels):
        if i:
            children.append({"id": f"{name}.divider{i}", "kind": "Rect",
                             "style": {"width": 1, "height": inner, "background": "outline"}})
        children.append({"id": f"{name}.s{i}", "kind": "Rect",
                         "style": {"width": segment, "height": inner, "background": "transparent",
                                   "flex_direction": "horizontal", "align_content": "center"},
                         "children": [
                             {"id": f"{name}.s{i}.check", "kind": "Icon", "icon": {"name": "check"},
                              "style": {"width": SEGMENT_CHECK, "height": SEGMENT_CHECK,
                                        "foreground": "on_secondary_container"}},
                             {"id": f"{name}.s{i}.label", "kind": "Text",
                              "text": {"content": text, "typography_role": "label_large"},
                              "style": {"foreground": "on_surface"}}]})
    spec = {"id": name, "kind": "Rect",
            "style": {"width": width, "height": height, "corner_radius": height / 2, "background": "transparent",
                      "border_color": "outline", "border_width": 1, "padding": 1, "flex_direction": "horizontal"},
            "children": children}
    widget = Widget(window, spec=spec, theme=theme, x=x, y=y,
                    interactive={f"s{i}": "on_surface" for i in range(count)}, name=name)
    a11y.describe(widget.node, role="group")
    widget.multi = multi
    widget.selected = Signal(chosen)
    changes: list[Callable[[Any], Any]] = []
    widget.on_change = lambda fn: (changes.append(fn), lambda: changes.remove(fn) if fn in changes else None)[1]
    end = inner / 2
    ends = {0: (end, 0.0, 0.0, end), count - 1: (0.0, end, end, 0.0)}  # (top_left, top_right, bottom_right, bottom_left)

    def is_on(i: int) -> bool:
        value = widget.selected.get()
        return i in value if multi else value == i

    def shape() -> None:  # a style takes one radius, so set here, and after re-colouring
        for i, corners in ends.items():
            for node in (widget.part(f"s{i}"), widget.interaction(f"s{i}").clip):
                node.set(corner_radius=corners)

    def draw() -> None:
        value = widget.selected.get()
        stop = None if multi else (value if value is not None else 0)
        for i in range(count):
            on = is_on(i)
            widget.part(f"s{i}").set(fill=widget.color("secondary_container") if on else (0, 0, 0, 0),
                                     focusable=stop is None or i == stop, checked=on)
            widget.part(f"s{i}.check").set(visible=on, width=SEGMENT_CHECK if on else 0.0,
                                           margin_right=SEGMENT_GAP if on else 0.0)
            widget.part(f"s{i}.label").set(fill=widget.color("on_secondary_container" if on else "on_surface"))

    def change(value: Any, focus: Optional[int] = None) -> None:
        if value != widget.selected.get():
            widget.selected.set(value)
            for fn in list(changes):
                fn(value)
        if focus is not None:
            widget.part(f"s{focus}").focus()

    def press(i: int) -> None:
        if multi:
            value = widget.selected.get()
            change(value - {i} if i in value else value | {i})
        else:
            change(i)

    def on_key(event: Any, i: int) -> None:
        step = {"arrow_right": 1, "arrow_left": -1}.get(event.key)
        if step is None:
            return
        target = (i + step) % count
        if multi:
            widget.part(f"s{target}").focus()
        else:
            change(target, focus=target)

    for i, text in enumerate(labels):
        widget.on_click(lambda i=i: press(i), part=f"s{i}", role="checkbox" if multi else "radio")
        a11y.describe(widget.part(f"s{i}"), label=text)
        widget._undo.append(widget.view._listen(widget.part(f"s{i}"), "key_down", lambda e, i=i: on_key(e, i)))
    effect = Effect(draw)  # after `on_click`, which makes every segment focusable
    widget._undo.append(effect.dispose)
    shape()
    widget.after_theme(lambda: (shape(), draw()))
    return widget


def _segments_selected(selected: Any, multi: bool, count: int) -> Any:
    chosen = [] if selected is None else [selected] if isinstance(selected, int) else list(selected)
    for i in chosen:
        if not isinstance(i, int) or not 0 <= i < count:
            raise ValueError(f"selected={selected!r} is out of range for {count} segments")
    if multi:
        return frozenset(chosen)
    if len(chosen) > 1:
        raise ValueError(f"a single-select segmented button can't select {selected!r}; pass multi=True")
    return chosen[0] if chosen else None
