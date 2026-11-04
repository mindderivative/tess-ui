"""M29 Phase 4: fonts. Tesserae reads a font file and hands `tess_re` the
bytes (`tess_re.register_font`, tess_re M86) -- `tess_re` never opens a font file,
per the user's own rule that `tess_re` gets specs and bytes, never files.

`tess_re` ships four faces and never discovers system fonts. A
`font_family` naming anything else silently falls back to a bundled
face, so Tesserae keeps track of which families are really available
and warns (`FontFallbackWarning`) about any a theme or view names that
isn't. It warns rather than raises because registering a font after a
view already exists is legitimate -- `tess_re` picks it up on the next
frame. Turn it into an error with
`warnings.filterwarnings("error", category=FontFallbackWarning)`.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Iterable

import tess_re

__all__ = [
    "BUNDLED_FAMILIES",
    "FontFallbackWarning",
    "available_families",
    "check_font_families",
    "register_font",
    "set_system_fonts",
]

#: The families of `tess_re`'s four vendored faces (Roboto Regular/Medium,
#: Noto Sans Arabic, Hack Nerd Font Mono), as `tess_re.register_font`
#: itself reports them -- checked against `tess_re`'s own
#: `crates/engine-render/assets/fonts/` at `d6c30ef`.
BUNDLED_FAMILIES = frozenset({"Roboto", "Noto Sans Arabic", "Hack Nerd Font Mono"})

_registered: set[str] = set()


class FontFallbackWarning(UserWarning):
    """A `font_family` names a family that isn't bundled with `tess_re` and
    hasn't been registered, so `tess_re` will draw a bundled face instead."""


def register_font(path: str | Path) -> list[str]:
    """Reads the font file at `path` and registers it with `tess_re`,
    process-wide. Returns the family names it contains -- the exact
    names to use as `font_family`. Registering the same file twice is
    harmless.

    Raises `OSError` if the file can't be read, and `ValueError` (from
    `tess_re`) if it contains no font faces.
    """
    path = Path(path)
    try:
        families = tess_re.register_font(path.read_bytes())
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    _registered.update(families)
    return families


_system_fonts = False


def set_system_fonts(enabled: bool = True) -> None:
    """Lets text fall back to the fonts installed on the system (CJK, Hebrew, Indic, Thai, colour emoji), as the engine
    does when it is on. Off by default, so text looks the same on every machine. Process-wide."""
    global _system_fonts
    import tess_re

    tess_re.set_system_fonts(bool(enabled))
    _system_fonts = bool(enabled)


def available_families() -> frozenset[str]:
    """Every family `tess_re` can draw right now: its bundled ones plus any
    registered through `register_font`."""
    return BUNDLED_FAMILIES | frozenset(_registered)


def check_font_families(families: Iterable[str], source: str) -> None:
    """Warns once, naming `source`, about any of `families` that
    `tess_re` would silently replace with a bundled face."""
    missing = sorted(set(families) - available_families())
    if missing and not _system_fonts:  # with system fonts on, an installed family may be there
        warnings.warn(
            f"{source}: font_family {', '.join(map(repr, missing))} is not bundled or registered -- "
            f"tess_re will fall back to a bundled face. Register it first with "
            f"tess_ui.register_font(path); available: {sorted(available_families())}",
            FontFallbackWarning,
            stacklevel=3,
        )
