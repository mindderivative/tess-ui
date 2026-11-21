"""MD3 design tokens, owned by Tesserae: the
colour scheme from a seed, the shape and elevation scales, MD3 elevation
as `shadows`, the type scale, and colour parsing.

`tess_re` resolves these today, in `engine-md3` and `engine-render`, and
removes them in 0.3.5 (its D7: `tess_re` keeps no theme). The values here are
`tess_re`'s at v0.3.4, and `tests/test_tokens.py` checks them against `tess_re`
while it still has them:

- **colour roles** come from `materialyoucolor`'s TonalSpot scheme with
  `spec_version="2021"`, which `tess_re`'s `material-colors` 0.4.2 follows,
  plus tone 10 for the four light-mode `on_*_container` roles, where
  newer `material-color-utilities` moved to tone 30 (M34's spike: 784 of
  784 role values identical);
- **shapes** and **elevation levels** are `tess_re`'s `engine-md3` scales;
- **elevation as shadows**: 0.3.4 nodes have no `elevation`, only
  `shadows`, so a level becomes `tess_re`'s own key and ambient shadow pair,
  with `engine-render`'s geometry, key first (it paints on top);
- **type styles** are `tess_re`'s 15 MD3 roles.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from materialyoucolor.dynamiccolor.material_dynamic_colors import MaterialDynamicColors
from materialyoucolor.hct import Hct
from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
from tess_utils import parse_color

__all__ = [
    "BASELINE", "BASELINE_SEED", "DENSITY", "DENSITY_LEVELS", "density_token", "ELEVATION_LEVELS", "baseline_scheme", "ROLES", "SHAPES", "TYPE_SCALE", "TypeStyle", "color_scheme",
    "RIPPLE_INITIAL_SCALE", "RIPPLE_MS", "STATE_LAYER",
    "elevation", "elevation_shadows", "FULL_RADIUS", "HEIGHT_CLASSES", "MD3_TRACKING", "MD3_TRACKING_TYPOGRAPHY", "WIDTH_CLASSES", "height_class", "width_class", "resolve_color", "resolve_scheme", "shape", "type_style",
]

RGBA = Tuple[int, int, int, int]

# -- colour -------------------------------------------------------------------

#: Every role `tess_re`'s `ColorScheme.role` answers, in its order.
ROLES = (
    "primary", "on_primary", "primary_container", "on_primary_container", "inverse_primary",
    "primary_fixed", "primary_fixed_dim", "on_primary_fixed", "on_primary_fixed_variant",
    "secondary", "on_secondary", "secondary_container", "on_secondary_container",
    "secondary_fixed", "secondary_fixed_dim", "on_secondary_fixed", "on_secondary_fixed_variant",
    "tertiary", "on_tertiary", "tertiary_container", "on_tertiary_container",
    "tertiary_fixed", "tertiary_fixed_dim", "on_tertiary_fixed", "on_tertiary_fixed_variant",
    "error", "on_error", "error_container", "on_error_container",
    "surface_dim", "surface", "surface_tint", "surface_bright",
    "surface_container_lowest", "surface_container_low", "surface_container",
    "surface_container_high", "surface_container_highest",
    "on_surface", "on_surface_variant", "outline", "outline_variant",
    "inverse_surface", "inverse_on_surface", "surface_variant",
    "background", "on_background", "shadow", "scrim",
)

def _hex(text: str) -> RGBA:
    return (int(text[1:3], 16), int(text[3:5], 16), int(text[5:7], 16), 0xFF)


#: MD3's published baseline colours, for widgets with no theme: `tess_re`'s
#: no-theme colours (its MD3 handover's `baseline`), plus `on_surface` and
#: `secondary` from MD3's baseline scheme. They differ from the scheme the
#: baseline seed generates, as `tess_re`'s did.
#: Density levels (the spec's Spacing and Density, ADR-0002): each token is (default, compact, dense).
DENSITY_LEVELS = ("default", "compact", "dense")
DENSITY: dict[str, tuple[float, float, float]] = {
    "control_height": (40.0, 32.0, 28.0),
    "row_height": (40.0, 32.0, 24.0),
    "menu_item_height": (40.0, 32.0, 28.0),
    "icon_button_container": (40.0, 32.0, 28.0),
    "icon_button_icon": (24.0, 20.0, 20.0),
    "row_padding_x": (12.0, 8.0, 4.0),
    "icon_label_gap": (8.0, 8.0, 4.0),
    "field_padding_x": (12.0, 8.0, 8.0),
    "tree_indent": (20.0, 16.0, 12.0),
    "chevron_box": (24.0, 20.0, 16.0),
    "dock_tab_height": (48.0, 40.0, 32.0),
    "dock_tab_padding": (16.0, 12.0, 8.0),
}


def density_token(level: str, token: str) -> float:
    """The value of density token `token` at `level` (`default`, `compact` or `dense`)."""
    if level not in DENSITY_LEVELS:
        raise ValueError(f"density must be one of {', '.join(DENSITY_LEVELS)}, got {level!r}")
    try:
        return DENSITY[token][DENSITY_LEVELS.index(level)]
    except KeyError:
        raise ValueError(f"no density token {token!r} (known: {', '.join(DENSITY)})") from None


#: The seed of Material 3's baseline colours (#6750A4): the scheme an app with no seed and no theme seed is drawn in, light or dark.
BASELINE_SEED: RGBA = (0x67, 0x50, 0xA4, 0xFF)
#: The state-layer opacities (the spec's State Layers, ADR-0009, ADR-0013): one definition, which `interaction` and `ripple` read. Precedence when several hold: dragged, pressed, focused, hovered.
STATE_LAYER: dict[str, float] = {"hover": 0.08, "focus": 0.10, "pressed": 0.10, "dragged": 0.16}
#: Material Web's `md-ripple` timing, in ms, and the ripple's start size as a fraction of the larger side.
RIPPLE_MS: dict[str, int] = {"hover_fade": 15, "press_grow": 450, "press_fade_in": 105, "minimum_press": 225, "release_fade": 375}
RIPPLE_INITIAL_SCALE = 0.2


BASELINE: dict[str, RGBA] = {role: _hex(value) for role, value in {
    "error": "#B3261E", "inverse_on_surface": "#F4EFF4", "inverse_primary": "#D0BCFF",
    "inverse_surface": "#313033", "on_error": "#FFFFFF", "on_primary": "#FFFFFF",
    "on_primary_container": "#21005D", "on_secondary_container": "#1D192B", "on_surface_variant": "#49454F",
    "on_tertiary_container": "#31111D", "outline": "#79747E", "outline_variant": "#CAC4D0",
    "primary": "#6750A4", "primary_container": "#EADDFF", "scrim": "#000000",
    "secondary_container": "#E8DEF8", "surface": "#FFFBFE", "surface_container": "#F3EDF7",
    "surface_container_high": "#ECE6F0", "surface_container_highest": "#E6E0E9",
    "surface_container_low": "#F7F2FA", "tertiary_container": "#FFD8E4",
    "on_surface": "#1D1B20", "secondary": "#625B71",
}.items()}

def unknown_role(role: str, roles: Any = None) -> ValueError:
    """The error for a colour role that is not one: it names the role and, when one is a slip away, the nearest (`roles` are the known names;
    MD3's own when not given)."""
    import difflib

    known = sorted(baseline_scheme() if roles is None else roles)
    close = difflib.get_close_matches(str(role), known, n=1, cutoff=0.6)
    return ValueError(f"{role!r} is not a colour role" + (f" -- did you mean {close[0]!r}?" if close else f"; they are {', '.join(known[:6])}, ..."))


def theme_color(theme: Any, role: str) -> RGBA:
    """A colour role of `theme`, else of MD3's baseline scheme (all of its roles, not only `BASELINE`'s published few), else the error
    `unknown_role` makes. For a control, which may have no theme."""
    found = theme.role(role)
    if found is not None:
        return found
    base = _full_baseline()
    if role in base:
        return base[role]
    raise unknown_role(role, theme.roles or base)


def baseline_scheme() -> dict[str, RGBA]:
    """Every role, for widgets with no theme: the scheme MD3's baseline
    seed (#6750A4) generates, with MD3's published `BASELINE` values over
    it where they differ."""
    return {**color_scheme(BASELINE["primary"]), **BASELINE}


#: The four roles `tess_re` keeps at tone 10 in light mode.
_TONE_10_LIGHT = {
    "on_primary_container": "primary_palette",
    "on_secondary_container": "secondary_palette",
    "on_tertiary_container": "tertiary_palette",
    "on_error_container": "error_palette",
}


def _argb_to_rgba(argb: int) -> RGBA:
    return ((argb >> 16) & 0xFF, (argb >> 8) & 0xFF, argb & 0xFF, (argb >> 24) & 0xFF)


def _camel(role: str) -> str:
    head, *rest = role.split("_")
    return head + "".join(word.capitalize() for word in rest)


def color_scheme(seed: RGBA, dark: bool = False, contrast: float = 0.0) -> dict[str, RGBA]:
    """Every MD3 role for `seed`, light or dark. `contrast` is MD3's contrast level, from -1 (less) through 0 (the
    standard) to 1 (the most): the roles for a user who asked the OS for more contrast."""
    r, g, b = seed[0], seed[1], seed[2]
    argb = 0xFF000000 | (r << 16) | (g << 8) | b
    scheme = SchemeTonalSpot(Hct.from_int(argb), dark, float(contrast), spec_version="2021")
    roles: dict[str, RGBA] = {}
    for role in ROLES:
        if not dark and contrast == 0.0 and role in _TONE_10_LIGHT:
            roles[role] = _argb_to_rgba(getattr(scheme, _TONE_10_LIGHT[role]).tone(10))
            continue
        dynamic = getattr(MaterialDynamicColors, role, None) or getattr(MaterialDynamicColors, _camel(role))
        roles[role] = _argb_to_rgba(dynamic.get_argb(scheme))
    return roles


_ALPHA = re.compile(r"^(?P<base>.+?)\s*@\s*(?P<pct>\d+(?:\.\d+)?)\s*%$")


def resolve_color(raw: str, roles: Optional[dict[str, RGBA]] = None) -> RGBA:
    """A colour as a style says it: a theme role (from `roles`), or anything `parse_color` takes, optionally ending in `@N%` to scale its
    alpha (`primary@12%`, `#6750A4@50%`; a colour that already has alpha keeps that fraction of it). Raises `ValueError`."""
    text = raw.strip()
    factor = None
    match = _ALPHA.match(text)
    if match:
        percent = float(match.group("pct"))
        if percent > 100:
            raise ValueError(f"the alpha in {raw!r} is {match.group('pct')}%, which is over 100%")
        text, factor = match.group("base"), percent / 100.0
    rgba = roles[text] if roles is not None and text in roles else parse_color(text)
    return rgba if factor is None else (rgba[0], rgba[1], rgba[2], round(rgba[3] * factor))


def _seed_of(theme: Optional[dict[str, Any]]) -> Optional[RGBA]:
    raw = (theme or {}).get("seed")
    return parse_color(raw) if isinstance(raw, str) else None


def resolve_scheme(
    theme_seed: Optional[RGBA],
    dark: bool,
    default_theme: Optional[dict[str, Any]],
    custom_theme: Optional[dict[str, Any]],
    contrast: float = 0.0,
) -> Optional[dict[str, RGBA]]:
    """The scheme a view resolves roles against, by `tess_re`'s `View` rules:
    the seed is `theme_seed`, else the custom theme's `seed:`, else the
    default theme's; `colors:` overrides apply default theme first, then
    custom. `None` when there's no seed at all: roles then don't resolve,
    as in `tess_re`."""
    seed = theme_seed or _seed_of(custom_theme) or _seed_of(default_theme)
    if seed is None:
        return None
    roles = color_scheme(seed, dark, contrast)
    for theme in (default_theme, custom_theme):
        for role, raw in ((theme or {}).get("colors") or {}).items():
            if role not in roles:
                raise ValueError(f"unknown color role {role!r} in theme colors")
            roles[role] = parse_color(raw)
    return roles


# -- shape and elevation ---------------------------------------------------------

#: `tess_re`'s shape scale, in pixels.
SHAPES = {"none": 0.0, "extra_small": 4.0, "small": 8.0, "medium": 12.0, "large": 16.0, "extra_large": 28.0}
#: `tess_re`'s elevation levels.
ELEVATION_LEVELS = {f"level_{n}": float(n) for n in range(6)}


#: The radius of the MD3 `full` shape (a pill, a circle): larger than any node, which the engine rounds down to half its shorter side.
FULL_RADIUS = 9999.0


def shape(name: str) -> Optional[float]:
    """The corner radius of the MD3 shape token `name` (`"small"`, `"medium"`, ... `"full"`), or `None` if it isn't one."""
    return FULL_RADIUS if name == "full" else SHAPES.get(name)


#: MD3's window size classes: the smallest width (dp) of each, and the same for heights.
WIDTH_CLASSES = (("compact", 0.0), ("medium", 600.0), ("expanded", 840.0), ("large", 1200.0), ("extra_large", 1600.0))
HEIGHT_CLASSES = (("compact", 0.0), ("medium", 480.0), ("expanded", 900.0))


def width_class(width: float) -> str:
    """The MD3 window size class for a window `width` wide: `compact` (under 600), `medium`, `expanded` (840), `large` (1200) or `extra_large` (1600)."""
    return [name for name, least in WIDTH_CLASSES if width >= least][-1]


def height_class(height: float) -> str:
    """The MD3 window size class for a window `height` tall: `compact` (under 480), `medium` or `expanded` (900)."""
    return [name for name, least in HEIGHT_CLASSES if height >= least][-1]


def elevation(name: str) -> Optional[float]:
    """The level (0 to 5) of the MD3 elevation token `name`, or `None` if it isn't one."""
    return ELEVATION_LEVELS.get(name)


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


Shadow = Tuple[RGBA, float, float, float, float]


def elevation_shadows(level: float) -> list[Shadow]:
    """MD3 elevation `level` (0–5, fractional allowed) as a `shadows` list,
    `(color, offset_x, offset_y, blur, spread)`: `tess_re`'s key shadow (30%
    black) first, so it paints on top, then its ambient shadow (15%).
    Level 0 is no shadow.

    One difference from `tess_re`'s legacy `elevation`: its ambient shadow
    keeps the node's corner radius, while a `shadows` entry grows it by
    the spread, as CSS does."""
    if level <= 0:
        return []
    key_y = _clamp(level, 0, 1) + _clamp(level - 3, 0, 1) + 2 * _clamp(level - 4, 0, 1)
    key_blur = 2 * _clamp(level, 0, 1) + _clamp(level - 2, 0, 1) + _clamp(level - 4, 0, 1)
    ambient_y = _clamp(level, 0, 1) + _clamp(level - 1, 0, 1) + 2 * _clamp(level - 2, 0, 3)
    ambient_blur = 3 * _clamp(level, 0, 2) + 2 * _clamp(level - 2, 0, 3)
    ambient_spread = _clamp(level, 0, 4) + 2 * _clamp(level - 4, 0, 1)
    return [
        ((0, 0, 0, int(0.30 * 255 + 0.5)), 0.0, float(key_y), float(key_blur), 0.0),
        ((0, 0, 0, int(0.15 * 255 + 0.5)), 0.0, float(ambient_y), float(ambient_blur), float(ambient_spread)),
    ]


# -- type scale --------------------------------------------------------------------


@dataclass(frozen=True)
class TypeStyle:
    font_family: str
    font_weight: float
    font_size: float
    #: A multiple of `font_size`.
    line_height: float
    #: Extra space between letters, in pixels. 0 for every role here (as `tess_re` draws them); `MD3_TRACKING` is Material 3's.
    tracking: float = 0.0


def _roboto(weight: float, size: float, line_height: float) -> TypeStyle:
    return TypeStyle("Roboto", weight, size, line_height)


#: `tess_re`'s 15 MD3 type roles.
TYPE_SCALE = {
    "display_large": _roboto(400, 57, 1.12), "display_medium": _roboto(400, 45, 1.16),
    "display_small": _roboto(400, 36, 1.22), "headline_large": _roboto(400, 32, 1.25),
    "headline_medium": _roboto(400, 28, 1.29), "headline_small": _roboto(400, 24, 1.33),
    "title_large": _roboto(400, 22, 1.27), "title_medium": _roboto(500, 16, 1.50),
    "title_small": _roboto(500, 14, 1.43), "body_large": _roboto(400, 16, 1.50),
    "body_medium": _roboto(400, 14, 1.43), "body_small": _roboto(400, 12, 1.33),
    "label_large": _roboto(500, 14, 1.43), "label_medium": _roboto(500, 12, 1.33),
    "label_small": _roboto(500, 11, 1.45),
}


#: Material 3's tracking for each type role, in pixels. Not applied unless a theme asks for it:
#: `typography: {body_large: {tracking: 0.5}, ...}` in a theme, or `typography: tokens.MD3_TRACKING_TYPOGRAPHY` for all of them.
MD3_TRACKING = {
    "display_large": -0.25, "display_medium": 0.0, "display_small": 0.0, "headline_large": 0.0, "headline_medium": 0.0, "headline_small": 0.0,
    "title_large": 0.0, "title_medium": 0.15, "title_small": 0.1, "body_large": 0.5, "body_medium": 0.25, "body_small": 0.4,
    "label_large": 0.1, "label_medium": 0.5, "label_small": 0.5,
}
MD3_TRACKING_TYPOGRAPHY = {role: {"tracking": tracking} for role, tracking in MD3_TRACKING.items()}


def type_style(role: str) -> Optional[TypeStyle]:
    """The font size, weight, line height and tracking of the MD3 type role `role`, or `None` if it isn't one."""
    return TYPE_SCALE.get(role)


_FULL: dict[str, RGBA] = {}


def _full_baseline() -> dict[str, RGBA]:
    if not _FULL:
        _FULL.update(baseline_scheme())
    return _FULL
