"""The Structure area's actions: add a child, remove, move up or down, move to another block, duplicate. The window's ViewModel gets their Signals and handlers from `StructureActions(viewmodel)`,
as it does for the form: `can_add` ... `can_duplicate` (each action's enabled state, for the buttons and the menu), `menu_open`, `menu_items`, `menu_chosen`, and `structure_add` ... `structure_command`.

Every action is one `DocumentModel` edit (one undo step) and then `ViewModel.sync`, so the text, the tree, the form and the selection follow. An edit `tess_dl` refuses (a block inside an `If` or `For`,
a place the file cannot take) is not applied and the status line says why. The choices come from the schema (`blocks.py`): the Add list is the selected block's `allowed_children`, and a block moves only
into a block whose schema entry lets it hold a block of that type. A list of choices (Add, Move to) is the same dialog the form's choice lists use.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from tess_dl import Block
from tess_ui import Signal

from tess_shell_config.blocks import accepts, children_of, new_block_text
from tess_shell_config.model import DocumentModel, EditError, block_names
from tess_shell_config.structure import ancestors, label_of, path_of, value_of
from tess_shell_config.tdl import IndexPath, walk

__all__ = ["COMMANDS", "StructureActions", "Command"]


@dataclass(frozen=True)
class Command:
    """A structure action: its `name` (the menu's value), the words on the menu, and its shortcut as text."""

    name: str
    label: str
    shortcut: str


COMMANDS = (
    Command("add", "Add child...", "Ctrl+Shift+N"),
    Command("remove", "Remove", "Delete"),
    Command("move_up", "Move up", "Alt+Up"),
    Command("move_down", "Move down", "Alt+Down"),
    Command("move_to", "Move to...", "Ctrl+Shift+M"),
    Command("duplicate", "Duplicate", "Ctrl+Shift+D"),
)


class StructureActions:
    """`viewmodel` is the window's ViewModel; the actions work on its session's current model."""

    def __init__(self, viewmodel: Any) -> None:
        self.vm = viewmodel
        self.enabled: dict[str, bool] = {c.name: False for c in COMMANDS}
        self.flags = {c.name: Signal(False) for c in COMMANDS}
        self.menu_open = Signal(False)
        self.menu_items = Signal([])
        self.menu_chosen = Signal("")
        for command in COMMANDS:
            setattr(viewmodel, f"can_{command.name}", self.flags[command.name])
            setattr(viewmodel, f"structure_{command.name}", getattr(self, command.name))
        for name, value in {"menu_open": self.menu_open, "menu_items": self.menu_items, "menu_chosen": self.menu_chosen}.items():
            setattr(viewmodel, name, value)
        viewmodel.structure_command = self.command
        viewmodel.structure_menu = self.open_menu
        self.picks: dict[str, Callable[[str], None]] = {"add": self._add_picked, "move_to": self._move_picked}
        self.refresh()

    # -- what can be done now -----------------------------------------------------------------------------------------------------

    @property
    def model(self) -> DocumentModel | None:
        return self.vm.session.model

    def refresh(self) -> None:
        """Work out which actions the selection allows, and set the buttons and the menu to match."""
        enabled = dict.fromkeys(self.enabled, False)
        model = self.model
        if model is not None and model.valid and model.selection is not None and model.selected is not None:
            path, node = tuple(model.selection), model.selected
            schema = self.vm.session.schema
            enabled["add"] = isinstance(node, Block) and schema is not None and bool(children_of(schema, node.type))
            if path and isinstance(model.node_at(path[:-1]), Block):
                enabled["remove"] = True
                enabled["move_up"] = model.neighbour(path, -1) is not None
                enabled["move_down"] = model.neighbour(path, 1) is not None
                enabled["move_to"] = enabled["duplicate"] = isinstance(node, Block)
        self.enabled = enabled
        for name, flag in self.flags.items():
            if flag.get() != enabled[name]:
                flag.set(enabled[name])
        items = [{"value": c.name, "label": c.label, "shortcut": c.shortcut, "disabled": not enabled[c.name]} for c in COMMANDS]
        items.insert(1, {"divider": True})
        items.insert(5, {"divider": True})
        if items != self.menu_items.get():
            self.menu_items.set(items)

    # -- the actions ----------------------------------------------------------------------------------------------------------------

    def _need(self, name: str) -> DocumentModel | None:
        """The model when `name` may be done now; else say why not and return `None`."""
        model = self.model
        if model is None or not model.valid:
            self.vm._say("There is no structure to edit: open a file that parses.", error=True)
            return None
        if model.selection is None:
            self.vm._say("Select a block in the structure first.", error=True)
            return None
        if not self.enabled.get(name):
            self.vm._say(_why_not(name, model), error=True)
            return None
        return model

    def _open(self, path: IndexPath) -> None:
        """Open every branch above `path` in the tree, so the block shows."""
        opened = set(self.vm.structure_expanded.get()) | set(ancestors(path)) | {value_of(path)}
        self.vm.structure_expanded.set(sorted(opened))

    def _run(self, edit: Callable[[], str], *, open_path: IndexPath | None = None, keep_focus: bool = True) -> None:
        """Do one edit, then bring the window in step with the model; an edit that is refused says why and changes nothing."""
        held = self._focus_in_structure()
        try:
            message = edit()
        except EditError as error:
            self.vm._say(str(error), error=True)
            return
        self.vm.sync()
        if open_path is not None:
            self._open(open_path)
        self.vm._say(message)
        if held and keep_focus:
            model = self.model
            if model is not None and model.selection is not None:
                self.vm.shortcuts.focus_structure(value_of(tuple(model.selection)))

    def _focus_in_structure(self) -> bool:
        shortcuts = self.vm.shortcuts
        return shortcuts is not None and shortcuts.focused_region() == 1

    def add(self) -> None:
        """Open the list of the blocks the selected block may hold."""
        model = self._need("add")
        if model is None:
            return
        schema = self.vm.session.schema
        node = model.selected
        assert schema is not None and isinstance(node, Block)
        options = [{"value": c.type, "label": c.type, "hint": c.doc + (" (a module)" if c.module else ""), "colour": ""} for c in children_of(schema, node.type)]
        self.vm.form.open_choice("add", f"Add to {label_of(node)}", options, hooks=self.picks)

    def _add_picked(self, type_name: str) -> None:
        model, schema = self.model, self.vm.session.schema
        if model is None or schema is None or model.selection is None:
            return
        parent = tuple(model.selection)
        document = model.document
        assert document is not None

        def edit() -> str:
            text = new_block_text(schema, type_name, block_names(document))
            model.add_block(parent, text)
            return f"Added {type_name} to {label_of(model.node_at(parent))}"

        self._run(edit, open_path=parent)

    def remove(self) -> None:
        model = self._need("remove")
        if model is None:
            return
        path = tuple(model.selection or ())
        label = label_of(model.node_at(path))

        def edit() -> str:
            model.remove_block(path)
            return f"Removed {label}"

        self._run(edit)

    def _move(self, name: str, step: int) -> None:
        model = self._need(name)
        if model is None:
            return
        path = tuple(model.selection or ())
        target = model.neighbour(path, step)
        assert target is not None
        label = label_of(model.node_at(path))

        def edit() -> str:
            model.move_block(path, None, target)
            return f"Moved {label} {'up' if step < 0 else 'down'}"

        self._run(edit)

    def move_up(self) -> None:
        self._move("move_up", -1)

    def move_down(self) -> None:
        self._move("move_down", 1)

    def move_to(self) -> None:
        """Open the list of the blocks the selected one may move into (the keyboard's way to another parent); it goes last in the one chosen."""
        model = self._need("move_to")
        schema = self.vm.session.schema
        if model is None or schema is None or model.document is None:
            return
        path = tuple(model.selection or ())
        node = model.node_at(path)
        assert isinstance(node, Block)
        found: list[tuple[IndexPath, str]] = []
        for target in walk(model.document.root):
            if not isinstance(target, Block):
                continue
            where = tuple(target.index_path)
            if where[: len(path)] == path or where == path[:-1] or not accepts(schema, target.type, node.type):
                continue
            found.append((where, _trail(model, where)))
        if not found:
            self.vm._say(f"There is no other block that may hold a {node.type}.", error=True)
            return
        options = [{"value": value_of(w), "label": text, "hint": "", "colour": ""} for w, text in found]
        self.vm.form.open_choice("move_to", f"Move {label_of(node)} into", options, hooks=self.picks)

    def _move_picked(self, value: str) -> None:
        model = self.model
        if model is None or model.selection is None:
            return
        path, target = tuple(model.selection), path_of(value)
        label = label_of(model.node_at(path))
        moved: list[IndexPath] = []

        def edit() -> str:
            moved.append(model.move_block(path, target, None))
            return f"Moved {label} into {_trail(model, moved[0][:-1])}"

        self._run(edit)
        if moved:
            self._open(moved[0])

    def duplicate(self) -> None:
        model = self._need("duplicate")
        if model is None:
            return
        path = tuple(model.selection or ())
        label = label_of(model.node_at(path))

        def edit() -> str:
            copy = model.duplicate_block(path)
            return f"Duplicated {label} as {label_of(model.node_at(copy))}"

        self._run(edit)

    # -- the menu --------------------------------------------------------------------------------------------------------------------

    def open_menu(self) -> None:
        """Show the menu of the structure actions (the Menu key, Shift+F10, a right click on the Structure area)."""
        self.refresh()
        self.menu_open.set(True)

    def command(self, name: str) -> None:
        """What a menu item does."""
        self.menu_open.set(False)
        action = getattr(self, str(name), None)
        if name in self.enabled and callable(action):
            action()


def _trail(model: DocumentModel, path: IndexPath) -> str:
    """`Shell › Monitor  Primary › Bar  Top_Bar`: where a block is, for a list of places."""
    return " › ".join(label_of(model.node_at(path[:n])) for n in range(len(path) + 1))


def _why_not(name: str, model: DocumentModel) -> str:
    path = tuple(model.selection or ())
    node = model.selected
    if name == "add":
        return f"A {getattr(node, 'type', 'block')} holds no blocks the schema names, so there is nothing to add to it."
    if not path:
        return "The root block cannot be removed, moved or copied."
    if not isinstance(model.node_at(path[:-1]), Block):
        return "A block inside an If or For is changed in the text view: the structure edits work on the blocks of a block."
    if name in ("move_up", "move_down"):
        return f"There is no block {'before' if name == 'move_up' else 'after'} it to move past."
    return "An If or For cannot be moved into another block or copied from the structure; use the text view."
