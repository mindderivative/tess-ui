"""Themes and stylesheets as data. Tesserae reads theme and stylesheet TDL files itself and hands the dicts to the `*_spec=` arguments --
`stylesheet_spec=`/`default_theme_spec=`/`custom_theme_spec=` on `View(...)` and `App(...)`, and the theme two on `View.set_theme`/`App.set_theme_specs`.
Tesserae's own cascade and `tess_ui.Theme` validate them (`seed`, `dark`, `colors`, `styles`, `components`, `typography`), so this module only reads,
parses, and checks fonts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from tess_ui.fonts import check_font_families
from tess_ui.project import KINDS, looks_like, tdl_wrong_kind, yaml_refused
from tess_ui.spec import marker
from tess_ui.spec.tdl_stylesheet import load_marked_tdl_stylesheet
from tess_ui.spec.tdl_theme import load_theme_tdl, plain

__all__ = ["load_stylesheet", "load_theme"]

_KIND_OF = {KINDS["stylesheet"][0]: "a stylesheet", KINDS["theme"][0]: "a theme"}


def _load_mapping(path: str | Path, what: str, kind: str) -> dict[str, Any]:
    """The plain mapping of the TDL theme or stylesheet file `path`, read as `kind` (`"theme"` or `"stylesheet"`); a root block that says it is another kind
    is refused with the name to give it."""
    path = Path(path)
    gone = yaml_refused(path)
    if gone is not None:
        raise ValueError(gone)
    suffix = KINDS[kind][0]
    named = next((word for end, word in _KIND_OF.items() if path.name.endswith(end)), None)
    if named is not None and not path.name.endswith(suffix):
        raise ValueError(f"{path}: loaded as {what}, but its name says it's {named} (*{KINDS['stylesheet'][0]} is a stylesheet, *{KINDS['theme'][0]} a theme)")
    text = path.read_text(encoding="utf-8")
    marker.note_if_missing(text, str(path))
    wrong = tdl_wrong_kind(text, kind, path.name)
    if wrong is not None:
        raise ValueError(f"{path}:{wrong[1]}: {wrong[0]}")
    data = load_theme_tdl(text, str(path)) if kind == "theme" else plain(load_marked_tdl_stylesheet(text, str(path)))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: {what} must be a mapping, got {type(data).__name__}")
    return data


def theme_font_families(theme: dict[str, Any]) -> Iterator[str]:
    """Every `font_family` a theme's `typography:` names."""
    typography = theme.get("typography")
    if isinstance(typography, dict):
        for role in typography.values():
            if isinstance(role, dict) and isinstance(role.get("font_family"), str):
                yield role["font_family"]


def view_font_families(spec: Any) -> Iterator[str]:
    """Every `text.font_family` in a view spec, children included."""
    if not isinstance(spec, dict):
        return
    text = spec.get("text")
    if isinstance(text, dict) and isinstance(text.get("font_family"), str):
        yield text["font_family"]
    for child in spec.get("children") or []:
        yield from view_font_families(child)


def load_theme(path: str | Path) -> dict[str, Any]:
    """Reads a theme file (`*_Theme.tdl`) into the dict `tess_re`'s
    `default_theme_spec=`/`custom_theme_spec=` take, for `View(...)` or
    for switching themes later:

    ```python
    view.set_theme(custom_theme_spec=load_theme("themes/Dark_Theme.tdl"))
    ```

    Warns (`tess_ui.fonts.FontFallbackWarning`) if its `Typography`
    names a font family that isn't available.
    """
    theme = _load_mapping(path, "a theme", "theme")
    from tess_ui.spec.cascade import check_theme

    try:
        check_theme(theme, str(path))  # an unknown key is found here, naming the file, and not when the theme is first used
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from None
    check_font_families(theme_font_families(theme), str(path))
    return theme


def load_stylesheet(path: str | Path) -> dict[str, Any]:
    """Reads a stylesheet file (`*_Stylesheet.tdl`) into the dict `tess_re`'s
    `stylesheet_spec=` takes. A file whose keys say it is a view or a theme is refused, naming the file to give it."""
    sheet = _load_mapping(path, "a stylesheet", "stylesheet")
    hint = looks_like(sheet, "stylesheet", Path(path).name)
    if hint:
        raise ValueError(f"{path}: {hint}")
    return sheet
