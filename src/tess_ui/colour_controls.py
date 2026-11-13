"""The four controls a colour picker is made of: `ColourArea` (saturation and value), `ColourStrip` (hue, or alpha), `ColourField` (the hex text or one
of the red, green, blue and alpha numbers) and `ColourSwatches` (the theme's colour roles).

Each holds the colour as `value`, a `Signal` of `'#rrggbb'` text (`'#rrggbbaa'` when alpha is below 1; see `tess_ui.colour`), so the four can be bound to
one name and stay in step: a change to the text by any of them is a change for all. The area and the hue strip also have `hue`, a `Signal` of degrees:
the hue the picker remembers for a colour that has none of its own (a grey, a black), which is what keeps the hue where the user left it when a drag goes
to a corner and comes back. `on_input(fn)` hears every change the user makes, while a drag is still going; `on_change(fn)` hears it once the drag is let go
and after each key, as a `Slider` does. They are made like the other controls (`tess_ui.controls`): a theme, `disabled`, a state layer and a focus ring,
and a role and value for a screen reader.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tess_ui import a11y, colour, tokens
from tess_ui.controls import DISABLED_CONTAINER, DISABLED_CONTENT, Control, with_alpha
from tess_ui.follow import initial_theme, unfollow
from tess_ui.interaction import Interaction
from tess_ui.listeners import Listeners, handled
from tess_ui.reactive import Effect, Signal, untrack
from tess_ui.theme import Theme

__all__ = ["ColourArea", "ColourField", "ColourStrip", "ColourSwatches", "SWATCH_ROLES"]

RGBA = tuple[int, int, int, int]
Listen = Callable[[Any, str, Callable[[Any], None]], Callable[[], None]]

#: The theme roles `ColourSwatches` shows when it is not told others.
SWATCH_ROLES = ("primary", "secondary", "tertiary", "error", "surface", "on_surface", "primary_container", "secondary_container")
_WHITE: RGBA = (255, 255, 255, 255)
_CLEAR: RGBA = (0, 0, 0, 0)
_BLACK: RGBA = (0, 0, 0, 255)
#: The hue strip's colours: red, yellow, green, cyan, blue, magenta and red again, a sixth of the strip apart.
_HUES = [(i / 6, colour.parse(colour.from_hsva(i * 60.0, 1.0, 1.0))) for i in range(7)]


def _clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, x))


def _gradient(stops: list[Any], angle: float) -> Any:
    import tess_re

    return tess_re.Gradient.linear(stops, angle)


def _checked(value: Any) -> str:
    text = value.lower() if isinstance(value, str) else value
    if not colour.is_valid(text):
        raise ValueError(f"a colour is written #rrggbb or #rrggbbaa, got {value!r}")
    return text


class _ColourControl(Control):
    """What the area and the strips share: the colour and the remembered hue as `Signal`s, the live and end-of-drag listeners, dragging the pointer
    over the control and the keys."""

    role = "slider"

    def __init__(self, window: Any, *, value: str = "#000000", hue: float | None = None, **kwargs: Any) -> None:
        text = _checked(value)
        self.value = Signal(text)
        self.hue = Signal(colour.hsva(text, hue)[0])
        self._live: list[Callable[[str], None]] = []
        self._telling = False
        self._dragging = False
        self._start: tuple[str, float] = (text, self.hue.get())
        super().__init__(window, **kwargs)
        for event, handler in (("pointer_down", self._on_down), ("pointer_move", self._on_move),
                               ("pointer_up", self._on_up), ("pointer_cancel", self._on_up),
                               ("key_down", self._on_key)):
            self._undo.append(self._listen(self.node, event, handler))
        self._undo.append(a11y.on_action(self.node, {
            "increment": lambda e: self._by_action(lambda: self._nudge(1)),
            "decrement": lambda e: self._by_action(lambda: self._nudge(-1)),
            "set_value": lambda e: self._by_action(lambda: self._set_number(float(e.value))) if e.value is not None else None,
        }, listen=self._listen))

    # -- for app code -------------------------------------------------------------

    def on_input(self, fn: Callable[[str], None]) -> Callable[[], None]:
        """Calls `fn(value)` on every change the user makes, while a drag is still going (`on_change` hears the end of one). Returns the function that
        stops it."""
        self._live.append(fn)
        return lambda: self._live.remove(fn) if fn in self._live else None

    def follow(self, value: str, hue: float | None = None) -> None:
        """Takes the colour (and the remembered hue) a view's bindings now hold. While the control is telling the view of the user's change, what comes
        back is older than the change, since the value and the hue are written one after the other, and is left alone."""
        if self._telling:
            return
        self.value.set(value)
        self.hue.set(colour.hsva(value, self.hue.get() if hue is None else hue)[0])  # what the handle shows: the remembered hue, or the colour's own

    def set_hsva(self, h: float, s: float, v: float, a: float = 1.0) -> None:
        """Sets the colour from hue, saturation, value and alpha, as the app (not the user): no listener is called."""
        self.value.set(colour.from_hsva(h, s, v, a))
        self.hue.set(float(h))

    # -- for subclasses -------------------------------------------------------------

    def _hsva(self) -> tuple[float, float, float, float]:
        return colour.hsva(self.value.get(), self.hue.get())

    def _tint(self) -> RGBA:
        return _WHITE

    def _commit(self, value: str | None = None, hue: float | None = None) -> bool:
        """The user's change: sets what is given and tells `on_input` when something differs."""
        before = (self.value.get(), self.hue.get())
        if hue is not None:
            self.hue.set(float(hue))
        if value is not None:
            self.value.set(value)
        if (self.value.get(), self.hue.get()) == before:
            return False
        self._telling = True
        try:
            for fn in list(self._live):
                fn(self.value.get())
        finally:
            self._telling = False
        return True

    def _point(self, event: Any) -> None:
        raise NotImplementedError

    def _key(self, event: Any) -> None:
        raise NotImplementedError

    def _nudge(self, direction: int) -> None:
        raise NotImplementedError

    def _set_number(self, number: float) -> None:
        raise NotImplementedError

    def _activate(self) -> None:
        pass  # a click has already set the colour, at pointer_down

    # -- input -----------------------------------------------------------------------

    def _on_down(self, event: Any) -> None:
        if self.disabled.get() or event.x is None:
            return
        self._dragging = True
        self._start = (self.value.get(), self.hue.get())
        self.node.capture_pointer()
        self.interaction.set_dragged(True)
        self._point(event)

    def _on_move(self, event: Any) -> None:
        if self._dragging and event.x is not None:
            self._point(event)

    def _on_up(self, event: Any) -> None:
        if not self._dragging:
            return
        self._dragging = False
        self.node.release_pointer()
        self.interaction.set_dragged(False)
        if (self.value.get(), self.hue.get()) != self._start:
            self._tell_change()

    def _tell_change(self) -> None:
        self._telling = True
        try:
            self._changed(self.value.get())
        finally:
            self._telling = False

    def _on_key(self, event: Any) -> None:
        if self.disabled.get():
            return
        before = (self.value.get(), self.hue.get())
        self._key(event)
        if (self.value.get(), self.hue.get()) != before:
            self._tell_change()

    def _by_action(self, change: Callable[[], None]) -> None:
        """What assistive technology asks for: `change()`, then `on_change` if it moved anything."""
        if self.disabled.get():
            return
        before = (self.value.get(), self.hue.get())
        change()
        if (self.value.get(), self.hue.get()) != before:
            self._tell_change()


class ColourArea(_ColourControl):
    """The square of saturation (left to right) and value (bottom to top) for the hue, with a handle at the colour. Pressing or dragging on it sets the
    colour, keeping its hue (and its alpha); the arrow keys move the handle by a hundredth, or a tenth with Shift, Page Up and Page Down move the value by
    a tenth, Home and End take the saturation to its ends. For a screen reader it is a slider: its number is the saturation in percent and its text says
    both, "saturation 40 percent, value 80 percent", and it can be incremented and decremented (the saturation) and set."""

    HANDLE = 20.0
    RADIUS = 12.0

    def __init__(self, window: Any, *, width: float = 256.0, height: float = 176.0, **kwargs: Any) -> None:
        if kwargs.get("label") is None:
            kwargs["label"] = "Saturation and value"
        super().__init__(window, width=width, height=height, **kwargs)

    def _build(self) -> None:
        width, height = self.target
        box = {"position": "absolute", "x": 0.0, "y": 0.0, "width": width, "height": height, "corner_radius": self.RADIUS, "hit_testable": False, "a11y_hidden": True}
        self.base = self.window.create("box", **box)
        self.shade = self.window.create("box", fill=_gradient([_CLEAR, _BLACK], 180.0), **box)
        half = self.HANDLE / 2
        self.handle = self.window.create("box", position="absolute", width=self.HANDLE, height=self.HANDLE, corner_radius=half, stroke_width=2.0,
                                         hit_testable=False, a11y_hidden=True)
        for child in (self.base, self.shade, self.handle, self.surface):  # the state layer rides on the handle, over the picture
            self.node.add_child(child)
        self.surface.set(width=self.HANDLE * 2, height=self.HANDLE * 2, corner_radius=self.HANDLE)
        self._painted_hue: float | None = None

    def _ring_around(self) -> Any:
        return self.base

    def _paint(self, animate: bool) -> None:
        width, height = self.target
        h, s, v, a = self._hsva()
        disabled = self.disabled.get()
        if h != self._painted_hue:  # the only thing the picture depends on
            self.base.set(fill=_gradient([_WHITE, colour.parse(colour.from_hsva(h, 1.0, 1.0))], 90.0))
            self._painted_hue = h
        x, y = s * width, (1.0 - v) * height
        own = colour.parse(colour.from_hsva(h, s, v))
        self.handle.set(x=x - self.HANDLE / 2, y=y - self.HANDLE / 2, fill=own, stroke_color=_WHITE)
        self.surface.set(x=x - self.HANDLE, y=y - self.HANDLE)
        self.node.set(value=float(round(s * 100)), value_min=0.0, value_max=100.0, value_step=1.0, opacity=0.38 if disabled else 1.0)
        a11y.describe(self.node, value_text=f"saturation {round(s * 100)} percent, value {round(v * 100)} percent")

    # -- input -----------------------------------------------------------------------

    def _move_to(self, s: float, v: float) -> None:
        h, _, _, a = self._hsva()
        self._commit(colour.from_hsva(h, _clamp(s), _clamp(v), a), h)

    def _point(self, event: Any) -> None:
        width, height = self.target
        self._move_to(event.x / width, 1.0 - event.y / height)

    def _key(self, event: Any) -> None:
        _, s, v, _ = self._hsva()
        step = 0.1 if getattr(event, "shift", False) else 0.01
        key = event.key
        if key == "arrow_left":
            self._move_to(s - step, v)
        elif key == "arrow_right":
            self._move_to(s + step, v)
        elif key == "arrow_up":
            self._move_to(s, v + step)
        elif key == "arrow_down":
            self._move_to(s, v - step)
        elif key == "page_up":
            self._move_to(s, v + 0.1)
        elif key == "page_down":
            self._move_to(s, v - 0.1)
        elif key == "home":
            self._move_to(0.0, v)
        elif key == "end":
            self._move_to(1.0, v)

    def _nudge(self, direction: int) -> None:
        _, s, v, _ = self._hsva()
        self._move_to(s + direction * 0.01, v)

    def _set_number(self, number: float) -> None:
        _, _, v, _ = self._hsva()
        self._move_to(number / 100.0, v)


class ColourStrip(_ColourControl):
    """A strip with a handle: `channel="hue"` picks the hue (0 to 360 degrees, across the colours of the rainbow) and `channel="alpha"` the alpha (0 to 100
    percent, from clear to the colour, over a chequerboard). Pressing or dragging sets it; the arrow keys move it by one degree or one percent (ten with
    Shift), Page Up and Page Down by ten, Home and End to the ends. For a screen reader it is a slider in degrees or in percent."""

    HANDLE = 20.0
    THICKNESS = 12.0
    CELL = 6.0

    def __init__(self, window: Any, *, channel: str = "hue", width: float = 256.0, height: float = 24.0, **kwargs: Any) -> None:
        if channel not in ("hue", "alpha"):
            raise ValueError(f"a colour strip's channel is 'hue' or 'alpha', got {channel!r}")
        self.channel = channel
        if kwargs.get("label") is None:
            kwargs["label"] = channel.capitalize()
        super().__init__(window, width=width, height=height, **kwargs)

    @property
    def _edge(self) -> float:
        return self.HANDLE / 2

    @property
    def _span(self) -> float:
        return self.target[0] - self.HANDLE

    @property
    def _top(self) -> float:
        return (self.target[1] - self.THICKNESS) / 2

    def _checkerboard(self) -> str:
        width, cells = self.target[0], []
        columns = int(width // self.CELL) + 1
        for row in range(2):
            for column in range(columns):
                if (row + column) % 2 == 0:
                    cells.append(f"M{column * self.CELL},{row * self.CELL}h{self.CELL}v{self.CELL}h-{self.CELL}z")
        return "".join(cells)

    def _build(self) -> None:
        width = self.target[0]
        thick = self.THICKNESS
        self.track = self.window.create("box", position="absolute", x=0.0, y=self._top, width=width, height=thick, corner_radius=thick / 2,
                                        clip_children=True, hit_testable=False, a11y_hidden=True)
        if self.channel == "alpha":  # a chequerboard under the ramp, so that clear shows as clear
            board = self.window.create("path", position="absolute", x=0.0, y=0.0, width=width, height=thick, view_box=(0, 0, width, thick),
                                       data=self._checkerboard(), hit_testable=False, a11y_hidden=True)
            self.track.set(fill=_WHITE)
            self.track.add_child(board)
            self.board = board
        self.ramp = self.window.create("box", position="absolute", x=0.0, y=0.0, width=width, height=thick, hit_testable=False, a11y_hidden=True)
        if self.channel == "hue":
            self.ramp.set(fill=_gradient(_HUES, 90.0))
        self.track.add_child(self.ramp)
        self.handle = self.window.create("box", position="absolute", y=(self.target[1] - self.HANDLE) / 2, width=self.HANDLE, height=self.HANDLE,
                                         corner_radius=self.HANDLE / 2, stroke_width=2.0, hit_testable=False, a11y_hidden=True)
        for child in (self.track, self.handle, self.surface):
            self.node.add_child(child)
        self.surface.set(width=self.HANDLE * 2, height=self.HANDLE * 2, corner_radius=self.HANDLE)

    def _ring_around(self) -> Any:
        return self.track

    def _fraction(self) -> float:
        h, _, _, a = self._hsva()
        return _clamp(h / 360.0 if self.channel == "hue" else a)

    def _paint(self, animate: bool) -> None:
        h, s, v, a = self._hsva()
        disabled = self.disabled.get()
        red, green, blue, _ = colour.parse(self.value.get()) or _BLACK
        if self.channel == "alpha":
            self.ramp.set(fill=_gradient([(red, green, blue, 0), (red, green, blue, 255)], 90.0))
            self.board.set(fill=(200, 200, 200, 255))
            handle = (red, green, blue, 255)
            self.node.set(value=float(round(a * 100)), value_min=0.0, value_max=100.0, value_step=1.0)
            a11y.describe(self.node, value_text=f"{round(a * 100)} percent")
        else:
            handle = colour.parse(colour.from_hsva(h, 1.0, 1.0)) or _BLACK
            self.node.set(value=float(round(h)), value_min=0.0, value_max=360.0, value_step=1.0)
            a11y.describe(self.node, value_text=f"{round(h)} degrees")
        x = self._edge + self._fraction() * self._span
        self.handle.set(x=x - self.HANDLE / 2, fill=handle, stroke_color=_WHITE)
        self.surface.set(x=x - self.HANDLE, y=(self.target[1] - self.HANDLE * 2) / 2)
        self.node.set(opacity=0.38 if disabled else 1.0)

    # -- input -----------------------------------------------------------------------

    def _go(self, fraction: float) -> None:
        fraction = _clamp(fraction)
        h, s, v, a = self._hsva()
        if self.channel == "hue":
            degrees = fraction * 360.0
            self._commit(colour.from_hsva(degrees, s, v, a), degrees)
        else:
            self._commit(colour.with_alpha(self.value.get(), fraction), h)

    def _point(self, event: Any) -> None:
        self._go((event.x - self._edge) / self._span)

    def _unit(self) -> float:
        """One degree or one percent, as a fraction of the strip."""
        return 1.0 / 360.0 if self.channel == "hue" else 0.01

    def _key(self, event: Any) -> None:
        at, unit, key = self._fraction(), self._unit(), event.key
        step = unit * (10 if getattr(event, "shift", False) else 1)
        if key in ("arrow_right", "arrow_up"):
            self._go(at + step)
        elif key in ("arrow_left", "arrow_down"):
            self._go(at - step)
        elif key == "page_up":
            self._go(at + 10 * unit)
        elif key == "page_down":
            self._go(at - 10 * unit)
        elif key == "home":
            self._go(0.0)
        elif key == "end":
            self._go(1.0)

    def _nudge(self, direction: int) -> None:
        self._go(self._fraction() + direction * self._unit())

    def _set_number(self, number: float) -> None:
        self._go(number / 360.0 if self.channel == "hue" else number / 100.0)


class ColourField:
    """A text field for the colour: `channel="hex"` takes `#rrggbb` or `#rrggbbaa`, and `"red"`, `"green"`, `"blue"` and `"alpha"` a whole number from 0 to
    255. Typing something that is a colour (or a number in range) sets `value` at once and `on_input` and `on_change` are told; typing something that is
    not leaves `value` as it was and sets `error`, which draws the field in the error colours and tells a screen reader it is invalid. Leaving the field
    (or Escape) puts back the text of the value; while it is being edited the text is not rewritten under the user. The up and down arrows step a number
    by one, by ten with Shift. Not a `Control`: its focus target is its text input."""

    CHANNELS = ("hex", "red", "green", "blue", "alpha")
    NAMES = {"hex": "Hex colour", "red": "Red", "green": "Green", "blue": "Blue", "alpha": "Alpha"}
    SHORT = {"hex": "Hex", "red": "R", "green": "G", "blue": "B", "alpha": "A"}
    HEIGHT = 40.0

    def __init__(self, window: Any, *, channel: str = "hex", value: str = "#000000", theme: Theme | None = None, label: str | None = None,
                 disabled: bool = False, listen: Listen | None = None, width: float | None = None) -> None:
        if channel not in self.CHANNELS:
            raise ValueError(f"a colour field's channel is one of {', '.join(self.CHANNELS)}, got {channel!r}")
        self.window = window
        self.theme = initial_theme(window, theme, self)
        self.channel = channel
        self.value = Signal(_checked(value))
        self.disabled = Signal(bool(disabled))
        self.error = Signal(False)
        self.focused = Signal(False)
        self.width = float(width if width is not None else (256.0 if channel == "hex" else 56.0))
        self._live: list[Callable[[str], None]] = []
        self._changes: list[Callable[[Any], None]] = []
        self._undo: list[Callable[[], None]] = []
        self._listen: Listen = listen if listen is not None else Listeners().listen
        shown = label if label is not None else self.SHORT[channel]
        self.node = window.create("box", flex_direction="vertical", gap=4.0, width=self.width)
        self.caption = window.create("text", text=shown, font_family="Roboto", font_size=12.0, hit_testable=False, a11y_hidden=True)
        self.field = window.create("box", width=self.width, height=self.HEIGHT, corner_radius=8.0, padding_left=12.0, padding_right=12.0,
                                   align_items="center", stroke_width=1.0)
        self.input = window.create("text_input", text=self._text(self.value.get()), font_family="Roboto", font_size=14.0, flex_grow=1.0,
                                   height=16.0, focusable=True, role="textbox")
        self.field.add_child(self.input)
        self.node.add_child(self.caption)
        self.node.add_child(self.field)
        a11y.describe(self.input, label=label if label is not None else self.NAMES[channel])
        for event, handler in (("change", self._on_typed), ("focus", self._on_focus), ("unfocus", self._on_leave), ("key_down", self._on_key)):
            self._undo.append(self._listen(self.input, event, handler))
        self._undo.append(a11y.on_action(self.input, {"increment": lambda e: self._bump(1), "decrement": lambda e: self._bump(-1)}, listen=self._listen))
        self._effect = Effect(self._render)

    # -- for app code -------------------------------------------------------------

    def follow(self, value: str, hue: float | None = None) -> None:
        """Takes the colour a view's bindings now hold (`hue` is the area's and the strip's, and is not used here)."""
        self.value.set(value)

    def on_input(self, fn: Callable[[str], None]) -> Callable[[], None]:
        """Calls `fn(value)` after each change the user makes. Returns the function that stops it."""
        self._live.append(fn)
        return lambda: self._live.remove(fn) if fn in self._live else None

    def on_change(self, fn: Callable[[Any], None]) -> Callable[[], None]:
        """Calls `fn(value)` after each change the user makes (the same moment as `on_input`: a typed field has no drag). Returns the function that stops it."""
        self._changes.append(fn)
        return lambda: self._changes.remove(fn) if fn in self._changes else None

    def color(self, role: str) -> RGBA:
        """A colour role of this field's theme, or MD3's baseline."""
        return tokens.theme_color(self.theme, role)

    def set_theme(self, theme: Theme) -> None:
        """Re-tints the field for `theme`, at once."""
        self.theme = theme
        untrack(self._paint)

    def dispose(self) -> None:
        """Stops the field (its repainting and listeners) but leaves its nodes, for a caller about to free the tree it sits in."""
        unfollow(self.window, self)
        self._effect.dispose()
        for undo in self._undo:
            undo()
        self._undo = []

    def destroy(self) -> None:
        """Stops the field and frees its nodes."""
        self.dispose()
        self.node.destroy()

    # -- internals -----------------------------------------------------------------

    def _text(self, value: str) -> str:
        if self.channel == "hex":
            return value
        return str(colour.parse(value)[("red", "green", "blue", "alpha").index(self.channel)])  # type: ignore[index]

    def _parse(self, text: str) -> str | None:
        """The colour `text` makes, or `None` when it is not one (here, a channel's number must be whole and from 0 to 255)."""
        text = text.strip()
        if self.channel == "hex":
            return text.lower() if colour.is_valid(text) else None
        if not text.isascii() or not text.isdigit() or int(text) > 255:
            return None
        return colour.with_channel(self.value.get(), self.channel, int(text))

    def _set(self, value: str) -> None:
        if value == self.value.get():
            return
        self.value.set(value)
        for fn in list(self._live):
            fn(value)
        for fn in list(self._changes):
            fn(value)

    def _on_typed(self, event: Any) -> None:
        text = self.input.get("text") or ""
        value = self._parse(text)
        self.error.set(value is None)
        if value is not None:
            self._set(value)

    def _on_focus(self, event: Any) -> None:
        self.focused.set(True)

    def _on_leave(self, event: Any) -> None:
        self.focused.set(False)
        self.error.set(False)
        self.input.set(text=self._text(self.value.get()))

    def _bump(self, by: int) -> None:
        if self.channel == "hex" or self.disabled.get():
            return
        number = int(self._text(self.value.get())) + by
        self._set(colour.with_channel(self.value.get(), self.channel, max(0, min(255, number))))
        self.error.set(False)
        self.input.set(text=self._text(self.value.get()))

    def _on_key(self, event: Any) -> None:
        key = str(event.key).lower()
        if key == "escape":
            self.error.set(False)
            self.input.set(text=self._text(self.value.get()))
        elif key in ("arrow_up", "arrow_down"):
            self._bump((10 if getattr(event, "shift", False) else 1) * (1 if key == "arrow_up" else -1))

    def _render(self) -> None:
        self.value.get()
        self.disabled.get()
        self.error.get()
        self.focused.get()
        self._paint()

    def _paint(self) -> None:
        value, disabled, error, focused = self.value.get(), self.disabled.get(), self.error.get(), self.focused.get()
        shown = self.input.get("text") or ""
        if not focused or self._parse(shown) != value:  # not while the user is typing something that is this colour already
            if not (focused and error):
                self.input.set(text=self._text(value))
        on_surface = self.color("on_surface")
        accent = self.color("error") if error else self.color("primary") if focused else self.color("outline")
        self.field.set(stroke_color=with_alpha(on_surface, DISABLED_CONTAINER) if disabled else accent, stroke_width=2.0 if (focused or error) else 1.0,
                       fill=_CLEAR)
        self.caption.set(fill=self.color("error") if error else with_alpha(on_surface, DISABLED_CONTENT) if disabled else self.color("on_surface_variant"))
        self.input.set(fill=with_alpha(on_surface, DISABLED_CONTENT) if disabled else on_surface, caret_color=self.color("primary"),
                       focusable=not disabled, disabled=disabled)
        a11y.describe(self.input, invalid=error)


class ColourSwatches:
    """A row of the theme's colour roles as round swatches (`roles`, by default `SWATCH_ROLES`). Pressing one (or Enter or Space on it) sets `value` to
    that role's colour, opaque, and the swatch whose colour is the value's is drawn selected. Each is a button for a screen reader, named by its role ("Primary
    container"); Tab goes to each and Left and Right move between them. A swatch follows a change of theme. Not a `Control`: it is a row of targets."""

    SIZE = 28.0
    GAP = 4.0

    def __init__(self, window: Any, *, value: str = "#000000", roles: Any = SWATCH_ROLES, theme: Theme | None = None, label: str | None = None,
                 disabled: bool = False, listen: Listen | None = None) -> None:
        self.window = window
        self.theme = initial_theme(window, theme, self)
        self.value = Signal(_checked(value))
        self.disabled = Signal(bool(disabled))
        self.roles = [str(r) for r in roles]
        if not self.roles:
            raise ValueError("colour swatches need at least one role")
        for role in self.roles:
            self.color(role)  # an unknown role is named here, with its near names
        self._live: list[Callable[[str], None]] = []
        self._changes: list[Callable[[Any], None]] = []
        self._undo: list[Callable[[], None]] = []
        self._listen: Listen = listen if listen is not None else Listeners().listen
        self.node = window.create("box", flex_direction="horizontal", flex_wrap="wrap", gap=self.GAP, align_items="center", role="group",
                                  label=label or "Theme colours")
        self.swatches: list[Any] = []
        self._interactions: list[Interaction] = []
        for role in self.roles:
            swatch = window.create("box", width=self.SIZE, height=self.SIZE, corner_radius=self.SIZE / 2, focusable=True, role="button",
                                   label=role.replace("_", " ").capitalize(), cursor="pointer", stroke_width=1.0)
            self.node.add_child(swatch)
            self.swatches.append(swatch)
            self._interactions.append(Interaction(window, swatch, self.color("on_surface"), self._listen, self.color("secondary")))
            self._undo.append(self._listen(swatch, "click", handled(self._picker(role))))
            self._undo.append(self._listen(swatch, "key_down", self._mover(len(self.swatches) - 1)))
        self._effect = Effect(self._render)

    # -- for app code -------------------------------------------------------------

    def follow(self, value: str, hue: float | None = None) -> None:
        """Takes the colour a view's bindings now hold (`hue` is the area's and the strip's, and is not used here)."""
        self.value.set(value)

    def on_input(self, fn: Callable[[str], None]) -> Callable[[], None]:
        """Calls `fn(value)` after each change the user makes. Returns the function that stops it."""
        self._live.append(fn)
        return lambda: self._live.remove(fn) if fn in self._live else None

    def on_change(self, fn: Callable[[Any], None]) -> Callable[[], None]:
        """Calls `fn(value)` after each change the user makes (as `on_input` does: a press has no drag). Returns the function that stops it."""
        self._changes.append(fn)
        return lambda: self._changes.remove(fn) if fn in self._changes else None

    def color(self, role: str) -> RGBA:
        """A colour role of this row's theme, or MD3's baseline."""
        return tokens.theme_color(self.theme, role)

    def role_value(self, role: str) -> str:
        """The `'#rrggbb'` text of a theme role now."""
        return colour.format_hex(*self.color(role)[:3])

    def set_theme(self, theme: Theme) -> None:
        """Re-tints the swatches for `theme`, at once."""
        self.theme = theme
        untrack(self._paint)

    def dispose(self) -> None:
        """Stops the row (its repainting and listeners) but leaves its nodes, for a caller about to free the tree it sits in."""
        unfollow(self.window, self)
        self._effect.dispose()
        for undo in self._undo:
            undo()
        self._undo = []
        for it in self._interactions:
            it.detach()

    def destroy(self) -> None:
        """Stops the row and frees its nodes."""
        self.dispose()
        self.node.destroy()

    # -- internals -----------------------------------------------------------------

    def _picker(self, role: str) -> Callable[[Any], None]:
        return lambda event: self._pick(role)

    def _mover(self, index: int) -> Callable[[Any], None]:
        return lambda event: self._on_key(event, index)

    def _pick(self, role: str) -> None:
        if self.disabled.get():
            return
        value = self.role_value(role)
        if value == self.value.get():
            return
        self.value.set(value)
        for fn in list(self._live):
            fn(value)
        for fn in list(self._changes):
            fn(value)

    def _on_key(self, event: Any, index: int) -> None:
        by = {"arrow_left": -1, "arrow_right": 1}.get(str(event.key).lower())
        if by is not None and 0 <= index + by < len(self.swatches):
            self.swatches[index + by].focus()

    def _render(self) -> None:
        self.value.get()
        self.disabled.get()
        self._paint()

    def _paint(self) -> None:
        value, disabled = self.value.get(), self.disabled.get()
        on_surface = self.color("on_surface")
        for role, swatch, it in zip(self.roles, self.swatches, self._interactions):
            chosen = self.role_value(role) == value
            swatch.set(fill=self.color(role), stroke_color=on_surface if chosen else self.color("outline_variant"), stroke_width=3.0 if chosen else 1.0,
                       focusable=not disabled, disabled=disabled, cursor="default" if disabled else "pointer", opacity=0.38 if disabled else 1.0)
            a11y.describe(swatch, selected=chosen)
            it.enabled = not disabled
            it.retint(on_surface, self.color("secondary"))
