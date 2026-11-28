"""The form's side of the window's ViewModel: the Signals the view binds, the handlers its widgets call, the picker list (choices, units) and the file dialog.

`FormController(viewmodel)` puts its names on the ViewModel, as the toolkit's own `FileDialogRequest` does (`form_items`, `form_commit`, `picker_open`, `file_open`, ...), so the view's handlers find them there. It owns the
`Form` (the part that knows the schema and writes the document) and does only the window's work: publish the rows, keep the focus on the row being edited while the row is rebuilt from the file, tell the ViewModel
when the document changed so the text and the structure follow, and open the list or the dialog a button asked for.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from tess_ui import Effect, Signal, batch
from tess_ui.reactive import untrack
from tess_ui.file_dialog import FileDialogRequest

from tess_shell_config.form import BlockStore, Form, Outcome
from tess_shell_config.structure import value_of
from tess_shell_config.widgets import PathWidget

__all__ = ["FormController"]

#: The node id of a form row's widgets holds the row's loop key: `...form_item[k:Width#3].row...`.
_ITEM = re.compile(r"form_item\[([^\]]*)\]")
_UP = {"arrowup", "up"}
_DOWN = {"arrowdown", "down"}


class FormController:
    """`viewmodel` is the window's ViewModel; its `session` has the schema (without one the form says so and stays empty)."""

    def __init__(self, viewmodel: Any) -> None:
        self.vm = viewmodel
        schema = viewmodel.session.schema
        self.form: Form | None = Form(schema) if schema is not None else None
        self.items = Signal([])
        self.notes = Signal([])
        self.title = Signal("")
        self.picker_open = Signal(False)
        self.picker_title = Signal("")
        self.picker_items = Signal([])
        self.picker_current = Signal("")
        self.picker_chosen = Signal("")
        self.picked_value = Signal("")  # the row a choice picker of the form last chose (it writes it before the key is committed)
        self.picker_anchor = Signal("structure_tree")
        self.files = FileDialogRequest(viewmodel)
        self._picking: str | None = None  # which command chooser is open
        self._busy = False
        self._hooks: dict[str, Any] = {}
        self._closing = Effect(self._chooser_closed)
        for name, signal in {"form_items": self.items, "form_notes": self.notes, "form_title": self.title, "picker_open": self.picker_open, "picker_title": self.picker_title,
                             "picker_items": self.picker_items, "picker_current": self.picker_current, "picker_chosen": self.picker_chosen, "picked_value": self.picked_value, "picker_anchor": self.picker_anchor}.items():
            setattr(viewmodel, name, signal)
        for name in ("commit", "reset", "expression", "token", "pick_choice", "pick_unit", "pick_option", "browse", "colour", "key", "group", "block"):
            setattr(viewmodel, ("form_" if name != "pick_option" else "") + name, getattr(self, name))

    # -- publishing --------------------------------------------------------------------------------------------------------------

    def refresh(self) -> None:
        """Build the form for what the open file has selected, and show it."""
        model = self.vm.session.model
        if self.form is None:
            self.notes.set(["The form needs the shell's schema: none was read, so there are no keys to show."])
            self.items.set([])
            self.title.set("")
            return
        self.form.schema = self.vm.session.schema or self.form.schema  # the schema with the user's own modules
        self.form.build(model, self.vm.session.folder)
        self._set_signals()

    def _set_signals(self) -> None:
        form = self.form
        if form is None:
            return
        view = form.view
        self.title.set(view.title)
        if view.notes != self.notes.get():
            self.notes.set(list(view.notes))
        self.items.set(view.items)

    def _restore(self, held: str | None) -> None:
        """The row being edited was built again from the file (so what it shows is what the file has): put the focus back on the same widget of the new row."""
        if held is not None and self.form is not None:
            self._refocus(held, {item["id"]: item["key"] for item in self.form.view.items})

    def _focused(self) -> str | None:
        """The id of the form node that holds the focus, or `None` (the focus is elsewhere, so it is not taken back)."""
        shortcuts = self.vm.shortcuts
        if shortcuts is None:
            return None
        view = shortcuts.view
        for inst in view.handle.composition.walk():
            if "form_item[" in inst.id:
                try:
                    if view.node(inst.id).get("focused"):
                        return inst.id
                except (KeyError, ValueError):
                    continue
        return None

    def _refocus(self, node_id: str, keys: dict[str, str]) -> None:
        match = _ITEM.search(node_id)
        if match is None:
            return
        old = match.group(1)
        row = old.rsplit("#", 1)[0]
        new = keys.get(row)
        if new is None or new == old:
            return
        try:
            self.vm.shortcuts.view.node(node_id.replace(f"form_item[{old}]", f"form_item[{new}]")).focus()
        except (KeyError, ValueError):
            return

    def _done(self, outcome: Outcome) -> None:
        """An action finished: show what it said, and when the file's text changed let the window follow. One batch, so the window composes once."""
        held = self._focused()

        def apply() -> None:
            if outcome.message:
                self.vm._say(outcome.message, error=not outcome.ok)
            self._set_signals()
            model = self.vm.session.model
            if outcome.changed and model is not None:
                self.vm._show(model, new_file=False, set_text=True, refresh_form=False)

        self._busy = True
        try:
            batch(apply)
        finally:
            self._busy = False
        self._restore(held)
        if outcome.changed:
            self.vm.services.edited()

    def reveal(self, key: str) -> bool:
        """Open the group that holds the row of the key `key` (so its row is built) and publish the rows. `False` when the form has no such row."""
        if self.form is None:
            return False
        try:
            row = self.form.view.row(f"k:{key}")
        except KeyError:
            return False
        self.form.open_group(row.group)
        batch(self._set_signals)
        return True

    # -- the handlers the view's widgets call ----------------------------------------------------------------------------------------

    def group(self, name: str) -> None:
        """Open or close a group of keys; a closed group builds none of its rows."""
        if self.form is None:
            return
        held = self._focused()
        self.form.toggle_group(str(name))
        batch(self._set_signals)
        self._restore(held)

    def commit(self, cell_id: str, edit: Any) -> None:
        """A field's value, a switch, a colour: written when the person commits it (Enter, or the focus leaving the field). A row that is being built again from the file loses its focus, which is a commit of the old field: it is ignored."""
        if self.form is not None and not self._busy:
            self._done(self.form.commit(str(cell_id), _plain(edit)))

    def reset(self, cell_id: str) -> None:
        if self.form is not None and not self._busy:
            self._done(self.form.reset(str(cell_id)))

    def expression(self, cell_id: str) -> None:
        if self.form is not None and not self._busy:
            self._done(self.form.toggle_expression(str(cell_id)))

    def colour(self, cell_id: str, picked: str) -> None:
        self.commit(cell_id, {"value": str(picked)})

    def key(self, cell_id: str, key: str, text: str) -> None:
        """A key pressed in a number field: Up and Down step it."""
        name = str(key).lower().replace("_", "")
        if self.form is not None and name in _UP | _DOWN:
            self._done(self.form.step(str(cell_id), 1 if name in _UP else -1, str(text)))

    def pick_choice(self, cell_id: str, value: str) -> None:
        """The choice picker of an enum key chose `value`: write it."""
        if self.form is not None and not self._busy:
            self._done(self.form.commit(str(cell_id), {"value": str(value)}))

    def pick_unit(self, cell_id: str, number: str, value: str) -> None:
        """The unit picker beside a length's number chose `value`: write the number typed with it."""
        if self.form is not None and not self._busy:
            self._done(self.form.commit(str(cell_id), {"text": str(number), "unit": str(value)}))

    def token(self, cell_id: str, ref: str) -> None:
        """The shipped token button picked a token: write `$group.name` (a reference is a plain word, written as it is). The button lists only the groups the key accepts, the preferred tokens first."""
        if self.form is not None and not self._busy and str(ref).strip():
            self._done(self.form.use_token(str(cell_id), str(ref).strip()))

    def _label(self, cell_id: str) -> str:
        assert self.form is not None
        row_id = str(cell_id).split("|", 1)[0]
        return next((r.label for r in self.form.view.rows if r.id == row_id), row_id)

    def open_choice(self, what: str, title: str, options: list[dict[str, str]], current: str = "", hooks: dict[str, Any] | None = None, anchor: str = "structure_tree") -> None:
        """Open the command chooser for an action (the Structure area's Add child and Move into, the Files area's New file): a menu of `options` under the node called `anchor`; `hooks[what](value)` is
        called with the value of the row the person picks, and Escape or a press outside runs nothing."""
        self._hooks = hooks or {}
        self._picking = what
        self.picker_title.set(title)
        self.picker_items.set(options)
        self.picker_current.set(current)
        self.picker_chosen.set("")
        self.picker_anchor.set(anchor)
        self.picker_open.set(True)

    def _chooser_closed(self) -> None:
        """The command chooser's `open` turned false. A pick turns it false first and calls `pick_option` right after (so `_picking` is cleared by the next tick); Escape or a press outside leaves it set:
        nothing runs then, and the focus goes back to the tree the chooser was opened for."""
        if self.picker_open.get() or self._picking is None:
            return
        shortcuts = self.vm.shortcuts
        if shortcuts is None:
            return
        anchor = untrack(self.picker_anchor.get)

        def dismissed() -> None:
            if self._picking is not None and not self.picker_open.get():
                self._picking = None
                shortcuts._focus(anchor)

        shortcuts.view.window.after(0.0, dismissed)

    def pick_option(self, value: str) -> None:
        """The person chose a row of the command chooser."""
        what, self._picking = self._picking, None
        self.picker_open.set(False)
        hook = self._hooks.get(what) if what is not None else None
        if hook is not None:
            hook(str(value))

    def block(self, cell_id: str) -> None:
        """The button of a key whose value is a block: add the block, or (when the file has it) choose it in the structure, where its own keys and children are edited."""
        if self.form is None or self._busy:
            return
        cell = self.form.cell(str(cell_id))
        document = self.vm.session.model.document if self.vm.session.model is not None else None
        child = cell.store.child(document) if isinstance(cell.store, BlockStore) and document is not None else None
        if child is None:
            self._done(self.form.commit(str(cell_id), {"add": True}))
            return
        path = tuple(child.index_path)
        self.vm.structure_actions._open(path)
        self.vm.structure_selected.set(value_of(path))

    def browse(self, cell_id: str) -> None:
        """Open the shipped file dialog in the key's mode and filters, starting where the path already points (else beside the open file)."""
        if self.form is None:
            return
        cell = self.form.cell(str(cell_id))
        if not isinstance(cell.widget, PathWidget):
            return
        shown = cell.view()
        model = self.vm.session.model
        base = model.path.parent if model is not None and model.path is not None else self.vm.session.folder
        start = base
        current = str(shown.get("field", "")).strip()
        if current:
            target = (base / current) if not Path(current).is_absolute() else Path(current)
            start = target if target.is_dir() else target.parent
        if not start.is_dir():
            start = base
        self.files.show(mode=str(shown.get("mode", "open")), filters=list(shown.get("filters", [])), start=str(start), headline=f"Choose {self._label(cell_id)}",
                        on_accept=lambda paths: self._chosen(str(cell_id), paths))

    def _chosen(self, cell_id: str, paths: list[str]) -> None:
        if paths and self.form is not None:
            self._done(self.form.use_path(cell_id, paths[0]))


def _plain(value: Any) -> Any:
    """The expression evaluator may hand a dict or list back wrapped; the form wants plain ones."""
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value
