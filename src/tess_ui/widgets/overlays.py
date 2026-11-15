"""Tesserae's own namespace for the Overlays category -- `dialog`,
`snackbar`, `side_sheet`, `menu`, `menu_item`, `tooltip`, `popover`.

Each (but `menu_item`, and a standard `side_sheet`) returns one of
`tess_ui.overlays`' overlays (M41; `popover` M42), built by Tesserae on
`tess_re`'s layers: `open()` shows it and `close()` hides it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional

from tess_ui import overlays
from tess_ui.widgets._composed import Widget
from tess_ui.widgets._views import Call
from tess_ui.widgets.buttons import _border, _borders

if TYPE_CHECKING:
    from tess_ui.theme import Theme
    from tess_re import Window


def dialog(
    window: "Window",
    headline: str,
    supporting_text: str,
    width: float,
    height: float,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    actions: list[tuple[str, Optional[Callable[[], Any]]]] | None = None,
    theme: "Theme | None" = None,
) -> overlays.Dialog:
    """MD3's dialog (`tess_ui.overlays.Dialog`). `open()` it; Escape
    or an action closes it."""
    d = overlays.Dialog(window, headline, supporting_text, width=width, height=height, actions=actions, theme=theme)
    border = _borders([None], border_color, border_width)
    if border is not None:
        panel = d.widget.part("panel")
        panel.set(**({"stroke_color": tuple(border_color)} if border_color else {}),
                  **({"stroke_width": float(border_width)} if border_width is not None else {}))
    return d


def snackbar(
    window: "Window",
    text: str,
    width: float,
    action_label: str | None = None,
    closable: bool = False,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    on_action: Callable[[], Any] | None = None,
    duration: int | None = 4000,
    theme: "Theme | None" = None,
) -> overlays.Snackbar:
    """MD3's snackbar (`tess_ui.overlays.Snackbar`). `open()` it; it
    hides itself after `duration` ms (`None` keeps it)."""
    s = overlays.Snackbar(window, text, width=width, action=action_label, on_action=on_action, closable=closable,
                          duration=duration, theme=theme)
    if border_color is not None or border_width is not None:
        s.node.set(**({"stroke_color": tuple(border_color)} if border_color else {}),
                   **({"stroke_width": float(border_width)} if border_width is not None else {}))
    return s


def side_sheet(
    window: "Window",
    width: float = 360.0,
    height: float | None = None,
    modal: bool = False,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    theme: "Theme | None" = None,
) -> "Widget | overlays.SideSheet":
    """MD3's side sheet. `modal=True` is `tess_ui.overlays.SideSheet` (an
    overlay: `open()` it); otherwise a standard sheet, a `surface` panel in
    the layout. Put content in `.panel`/`.node`."""
    if modal:
        return overlays.SideSheet(window, width=width, theme=theme)
    call = Call("Container", style={"width": width, "height": height if height is not None else 400, "background": "surface", "corner_radius": "large",
                                    **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: "side_sheet"}, theme=theme, x=x, y=y, name="side_sheet")
    widget.panel = widget.node
    return widget


def menu(window: "Window", items: list[Any], width: float = 200.0, *,
         theme: "Theme | None" = None) -> overlays.Menu:
    """MD3's menu (`tess_ui.overlays.Menu`) of `menu_item(...)`s or
    `(label, fn)` pairs. `open(anchor)` below a node, `open_at(x, y)`, or
    `attach_context(node)` for a right-click."""
    return overlays.Menu(window, items, width=width, theme=theme)


def menu_item(
    window: "Window",
    label: str,
    icon: str | None = None,
    submenu: bool = False,
    width: float = 200.0,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    on_click: Callable[[], Any] | None = None,
    theme: "Theme | None" = None,
) -> Widget:
    """One of MD3's 48 px menu items, for
    `menu(...)`: a `label_large` label, an optional 24 px leading `icon`,
    and a trailing chevron when `submenu`. `on_click` runs when it's
    chosen (the menu closes)."""
    call = Call("MenuItem", props={"label": label, "icon": icon, "submenu": submenu or None},
                style={"width": width, "height": 48, "padding": {"left": 12, "right": 12, "top": 0, "bottom": 0}, **_border(border_color, border_width)})
    widget = Widget(window, call=call, components={None: "menu_item"}, parts={"icon": "lead", "submenu": "chevron"}, theme=theme, x=x, y=y, name="menu_item")
    widget._menu_action = on_click
    return widget


def tooltip(
    window: "Window",
    text: str,
    width: float | None = None,
    x: float | None = None,
    y: float | None = None,
    border_color: tuple[int, int, int, int] | None = None,
    border_width: float | None = None,
    *,
    anchor: Any = None,
    theme: "Theme | None" = None,
) -> overlays.Tooltip:
    """MD3's plain tooltip (`tess_ui.overlays.Tooltip`).
    `attach(anchor)` (or `anchor=`) shows it on hover and keyboard focus."""
    t = overlays.Tooltip(window, text, width=width, theme=theme)
    if anchor is not None:
        t.attach(getattr(anchor, "node", anchor))
    return t


def popover(
    window: "Window",
    supporting_text: str,
    subhead: str | None = None,
    width: float = 312.0,
    *,
    actions: list[tuple[str, Optional[Callable[[], Any]]]] | None = None,
    anchor: Any = None,
    theme: "Theme | None" = None,
) -> overlays.Popover:
    """MD3's rich tooltip, `tess_re`'s popover (`tess_ui.overlays.Popover`).
    `open(anchor)` it, or `attach(anchor)` (or `anchor=`) to open and close
    it on the anchor's click; an outside press, Escape or an action closes it."""
    p = overlays.Popover(window, supporting_text, subhead=subhead, width=width, actions=actions, theme=theme)
    if anchor is not None:
        p.attach(getattr(anchor, "node", anchor))
    return p
