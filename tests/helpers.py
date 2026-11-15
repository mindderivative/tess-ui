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


def expand_components(yaml_text: str) -> dict:
    """The kind-tree a test's YAML node (`id`, `component`, `with`, `children`) expands to: tests write their input as YAML text, the package itself reads none."""
    from tess_ui.spec import expand_components_to_spec

    return expand_components_to_spec(yaml.safe_load(yaml_text))


def view_from(spec, **kwargs):
    """A Tesserae `View` built from an expanded kind-tree (what `expand_components` returns: the internal form the Python widget factories build from), or from
    a view's TDL text (it starts with the `---` metadata block)."""
    from tess_ui import View

    if isinstance(spec, str):
        from tess_ui.spec.tdl import load_marked_tdl
        from tess_ui.spec.tdl_theme import plain

        spec = plain(load_marked_tdl(spec, "T_View.tdl"))
    return View(spec, **kwargs)
