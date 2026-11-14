"""The window's ViewModel: Files, Structure and Text areas over a `ConfigSession`.

The window holds no rule of its own: the file list, the structure rows, the text and the messages are `Signal`s the view binds, and each action is a method the view's handlers call.
Choosing a file in the Files tree opens it; choosing a row in the Structure tree selects that block in the model; a text edit goes to the model, which reparses, and the structure follows
when the text parses. A file with syntax errors shows its errors and no structure.
"""

from __future__ import annotations

from typing import Any

from tess_ui import Effect, Signal, ViewModel, batch, untrack

from tess_shell_config.fileactions import FileActions
from tess_shell_config.folder import FileType
from tess_shell_config.actions import StructureActions
from tess_shell_config.formcontrol import FormController
from tess_shell_config.model import DocumentModel, EditError
from tess_shell_config.services import Services
from tess_shell_config.session import ConfigSession
from tess_shell_config.structure import ancestors, label_of, nodes_for, path_of, value_of
from tess_shell_config.tdl import Node

__all__ = ["ShellConfigViewModel"]

#: Tree values of the Files area: a file is `f:<path from the folder>`, a type's group `g:<label>`.
FILE = "f:"
GROUP = "g:"
#: A folder with more files than this starts with the groups of the Files tree closed (the group of the open file excepted).
MANY_FILES = 12


class ShellConfigViewModel(ViewModel):
    """Serves the `main` view. `session` is the configuration folder's session; nothing here runs a command or touches a file except through it."""

    views = "main"

    def __init__(self, session: ConfigSession) -> None:
        super().__init__()
        self.session = session
        self.file_nodes = Signal([])
        self.file_selected = Signal("")
        self.file_expanded = Signal([])
        self.structure_nodes = Signal([])
        self.structure_selected = Signal("")
        self.structure_expanded = Signal([])
        self.text = Signal("")
        self.has_file = Signal(False)
        self.has_tree = Signal(False)
        self.read_only = Signal(False)
        self.error_rows = Signal([])
        self.title = Signal("No file open")
        self.folder = Signal(str(session.folder))
        self.status = Signal("")
        self.status_is_error = Signal(False)
        self.dirty = Signal(False)
        self.can_undo = Signal(False)
        self.can_redo = Signal(False)
        self.selected_label = Signal("")
        self._known_branches: set[str] = set()
        self.shortcuts: Any = None  # a `Shortcuts`, set by `build`, which has the view to move the focus in
        self.form = FormController(self)  # the form's Signals and handlers (`form_*`, `picker_*`, `file_*`) are put on this ViewModel
        self.structure_actions = StructureActions(self)  # the Structure area's actions (`structure_*`, `can_*`, `menu_*`)
        self.file_actions = FileActions(self)  # the Files area's actions (`file_*`, `can_file_*`, the name prompt)
        self.services = Services(self)  # check and the problems list, status, reload, Apply as I edit, the file watch (`problems`, `check_run`, `shell_state`, `disk_*`, ...)
        self._effects = [Effect(self._file_picked), Effect(self._structure_picked)]
        self.refresh_files()

    # -- the Files area ----------------------------------------------------------------------------------------------------------

    def refresh_files(self) -> None:
        """Read the folder again and rebuild the Files tree (files grouped by type); every group opens."""
        self.session.refresh()
        self._relabel_files()
        self.file_expanded.set(self._open_groups())
        self.folder.set(str(self.session.folder))

    def _open_groups(self) -> list[str]:
        """The groups of the Files tree that start open: every one while the folder has up to `MANY_FILES` files; in a larger folder only the group of the open file (every row of an open group is a dozen nodes the window composes again at each change, so a folder of many files would spend the 16 ms of an edit on rows nobody looks at)."""
        groups = self.file_nodes.get()
        if sum(len(g["children"]) for g in groups) <= MANY_FILES:
            return [g["value"] for g in groups]
        model = self.session.model
        wanted = FILE + model.relative if model is not None else None
        return [g["value"] for g in groups if any(c["value"] == wanted for c in g["children"])]

    def _relabel_files(self) -> None:
        """The Files tree from the files already read, with what each says about itself: unsaved changes, syntax errors. Set only when it differs."""
        groups: list[dict] = []
        for file_type in FileType:
            rows = []
            for f in (f for f in self.session.files if f.type is file_type):
                model = self.session.models.get(f.rel)
                notes = (["unsaved"] if model and model.dirty else []) + ([] if (model.valid if model else f.parses) else ["syntax errors"])
                short = f.rel.split("/", 1)[1] if "/" in f.rel else f.rel  # the group already says Shells, Modules...
                rows.append({"value": FILE + f.rel, "label": short + (f" ({', '.join(notes)})" if notes else "")})
            if rows:
                groups.append({"value": GROUP + file_type.label, "label": file_type.label, "children": rows})
        if groups != self.file_nodes.get():
            self.file_nodes.set(groups)

    def _file_picked(self) -> None:
        value = self.file_selected.get()
        if value.startswith(FILE):
            rel = value[len(FILE):]
            if self.session.current != rel or rel not in self.session.models:  # the file the model already shows needs no reopening
                untrack(lambda: self.open_file(rel))

    def close_view(self) -> None:
        """No file is open any more (the open one was renamed or deleted): the text, the structure and the form are empty."""
        batch(self._close_view_now)

    def _close_view_now(self) -> None:
        self.has_file.set(False)
        self.has_tree.set(False)
        self.text.set("")
        self.read_only.set(False)
        self.error_rows.set([])
        self.structure_nodes.set([])
        self.structure_selected.set("")
        self.selected_label.set("")
        self.title.set("No file open")
        self.dirty.set(False)
        self.can_undo.set(False)
        self.can_redo.set(False)
        self.structure_actions.refresh()
        self.form.refresh()

    def open_file(self, rel: str) -> None:
        """Open a file of the folder: its text shows, and its structure when it parses."""
        try:
            model = self.session.open(rel)
        except (KeyError, OSError) as error:
            self._say(f"Cannot open {rel}: {error}", error=True)
            return
        self._show(model, new_file=True)
        if model.valid:
            self._say(f"Opened {rel}")
        else:
            self._say(f"{rel} has syntax errors: the structure view is off until it parses. Fix it in the text view.", error=True)

    # -- the Structure area ------------------------------------------------------------------------------------------------------

    def _structure_picked(self) -> None:
        value = self.structure_selected.get()
        model = self.session.model
        if not value or model is None or not model.valid:
            return
        try:
            path = path_of(value)
        except ValueError:
            return
        untrack(lambda: batch(lambda: self._select(model, path)))

    def _select(self, model: DocumentModel, path: tuple[int, ...]) -> None:
        if model.selection == path:
            return
        try:
            model.select(path)
        except EditError as error:
            self._say(str(error), error=True)
            return
        self._describe_selection(model)
        self.form.refresh()
        self.structure_actions.refresh()

    # -- the Text area -----------------------------------------------------------------------------------------------------------

    def text_edited(self) -> None:
        """The text view changed the text (the handler of the editor's edits): the model reparses, and the structure follows when it parses."""
        model = self.session.model
        if model is None:
            return
        try:
            model.set_text(self.text.get())
        except EditError as error:
            self._say(str(error), error=True)
            self.text.set(model.display_text)
            return
        self._show(model, new_file=False)
        self.services.edited(typing=True)

    def key_pressed(self, key: str, ctrl: bool, shift: bool, alt: bool) -> None:
        """Every key that reaches the window's root: the shortcuts (`shortcuts.py`) act on it, once `build` has attached them."""
        if self.shortcuts is not None:
            self.shortcuts.handle(str(key), bool(ctrl), bool(shift), bool(alt))

    # -- actions -----------------------------------------------------------------------------------------------------------------

    def save(self) -> None:
        """Write the open file (a temporary file and a rename; the first save keeps the old content in the application's state folder), then check it. A file another program changed since is not overwritten."""
        self.services.save()

    def sync(self) -> None:
        """The model changed by a structure edit (the form, a menu): bring the text, the structure, the selection and the flags in step with it."""
        model = self.session.model
        if model is not None:
            self._show(model, new_file=False, set_text=True)
            self.services.edited()

    def undo(self) -> None:
        model = self.session.model
        if model is not None and model.undo():
            self._show(model, new_file=False, set_text=True)
            self._say("Undone")
            self.services.edited()

    def redo(self) -> None:
        model = self.session.model
        if model is not None and model.redo():
            self._show(model, new_file=False, set_text=True)
            self._say("Redone")
            self.services.edited()

    def format_file(self) -> None:
        """Run `tess_dl.format` on the open file. Never done unless asked."""
        model = self.session.model
        if model is None:
            return
        try:
            model.format_file()
        except EditError as error:
            self._say(str(error), error=True)
            return
        self._show(model, new_file=False, set_text=True)
        self._say("Formatted")
        self.services.edited()

    # -- showing the model -------------------------------------------------------------------------------------------------------

    def _show(self, model: DocumentModel, *, new_file: bool, set_text: bool | None = None, refresh_form: bool = True) -> None:
        """Bring every Signal in step with the model, in one batch so the window is composed once. The text is written back to the editor only when the model changed it (a new file, undo, format), never while the person types."""
        form = self.form
        focused = form._focused()  # the form field that holds the focus: its row is built again from the file, and the focus goes back to the same field of the new row
        held, form._busy = form._busy, True  # a field that loses its focus in the process is not a commit of what it held
        try:
            batch(lambda: self._show_now(model, new_file=new_file, set_text=set_text, refresh_form=refresh_form))
        finally:
            form._busy = held
        form._restore(focused)

    def _show_now(self, model: DocumentModel, *, new_file: bool, set_text: bool | None, refresh_form: bool) -> None:
        if new_file or set_text:
            self.text.set(model.display_text)
        if model.relative.startswith("Modules/"):  # a module's params are what the Add menu and the forms of its calls say
            self.session.update_modules()
        self.has_file.set(True)
        self.read_only.set(not model.utf8)
        self.title.set(model.relative + ("  (read only: not UTF-8)" if not model.utf8 else ""))
        self.has_tree.set(model.valid)
        self.error_rows.set([{"text": f"line {e.line}, column {e.column}: {e.message}" + (f" ({e.hint})" if e.hint else ""), "code": e.code} for e in model.errors])
        self._structure(model)
        self._flags(model)
        self._relabel_files()
        wanted = FILE + model.relative
        if self.file_selected.get() != wanted:
            self.file_selected.set(wanted)
        opened = self.file_expanded.get()
        group = next((g["value"] for g in self.file_nodes.get() if any(c["value"] == wanted for c in g["children"])), None)
        if group is not None and group not in opened:  # the file that is open shows in the Files tree
            self.file_expanded.set([*opened, group])
        if refresh_form:
            self.form.refresh()

    def _structure(self, model: DocumentModel) -> None:
        rows = nodes_for(model.document)
        self.structure_nodes.set(rows)
        branches = {r["value"] for r in _walk_rows(rows) if r.get("children")}
        opened = set(self.structure_expanded.get()) & branches
        opened |= branches - self._known_branches
        self._known_branches = branches
        selection = model.selection
        if selection is not None:
            opened |= set(ancestors(selection))
        self.structure_expanded.set(sorted(opened))
        wanted = value_of(selection) if selection is not None else ""
        if self.structure_selected.get() != wanted:
            self.structure_selected.set(wanted)
        self._describe_selection(model)

    def _describe_selection(self, model: DocumentModel) -> None:
        node: Node | None = model.selected
        self.selected_label.set(f"Selected: {label_of(node)}" if node is not None else "")

    def _flags(self, model: DocumentModel) -> None:
        self.dirty.set(model.dirty)
        self.can_undo.set(model.can_undo)
        self.can_redo.set(model.can_redo)
        self.structure_actions.refresh()

    def _say(self, message: str, *, error: bool = False) -> None:
        self.status.set(message)
        self.status_is_error.set(error)


def _walk_rows(rows: list[dict]):
    for row in rows:
        yield row
        yield from _walk_rows(row.get("children", []))
