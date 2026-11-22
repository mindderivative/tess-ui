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
