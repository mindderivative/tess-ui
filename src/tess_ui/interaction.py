"""MD3 interaction feedback: a state layer and a ripple, built from
`tess_re` 0.3.4's building blocks, since `tess_re` 0.3.5 draws none (`tess_re` D7).

A node that gets an `Interaction` holds two extra children, after its
content, absolutely positioned, never hit-tested and hidden from
assistive technology:

- **A clip box** covering the node, clipped to the node's rounded box,
  holding:
  - **the state layer**, in the tint. Its opacity is the strongest state
    the node is in: dragged 16%, else focused 10% (keyboard focus only,
    `focus_visible`), else hovered 8%;
  - **ripples**, one per press: a circle centred on the press point that
    grows until it covers the node while the press is held, at the
    pressed opacity (10%), and fades once it's released. A keyboard
    click (Enter or Space) ripples from the centre.
- **The focus ring**, shown on keyboard focus only: MD3's focus indicator,
  3 px in `secondary`, 2 px outside the node and following its corners.

The opacities and the ring are MD3's; the ripple's timing is Material
Web's (`md-ripple`), MD3's reference implementation. The layer and ripples
paint over the node's content, as in Material Web and Compose. The node
itself isn't clipped, so its children and the ring can overflow it. Views
apply this to clickable YAML nodes (`tess_ui.view`); M40's widgets use
it directly.
"""

from __future__ import annotations

import math
from typing import Any, Callable
from tess_ui import focusring, motion, ripple, tokens

__all__ = ["DRAGGED", "FOCUSED", "HOVERED", "Interaction", "PRESSED"]

RGBA = tuple[int, int, int, int]
#: A listener registrar: `listen(node, event, fn)` returns a function
#: that removes the listener (`tess_re` keeps one listener per event, so the
#: caller shares a dispatcher between everyone listening on a node).
Listen = Callable[[Any, str, Callable[[Any], None]], Callable[[], None]]

#: MD3's state-layer opacities.
HOVERED, FOCUSED, PRESSED, DRAGGED = (tokens.STATE_LAYER[k] for k in ("hover", "focus", "pressed", "dragged"))

#: Material Web's `md-ripple` timing, in ms.
#: The state layers' fades, per state (the engine's `hover_layer_ms`, `pressed_layer_ms`, `focus_layer_ms`): the spec's 105 ms for pressed and 150 ms for focus. Hover is
#: the engine's own 100 ms, not the spec's 15 ms, until tre fixes its 15 ms hover leaving a layer pixel behind on the real compositor.
HOVER_MS = 100
PRESSED_LAYER_MS = tokens.RIPPLE_MS["press_fade_in"]
FOCUS_LAYER_MS = 150
PRESS_GROW_MS = tokens.RIPPLE_MS["press_grow"]
PRESS_FADE_IN_MS = tokens.RIPPLE_MS["press_fade_in"]
MINIMUM_PRESS_MS = tokens.RIPPLE_MS["minimum_press"]
RELEASE_FADE_MS = tokens.RIPPLE_MS["release_fade"]
#: MD3's focus indicator, in px: its thickness, and its gap outside the node.
RING_WIDTH = 3.0
RING_OFFSET = 2.0
#: The ripple starts at this fraction of the node's larger side.
INITIAL_SCALE = tokens.RIPPLE_INITIAL_SCALE
#: MD3's standard easing, which `md-ripple` grows with.
STANDARD = (0.2, 0.0, 0.0, 1.0)


class Interaction:
    """The state layer, ripple and focus ring on one `box` node: the layer
    and ripple tinted `tint`, the ring `ring_color`.

    `listen` registers the pointer and focus listeners (see `Listen`).
    `surface`, a child of `node`, is where the layer, ripples and ring are
    drawn and sized, when that isn't the node itself: a selection
    control's 40 px circle inside its 48 px touch target. Events
    still come from `node`. `ring_around` is where the focus ring goes,
    when that isn't the surface (a switch's track, not its moving handle). `enabled = False` shows no feedback (a
    disabled control). Call `refresh()` after the surface's corners
    change, and `detach()` to remove everything this added."""

    def __init__(self, window: Any, node: Any, tint: RGBA, listen: Listen, ring_color: RGBA,
                 surface: Any = None, ring_around: Any = None, glow: tuple[RGBA, RGBA] | None = None) -> None:
        self.window = window
        self.node = node
        self.glow = glow  # the two colours after the ring's own in a turning gradient ring (`tess_ui.focusring`)
        self.surface = node if surface is None else surface
        self.ring_around = self.surface if ring_around is None else ring_around
        self._enabled = True
        self.tint = tint
        self.ring_color = ring_color
        self.hovered = self.focused = self.dragged = False
        self._ripples: list[_Ripple] = []
        decoration = dict(position="absolute", hit_testable=False, a11y_hidden=True)
        self.clip = window.create("box", x=0, y=0, width="100%", height="100%", clip_children=True,
                                  **decoration)
        #: The focus ring. A plain ring is the engine's (tre 0.6.12): `focus_outline_*` on `ring_around`, drawn on keyboard focus only, following the node's corners; no node of ours. The turning gradient ring
        #: (`tess_ui.focusring`, an app option) is a stroke gradient an outline cannot be, so it keeps its own node.
        self.ring: Any = None
        if focusring.uses_gradient(window):
            self.ring = window.create("box", stroke_color=ring_color, stroke_width=RING_WIDTH, visible=False, **decoration)
        self._glow: Any = None
        self.sparks: Any = None  # the ripple shader's node, when the window draws ripples that way (`tess_ui.ripple`)
        self._shader: Any = None
        if ripple.uses_shader(window):
            self.sparks = window.create("box", x=0, y=0, width="100%", height="100%", **decoration)
            self.clip.add_child(self.sparks)
            self._shader = ripple.RippleShader(window, self.sparks, tint)
        self.surface.add_child(self.clip)
        if self.ring is not None:
            self.ring_around.add_child(self.ring)
        else:
            self._set_outline()
        if focusring.uses_gradient(window):
            self._glow = focusring.GradientRing(window, self.ring, self._glow_colors())
        self.refresh()
        self._paint_layers()
        _INTERACTIVE.append(node)
        self._undo = [listen(node, event, handler) for event, handler in (
            ("pointer_enter", self._on_enter), ("pointer_leave", self._on_leave),
            ("pointer_down", self._on_down), ("pointer_up", self._on_up), ("click", self._on_click),
            ("pointer_cancel", self._on_up),  # the OS took the press (a window drag, 0.3.0): released, no click
            ("focus", self._on_focus), ("unfocus", self._on_unfocus),
        )]

    # -- state --------------------------------------------------------------

    def _paint_layers(self) -> None:
        """The state layers are the engine's (tre 0.6.11): `hover_layer` and `focus_layer` on the surface are the tint at 8 and 10 percent, drawn over its fill and under its content, hover when the
        pointer is over it (children included) and focus on keyboard focus only, one at a time, faded by the engine, so no node and no per-frame code here. Dragged (16 percent) is the
        hover and the focus layer raised while a drag holds (dragged beats focus beats hover). Pressed is the ripple. A disabled control has no layers."""
        if not self._enabled:
            self.surface.set(hover_layer=None, focus_layer=None)
            return
        r, g, b = self.tint[0], self.tint[1], self.tint[2]
        alpha = self.tint[3] / 255 if len(self.tint) > 3 else 1.0  # a tint with its own alpha scales the layer
        hover = DRAGGED if self.dragged else HOVERED
        self.surface.set(hover_layer=(r, g, b, round(255 * hover * alpha)), focus_layer=(r, g, b, round(255 * (DRAGGED if self.dragged else FOCUSED) * alpha)), focus_layer_any_modality=False,
                         hover_layer_ms=float(motion.duration(self.window, HOVER_MS)),
                         pressed_layer_ms=float(motion.duration(self.window, PRESSED_LAYER_MS)),
                         focus_layer_ms=float(motion.duration(self.window, FOCUS_LAYER_MS)))

    @property
    def enabled(self) -> bool:
        """Whether the node shows state feedback (hover, focus, press); set it to turn that on or off."""
        return self._enabled

    @enabled.setter
    def enabled(self, enabled: bool) -> None:
        """Turning it off clears the feedback at once and shows none until
        it's turned on again."""
        self._enabled = enabled
        self._paint_layers()
        if self.ring is None:
            self._set_outline()
        if not enabled:
            self.hovered = self.focused = self.dragged = False
            if self.ring is not None:
                self.ring.set(visible=False)
            if self._glow is not None:
                self._glow.hide()
            for each in self._ripples:
                each.circle.set(opacity=0.0)
                each.release()
            if self._shader is not None:
                self._shader.clear()
            self._paint_layers()

    @property
    def ripples(self) -> list[Any]:
        """The live ripples, oldest first: their circle nodes, or (drawn by the shader) the presses it holds."""
        if self._shader is not None:
            return list(self._shader.presses)
        return [ripple.circle for ripple in self._ripples]

    def release(self) -> None:
        """Lets go of every press held, for a widget whose pointer was taken by another node (a captured drag), so the release never came here."""
        self._release_all()

    def set_dragged(self, dragged: bool) -> None:
        """For widgets that drag: MD3's dragged state."""
        self.dragged = dragged
        self._update()

    def _set_outline(self) -> None:
        """The engine's focus outline on `ring_around`: 3 px, 2 px off, in the ring colour; none while the control is disabled."""
        self.ring_around.set(focus_outline_width=RING_WIDTH if self._enabled else 0.0, focus_outline_offset=RING_OFFSET, focus_outline_color=self.ring_color)

    @property
    def ring_visible(self) -> bool:
        """Whether the focus ring is showing."""
        return self.focused

    def _glow_colors(self) -> tuple[RGBA, RGBA, RGBA]:
        """The turning ring's three colours: the ring's own, then the two `glow` gives (the theme's primary and tertiary), else the ring's own again."""
        second, third = self.glow if self.glow is not None else (self.ring_color, self.ring_color)
        return self.ring_color, second, third

    def retint(self, tint: RGBA, ring_color: RGBA, glow: tuple[RGBA, RGBA] | None = None) -> None:
        """New colours (a theme change), for the layer, live ripples and ring."""
        self.tint, self.ring_color = tint, ring_color
        if glow is not None:
            self.glow = glow
        self._paint_layers()
        if self.ring is not None:
            self.ring.set(stroke_color=ring_color)
        else:
            self._set_outline()
        if self._glow is not None:
            self._glow.recolor(self._glow_colors(), paint=self.ring_visible)
        for each in self._ripples:
            each.circle.set(fill=tint)
        if self._shader is not None:
            self._shader.retint(tint)

    def refresh(self) -> None:
        """Follows the node's corners (and, for the ring, its size)."""
        radius = self.surface.get("corner_radius") or 0.0
        self.clip.set(corner_radius=radius)
        self._place_ring()

    def _place_ring(self) -> None:
        if self.ring is None:  # the engine's outline follows the node by itself
            return
        # A box's stroke is drawn inside it, so the ring's box starts the
        # gap and the stroke's width outside the node.
        out = RING_OFFSET + RING_WIDTH
        radius = self.ring_around.get("corner_radius") or 0.0
        grown = (tuple(r + out if r else 0.0 for r in radius) if isinstance(radius, (tuple, list))
                 else radius + out if radius else 0.0)
        width, height = self.ring_around.get("layout_width") or 0.0, self.ring_around.get("layout_height") or 0.0
        self.ring.set(x=-out, y=-out, width=width + 2 * out, height=height + 2 * out, corner_radius=grown)

    def detach(self) -> None:
        """Removes the listeners, the layer and any ripples. Safe after the
        node itself was destroyed."""
        for undo in self._undo:
            _quietly(undo)
        self._undo = []
        for node in (self.clip, self.ring):
            if node is not None:
                _quietly(node.destroy)
        if self.ring is None:
            _quietly(lambda: self.ring_around.set(focus_outline_width=0.0))
        self._ripples = []
        if self._glow is not None:
            self._glow.hide()
        if self._shader is not None:
            self._shader.detach()
        if self.node in _INTERACTIVE:
            _INTERACTIVE.remove(self.node)

    def _update(self) -> None:
        self._paint_layers()  # the dragged state changes the hover layer's strength; hover and focus are the engine's

    # -- events ------------------------------------------------------------

    def _mine(self, event: Any) -> bool:
        """Whether a bubbled event is this node's: no nearer interactive
        node sits between its target and this one."""
        node = event.target
        while node is not None and node != self.node:
            if node in _INTERACTIVE:
                return False
            node = node.parent()
        return True

    def _on_enter(self, event: Any) -> None:
        if not self._enabled:
            return
        self.hovered = True
        self._update()

    def _on_leave(self, event: Any) -> None:
        self.hovered = False
        self._update()
        self._release_all()  # a press dragged off the node is cancelled

    def _on_down(self, event: Any) -> None:
        if self._enabled and self._mine(event) and event.x is not None:
            x, y = event.x, event.y
            if self.surface is not self.node:  # the event is local to the node; layout is window-wide
                x -= (self.surface.get("layout_x") or 0.0) - (self.node.get("layout_x") or 0.0)
                y -= (self.surface.get("layout_y") or 0.0) - (self.node.get("layout_y") or 0.0)
            if self._shader is not None:
                self._shader.press(x, y, self.surface.get("layout_width") or 0.0, self.surface.get("layout_height") or 0.0)
            else:
                self._ripples.append(_Ripple(self, x, y))

    def _on_up(self, event: Any) -> None:
        self._release_all()

    def _on_click(self, event: Any) -> None:
        # A keyboard click has no position, and no press came first.
        if self._enabled and event.x is None and self._mine(event):
            if self._shader is not None:
                self._shader.release(self._shader.press(None, None, self.surface.get("layout_width") or 0.0, self.surface.get("layout_height") or 0.0))
                return
            each = _Ripple(self, None, None)
            self._ripples.append(each)
            each.release()

    def _on_focus(self, event: Any) -> None:
        if event.target == self.node and self._enabled:
            self.focused = bool(event.focus_visible)
            if self.focused:
                self._place_ring()  # the node may have been resized since
            if self.ring is not None:
                self.ring.set(visible=self.focused)
            if self._glow is not None:
                self._glow.show() if self.focused else self._glow.hide()
            self._update()

    def _on_unfocus(self, event: Any) -> None:
        if event.target == self.node:
            self.focused = False
            if self.ring is not None:
                self.ring.set(visible=False)
            if self._glow is not None:
                self._glow.hide()
            self._update()

    def _release_all(self) -> None:
        for each in list(self._ripples):
            each.release()
        if self._shader is not None:
            self._shader.release()


class _Ripple:
    """One press's ripple. `x`/`y` are local to the node; `None` ripples
    from the centre."""

    def __init__(self, owner: Interaction, x: Any, y: Any) -> None:
        self.owner = owner
        self.released = False
        self.held_long_enough = False
        node = owner.surface
        width, height = node.get("layout_width") or 0.0, node.get("layout_height") or 0.0
        if x is None:
            x, y = width / 2, height / 2
        # Big enough to cover the node from the press point.
        radius = max(math.hypot(x - cx, y - cy) for cx in (0.0, width) for cy in (0.0, height)) or 1.0
        start = min(1.0, INITIAL_SCALE * max(width, height) / (2 * radius))
        self.circle = owner.window.create(
            "box", position="absolute", x=x - radius, y=y - radius, width=2 * radius, height=2 * radius,
            corner_radius=radius, fill=owner.tint, opacity=0.0, scale=start, hit_testable=False,
            a11y_hidden=True)
        owner.clip.add_child(self.circle)
        self.circle.animate("scale", 1.0, motion.duration(owner.window, PRESS_GROW_MS), easing=STANDARD)
        self.circle.animate("opacity", PRESSED, motion.duration(owner.window, PRESS_FADE_IN_MS))
        # `tess_re` has no timers; an invisible animation of the circle's
        # stroke width stands in for one, so a quick tap still shows.
        self.circle.animate("stroke_width", 0.001, MINIMUM_PRESS_MS, on_complete=self._held)

    def _held(self) -> None:
        self.held_long_enough = True
        if self.released:
            self._fade()

    def release(self) -> None:
        if self.released:
            return
        self.released = True
        if self.held_long_enough:
            self._fade()

    def _fade(self) -> None:
        self.circle.animate("opacity", 0.0, motion.duration(self.owner.window, RELEASE_FADE_MS), on_complete=self._done)

    def _done(self) -> None:
        if self in self.owner._ripples:
            self.owner._ripples.remove(self)
        _quietly(self.circle.destroy)


#: Every node with an `Interaction`, so a bubbled press ripples only the
#: nearest. Each `Interaction` adds its node, and `detach` removes it.
_INTERACTIVE: list[Any] = []


def _quietly(fn: Callable[[], Any]) -> None:
    try:
        fn()
    except (ValueError, RuntimeError):
        pass  # the node is already gone
