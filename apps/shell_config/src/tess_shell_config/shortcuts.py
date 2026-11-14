"""Keyboard shortcuts of the window. The main view's root hands every key press that reaches it to `ShellConfigViewModel.key_pressed` (`handlers: {on_key: ...}`), so they work wherever the
focus is; the text editor takes Tab and the arrow keys itself, so a shortcut is the way out of it.

| Keys | Does |
|---|---|
| Ctrl+S | Save the open file |
| Ctrl+Z | Undo |
| Ctrl+Y, Ctrl+Shift+Z | Redo |
| F6, Shift+F6 | Move the focus to the next, or the previous, of the four areas: Files, Structure, Form, Text |
| Ctrl+Shift+N | Add a child to the selected block (a list of the blocks the schema lets it hold) |
| Delete (in the Structure tree), Ctrl+Shift+Delete | Remove the selected block |
| Alt+Up, Alt+Down | Move the selected block up or down among its siblings |
| Ctrl+Shift+M | Move the selected block into another block, chosen from a list |
| Ctrl+Shift+D | Duplicate the selected block (a `Name:` becomes a name no other block has) |
| Menu key, Shift+F10 | The Structure menu, with every action and its shortcut |

Every one of these is also a button or a tree on the window, so nothing needs the pointer.
"""

from __future__ import annotations

from typing import Any

from tess_shell_config.viewmodel import ShellConfigViewModel

__all__ = ["REGIONS", "Shortcuts"]

#: The structure actions that have a Ctrl+Shift+letter, by the letter.
_STRUCTURE = {"n": "add", "m": "move_to", "d": "duplicate"}
#: The four areas in the order F6 visits them: (the node that takes the focus, the pane it is in).
REGIONS = (("files_tree", "files_pane"), ("structure_tree", "structure_pane"), ("form_pane", "form_pane"), ("editor", "text_pane"))


class Shortcuts:
    """Acts on `viewmodel` for a key press; `view` is the opened `main` view, which it moves the focus in."""

    def __init__(self, view: Any, viewmodel: ShellConfigViewModel) -> None:
        self.view = view
        self.viewmodel = viewmodel

    def handle(self, key: str, ctrl: bool = False, shift: bool = False, alt: bool = False) -> bool:
        """Do what the keys mean; returns whether they meant something."""
        key = key.lower().replace("_", "")
        if alt:
            return self._alt(key, ctrl, shift)
        if ctrl and shift and key in _STRUCTURE:
            getattr(self.viewmodel.structure_actions, _STRUCTURE[key])()
        elif key == "delete" and (ctrl and shift or (not ctrl and not shift and self.focused_region() == 1)):
            self.viewmodel.structure_actions.remove()
        elif key == "contextmenu" or (key == "f10" and shift and not ctrl):
            self.viewmodel.structure_actions.open_menu()
        elif ctrl and key == "s":
            self.viewmodel.save()
        elif ctrl and key == "z" and not shift:
            self.viewmodel.undo()
        elif ctrl and (key == "y" or (key == "z" and shift)):
            self.viewmodel.redo()
        elif key == "f6" and not ctrl:
            self.move_focus(-1 if shift else 1)
        else:
            return False
        return True

    def _alt(self, key: str, ctrl: bool, shift: bool) -> bool:
        if ctrl or shift or key not in ("arrowup", "up", "arrowdown", "down"):
            return False
        (self.viewmodel.structure_actions.move_up if key.endswith("up") else self.viewmodel.structure_actions.move_down)()
        return True

    def focused_region(self) -> int | None:
        """Which of the three areas holds the focus now, or `None`: an area holds it when a node inside its pane does."""
        for inst in self.view.handle.composition.walk():
            for i, (_, pane) in enumerate(REGIONS):
                if f".{pane}." in inst.id + "." and self._focused(inst.id):
                    return i
        return None

    def _focused(self, node_id: str) -> bool:
        try:
            return bool(self.view.node(node_id).get("focused"))
        except (KeyError, ValueError, AttributeError):
            return False

    def move_focus(self, step: int) -> None:
        """Focus the next (`step` 1) or previous (-1) area that can take it (the structure is skipped while it is off)."""
        here = self.focused_region()
        index = (-1 if step > 0 else 0) if here is None else here
        for _ in range(len(REGIONS)):
            index = (index + step) % len(REGIONS)
            name = REGIONS[index][0]
            if name == "structure_tree" and not self.viewmodel.has_tree.get():
                continue
            if name == "form_pane" and not getattr(self.viewmodel, "form_items").get():
                continue
            self._focus(name)
            return

    def focus_structure(self, value: str) -> None:
        """Give the focus to the Structure tree's row `value` (after an edit rebuilt the rows: the block that moved is on a row of its own, and its row may be built by the next frame, so this tries now and once more after it)."""
        if not self._focus_row(value):
            self.view.window.after(0.0, lambda: self._focus_row(value))

    def _focus_row(self, value: str) -> bool:
        for inst in self.view.handle.composition.walk():
            if inst.name == "row" and f"structure_tree.top." in inst.id and inst.id.endswith(f"entry[{value}].row"):
                self.view.node(inst.id).focus()
                return True
        return False

    def _focus(self, name: str) -> None:
        """Give the focus to an area. A tree is one tab stop whose arrow keys work from a row, so the focus goes to the chosen row (else the first); the form takes it at its first group header; the editor takes it itself."""
        if name == "form_pane":
            headers = [inst.id for inst in self.view.handle.composition.walk() if inst.name == "group_header"]
            if headers:
                self.view.node(headers[0]).focus()
            return
        if not name.endswith("_tree"):
            self.view.focus(None, name)
            return
        rows = [inst.id for inst in self.view.handle.composition.walk() if inst.name == "row" and f".{name}." in inst.id + "."]
        chosen = next((r for r in rows if self._selected(r)), rows[0] if rows else None)
        if chosen is None:
            self.view.focus(None, name)
        else:
            self.view.node(chosen).focus()

    def _selected(self, node_id: str) -> bool:
        try:
            return bool(self.view.node(node_id).get("selected"))
        except (KeyError, ValueError, AttributeError):
            return False
