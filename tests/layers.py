"""What the engine's state layers show for an `Interaction`, read from the properties set on its surface (tre 0.6.11 draws them: `hover_layer` and `focus_layer`, one at a time, focus over hover, keyboard focus only):
`.get("opacity")` is the strength showing now and `.get("fill")` the tint. The painting itself is pinned by a pixel test in `test_state_layers.py`."""


class _Layer:
    def __init__(self, it):
        self.it = it

    def get(self, name):
        it = self.it
        hover, focus = it.surface.get("hover_layer"), it.surface.get("focus_layer")
        if name == "fill":
            held = hover or focus
            return None if held is None else tuple(held[:3]) + (255,)
        if name == "opacity":
            if hover is None or not it.enabled:
                return 0.0
            if it.focused:
                return focus[3] / 255
            return hover[3] / 255 if (it.hovered or it.dragged) else 0.0
        raise KeyError(name)


def layer_of(it):
    return _Layer(it)


class _Ring:
    """What the focus ring shows for an `Interaction`: the engine's `focus_outline_*` on the node it goes around (tre 0.6.12), read as the old ring node's stroke and box were, or the gradient ring's own node."""

    def __init__(self, it):
        self.it = it

    def get(self, name):
        it, around = self.it, self.it.ring_around
        if it.ring is not None:
            return it.ring.get(name)
        out = around.get("focus_outline_offset") + around.get("focus_outline_width")
        if name == "stroke_color":
            return around.get("focus_outline_color")
        if name == "stroke_width":
            return around.get("focus_outline_width")
        if name == "visible":
            return it.ring_visible
        if name == "layout_width":
            return around.get("layout_width") + 2 * out
        if name == "layout_height":
            return around.get("layout_height") + 2 * out
        if name == "corner_radius":
            radius = around.get("corner_radius") or 0.0
            return tuple(r + out if r else 0.0 for r in radius) if isinstance(radius, (tuple, list)) else radius + out if radius else 0.0
        raise KeyError(name)

    def parent(self):
        return self.it.ring_around


def ring_of(it):
    return _Ring(it)
