"""The commands of the window, in one table: the menu bar, the toolbar and the keyboard map read the same names, shortcuts and enabled states (the vault's Config App Layout, "Menu map" and AC-CFG-11).

`Commands(viewmodel)` makes the table. Its `menus` and `toolbar` are `Computed` lists the `MenuBar` and the `Toolbar` bind: each entry is rebuilt when a Signal that decides whether its command
can run (or whether a check or radio entry is on) changes, so a menu entry and its toolbar button are enabled together at every step. `run(command_id)` does what the entry does when it is enabled.

The shortcuts are the ones `shortcuts.py` handles; they are text here (the menu shows them, the keyboard handler binds them). The two commands that need the window itself, Quit and Reset layout, call
a hook that `app.build` sets.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from tess_ui.reactive import Computed, Signal

__all__ = ["Command", "Commands", "GO_TO"]

#: The panels `View > Go to` names: (command id, label, the area `Shortcuts` gives the focus to).
GO_TO = (("go_files", "Files", "files_tree"), ("go_structure", "Structure", "structure_tree"), ("go_editor", "Editor", "editor"),
         ("go_view", "View", "view_pane"), ("go_properties", "Properties", "form_pane"), ("go_problems", "Problems", "problem_row"))
_THEMES = (("theme_system", "System", "system"), ("theme_light", "Light", "light"), ("theme_dark", "Dark", "dark"))
#: The Structure submenu, in the vault's order, with the words of the menu (the Structure area's own menu keeps its shorter ones).
_STRUCTURE = (("add", "Add child block...", "Ctrl+Shift+N"), ("duplicate", "Duplicate block", "Ctrl+Shift+D"), ("move_to", "Move block into...", "Ctrl+Shift+M"),
              ("move_up", "Move up", "Alt+Up"), ("move_down", "Move down", "Alt+Down"), ("remove", "Remove block", "Ctrl+Shift+Delete"))


def _flag(signal: Any) -> Callable[[], bool]:
    return lambda: bool(signal.get())


def _is(signal: Any, value: Any) -> Callable[[], bool]:
    return lambda: bool(signal.get() == value)


def _call(function: Callable[..., Any], *args: Any) -> Callable[[], None]:
    return lambda: function(*args)


def _go_to(viewmodel: Any, area: str) -> Callable[[], None]:
    def go() -> None:
        if viewmodel.shortcuts is not None:
            viewmodel.shortcuts.go_to(area)

    return go


@dataclass
class Command:
    """One command: `id` (what a menu entry or toolbar button gives back), the words, what it does, its shortcut as text, its toolbar icon, when it can run, and (a check or radio entry) whether it is on."""

    id: str
    label: str
    run: Callable[[], None]
    shortcut: str = ""
    icon: str = ""
    enabled: Callable[[], bool] = lambda: True
    checked: Callable[[], bool] | None = None
    toggle: bool = False


class Commands:
    """The table, and the lists the view binds."""

    def __init__(self, viewmodel: Any) -> None:
        self.vm = viewmodel
        #: what `build` gives for the commands that need the window: `quit` and `reset_layout`
        self.hooks: dict[str, Callable[[], None]] = {}
        self.table: dict[str, Command] = {}
        self._make()
        self.menus = Computed(self._menus)
        self.toolbar = Computed(self._toolbar)
        viewmodel.menu_bar = self.menus
        viewmodel.tool_items = self.toolbar
        self.menu_chosen, self.tool_chosen = Signal(""), Signal("")  # the `Chosen` the menu bar and the toolbar write; `On_Pick` runs the command
        viewmodel.menubar_chosen, viewmodel.toolbar_chosen = self.menu_chosen, self.tool_chosen

    # -- the table --------------------------------------------------------------------------------------------------------------

    def _hook(self, name: str) -> Callable[[], None]:
        return lambda: self.hooks.get(name, lambda: None)()

    def _make(self) -> None:
        vm, services, files, structure = self.vm, self.vm.services, self.vm.file_actions, self.vm.structure_actions
        add = lambda command: self.table.__setitem__(command.id, command)  # noqa: E731
        add(Command("new_file", "New file...", files.new, "Ctrl+N"))
        add(Command("save", "Save", vm.save, "Ctrl+S", "content_save", lambda: bool(vm.dirty.get())))
        add(Command("rename_file", "Rename file...", files.rename, "F2", enabled=lambda: bool(files.can["rename"].get())))
        add(Command("duplicate_file", "Duplicate file", files.duplicate, "Ctrl+Alt+D", enabled=lambda: bool(files.can["duplicate"].get())))
        add(Command("delete_file", "Delete file", files.delete, "Delete", enabled=lambda: bool(files.can["delete"].get())))
        add(Command("disk_reload", "Reload from disk", services.disk_reload, "Ctrl+Shift+L", enabled=lambda: bool(services.has_disk_change.get())))
        add(Command("disk_keep", "Keep my version", services.disk_keep, "Ctrl+Shift+U", enabled=lambda: bool(services.has_disk_change.get())))
        add(Command("quit", "Quit", self._hook("quit"), "Ctrl+Q"))
        add(Command("undo", "Undo", vm.undo, "Ctrl+Z", "undo", lambda: bool(vm.can_undo.get())))
        add(Command("redo", "Redo", vm.redo, "Ctrl+Y", "redo", lambda: bool(vm.can_redo.get())))
        add(Command("format", "Format file", vm.format_file, "", "format_align_left", lambda: bool(vm.has_tree.get())))
        for name, label, shortcut in _STRUCTURE:
            add(Command(f"structure_{name}", label, getattr(structure, name), shortcut, enabled=_flag(structure.flags[name])))
        for command_id, label, mode in _THEMES:
            add(Command(command_id, label, _call(services.set_theme, mode), checked=_is(services.theme_mode, mode)))
        enabled_of: dict[str, Callable[[], bool]] = {
            "go_structure": lambda: bool(vm.has_tree.get()), "go_editor": lambda: bool(vm.has_file.get()), "go_view": lambda: bool(vm.has_file.get()),
            "go_properties": lambda: bool(vm.form_items.get()), "go_problems": lambda: bool(services.has_problems.get()),
        }
        for command_id, label, area in GO_TO:
            add(Command(command_id, label, _go_to(vm, area), enabled=enabled_of.get(command_id, lambda: True)))
        add(Command("reset_layout", "Reset layout", self._hook("reset_layout")))
        add(Command("check", "Check", services.request_check, "F5", "check_circle", lambda: not services.checking.get()))
        add(Command("reload_shell", "Reload shell", services.reload_shell, "Ctrl+Shift+R", "refresh", lambda: bool(services.shell_running.get())))
        add(Command("apply", "Apply as I edit", lambda: services.apply_changed(not services.apply_on_edit.get()), "Ctrl+Shift+A", "sync",
                    checked=lambda: bool(services.apply_on_edit.get()), toggle=True))

    # -- what the view binds ----------------------------------------------------------------------------------------------------

    def _entry(self, command_id: str) -> dict[str, Any]:
        c = self.table[command_id]
        row: dict[str, Any] = {"value": c.id, "label": c.label, "disabled": not c.enabled()}
        if c.shortcut:
            row["shortcut"] = c.shortcut
        if c.checked is not None:
            row["checked"] = bool(c.checked())
        return row

    def _menus(self) -> list[dict[str, Any]]:
        e = self._entry
        divider = {"divider": True}
        return [
            {"label": "&File", "items": [e("new_file"), e("save"), divider, e("rename_file"), e("duplicate_file"), e("delete_file"), divider, e("disk_reload"), e("disk_keep"), divider, e("quit")]},
            {"label": "&Edit", "items": [e("undo"), e("redo"), divider, e("format"), divider, {"label": "Structure", "submenu": [e(f"structure_{name}") for name, _, _ in _STRUCTURE]}]},
            {"label": "&View", "items": [{"label": "Theme", "submenu": [e(i) for i, _, _ in _THEMES]}, {"label": "Go to", "submenu": [e(i) for i, _, _ in GO_TO]}, divider, e("reset_layout")]},
            {"label": "&Shell", "items": [e("check"), e("reload_shell"), divider, e("apply")]},
        ]

    def _toolbar(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for group, ids in enumerate((("save", "undo", "redo"), ("format",), ("check", "reload_shell", "apply"))):
            if group:
                out.append({"divider": True})
            for command_id in ids:
                c = self.table[command_id]
                item: dict[str, Any] = {"value": c.id, "icon": c.icon, "label": c.label, "disabled": not c.enabled()}
                if c.shortcut:
                    item["shortcut"] = c.shortcut
                if c.toggle:
                    item["toggle"] = True
                    item["pressed"] = bool(c.checked()) if c.checked is not None else False
                out.append(item)
        return out

    def run(self, command_id: str) -> None:
        """Do what a menu entry or toolbar button does, when its command can run now."""
        command = self.table.get(str(command_id))
        if command is not None and command.enabled():
            command.run()
