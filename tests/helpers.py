"""Small helpers shared by tests."""

import yaml

from tess_ui import tokens


def window_unthemed(window) -> bool:
    """Whether `tess_re`'s window has no theme of its own (M42 Phase 7).
    `tess_re` 0.3.5 removes `Window.theme` altogether, which is unthemed too."""
    try:
        theme = window.theme
    except AttributeError:
        return True
    return not theme.is_set()


def elevation(node) -> float:
    """A node's MD3 elevation level. A Tesserae-built node carries it as
    `shadows` (0.3.4 nodes have no `elevation`); a node from one of
    `tess_re`'s legacy factories still has its own `elevation`."""
    shadows = node.get("shadows")
    if not shadows:
        try:  # a legacy node's own level, while `tess_re` 0.3.4 has one
            return node.get("elevation")
        except (AttributeError, ValueError):  # 0.3.5 has no `elevation` (its shim raised AttributeError,
            return 0.0                         # the release ValueError); no shadows is level 0
    for level in range(6):
        if shadows == tokens.elevation_shadows(level):
            return float(level)
    raise AssertionError(f"shadows {shadows!r} aren't an MD3 elevation level")


def view_from(expanded_yaml: str, **kwargs):
    """A Tesserae `View` built from `expand_components`' YAML text -- what
    `tess_re.View("T.yaml", source=...)` did before M37."""
    from tess_ui import View

    return View(yaml.safe_load(expanded_yaml), **kwargs)
