"""Tesserae's own declarative macro-expansion layer: the Python widget factories (`widgets.button()`, the overlays) expand a `component: Name` /
`with: {...}` node into the `WidgetSpec`-shaped subtree of a `*_Component.yaml` fragment that ships inside the library. See `expand.py` for the real
design and its stated limits. Views, stylesheets and themes are TDL (`tdl.py`, `tdl_stylesheet.py`, `tdl_theme.py`)."""

from __future__ import annotations

from tess_ui.spec.expand import ComponentError, expand_components, expand_components_to_spec
from tess_ui.spec.themes import load_stylesheet, load_theme

__all__ = ["ComponentError", "expand_components", "expand_components_to_spec", "load_stylesheet", "load_theme"]
