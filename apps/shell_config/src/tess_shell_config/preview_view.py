"""The View tab: a picture of the shell's surfaces drawn from the shell's preview model (`tess_shell.preview.preview(...).to_dict()`, schema `preview`, version 1).

The picture is a mockup, not the shell: surfaces are rectangles at their real positions and sizes scaled into the pane, the colours are the MODEL's own tokens (the shell's theme, not the
role colours of this application's window), a bar or panel shows its modules as labelled chips, a frame is a ring, the desktop (what is left after the exclusive zones) is outlined. It is
not interactive: one region named "Shell preview" with a text alternative, and nothing inside takes the focus or the pointer.

`PreviewPane` draws into a node of the window (`stage`); a model it cannot draw (none yet, or the last one with errors) keeps the last good picture, dimmed, under a message.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

#: The picture's colours when the model's tokens do not say.
FALLBACK = {"color.surface": "#1a1626", "color.surface_raised": "#2a2438", "color.on_surface": "#e4eaf1", "color.on_surface_muted": "#9a94a8", "color.outline": "#4a4458",
            "color.primary": "#b392f0", "color.scrim": "#000000"}
#: How much of the picture the dimming of an unavailable preview covers (the vault's Preview Pane: 38 percent).
DIM = 0.38
#: The smallest pane the picture is drawn in; a smaller one says so.
MIN_WIDTH, MIN_HEIGHT = 160.0, 100.0


def rgba(value: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    """`#RRGGBB` or `#RRGGBBAA` as an (r, g, b, a) tuple, `alpha` scaling the model's own."""
    text = value.lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    r, g, b = (int(text[i : i + 2], 16) for i in (0, 2, 4))
    a = int(text[6:8], 16) if len(text) >= 8 else 255
    return (r, g, b, round(a * alpha))


def sides(value: Any) -> tuple[float, float, float, float]:
    """A margin or thickness as (top, right, bottom, left): the model gives a number, a [t, r, b, l] list or a {left, top, right, bottom} mapping."""
    if isinstance(value, (int, float)):
        return (float(value),) * 4
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return tuple(float(v) for v in value)  # type: ignore[return-value]
    if isinstance(value, dict):
        return (float(value.get("top", 0)), float(value.get("right", 0)), float(value.get("bottom", 0)), float(value.get("left", 0)))
    return (0.0, 0.0, 0.0, 0.0)


def style_value(style: dict[str, Any] | None, key: str) -> Any:
    """A style key of the model by its name in any case (the model writes the shell's own spelling; this application names no key of the shell's schema: it reads them)."""
    return next((v for k, v in (style or {}).items() if k.lower() == key), None)


class Palette:
    """The model's tokens, with a fallback for what it lacks."""

    def __init__(self, tokens: dict[str, Any]) -> None:
        self.tokens = tokens

    def color(self, name: str) -> str:
        value = self.tokens.get(name, FALLBACK.get(name, "#808080"))
        return value if isinstance(value, str) and value.startswith("#") else FALLBACK.get(name, "#808080")

    def resolve(self, value: Any, default: str) -> str:
        """A style value: a colour, a token reference {token, value}, or none (then `default`, a token name)."""
        if isinstance(value, dict) and isinstance(value.get("value"), str) and value["value"].startswith("#"):
            return str(value["value"])
        if isinstance(value, str) and value.startswith("#"):
            return value
        return self.color(default)


def chips(blocks: list[dict[str, Any]]) -> list[str]:
    """The labels of what a surface shows, in order: each module by its name (or label), each other block by its kind; containers are looked through."""
    labels: list[str] = []
    for block in blocks:
        if block.get("type") == "module":
            labels.append(str(block.get("label") or block.get("name") or block.get("module") or "module"))
        elif block.get("type") in ("block", "if", "for"):
            inner = chips(block.get("children", []) or [])
            if inner:
                labels += inner
            elif block.get("type") == "block" and block.get("kind") not in ("FlexBox", "Box", "Spacer", "Stack", None):
                labels.append(str(block.get("name") or block.get("kind")))
    return labels


class PreviewPane:
    """Draws a preview model into `stage` (a node of `window` with a layout size) and keeps the last good picture."""

    def __init__(self, window: Any, stage: Any, message: Any = None) -> None:
        self.window = window
        self.stage = stage
        self.message = message  # a node whose text says why the picture is not current, or None
        self.model: dict[str, Any] | None = None
        self._nodes: list[Any] = []
        self.unavailable = False

    # -- the model ---------------------------------------------------------------------------------------------------

    def show(self, model: dict[str, Any] | None) -> None:
        """A new model replaces the picture. A model with no surface and an error finding (a syntax error in the main shell file) is not a picture: the last good one stays, dimmed."""
        usable = model is not None and (model.get("surfaces") or not any(f.get("severity") == "error" for f in model.get("findings", [])))
        if usable:
            self.model = model
            self.unavailable = False
        elif model is not None or self.model is None:
            self.unavailable = True
        self.paint()

    def refit(self) -> None:
        """The pane changed size: draw again at the new scale."""
        self.paint()

    # -- drawing -----------------------------------------------------------------------------------------------------

    def _clear(self) -> None:
        for node in self._nodes:
            node.destroy()
        self._nodes = []

    def _add(self, parent: Any, kind: str, **props: Any) -> Any:
        node = self.window.create(kind, hit_testable=False, a11y_hidden=True, **props)
        parent.add_child(node)
        if parent is self.stage:
            self._nodes.append(node)
        return node

    def _box(self, parent: Any, x: float, y: float, w: float, h: float, fill: tuple[int, int, int, int] | None, radius: float = 0.0, **extra: Any) -> Any:
        props: dict[str, Any] = {"position": "absolute", "x": x, "y": y, "width": max(w, 0.0), "height": max(h, 0.0), "corner_radius": radius, **extra}
        if fill is not None:
            props["fill"] = fill
        return self._add(parent, "box", **props)

    def _text(self, parent: Any, text: str, x: float, y: float, size: float, color: tuple[int, int, int, int], width: float | None = None) -> Any:
        props: dict[str, Any] = {"position": "absolute", "x": x, "y": y, "text": text, "font_size": size, "fill": color, "wrap": "none", "overflow": "ellipsis"}
        if width is not None:
            props["width"] = max(width, 1.0)
        return self._add(parent, "text", **props)

    def paint(self) -> None:
        self._clear()
        width, height = float(self.stage.get("layout_width") or 0.0), float(self.stage.get("layout_height") or 0.0)
        if self.message is not None:
            self.message.set(text="Preview unavailable: see Problems" if self.unavailable else "")
        if self.model is None or width < 1 or height < 1:
            return
        if width < MIN_WIDTH or height < MIN_HEIGHT:
            self._text(self.stage, "Make the pane larger to see the preview", 8.0, 8.0, 12.0, (200, 200, 200, 255), width - 16)
            return
        palette = Palette(self.model.get("tokens", {}))
        for output in self.model.get("outputs", [])[:1]:
            self._output(palette, output, width, height)

    def _output(self, palette: Palette, output: dict[str, Any], width: float, height: float) -> None:
        ow, oh = float(output["width"]), float(output["height"])
        scale = min((width - 16.0) / ow, (height - 16.0) / oh)
        ox, oy = (width - ow * scale) / 2, (height - oh * scale) / 2
        dim = DIM if self.unavailable else 1.0
        name = output.get("name")

        def sx(v: float) -> float:
            return ox + v * scale

        def sy(v: float) -> float:
            return oy + v * scale

        screen = self._box(self.stage, ox, oy, ow * scale, oh * scale, rgba("#0b0a10", dim), 4.0)
        screen.set(clip_children=True)
        for area in self.model.get("desktop", []) if self.model else []:
            if area.get("output") == name:
                self._box(self.stage, sx(area["x"]), sy(area["y"]), area["width"] * scale, area["height"] * scale, rgba(palette.color("color.surface"), 0.35 * dim), 0.0,
                          stroke_width=1.0, stroke_color=rgba(palette.color("color.outline"), 0.6 * dim))
        for surface in (self.model or {}).get("surfaces", []):
            if surface.get("output") not in (None, name):
                continue
            if surface["kind"] == "frame":
                self._frame(palette, surface, ox, oy, ow, oh, scale, dim)
            elif surface.get("status") == "ok" and surface.get("rect"):
                self._surface(palette, surface, sx, sy, scale, dim * (1.0 if surface.get("visible", True) else 0.4), ghost=not surface.get("visible", True))
        self._text(self.stage, f"{name}  {int(ow)}x{int(oh)}", ox + 4, oy + oh * scale + 2, 10.0, (160, 160, 170, round(255 * dim)))

    def _surface(self, palette: Palette, surface: dict[str, Any], sx: Callable[[float], float], sy: Callable[[float], float], scale: float, dim: float, ghost: bool = False) -> None:
        """A surface that is not visible now (a panel that opens on a key) is drawn faint, as a ghost."""
        rect = surface["rect"]
        x, y, w, h = sx(rect["x"]), sy(rect["y"]), rect["width"] * scale, rect["height"] * scale
        fill = palette.resolve(style_value(surface.get("style"), "background"), "color.surface")
        radius = 3.0 if surface["kind"] == "panel" else 0.0
        box = self._box(self.stage, x, y, w, h, rgba(fill, dim * (0.5 if ghost else 1.0)), radius, stroke_width=1.0, stroke_color=rgba(palette.color("color.outline"), dim))
        labels = chips(surface.get("blocks", []))
        small = 10.0
        if h < 8 or w < 24:
            return
        small = 8.0 if h < 16 else small
        self._text(box, str(surface.get("name", "")), 4.0, 2.0, small, rgba(palette.color("color.on_surface"), dim), w - 8)
        horizontal = surface["kind"] == "bar" and (surface.get("edge") in ("top", "bottom", None))
        cx, cy = 4.0, 2.0 + (0.0 if horizontal and h < 22 else small + 3.0)
        if horizontal and h < 22:
            cx = min(4.0 + 7.0 * len(str(surface.get("name", ""))) * 0.9, w * 0.4)
        for label in labels:
            cw, ch = max(28.0, 6.5 * len(label) + 8.0) * 1.0, min(14.0, max(h - cy - 2.0, 0.0)) if not horizontal else min(14.0, max(h - 4.0, 8.0))
            if horizontal and cx + cw > w - 4 or not horizontal and cy + ch > h - 2:
                break
            chip = self._box(box, cx, cy if not horizontal or h >= 22 else (h - ch) / 2, cw, ch, rgba(palette.color("color.surface_raised"), dim), 3.0)
            self._text(chip, label, 4.0, 1.0, 9.0, rgba(palette.color("color.on_surface_muted"), dim), cw - 6)
            if horizontal:
                cx += cw + 4.0
            else:
                cy += ch + 3.0

    def _frame(self, palette: Palette, frame: dict[str, Any], ox: float, oy: float, ow: float, oh: float, scale: float, dim: float) -> None:
        mt, mr, mb, ml = sides(frame.get("margin"))
        tt, tr, tb, tl = sides(frame.get("thickness"))
        ring = palette.resolve(style_value(frame.get("style"), "background"), "color.surface")
        outer = (ox + ml * scale, oy + mt * scale, (ow - ml - mr) * scale, (oh - mt - mb) * scale)
        inner = (outer[0] + tl * scale, outer[1] + tt * scale, outer[2] - (tl + tr) * scale, outer[3] - (tt + tb) * scale)
        r_out = max(list(frame["outer_radius"].values()) or [0]) if isinstance(frame.get("outer_radius"), dict) else 0
        r_in = max(list(frame["inner_radius"].values()) or [0]) if isinstance(frame.get("inner_radius"), dict) else 0
        # the ring is four strips round a window onto the desktop (so what shows through is the desktop, not a filled box)
        for strip in ((outer[0], outer[1], outer[2], inner[1] - outer[1]), (outer[0], inner[1] + inner[3], outer[2], outer[1] + outer[3] - inner[1] - inner[3]),
                      (outer[0], inner[1], inner[0] - outer[0], inner[3]), (inner[0] + inner[2], inner[1], outer[0] + outer[2] - inner[0] - inner[2], inner[3])):
            self._box(self.stage, *strip, rgba(ring, dim), r_out * scale)
        border = frame.get("inner_border")
        if isinstance(border, dict) and border.get("color"):
            self._box(self.stage, *inner, None, r_in * scale, stroke_width=max(1.0, float(border.get("width", 1)) * scale), stroke_color=rgba(str(border["color"]), dim))
        for edge in (frame.get("edges") or {}).values():
            rect = edge.get("rect")
            if rect:
                self._box(self.stage, ox + rect["x"] * scale, oy + rect["y"] * scale, rect["width"] * scale, rect["height"] * scale, None, 0.0, stroke_width=1.0,
                          stroke_color=rgba(palette.color("color.outline"), 0.8 * dim))
        for meld in frame.get("meld_panels") or []:
            rect = meld.get("rect")
            if rect:
                label = str(meld.get("name", ""))
                box = self._box(self.stage, ox + rect["x"] * scale, oy + rect["y"] * scale, rect["width"] * scale, rect["height"] * scale,
                                rgba(palette.color("color.surface_raised"), dim), 3.0, stroke_width=1.0, stroke_color=rgba(palette.color("color.primary"), dim))
                self._text(box, label, 4.0, 2.0, 9.0, rgba(palette.color("color.on_surface"), dim), rect["width"] * scale - 8)

    def alternative(self) -> str:
        """The text alternative of the picture: what a screen reader says for the region."""
        if self.model is None:
            return "Shell preview: no picture yet"
        parts = []
        for surface in self.model.get("surfaces", []):
            kind, name = surface["kind"], surface.get("name", "")
            if surface.get("status", "ok") != "ok":
                parts.append(f"{kind} {name} not shown ({surface.get('status')})")
            elif kind == "frame":
                parts.append(f"frame {name}")
            else:
                rect = surface.get("rect") or {}
                parts.append(f"{kind} {name}, {rect.get('width')} by {rect.get('height')} at {rect.get('x')}, {rect.get('y')}")
        text = "; ".join(parts) or "no surfaces"
        return f"Shell preview: {text}" + (". Unavailable now: showing the last good picture" if self.unavailable else "")
