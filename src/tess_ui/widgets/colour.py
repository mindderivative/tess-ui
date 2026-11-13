"""Tesserae's own namespace for the colour picker's controls -- `colour_area`, `colour_strip`, `colour_field` and `colour_swatches`
(`tess_ui.colour_controls`), each attached to the window's root and returned, like the other controls. `value` is the colour as text,
`'#rrggbb'` or `'#rrggbbaa'` (lowercase); `.value` is a `Signal` of it, and `on_input(fn)` and `on_change(fn)` hear the user's changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tess_ui import colour_controls
from tess_ui.widgets._controls import place

if TYPE_CHECKING:
    from tess_re import Window


def colour_area(window: Window, value: str = "#000000", x: float | None = None, y: float | None = None, **kwargs: Any) -> colour_controls.ColourArea:
    """The square of saturation (across) and value (up) for the colour's hue; `width=` and `height=` size it (256 by 176). `.hue` is the hue the picker
    remembers for a colour with none of its own."""
    return place(window, colour_controls.ColourArea(window, value=value, **kwargs), x, y)


def colour_strip(window: Window, channel: str = "hue", value: str = "#000000", x: float | None = None, y: float | None = None,
                 **kwargs: Any) -> colour_controls.ColourStrip:
    """A strip that picks the `channel` (`"hue"` or `"alpha"`) of the colour; `width=` and `height=` size it (256 by 24)."""
    return place(window, colour_controls.ColourStrip(window, channel=channel, value=value, **kwargs), x, y)


def colour_field(window: Window, channel: str = "hex", value: str = "#000000", x: float | None = None, y: float | None = None,
                 **kwargs: Any) -> colour_controls.ColourField:
    """A text field for the `channel` (`"hex"`, `"red"`, `"green"`, `"blue"` or `"alpha"`) of the colour; `.error` is a `Signal` that says the text typed
    is not a colour."""
    return place(window, colour_controls.ColourField(window, channel=channel, value=value, **kwargs), x, y)


def colour_swatches(window: Window, value: str = "#000000", x: float | None = None, y: float | None = None,
                    **kwargs: Any) -> colour_controls.ColourSwatches:
    """A row of the theme's colour roles (`roles=` names others); pressing one sets `.value` to its colour."""
    return place(window, colour_controls.ColourSwatches(window, value=value, **kwargs), x, y)
