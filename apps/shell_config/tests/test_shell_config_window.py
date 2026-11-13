"""The window (Main_View.yaml), headless: Files, Structure and Text areas over a copy of the representative configuration, driven with key events only.

Nothing here opens a window on a desktop: the toolkit's own headless window draws into memory (the real-session guard in conftest removes DISPLAY and the session bus), the folder is a copy under
`tmp_path`, and the shell command is never started.
"""

import shutil
from pathlib import Path

import pytest

from tess_shell_config.app import build
from tess_shell_config.session import ConfigSession

CONFIG = Path(__file__).parent / "fixtures" / "config"


@pytest.fixture
def folder(tmp_path):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    return target


class Window:
    """A built window with the helpers a key-driven test needs."""

    def __init__(self, folder, tmp_path, **options):
        self.session = ConfigSession(folder, state_dir=tmp_path / "state")
        self.built = build(self.session, reduced_motion=True, **options)
        self.vm = self.built.viewmodel
        self.window = self.built.window
        self.settle(8)

    def settle(self, n=4):
        for _ in range(n):
            self.window.advance(16)

    def key(self, name, **modifiers):
        self.window.simulate("key_down", key=name, **modifiers)
        self.settle()

    def type(self, text):
        for character in text:
            self.window.simulate("input", text=character)
        self.settle()

    def focused(self):
        """Names of the nodes holding the focus, as `pane.node` paths."""
        found = []
        for inst in self.built.view.handle.composition.walk():
            try:
                if self.built.view.node(inst.id).get("focused"):
                    found.append(inst.id)
            except (KeyError, ValueError):
                pass
        return found

    def region(self):
        return self.built.shortcuts.focused_region()

    def row(self, value):
        """Move down the focused tree until the row with the tree value `value` has the focus (a row's node id holds its value)."""
        for _ in range(80):
            if any(f"entry[{value}].row" in i for i in self.focused()):
                return
            self.key("arrow_down")
        raise AssertionError(f"no row {value!r} down the tree")

    def label_of(self, node_id):
        for inst in self.built.view.handle.composition.walk():
            if inst.id == node_id:
                try:
                    value = inst.value("label")
                except KeyError:
                    return ""
                return str(value) if value is not None else ""
        return ""


def opened(folder, tmp_path):
    return Window(folder, tmp_path)


# -- the three areas ---------------------------------------------------------------------------------------------------------------

def test_the_window_has_a_files_a_structure_and_a_text_area(folder, tmp_path):
    w = opened(folder, tmp_path)
    names = {inst.name for inst in w.built.view.handle.composition.walk() if inst.name}
    assert {"files_pane", "structure_pane", "text_pane", "files_tree", "editor", "status_bar", "toolbar"} <= names
    groups = w.vm.file_nodes.get()
    assert [g["label"] for g in groups] == ["Shells", "Modules", "Styles", "Stylesheets", "Themes", "Settings"]
    assert sum(len(g["children"]) for g in groups) == 10 and w.vm.status.get() == ""
    assert not w.vm.has_file.get() and not w.vm.has_tree.get() and w.vm.structure_nodes.get() == []


def test_opening_a_file_shows_its_text_and_its_structure_with_if_and_for_as_nodes(folder, tmp_path):
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.settle()
    assert w.vm.text.get() == (folder / "Shells" / "Main_Shell.tdl").read_text() and w.vm.has_tree.get()
    labels = _labels(w.vm.structure_nodes.get())
    assert labels[0] == "Shell" and "Monitor  Primary" in labels and "Bar  Top_Bar" in labels and "Popup  Calendar_Popup" in labels
    assert any(label.startswith("If {{ battery.present }}") for label in labels) and "Else" in labels and any(label.startswith("For item In") for label in labels)
    assert w.vm.title.get() == "Shells/Main_Shell.tdl" and w.vm.selected_label.get() == "Selected: Shell"
    assert w.session.model.selection == ()


def _labels(rows):
    """Every row label of a tree, depth first."""
    found = []
    for row in rows:
        found.append(row["label"])
        found += _labels(row.get("children", []))
    return found


def test_a_file_with_syntax_errors_opens_in_the_text_view_only_with_its_errors_marked(folder, tmp_path):
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Broken_Shell.tdl")
    w.settle()
    assert not w.vm.has_tree.get() and w.vm.structure_nodes.get() == []
    assert w.vm.text.get() == (folder / "Shells" / "Broken_Shell.tdl").read_text()
    rows = w.vm.error_rows.get()
    assert rows and rows[0]["text"].startswith("line ") and rows[0]["code"]
    assert w.vm.status_is_error.get() and "syntax errors" in w.vm.status.get()
    names = {inst.name for inst in w.built.view.handle.composition.walk() if inst.name}
    assert "errors" in names and "structure_off" in names and "structure_tree" not in names
    with pytest.raises(ValueError):
        w.built.view.focus(None, "structure_tree")


def test_editing_the_text_until_it_parses_brings_the_structure_back(folder, tmp_path):
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Broken_Shell.tdl")
    w.settle()
    fixed = (folder / "Shells" / "Broken_Shell.tdl").read_text().rstrip("\n") + "\n}\n"
    w.vm.text.set(fixed)
    w.vm.text_edited()
    w.settle()
    assert w.vm.has_tree.get() and w.vm.error_rows.get() == [] and w.vm.structure_nodes.get()[0]["label"] == "Shell"
    names = {inst.name for inst in w.built.view.handle.composition.walk() if inst.name}
    assert "structure_tree" in names and "errors" not in names


def test_the_files_tree_marks_a_file_with_syntax_errors_or_unsaved_changes_in_words(folder, tmp_path):
    w = opened(folder, tmp_path)
    labels = list(_labels(w.vm.file_nodes.get()))
    assert "Broken_Shell.tdl (syntax errors)" in labels and "Main_Shell.tdl" in labels
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.session.model.set_value((0,), "Index", "3")
    w.vm.sync()  # the model changed under the view: bring every Signal in step
    assert "Main_Shell.tdl (unsaved)" in list(_labels(w.vm.file_nodes.get()))


# -- the keyboard ------------------------------------------------------------------------------------------------------------------

def test_every_step_from_open_to_save_works_from_the_keyboard_alone(folder, tmp_path):
    """Files area -> open a file -> Structure area -> select a block -> Text area -> type -> Save -> Undo -> Redo, with key events only."""
    w = opened(folder, tmp_path)
    main = folder / "Shells" / "Main_Shell.tdl"
    before = main.read_bytes()
    assert w.region() == 0, "the window starts with the focus in the Files area"
    # Files: arrow down to Main_Shell.tdl, Enter opens it
    w.row("f:Shells/Main_Shell.tdl")
    w.key("enter")
    assert w.session.current == "Shells/Main_Shell.tdl" and w.vm.has_tree.get() and w.vm.status.get() == "Opened Shells/Main_Shell.tdl"
    # F6 moves to Structure: arrow down to the Bar and Enter selects it
    w.key("F6")
    assert w.region() == 1
    w.row(next(r["value"] for r in _rows(w.vm.structure_nodes.get()) if r["label"] == "Bar  Top_Bar"))
    w.key("enter")
    assert w.vm.selected_label.get() == "Selected: Bar  Top_Bar" and w.session.model.selected.name == "Top_Bar"
    # F6 moves to Text: typing goes into the file
    w.key("F6")
    assert w.region() == 2 and w.focused()[0].endswith("editor")
    w.key("end", ctrl=True)
    w.type("\n# written from the keyboard\n")
    assert w.session.model.dirty and w.session.model.text.endswith("# written from the keyboard\n") and w.vm.dirty.get()
    assert w.session.model.selected.name == "Top_Bar", "the selection stays on its block while the text is edited"
    assert "Main_Shell.tdl (unsaved)" in list(_labels(w.vm.file_nodes.get()))
    # Ctrl+S saves: the disk has the new text, the old file is kept in the state folder
    assert main.read_bytes() == before
    w.key("s", ctrl=True)
    assert main.read_bytes().endswith(b"# written from the keyboard\n") and w.vm.status.get() == "Saved Shells/Main_Shell.tdl" and not w.vm.dirty.get()
    assert [p.read_bytes() for p in (tmp_path / "state" / "backups").rglob("Main_Shell.tdl")] == [before]
    # Ctrl+Z undoes (the text in the editor too), Ctrl+Y redoes
    w.key("z", ctrl=True)
    assert w.session.model.data == before and w.vm.text.get() == before.decode() and w.vm.can_redo.get()
    w.key("y", ctrl=True)
    assert w.session.model.text.endswith("# written from the keyboard\n") and w.vm.text.get().endswith("# written from the keyboard\n")
    w.key("z", ctrl=True, shift=True)
    w.key("z", ctrl=True, shift=True)  # nothing is left to redo
    assert w.session.model.text.endswith("# written from the keyboard\n")


def test_f6_and_shift_f6_cycle_the_three_areas_and_skip_the_structure_while_it_is_off(folder, tmp_path):
    w = opened(folder, tmp_path)
    assert w.region() == 0
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.settle()
    seen = []
    for _ in range(4):
        w.key("F6")
        seen.append(w.region())
    assert seen == [1, 2, 0, 1]
    for expected in (0, 2, 1):
        w.key("F6", shift=True)
        assert w.region() == expected
    w.vm.open_file("Shells/Broken_Shell.tdl")
    w.settle()
    w.built.shortcuts.move_focus(-1)
    regions = []
    for _ in range(4):
        w.key("F6")
        regions.append(w.region())
    assert 1 not in regions and regions == [0, 2, 0, 2]


def test_typing_text_that_does_not_parse_turns_the_structure_off_and_deleting_it_turns_it_on(folder, tmp_path):
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.settle()
    w.built.shortcuts.move_focus(-1)  # Text
    assert w.region() == 2
    w.key("home", ctrl=True)
    w.type("}")  # a stray brace before the metadata block
    assert not w.vm.has_tree.get() and w.vm.error_rows.get() and w.session.model.errors
    w.vm.text.set((folder / "Shells" / "Main_Shell.tdl").read_text())  # the text put back (what deleting the brace does)
    w.vm.text_edited()
    assert w.vm.has_tree.get() and w.vm.error_rows.get() == [] and w.session.model.text == (folder / "Shells" / "Main_Shell.tdl").read_text()
    assert not w.session.model.dirty


def test_the_toolbar_buttons_follow_the_state_and_save_writes_the_file(folder, tmp_path):
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.settle()
    assert not w.vm.dirty.get() and not w.vm.can_undo.get()
    w.session.model.set_value((0,), "Index", "7")
    w.vm.sync()
    assert w.vm.dirty.get() and w.vm.can_undo.get()
    w.window.simulate("click", node=w.built.view.node("root.toolbar.save_button"))
    w.settle()
    assert b"Index: 7" in (folder / "Shells" / "Main_Shell.tdl").read_bytes() and not w.vm.dirty.get()
    w.window.simulate("click", node=w.built.view.node("root.toolbar.undo_button"))
    w.settle()
    assert w.vm.dirty.get() and "Index: 0" in w.vm.text.get()


def test_the_format_button_formats_only_when_asked(folder, tmp_path):
    w = opened(folder, tmp_path)
    shell = folder / "Shells" / "Main_Shell.tdl"
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.settle()
    assert w.session.model.text == shell.read_text(), "opening formats nothing"
    w.window.simulate("click", node=w.built.view.node("root.toolbar.format_button"))
    w.settle()
    assert w.vm.status.get() == "Formatted" and w.session.model.dirty and shell.read_bytes() == (CONFIG / "Shells" / "Main_Shell.tdl").read_bytes()


def test_a_failed_save_says_why_in_the_status_and_keeps_the_edit(folder, tmp_path):
    import os

    if os.geteuid() == 0:
        pytest.skip("root can write to a read-only folder")
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.session.model.set_value((0,), "Index", "9")
    w.vm.sync()
    old = (folder / "Shells" / "Main_Shell.tdl").read_bytes()
    (folder / "Shells").chmod(0o555)
    try:
        w.vm.save()
    finally:
        (folder / "Shells").chmod(0o755)
    assert w.vm.status_is_error.get() and "permission denied" in w.vm.status.get() and w.vm.dirty.get()
    assert (folder / "Shells" / "Main_Shell.tdl").read_bytes() == old


def test_choosing_a_structure_row_selects_that_block_in_the_model(folder, tmp_path):
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Main_Shell.tdl")
    w.settle()
    bar_value = next(r["value"] for r in _rows(w.vm.structure_nodes.get()) if r["label"] == "Bar  Top_Bar")
    w.vm.structure_selected.set(bar_value)
    w.settle()
    assert w.session.model.selected.name == "Top_Bar" and w.vm.selected_label.get() == "Selected: Bar  Top_Bar"
    else_value = next(r["value"] for r in _rows(w.vm.structure_nodes.get()) if r["label"] == "Else")
    w.vm.structure_selected.set(else_value)
    w.settle()
    assert type(w.session.model.selected).__name__ == "If", "an Else row selects its If"


def _rows(rows):
    for row in rows:
        yield row
        yield from _rows(row.get("children", []))


def test_a_file_that_is_not_utf8_opens_read_only_and_saves_its_bytes(folder, tmp_path):
    raw = b"---\nTDL: 0.1\nName: Odd\n---\nShell { }\n# \xff\n"
    (folder / "Shells" / "Odd_Shell.tdl").write_bytes(raw)
    w = opened(folder, tmp_path)
    w.vm.open_file("Shells/Odd_Shell.tdl")
    w.settle()
    assert w.vm.read_only.get() and "\ufffd" in w.vm.text.get() and "not UTF-8" in w.vm.title.get()
    w.vm.save()
    assert (folder / "Shells" / "Odd_Shell.tdl").read_bytes() == raw


def test_the_window_renders_in_dark_and_light(folder, tmp_path):
    for dark in (False, True):
        w = Window(folder, tmp_path, dark=dark)
        w.vm.open_file("Shells/Main_Shell.tdl")
        w.settle(6)
        rgba, width, height = w.window.snapshot()
        data = bytes(rgba)
        corner = data[:4]
        different = sum(1 for i in range(0, len(data), 4 * 7) if data[i:i + 4] != corner)
        assert (width, height) == (1280, 800) and different > 1000
