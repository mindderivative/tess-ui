"""A `Window` view opened by an app: the frame it is.

`app.open_view("Window")` opens a `Window_View.tdl` whose root is a `Window` widget. It is the app's frame: mounted in the OS window once, for as long as
the app runs, with the screens (the views it calls with a `Route`) shown inside it. There is one per app.
"""

from __future__ import annotations

from typing import Any

__all__ = ["Frame"]


class Frame:
    """The window view an app is showing: its name, its view, and the screens in it. A screen is a routed call of a view: the view is registered under its
    name (`Settings_View.tdl` is `Settings`) and the route, and shown in that node while it is the app's current screen; the others are hidden (out of the
    layout), with their state."""

    def __init__(self, app: Any, name: str, view: Any) -> None:
        self.app = app
        self.name = name
        self.view = view
        self.screens: dict[str, str | None] = {}  # a screen's name -> the id of the node it shows in (None: a lazy screen not built yet)
        self.parents: dict[str, str | None] = {}  # a nested screen's name -> the screen it is inside
        self.records: dict[str, Any] = {}  # a screen's name -> its `RouteRecord`

    def _routed(self) -> dict[str, tuple[str, Any, Any, str]]:
        found: dict[str, tuple[str, Any, Any, str]] = {}
        self.records = {}
        for record in self.view.handle.composition.routes:
            if record.view in found:
                raise ValueError(f'the screen {record.view!r} is already a routed view: a view is routed once')
            self.records[record.view] = record
            found[record.view] = (record.instance.id if record.instance is not None else None, self.view.screen_of(record), None, record.path)  # type: ignore[assignment]
        return found

    def sync(self) -> None:
        """Makes the app's screens the window view's routed views: registers the new ones, drops the gone or rebuilt ones,
        and puts the current screen's view back where it shows."""
        app = self.app
        wanted = self._routed()
        for screen in list(self.screens):
            if screen not in wanted or app._registered[screen].view is not wanted[screen][1]:
                app._unregister_screen(screen, rebuilt=screen in wanted)
                del self.screens[screen]
        for screen, (node_id, component, viewmodel, route) in wanted.items():
            if screen not in self.screens:
                app._register_screen(screen, component, viewmodel, route)
            self.screens[screen] = node_id
        self.parents = {screen: (record.parent.view if record.parent is not None else None) for screen, record in self.records.items()}
        app._set_guards({screen: self._guard_of(record) for screen, record in self.records.items() if record.guard is not None or record.parent is not None})
        if app._playing is not None:
            return  # a transition is showing both screens; it leaves the right one when it ends
        self._show_only(app._current)

    def _guard_of(self, record: Any) -> Any:
        """What the app asks before it goes to this screen: True, False, or the route to go to instead."""
        def guard(params: dict[str, Any]) -> Any:
            refused = record.refused_by()
            return True if refused is None else (refused.redirect if refused.redirect is not None else False)
        return guard

    def ancestry(self, name: str | None) -> list[str]:
        """`name` and the screens it is inside, innermost first: they all show while it is current."""
        out: list[str] = []
        while name is not None and name in self.screens and name not in out:
            out.append(name)
            name = self.parents.get(name)
        return out

    def _show_only(self, current: str | None) -> None:
        showing = set(self.ancestry(current))
        for screen, node_id in self.screens.items():  # only the current screen (and the ones it is inside) shows
            if node_id is not None:
                self.view.node(node_id).set(visible=(screen in showing))

    def activate(self, name: str) -> None:
        """Builds a lazy screen (and the ones it is inside) the first time it is reached; the view syncs, and `sync` finds the new nodes."""
        record = self.records.get(name)
        if record is not None:
            record.activate()

    def show_screen(self, name: str, previous: str | None) -> None:
        if name not in self.screens:
            raise ValueError(f"the window view {self.name!r} has no place for the screen {name!r}: a screen is a routed view "
                             "in the window view")
        self.activate(name)
        self._show_only(name)
