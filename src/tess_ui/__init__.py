"""Tesserae -- a pyCopper-style declarative Python GUI framework, powered
by the Tesserae Render Engine (`tre`) instead of pyCopper's own direct
GLFW/wgpu-py stack.

Real, current surface (v1): `App`, the real single entry point owning a
named `View`/`ViewModel` registry and one live `Window`, letting
`App.show(name)` switch which pair is currently rendered without
re-bootstrapping either. `Component`/`instantiate` are the real,
multi-instance embedded-component layer -- a component gets its own,
independent `ViewModel`, and `instantiate` enforces the identical
`*_View.yaml`/`*_ViewModel.py` naming convention `App.load` already does
for top-level screens. `Repeater` is the declarative-*feeling* layer on
top of that: one list `Signal` as the single source of truth, automatic
keyed add/remove diffing. `Signal`/`Computed`/`Effect`/`batch`/
`untrack`/`ViewModel` are Tesserae's own (`tess_ui.reactive`, M35),
taken over from `tre`, which removes its copy in 0.3.5 (`tre` D5).
`View`/`Component` are Tesserae's too (`tess_ui.view`, M37): views are
built, reconciled and wired by Tesserae on `tre` 0.3.4's building blocks.
"""

from tess_ui.app import App
from tess_ui.component import instantiate
from tess_ui.fonts import register_font
from tess_ui.log import configure_logging
from tess_ui.reactive import Computed, Effect, Signal, ViewModel, batch, untrack
from tess_ui.theme import Theme
from tess_ui.view import Component, View
from tess_ui.repeater import Repeater

__all__ = [
    "App",
    "Component",
    "Computed",
    "Effect",
    "Repeater",
    "Signal",
    "Theme",
    "View",
    "ViewModel",
    "batch",
    "configure_logging",
    "instantiate",
    "register_font",
    "untrack",
]
