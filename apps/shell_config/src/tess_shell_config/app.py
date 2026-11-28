"""The window of the application: a Tesserae UI `App` over a `ConfigSession`. `build()` makes the app, its ViewModel and the shown window without running the event loop, so a test can drive it headlessly."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tess_ui import App, tokens
from tess_ui.listeners import handled

from tess_shell_config.files import SaveError
from tess_shell_config.preview_view import PreviewPane
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
    settings: Any = None
    preview: Any = None

    def close(self) -> None:
        """Keep where the panels are, and stop what `live` started (the file watch)."""
        self.remember_layout()
        self.viewmodel.services.stop()

    def remember_layout(self) -> None:
        """Write the dock's arrangement to the settings (the state folder): the next start puts the panels back. A folder that cannot be written is not worth a message here."""
        if self.settings is not None:
            with contextlib.suppress(SaveError, KeyError, ValueError):
                self.settings.set_dock_layout(self.view.dock_host("root.dock").layout())


#: The window's accent seed (Material's baseline purple); the light and dark schemes are made from it.
THEME_SEED = (0x67, 0x50, 0xA4, 0xFF)
_DARK: dict[str, bool | str] = {"system": "system", "light": False, "dark": True}


def build(session: ConfigSession, *, width: int = 1280, height: int = 800, dark: bool | str | None = None, live: bool = False, **options: Any) -> Built:
    """The app for `session`. `options` go to `App` (a test passes `reduced_motion=True`, a theme seed...). `live` starts what runs beside the window: the file watch, the first `status` and `check`, each
    command on a worker thread whose answer is posted to the loop (`close` stops the watch). Without it nothing runs a command or watches the folder."""
    from tess_shell_config.settings import Settings

    # `dark`: True, False or "system" for this run (the `--theme` flag); None is what the window remembered. The roles only have a dark scheme when the App has a seed: without one the window
    # kept the engine's light roles whatever `dark` said, which is why the window was white on a dark desktop.
    options.setdefault("theme_seed", THEME_SEED)
    remembered = Settings(session.state_dir).theme
    options.setdefault("density", "compact")  # a configuration tool: the spec's compact level (rows 32, 8 px in, 16 per level), which replaces the tree override the window had
    app = App(root=ROOT, width=width, height=height, title=TITLE, dark=_DARK[remembered] if dark is None else dark, stylesheet=ROOT / "Views" / "Main_Stylesheet.tdl", **options)
    viewmodel = ShellConfigViewModel(session)
    viewmodel.services.theme_setter = lambda mode: app.set_dark(_DARK[mode])
    if dark is not None:
        viewmodel.services.set_theme("dark" if dark is True else "light" if dark is False else "system", remember=False)
    app.bind(viewmodel)
    view = app.open_view("Main")
    window = app.show("main")
    viewmodel.shortcuts = shortcuts = Shortcuts(view, viewmodel)
    # a right click anywhere in the Structure area opens the Structure menu (the Menu key and Shift+F10 do too: see `shortcuts.py`)
    view._listen(view.node("root.dock.structure_panel.structure_pane"), "secondary_click", handled(lambda event: viewmodel.structure_actions.open_menu()))
    if live:
        viewmodel.services.start(app.thread_handle().call_soon, lambda ms, fn: window.after(ms, fn))
    dock_host = view.dock_host("root.dock")
    arrangement = dock_host.layout()  # as the dock starts, before a remembered layout is put back: what Reset layout goes back to
    viewmodel.commands.hooks["quit"] = app.close

    def reset_layout() -> None:
        with contextlib.suppress(KeyError, ValueError, TypeError):
            dock_host.restore(arrangement)
        with contextlib.suppress(SaveError, KeyError, ValueError):
            Settings(session.state_dir).set_dock_layout(arrangement)

    viewmodel.commands.hooks["reset_layout"] = reset_layout
    settings = Settings(session.state_dir)
    if settings.dock_layout is not None:  # the panels where the person left them (a layout that no longer fits is skipped, not an error: `restore` ignores what the dock does not have)
        with contextlib.suppress(KeyError, ValueError, TypeError):
            view.dock_host("root.dock").restore(settings.dock_layout)
    shortcuts.move_focus(1)  # (this shows the Files tab) a key press goes to the focused node, so the window starts with the focus in the Files area
    stage = view.node("root.dock.view_panel.view_pane.preview_stage")
    roles = view._scheme or tokens.BASELINE
    preview = PreviewPane(window, stage, tuple(roles["on_surface"]), tuple(roles["surface_container_high"]))
    drawn = [(0.0, 0.0)]

    def refit(event: Any = None) -> None:
        size = (float(stage.get("layout_width") or 0.0), float(stage.get("layout_height") or 0.0))
        if size != drawn[0]:  # drawing adds nodes, which lays out again: only a new size draws again
            drawn[0] = size
            preview.refit()

    view._listen(stage, "layout", refit)
    viewmodel.services.preview_sink = preview.show
    viewmodel.services.request_preview(soon=True)
    return Built(app, view, viewmodel, window, shortcuts, settings, preview)
