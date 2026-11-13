"""Colour values as the colour picker holds them (the `ColourPicker` view and its `ColourArea`, `ColourStrip`, `ColourField` and `ColourSwatches` controls).

A colour is text: `'#rrggbb'`, or `'#rrggbbaa'` when its alpha is below 1 (lowercase; a fully opaque colour never has the alpha digits). `parse` reads
either form in either case and nothing else, so `'#fff'`, `'red'` and `'ff0000'` are not colours here. The picker also works in hue, saturation, value and
alpha (`hsva`, `from_hsva`); the hue of a grey or a black is not in the text, so `hsva(value, hue)` takes the hue the picker remembers and keeps it for as
long as the text still agrees with it, which is why dragging to a corner and back does not lose the hue.
"""

from __future__ import annotations

import re

__all__ = ["format_hex", "from_hsva", "hsva", "is_valid", "parse", "with_alpha", "with_channel"]

RGBA = tuple[int, int, int, int]
_HEX = re.compile(r"#([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})([0-9a-fA-F]{2})?")
_CHANNELS = {"red": 0, "green": 1, "blue": 2, "alpha": 3}


def parse(text: object) -> RGBA | None:
    """`(r, g, b, a)` bytes for `'#rrggbb'` or `'#rrggbbaa'`; `None` for anything else."""
    found = _HEX.fullmatch(text) if isinstance(text, str) else None
    if found is None:
        return None
    r, g, b, a = found.groups()
    return int(r, 16), int(g, 16), int(b, 16), 255 if a is None else int(a, 16)


def is_valid(text: object) -> bool:
    """Whether `text` is `'#rrggbb'` or `'#rrggbbaa'`."""
    return parse(text) is not None


def format_hex(r: float, g: float, b: float, a: float = 255) -> str:
    """`'#rrggbb'`, or `'#rrggbbaa'` when `a` is below 255; the channels are held to 0 to 255."""
    r, g, b, a = (max(0, min(255, int(n))) for n in (r, g, b, a))
    return f"#{r:02x}{g:02x}{b:02x}" + ("" if a == 255 else f"{a:02x}")


def _byte(x: float) -> int:
    return max(0, min(255, int(x * 255 + 0.5)))


def from_hsva(h: float, s: float, v: float, a: float = 1.0) -> str:
    """The text of a colour given by hue (degrees, 360 is 0), saturation, value and alpha (each 0 to 1, held to it)."""
    s, v, a = (max(0.0, min(1.0, float(n))) for n in (s, v, a))
    h = float(h) % 360.0 / 60.0
    sector, f = int(h), h - int(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r, g, b = ((v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q))[sector % 6]
    return format_hex(_byte(r), _byte(g), _byte(b), _byte(a))


def _hsv_of(r: int, g: int, b: int) -> tuple[float, float, float]:
    high, low = max(r, g, b), min(r, g, b)
    spread = high - low
    if spread == 0:
        hue = 0.0
    elif high == r:
        hue = 60.0 * (((g - b) / spread) % 6)
    elif high == g:
        hue = 60.0 * ((b - r) / spread + 2)
    else:
        hue = 60.0 * ((r - g) / spread + 4)
    return hue % 360.0, (spread / high if high else 0.0), high / 255.0


def hsva(value: str, hue: float | None = None) -> tuple[float, float, float, float]:
    """`(hue, saturation, value, alpha)` of a colour's text: hue in degrees (0 to 360), the others 0 to 1. `hue` is the hue the picker remembers. It is
    returned, as it is, when the colour has no hue of its own (a grey or a black) or when it still makes the colour (to a byte of each channel: a pale colour's
    text cannot say its hue to better than a few degrees, and the remembered one is the finer); otherwise the colour's own hue is. Raises `ValueError` for text
    that is not a colour."""
    rgba = parse(value)
    if rgba is None:
        raise ValueError(f"{value!r} is not a colour written #rrggbb or #rrggbbaa")
    h, s, v = _hsv_of(*rgba[:3])
    a = rgba[3] / 255.0
    if hue is not None and 0.0 <= hue <= 360.0 and (s == 0.0 or v == 0.0 or _agrees(hue, s, v, a, rgba)):
        h = float(hue)
    return h, s, v, a


def _agrees(hue: float, s: float, v: float, a: float, rgba: RGBA) -> bool:
    """Whether the colour of `hue`, `s`, `v` and `a` is `rgba` to within a byte of each channel."""
    made = parse(from_hsva(hue, s, v, a))
    return made is not None and all(abs(m - r) <= 1 for m, r in zip(made, rgba))


def with_alpha(value: str, alpha: float) -> str:
    """The colour of `value` with alpha `alpha` (0 to 1)."""
    rgba = parse(value)
    if rgba is None:
        raise ValueError(f"{value!r} is not a colour written #rrggbb or #rrggbbaa")
    return format_hex(*rgba[:3], _byte(alpha))


def with_channel(value: str, channel: str, number: int) -> str:
    """The colour of `value` with one channel (`red`, `green`, `blue` or `alpha`, 0 to 255) replaced."""
    rgba = parse(value)
    if rgba is None:
        raise ValueError(f"{value!r} is not a colour written #rrggbb or #rrggbbaa")
    if channel not in _CHANNELS:
        raise ValueError(f"a channel is red, green, blue or alpha, not {channel!r}")
    new = list(rgba)
    new[_CHANNELS[channel]] = int(number)
    return format_hex(*new)
