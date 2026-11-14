"""The window of the application: a Tesserae UI `App` over a `ConfigSession`. `build()` makes the app, its ViewModel and the shown window without running the event loop, so a test can drive it headlessly."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tess_ui import App
from tess_ui.listeners import handled

from tess_shell_config.session import ConfigSession
from tess_shell_config.shortcuts import Shortcuts
from tess_shell_config.viewmodel import ShellConfigViewModel

__all__ = ["ROOT", "Built", "build"]

#: The application's own project folder: its `Views/` are found here by name.
ROOT = Path(__file__).resolve().parent
TITLE = "Tesserae Shell Configuration"


@dataclass
class Built:
    """What `build` returns: the `app`, the `view` (`app.open_view`), the ViewModel, the shown `window` and the keyboard `shortcuts`."""

    app: App
    view: Any
    viewmodel: ShellConfigViewModel
    window: Any
    shortcuts: Shortcuts


def build(session: ConfigSession, *, width: int = 1280, height: int = 800, dark: bool | str = "system", **options: Any) -> Built:
    """The app for `session`. `options` go to `App` (a test passes `reduced_motion=True`, a theme seed...)."""
    app = App(root=ROOT, width=width, height=height, title=TITLE, dark=dark, stylesheet=ROOT / "Views" / "Main_Stylesheet.yaml", **options)
    viewmodel = ShellConfigViewModel(session)
    app.bind(viewmodel)
    view = app.open_view("Main")
    window = app.show("main")
    viewmodel.shortcuts = shortcuts = Shortcuts(view, viewmodel)
    # a right click anywhere in the Structure area opens the Structure menu (the Menu key and Shift+F10 do too: see `shortcuts.py`)
    view._listen(view.node("root.panes.structure_pane"), "secondary_click", handled(lambda event: viewmodel.structure_actions.open_menu()))
    shortcuts.move_focus(1)  # a key press goes to the focused node, so the window starts with the focus in the Files area
    return Built(app, view, viewmodel, window, shortcuts)
