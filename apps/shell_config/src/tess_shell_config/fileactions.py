"""The Files area's actions: a new file from a type, duplicate, rename, delete (to the trash folder of the application's state folder). The window's ViewModel gets their Signals and handlers from
`FileActions(viewmodel)`: `can_file_duplicate`, `can_file_rename`, `can_file_delete` (enabled while a file is chosen in the Files tree), `file_new`, `file_duplicate`, `file_rename`, `file_delete`, and the name
prompt a new file, a copy or a rename asks (`prompt_open`, `prompt_title`, `prompt_text`, `prompt_error`, `prompt_accept`, `prompt_cancel`).

The work is `fileops.py`; this module chooses what the person is asked (the type of a new file from the shared choice list, then a name in a prompt that stays open and says why while the name is refused),
keeps the open files in step (a file with unsaved changes is not renamed or deleted: nothing would be lost silently) and shows what was done.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tess_ui import Effect, Signal, untrack

from tess_shell_config.fileops import FileOpError, SETTINGS_FILE, create, duplicate, name_of, rename, trash, unique_name
from tess_shell_config.folder import ConfigFile, FileType

__all__ = ["FileActions"]

FILE = "f:"  # the Files tree's value of a file (`viewmodel.FILE`)
#: The types a new file can have, with a line for each.
NEW_TYPES = (
    (FileType.SHELL, "The monitors, bars, panels and popups of a shell."),
    (FileType.MODULE, "A module of your own: params and a layout."),
    (FileType.STYLE, "Classes and per-type defaults."),
    (FileType.STYLESHEET, "Rules that style by selector."),
    (FileType.THEME, "Colours, type, shape, space, elevation and motion, and their modes."),
    (FileType.SETTINGS, "The settings file: one for the folder."),
)


class FileActions:
    """`viewmodel` is the window's ViewModel; the actions work on its session."""

    def __init__(self, viewmodel: Any) -> None:
        self.vm = viewmodel
        self.can = {name: Signal(False) for name in ("duplicate", "rename", "delete")}
        self.prompt_open = Signal(False)
        self.prompt_title = Signal("")
        self.prompt_text = Signal("")
        self.prompt_rows = Signal([])  # one row holding the text the field starts with: the field is built again, with that text, each time the prompt opens
        self._opened = 0
        self.prompt_error = Signal("")
        self._ask: Callable[[str], str | None] | None = None
        for name, flag in self.can.items():
            setattr(viewmodel, f"can_file_{name}", flag)
            setattr(viewmodel, f"file_{name}", getattr(self, name))
        viewmodel.file_new = self.new
        for name in ("prompt_open", "prompt_title", "prompt_text", "prompt_rows", "prompt_error"):
            setattr(viewmodel, name, getattr(self, name))
        viewmodel.prompt_accept = self.accept
        viewmodel.prompt_cancel = self.cancel
        self._effect = Effect(self._refresh)

    # -- what can be done -------------------------------------------------------------------------------------------------------

    @property
    def selected(self) -> ConfigFile | None:
        """The file chosen in the Files tree (`None` when a group or nothing is)."""
        value = self.vm.file_selected.get()
        if not value.startswith(FILE):
            return None
        return next((f for f in self.vm.session.files if f.rel == value[len(FILE):]), None)

    def _refresh(self) -> None:
        entry = self.selected
        flags = {"duplicate": entry is not None and entry.type is not FileType.SETTINGS, "rename": entry is not None and entry.type is not FileType.SETTINGS, "delete": entry is not None}
        untrack(lambda: self._set_flags(flags))

    def _set_flags(self, flags: dict[str, bool]) -> None:
        for name, flag in self.can.items():
            if flag.get() != flags[name]:
                flag.set(flags[name])

    def _need(self, what: str) -> ConfigFile | None:
        entry = self.selected
        if entry is None:
            self.vm._say(f"Choose a file in the Files area first, to {what} it.", error=True)
            return None
        model = self.vm.session.models.get(entry.rel)
        if model is not None and model.dirty and what != "copy":
            self.vm._say(f"{entry.rel} has unsaved changes: save them or undo them first, then {what} it.", error=True)
            return None
        if model is not None and model.dirty:
            self.vm._say(f"{entry.rel} has unsaved changes: the copy is of the saved file.")
        return entry

    # -- the actions ------------------------------------------------------------------------------------------------------------

    def new(self) -> None:
        """Ask which type of file to make (the choice list), then its name."""
        options = [{"value": t.root, "label": t.root, "hint": line, "colour": ""} for t, line in NEW_TYPES]
        self.vm.form.open_choice("new_file", "New file of type", options, hooks={"new_file": self._type_chosen})

    def _type_chosen(self, root: str) -> None:
        file_type = FileType.for_root(root)
        session = self.vm.session
        if file_type is FileType.SETTINGS:
            if any(f.type is FileType.SETTINGS for f in session.files):
                self.vm._say(f"{SETTINGS_FILE} exists already: it is the one file of its kind.", error=True)
                return
            self._done(lambda: create(session.folder, session.files, file_type, "Settings"), f"Made {SETTINGS_FILE}")
            return
        default = unique_name(session.files, file_type, f"New_{file_type.root}")
        self._prompt(f"Name of the new {file_type.root.lower()}", default, lambda name: self._make(file_type, name))

    def _make(self, file_type: FileType, name: str) -> str | None:
        session = self.vm.session
        return self._attempt(lambda: create(session.folder, session.files, file_type, name), f"Made {file_type.root.lower()} {name}")

    def duplicate(self) -> None:
        entry = self._need("copy")
        if entry is None or entry.type is FileType.SETTINGS:
            if entry is not None:
                self.vm._say("settings.tdl is the one file of its kind: it cannot be copied.", error=True)
            return
        session = self.vm.session
        default = unique_name(session.files, entry.type, f"{name_of(entry)}_Copy")
        self._prompt(f"Name of the copy of {entry.rel}", default, lambda name: self._attempt(lambda: duplicate(session.folder, session.files, entry, name), f"Copied {entry.rel} as {name}"))

    def rename(self) -> None:
        entry = self._need("rename")
        if entry is None:
            return
        if entry.type is FileType.SETTINGS:
            self.vm._say("settings.tdl keeps its name: the shell looks for that file.", error=True)
            return
        self._prompt(f"New name of {entry.rel}", name_of(entry), lambda name: self._attempt(lambda: self._rename(entry, name), f"Renamed {entry.rel} to {name}", closes=entry.rel))

    def _rename(self, entry: ConfigFile, name: str) -> str:
        session = self.vm.session
        return rename(session.folder, session.files, entry, name, session.state_dir)

    def delete(self) -> None:
        """Move the chosen file to the trash folder of the state folder. It is never removed."""
        entry = self._need("delete")
        if entry is None:
            return
        session = self.vm.session
        moved: list[str] = []

        def run() -> str:
            moved.append(str(trash(session.folder, entry, session.state_dir)))
            return ""

        self._attempt(run, "", closes=entry.rel)
        if moved:
            self.vm._say(f"Moved {entry.rel} to the trash folder: {moved[0]}. It is not removed.")

    # -- the name prompt --------------------------------------------------------------------------------------------------------

    def _prompt(self, title: str, text: str, ask: Callable[[str], str | None]) -> None:
        self._ask = ask
        self.prompt_title.set(title)
        self.prompt_text.set(text)
        self._opened += 1
        self.prompt_rows.set([{"id": self._opened, "text": text}])
        self.prompt_error.set("")
        self.prompt_open.set(True)

    def accept(self, text: str) -> None:
        """The person confirmed the name. A refused name leaves the prompt open with the reason."""
        ask = self._ask
        if ask is None:
            self.prompt_open.set(False)
            return
        problem = ask(str(text).strip())
        if problem:
            self.prompt_text.set(str(text))
            self.prompt_error.set(problem)
            return
        self._ask = None
        self.prompt_open.set(False)

    def cancel(self) -> None:
        self._ask = None
        self.prompt_open.set(False)

    # -- doing it -----------------------------------------------------------------------------------------------------------------

    def _attempt(self, work: Callable[[], str], message: str, closes: str | None = None) -> str | None:
        """Run an operation of `fileops`. Returns the reason when it is refused (the prompt shows it), else `None` after the window shows the result: the folder read again, the new file open."""
        try:
            rel = work()
        except FileOpError as error:
            self.vm._say(str(error), error=True)
            return str(error)
        session = self.vm.session
        if closes is not None:
            session.close(closes)
            if self.vm.file_selected.get() == FILE + closes:
                self.vm.file_selected.set("")
            if session.current is None:
                self.vm.close_view()
        self.vm.refresh_files()
        if rel:
            self.vm.open_file(rel)
        if message:
            self.vm._say(message)
        return None

    def _done(self, work: Callable[[], str], message: str) -> None:
        self._attempt(work, message)
