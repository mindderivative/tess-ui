"""Tesserae -- a pyCopper-style declarative Python GUI framework, powered
by the Tesserae Render Engine (`tess_re`) instead of pyCopper's own direct
GLFW/wgpu-py stack.

Real, current surface (v1): `App`, the real single entry point owning a
named `View`/`ViewModel` registry and one live `Window`, letting
`App.show(name)` switch which pair is currently rendered without
re-bootstrapping either. `Signal`/`Computed`/`Effect`/`batch`/
`untrack`/`ViewModel` are Tesserae's own (`tess_ui.reactive`, M35),
taken over from `tess_re`, which removes its copy in 0.3.5 (`tess_re` D5).
`View` is Tesserae's too (`tess_ui.view`, M37): views are
built, reconciled and wired by Tesserae on `tess_re` 0.3.4's building blocks.
"""

from tess_ui.app import App
from tess_ui.fonts import register_font
from tess_ui.log import configure_logging
from tess_ui.reactive import Computed, Effect, Signal, ViewModel, batch, untrack
from tess_ui.theme import Theme
from tess_ui.view import View

__all__ = [
    "App",
    "Computed",
    "Effect",
    "Signal",
    "Theme",
    "View",
    "ViewModel",
    "batch",
    "configure_logging",
    "register_font",
    "untrack",
]
