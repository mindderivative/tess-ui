"""#299: the file dialog as a view -- opened from a ViewModel's Signal, driven by presses, clicks and keys on a headless window, over `tmp_path` trees
and a fake file system for the errors. Nothing here reads outside `tmp_path`."""

import os

import pytest

from tess_ui import App, Signal, ViewModel, filesystem
from tess_ui.file_dialog import FileDialogRequest
from tess_ui.filesystem import Entry, FileSystemError, LocalFileSystem
from tess_ui.shipped import shipped_views
from tess_ui.spec.widgets import lookup


class VM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.shown = Signal(False)
        self.got = Signal("")
        self.log = []

    def accepted(self):
        self.log.append(("accept", self.got.get()))

    def cancelled(self):
        self.log.append(("cancel",))


def tree(tmp_path):
    """A small tree in `data` under `tmp_path` (the views are written beside it, in `Views`)."""
    base = tmp_path / "data"
    base.mkdir()
    for name in ("beta", "Alpha", ".hidden_dir"):
        (base / name).mkdir()
    for name, text in (("b.txt", "b"), ("A.TDL", "aa"), ("c.tdl", "ccc"), (".secret", "s"), ("notes.md", "n" * 2000)):
        (base / name).write_text(text)
    (base / "Alpha" / "inner.txt").write_text("i")
    (base / "Alpha" / "deeper").mkdir()
    return base


def settle(view, n=6):
    for _ in range(n):
        view.window.advance(16)


def opened(tmp_path, options="", *, dark=False, size=(900, 800), show=True):
    """A window with a view that holds a `FileDialog` named `fd`: `options` are its properties (`start`, `mode`, ...), `open` and `value` are the ViewModel's."""
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.yaml").write_text(f"""tesserae: 0.6
name: main
widget: Container
style: {{flex_direction: vertical, width: {size[0]}, height: {size[1]}}}
children:
  - {{widget: Rect, name: elsewhere, style: {{width: 80, height: 80, background: surface_variant}}}}
  - {{widget: FileDialog, name: fd, open: "{{{{ shown }}}}", value: "{{{{ got }}}}", on_accept: accepted, on_cancel: cancelled, {options}}}
""")
    app = App(root=tmp_path, width=size[0], height=size[1], theme_seed=(0x67, 0x50, 0xA4, 0xFF), dark=dark)
    app.bind(VM)
    view = app.open_view("Main")
    app.show("main")
    settle(view)
    vm = app.bindings.viewmodel_for("main")
    if show:
        vm.shown.set(True)
        settle(view)
    return view, vm


PANEL = "root.fd.panel"


def ctl(view):
    return view._built.controls[f"{PANEL}.browser"]


def node(view, name):
    return view._built.nodes[f"{PANEL}.{name}"]


def row_ids(view):
    """The rows built, top to bottom (the nodes of a row that has gone and come back are made again, so their order in the view is not the list's)."""
    ids = [k for k in view._built.nodes if k.startswith(f"{PANEL}.list_group.list_box.list.row[") and k.endswith("]")]
    return sorted(ids, key=lambda k: view._built.nodes[k].get("layout_y"))


def shown_names(view):
    return [os.path.basename(k[len(f"{PANEL}.list_group.list_box.list.row["):-1]) for k in row_ids(view)]


def row(view, path):
    return view._built.nodes[f"{PANEL}.list_group.list_box.list.row[{path}]"]


def press(view, target, n=3, **mods):
    view.window.simulate("pointer_down", node=target, **mods)
    settle(view, n)


def click(view, name, n=4):
    view.window.simulate("click", node=node(view, name))
    settle(view, n)


def key(view, name, n=3, **mods):
    """A key in the list (its node holds the focus first)."""
    list_node = view._built.nodes[f"{PANEL}.list_group.list_box"]
    if not list_node.get("focused"):
        list_node.focus()
    view.window.simulate("key_down", key=name, **mods)
    settle(view, n)


def typed(view, name, text, n=3):
    """Types `text` in the text field `name` (a path to it from the panel), as the keyboard does."""
    field = view._built.nodes[f"{PANEL}.{name}.box.body.input"]
    field.focus()
    field.set(text=text[:-1])
    view.window.simulate("key_down", key="end")
    view.window.simulate("input", text=text[-1])
    settle(view, n)


def enter(view, name, n=4):
    view._built.nodes[f"{PANEL}.{name}.box.body.input"].focus()
    view.window.simulate("key_down", key="Enter")  # the name a text field's Enter has, which `on_submit` waits for
    settle(view, n)


def pick(view, name, **mods):
    """A press on the row of the entry `name` in the folder shown."""
    press(view, row(view, os.path.join(ctl(view).folder.get(), name)), **mods)


# -- the view and the control are shipped and declared ---------------------------------------------------------------------------------

def test_the_dialog_and_its_control_are_shipped_and_declared():
    assert "FileDialog" in set(shipped_views())
    decl = lookup("FileBrowser")
    assert decl is not None
    for name in ("path", "filename", "hidden", "filter", "scroll", "confirm", "entries", "selection", "valid", "target"):
        assert decl.properties[name].model, name
    assert not decl.properties["command"].model and not decl.properties["open"].model
    assert lookup("FileDialog") is None  # a view, not a widget: it is called by name


def test_the_view_checks_against_its_viewmodel(tmp_path):
    view, vm = opened(tmp_path, f'start: "{tree(tmp_path)}"', show=False)
    assert view.handle.viewmodel is vm


# -- nothing is read until it opens ------------------------------------------------------------------------------------------------------

class Counting(LocalFileSystem):
    def __init__(self):
        self.listed = []

    def list_dir(self, path):
        self.listed.append(path)
        return super().list_dir(path)


def test_a_closed_dialog_reads_nothing_and_each_opening_reads_its_folder_afresh(tmp_path, monkeypatch):
    base = tree(tmp_path)
    fs = Counting()
    monkeypatch.setattr(filesystem, "_default", fs)
    view, vm = opened(tmp_path, f'start: "{base}"', show=False)
    assert fs.listed == []
    vm.shown.set(True)
    settle(view)
    assert fs.listed == [str(base)]
    assert shown_names(view)[:2] == ["Alpha", "beta"]
    vm.shown.set(False)
    settle(view)
    (base / "new.txt").write_text("")
    vm.shown.set(True)
    settle(view)
    assert fs.listed == [str(base), str(base)] and "new.txt" in shown_names(view)  # each opening starts again, at `start`, with the folder as it is


# -- what it shows --------------------------------------------------------------------------------------------------------------------

def test_it_lists_the_folder_folders_first_and_shows_the_path_and_the_trail(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    assert shown_names(view) == ["Alpha", "beta", "A.TDL", "b.txt", "c.tdl", "notes.md"]
    assert ctl(view).folder.get() == str(base)
    assert view._built.nodes[f"{PANEL}.toolbar.path_field.box.body.input"].get("text") == str(base)
    trail = [k[len(f"{PANEL}.crumbs.crumb["):-len("].crumb_button")] for k in view._built.nodes if k.endswith("].crumb_button")]
    assert trail[0] == os.sep and trail[-1] == str(base) and len(trail) == len(ctl(view).crumbs.get())
    assert not ctl(view).valid.get()  # nothing is picked: OK is off
    assert node(view, "actions.accept").get("disabled")


def test_a_press_picks_a_file_and_turns_ok_on_and_a_folder_only_moves_the_cursor(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    pick(view, "b.txt")
    assert ctl(view).selection.get() == [str(base / "b.txt")] and ctl(view).valid.get()
    assert not node(view, "actions.accept").get("disabled")
    pick(view, "Alpha")
    assert ctl(view).selection.get() == [] and ctl(view).cursor.get() == 0 and not ctl(view).valid.get()
    assert node(view, "actions.accept").get("disabled")


# -- the answer ----------------------------------------------------------------------------------------------------------------------

def test_ok_writes_the_path_closes_the_dialog_and_calls_on_accept_once(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    pick(view, "b.txt")
    click(view, "actions.accept")
    assert vm.got.get() == str(base / "b.txt") and vm.shown.get() is False
    assert vm.log == [("accept", str(base / "b.txt"))]  # accepted, and not also cancelled


def test_cancel_closes_without_an_answer(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    pick(view, "b.txt")
    click(view, "actions.cancel")
    assert vm.got.get() == "" and vm.shown.get() is False and vm.log == [("cancel",)]


def test_escape_cancels_once(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    pick(view, "b.txt")
    view._built.nodes[f"{PANEL}.list_group.list_box"].focus()
    view.window.simulate("key_down", key="escape")
    settle(view)
    assert vm.shown.get() is False and vm.got.get() == "" and vm.log == [("cancel",)]


def test_a_double_press_on_a_file_accepts_it_and_on_a_folder_goes_in(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    pick(view, "Alpha")
    pick(view, "Alpha")
    assert ctl(view).folder.get() == str(base / "Alpha") and shown_names(view) == ["deeper", "inner.txt"] and vm.shown.get()
    pick(view, "inner.txt")
    pick(view, "inner.txt")
    assert vm.got.get() == str(base / "Alpha" / "inner.txt") and vm.shown.get() is False and len(vm.log) == 1


def test_enter_in_the_list_opens_the_row_the_cursor_is_on(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    key(view, "arrow_down")
    key(view, "enter")
    assert ctl(view).folder.get() == str(base / "Alpha")
    key(view, "arrow_down")
    key(view, "arrow_down")  # deeper, inner.txt
    key(view, "enter")
    assert vm.got.get() == str(base / "Alpha" / "inner.txt") and vm.shown.get() is False


def test_several_files_come_back_as_a_list_when_multiple_is_on(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", multiple: true')
    pick(view, "A.TDL")
    pick(view, "c.tdl", ctrl=True)
    pick(view, "notes.md", ctrl=True)
    pick(view, "c.tdl", ctrl=True)
    assert ctl(view).selection.get() == [str(base / "A.TDL"), str(base / "notes.md")]
    click(view, "actions.accept")
    assert vm.got.get() == [str(base / "A.TDL"), str(base / "notes.md")]
    vm.shown.set(True)
    settle(view)
    pick(view, "A.TDL")
    pick(view, "c.tdl", shift=True)
    assert [os.path.basename(p) for p in ctl(view).selection.get()] == ["A.TDL", "b.txt", "c.tdl"]


def test_folder_mode_chooses_the_folder_picked_or_the_one_it_is_in(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", mode: folder')
    assert shown_names(view) == ["Alpha", "beta"] and ctl(view).valid.get()
    assert not node(view, "actions.accept").get("disabled")
    assert node(view, "actions.accept.label").get("text") == "Choose"
    click(view, "actions.accept")
    assert vm.got.get() == str(base)
    vm.shown.set(True)
    settle(view)
    pick(view, "beta")
    click(view, "actions.accept")
    assert vm.got.get() == str(base / "beta") and isinstance(vm.got.get(), str)


# -- saving --------------------------------------------------------------------------------------------------------------------------

def test_save_takes_the_typed_name_and_the_extension_of_the_type(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", mode: save, filters: [{{label: TDL files, patterns: ["*.tdl"]}}]')
    assert node(view, "actions.accept").get("disabled") and node(view, "actions.accept.label").get("text") == "Save"
    typed(view, "filename_field", "plan")
    assert ctl(view).valid.get() and ctl(view).target.get() == [str(base / "plan.tdl")]
    click(view, "actions.accept")
    assert vm.got.get() == str(base / "plan.tdl") and vm.log == [("accept", str(base / "plan.tdl"))] and not (base / "plan.tdl").exists()  # the dialog writes nothing


def test_save_starts_with_the_name_it_is_given_and_a_picked_file_names_the_save(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", mode: save, filename: "draft.txt"')
    assert ctl(view).filename.get() == "draft.txt" and ctl(view).valid.get()
    assert view._built.nodes[f"{PANEL}.filename_field.box.body.input"].get("text") == "draft.txt"
    pick(view, "b.txt")
    assert view._built.nodes[f"{PANEL}.filename_field.box.body.input"].get("text") == "b.txt"


def test_saving_over_a_file_that_is_there_asks_first(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", mode: save')
    typed(view, "filename_field", "b.txt")
    assert ctl(view).exists.get() and ctl(view).chosen.get() == "b.txt"
    click(view, "actions.accept")
    assert ctl(view).confirm.get() is True and vm.log == [] and vm.shown.get() is True
    assert node(view, "replace.replace_panel.replace_body").get("text") == "b.txt is there already. Saving writes over it."
    click(view, "replace.replace_panel.replace_actions.replace_cancel")
    assert ctl(view).confirm.get() is False and vm.log == [] and vm.shown.get() is True  # back to the dialog, nothing chosen
    click(view, "actions.accept")
    click(view, "replace.replace_panel.replace_actions.replace_yes")
    assert vm.got.get() == str(base / "b.txt") and vm.shown.get() is False and vm.log == [("accept", str(base / "b.txt"))]


def test_a_new_name_needs_no_confirmation_and_enter_in_the_name_field_saves(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", mode: save')
    typed(view, "filename_field", "fresh.txt")
    assert not ctl(view).exists.get()
    enter(view, "filename_field")
    assert vm.got.get() == str(base / "fresh.txt") and ctl(view).confirm.get() is False and vm.shown.get() is False


def test_a_save_name_that_is_a_folder_is_a_problem_not_an_answer(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", mode: save')
    typed(view, "filename_field", "Alpha")
    assert not ctl(view).valid.get() and ctl(view).problem.get() == "Alpha is a folder"
    assert f"{PANEL}.message_text" in view._built.nodes


# -- moving about ------------------------------------------------------------------------------------------------------------------------

def test_up_back_forward_and_the_trail_move_the_dialog_and_the_path_bar(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    def path_text():
        return view._built.nodes[f"{PANEL}.toolbar.path_field.box.body.input"].get("text")

    assert node(view, "toolbar.back").get("disabled") and node(view, "toolbar.forward").get("disabled")
    pick(view, "Alpha")
    pick(view, "Alpha")
    assert ctl(view).folder.get() == str(base / "Alpha") and path_text() == str(base / "Alpha")
    assert not node(view, "toolbar.back").get("disabled")
    click(view, "toolbar.up")
    assert ctl(view).folder.get() == str(base) and path_text() == str(base)
    click(view, "toolbar.back")
    assert ctl(view).folder.get() == str(base / "Alpha")
    assert not node(view, "toolbar.forward").get("disabled")
    click(view, "toolbar.forward")
    assert ctl(view).folder.get() == str(base)
    crumb = f"crumbs.crumb[{os.path.dirname(base)}].crumb_button"
    click(view, crumb)
    assert ctl(view).folder.get() == str(tmp_path) and "data" in shown_names(view) and "Views" in shown_names(view)


def test_home_goes_to_the_file_systems_home(tmp_path, monkeypatch):
    base = tree(tmp_path)

    class Homed(LocalFileSystem):
        def home(self):
            return str(base / "beta")

    monkeypatch.setattr(filesystem, "_default", Homed())
    view, vm = opened(tmp_path, f'start: "{base}"')
    click(view, "toolbar.home")
    assert ctl(view).folder.get() == str(base / "beta")


def test_the_path_bar_goes_where_it_is_told_with_enter_and_says_when_it_cannot(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    typed(view, "toolbar.path_field", str(base / "Alpha"))
    assert ctl(view).folder.get() == str(base)  # typing alone goes nowhere
    enter(view, "toolbar.path_field")
    assert ctl(view).folder.get() == str(base / "Alpha") and f"{PANEL}.message_text" not in view._built.nodes
    typed(view, "toolbar.path_field", str(base / "missing"))
    enter(view, "toolbar.path_field")
    assert ctl(view).folder.get() == str(base / "Alpha")  # stays
    assert f"There is no folder {base / 'missing'}" == node(view, "message_text").get("text")
    typed(view, "toolbar.path_field", str(base / "b.txt"))
    enter(view, "toolbar.path_field")
    assert ctl(view).folder.get() == str(base) and ctl(view).selection.get() == [str(base / "b.txt")] and ctl(view).valid.get()  # a file is picked in its folder
    assert f"{PANEL}.message_text" not in view._built.nodes


def test_a_root_keeps_the_dialog_inside_it(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base / "Alpha"}", root: "{base}"')
    assert [k for k in view._built.nodes if k.endswith("].crumb_button")][0].endswith(f"[{base}].crumb_button")
    assert not node(view, "toolbar.up").get("disabled")
    click(view, "toolbar.up")
    assert ctl(view).folder.get() == str(base) and node(view, "toolbar.up").get("disabled")
    click(view, "toolbar.up")
    typed(view, "toolbar.path_field", str(tmp_path))
    enter(view, "toolbar.path_field")
    assert ctl(view).folder.get() == str(base) and f"{tmp_path} is outside {base}" == node(view, "message_text").get("text")
    key(view, "backspace")
    assert ctl(view).folder.get() == str(base)
    typed(view, "toolbar.path_field", "..")
    enter(view, "toolbar.path_field")
    assert ctl(view).folder.get() == str(base)


# -- the type filter and the hidden names ---------------------------------------------------------------------------------------------

def test_a_file_type_hides_the_files_that_do_not_match_and_never_a_folder(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", filters: [{{label: TDL files, patterns: ["*.tdl"]}}, {{label: Text, patterns: ["*.txt", "*.md"]}}]')
    assert shown_names(view) == ["Alpha", "beta", "A.TDL", "c.tdl"]
    assert node(view, "options.filter_button.label").get("text") == "TDL files"
    click(view, "options.filter_button")
    click(view, "options.filter_menu.surface.row[1].item")
    assert shown_names(view) == ["Alpha", "beta", "b.txt", "notes.md"]
    assert node(view, "options.filter_button.label").get("text") == "Text"
    click(view, "options.filter_button")
    click(view, "options.filter_menu.surface.row[2].item")
    assert node(view, "options.filter_button.label").get("text") == "All files" and len(shown_names(view)) == 6


def test_without_filters_there_is_no_type_button_and_everything_shows(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    assert f"{PANEL}.options.filter_button" not in view._built.nodes and len(shown_names(view)) == 6


def test_hidden_names_are_off_until_the_box_is_ticked(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    assert ".secret" not in shown_names(view) and ".hidden_dir" not in shown_names(view)
    click(view, "options.show_hidden_box")
    assert shown_names(view) == [".hidden_dir", "Alpha", "beta", ".secret", "A.TDL", "b.txt", "c.tdl", "notes.md"]
    click(view, "options.show_hidden_box")
    assert ".secret" not in shown_names(view)
    (tmp_path / "two").mkdir()
    view2, _ = opened(tmp_path / "two", f'start: "{base}", show_hidden: true')
    assert ".secret" in shown_names(view2)


# -- making a folder -----------------------------------------------------------------------------------------------------------------

def test_new_folder_is_offered_when_saving_or_choosing_a_folder_and_makes_it(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", mode: save')
    assert f"{PANEL}.new_folder_row" not in view._built.nodes
    click(view, "options.new_folder_button")
    typed(view, "new_folder_row.new_folder_field", "fresh")
    click(view, "new_folder_row.new_folder_make")
    assert (base / "fresh").is_dir() and f"{PANEL}.new_folder_row" not in view._built.nodes
    assert "fresh" in shown_names(view) and ctl(view).folder.get() == str(base)
    click(view, "options.new_folder_button")
    typed(view, "new_folder_row.new_folder_field", "fresh")
    click(view, "new_folder_row.new_folder_make")
    assert node(view, "message_text").get("text") == "fresh already exists"


def test_open_mode_has_no_new_folder_button_and_folder_mode_has_one(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    assert f"{PANEL}.options.new_folder_button" not in view._built.nodes
    other = tmp_path / "other"
    other.mkdir()
    view, vm = opened(other, f'start: "{base}", mode: folder')
    assert f"{PANEL}.options.new_folder_button" in view._built.nodes
    assert node(view, "options.new_folder_button.label").get("text") == "New folder"


# -- the keyboard and a long list --------------------------------------------------------------------------------------------------------

def test_the_keys_in_the_list_move_the_cursor_and_the_list_follows_it(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for i in range(40):
        (data / f"f{i:02d}.txt").write_text("")
    view, vm = opened(tmp_path, f'start: "{data}", rows: 6')
    scroller = view._built.outer[f"{PANEL}.list_group.list_box.list"]
    assert len(row_ids(view)) <= 12 and ctl(view).cursor.get() == -1
    key(view, "arrow_down")
    key(view, "arrow_down")
    assert ctl(view).cursor.get() == 1 and ctl(view).selection.get() == [str(data / "f01.txt")]
    key(view, "page_down")
    assert ctl(view).cursor.get() == 6  # a page is a row less than the list shows
    assert scroller.get("scroll_offset") == 1 * 40  # the cursor row (the seventh) is the last one in view, so the first has gone
    key(view, "end")
    assert ctl(view).cursor.get() == 39 and scroller.get("scroll_offset") == 40 * 40 - 6 * 40
    assert "f39.txt" in shown_names(view) and "f00.txt" not in shown_names(view)
    key(view, "home")
    assert ctl(view).cursor.get() == 0 and scroller.get("scroll_offset") == 0
    key(view, "arrow_up")
    assert ctl(view).cursor.get() == 0
    key(view, "f", shift=False)  # a letter jumps to the next name that starts with it
    assert ctl(view).cursor.get() == 1


def test_alt_arrows_and_backspace_go_back_forward_and_up(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    pick(view, "Alpha")
    pick(view, "Alpha")
    key(view, "arrow_left", alt=True)
    assert ctl(view).folder.get() == str(base)
    key(view, "arrow_right", alt=True)
    assert ctl(view).folder.get() == str(base / "Alpha")
    key(view, "backspace")
    assert ctl(view).folder.get() == str(base)


def test_ctrl_a_picks_every_file_when_several_are_allowed_and_nothing_otherwise(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", multiple: true')
    key(view, "a", ctrl=True)
    assert [os.path.basename(p) for p in ctl(view).selection.get()] == ["A.TDL", "b.txt", "c.tdl", "notes.md"]
    other = tmp_path / "other"
    other.mkdir()
    view, vm = opened(other, f'start: "{base}"')
    key(view, "a", ctrl=True)
    assert ctl(view).selection.get() == []


def test_shift_with_the_arrows_extends_the_picks(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}", multiple: true')
    pick(view, "A.TDL")
    key(view, "arrow_down", shift=True)
    key(view, "arrow_down", shift=True)
    assert [os.path.basename(p) for p in ctl(view).selection.get()] == ["A.TDL", "b.txt", "c.tdl"]


def test_a_folder_of_ten_thousand_entries_opens_at_once_and_builds_only_the_rows_in_view(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    for i in range(10_000):
        (data / f"file{i:05d}.dat").write_text("")
    view, vm = opened(tmp_path, f'start: "{data}"', show=False)
    vm.shown.set(True)
    settle(view)
    assert len(ctl(view).entries.get()) == 10_000
    built = row_ids(view)
    assert 0 < len(built) <= 14  # eight rows in view, and the overscan (3) at each end
    assert shown_names(view)[0] == "file00000.dat"
    key(view, "end")
    assert ctl(view).cursor.get() == 9_999
    assert "file09999.dat" in shown_names(view) and len(row_ids(view)) <= 14
    pick(view, "file09999.dat")
    click(view, "actions.accept")
    assert vm.got.get() == str(data / "file09999.dat")


# -- accessibility -------------------------------------------------------------------------------------------------------------------

def test_the_dialog_the_list_and_the_buttons_have_roles_and_labels(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    panel = view._built.nodes[PANEL]
    assert panel.get("role") == "dialog" and panel.get("label") == "Open file"
    assert node(view, "list_group.list_box").get("role") == "list" and node(view, "list_group.list_box").get("label") == "Files and folders"
    for name, label in (("back", "Back"), ("forward", "Forward"), ("up", "Up"), ("home", "Home"), ("refresh", "Refresh")):
        assert node(view, f"toolbar.{name}").get("label") == label, name
    first = row(view, str(base / "Alpha"))
    assert first.get("role") == "listitem" and first.get("label") == "Alpha"
    pick(view, "b.txt")
    assert row(view, str(base / "b.txt")).get("selected") is True and row(view, str(base / "Alpha")).get("selected") is False
    other = tmp_path / "other"
    other.mkdir()
    view, vm = opened(other, f'start: "{base}", mode: save, headline: "Save the plan", accept_label: "Store"')
    assert view._built.nodes[PANEL].get("label") == "Save the plan" and node(view, "actions.accept.label").get("text") == "Store"
    third = tmp_path / "third"
    third.mkdir()
    view, vm = opened(third, f'start: "{base}", mode: folder')
    assert view._built.nodes[PANEL].get("label") == "Choose folder" and node(view, "list_group.list_box").get("label") == "Folders"


def test_an_error_is_announced_as_an_alert(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    typed(view, "toolbar.path_field", str(base / "missing"))
    enter(view, "toolbar.path_field")
    assert node(view, "message_text").get("role") == "alert"


# -- errors ----------------------------------------------------------------------------------------------------------------------------

class Fake:
    def __init__(self, folders):
        self.folders = folders
        self.denied = set()

    def list_dir(self, path):
        if path in self.denied:
            raise FileSystemError(f"Cannot open {path}: permission denied", path)
        if path not in self.folders:
            raise FileSystemError(f"Cannot open {path}: it is not there any more", path)
        return list(self.folders[path])

    def is_dir(self, path):
        return path in self.folders

    def exists(self, path):
        return path in self.folders or any(e.path == path for v in self.folders.values() for e in v)

    def make_dir(self, path):
        raise FileSystemError(f"Cannot create {path}: permission denied", path)

    def real_path(self, path):
        return path

    def home(self):
        return "/home"

    def cwd(self):
        return "/home"


def entry(folder, name, is_dir=False):
    return Entry(name, f"{folder}/{name}", is_dir, None if is_dir else 5, 86400.0 * 400, name.startswith("."))


def test_an_unreadable_folder_is_a_message_in_the_dialog_and_the_dialog_stays_usable(tmp_path, monkeypatch):
    fake = Fake({"/home": [entry("/home", "locked", True), entry("/home", "gone", True), entry("/home", "f.txt")], "/home/gone": [], "/home/locked": []})
    fake.denied.add("/home/locked")
    monkeypatch.setattr(filesystem, "_default", fake)
    view, vm = opened(tmp_path, 'start: "/home"')
    assert shown_names(view) == ["gone", "locked", "f.txt"]
    pick(view, "locked")
    pick(view, "locked")
    assert ctl(view).folder.get() == "/home" and node(view, "message_text").get("text") == "Cannot open /home/locked: permission denied"
    pick(view, "f.txt")
    assert ctl(view).valid.get()  # the message stays until a folder is entered or the listing is read again
    click(view, "actions.accept")
    assert vm.got.get() == "/home/f.txt"


def test_a_folder_that_goes_while_the_dialog_shows_it_is_an_empty_list_with_the_reason(tmp_path, monkeypatch):
    fake = Fake({"/home": [entry("/home", "x.txt")], "/home/sub": [entry("/home/sub", "y.txt")]})
    monkeypatch.setattr(filesystem, "_default", fake)
    view, vm = opened(tmp_path, 'start: "/home/sub"')
    assert shown_names(view) == ["y.txt"]
    del fake.folders["/home/sub"]
    click(view, "toolbar.refresh")
    assert shown_names(view) == [] and node(view, "message_text").get("text") == "There is no folder /home/sub"
    assert f"{PANEL}.empty" not in view._built.nodes  # the message says why: no second line
    click(view, "toolbar.up")
    assert shown_names(view) == ["x.txt"] and f"{PANEL}.message_text" not in view._built.nodes


def test_a_start_that_cannot_be_read_opens_the_nearest_folder_above_it_with_the_reason(tmp_path, monkeypatch):
    fake = Fake({"/home": [entry("/home", "x.txt")]})
    monkeypatch.setattr(filesystem, "_default", fake)
    view, vm = opened(tmp_path, 'start: "/home/nowhere/deeper"')
    assert ctl(view).folder.get() == "/home" and node(view, "message_text").get("text") == "There is no folder /home/nowhere/deeper"


def test_an_empty_folder_says_so(tmp_path):
    base = tmp_path / "empty"
    base.mkdir()
    view, vm = opened(tmp_path, f'start: "{base}"')
    assert node(view, "empty").get("text") == "This folder is empty"
    assert f"{PANEL}.message_text" not in view._built.nodes


def test_new_folder_that_the_place_refuses_is_a_message(tmp_path, monkeypatch):
    fake = Fake({"/home": [entry("/home", "x.txt")]})
    monkeypatch.setattr(filesystem, "_default", fake)
    view, vm = opened(tmp_path, 'start: "/home", mode: save')
    click(view, "options.new_folder_button")
    typed(view, "new_folder_row.new_folder_field", "made")
    click(view, "new_folder_row.new_folder_make")
    assert node(view, "message_text").get("text") == "Cannot create /home/made: permission denied"


# -- opening it from Python ----------------------------------------------------------------------------------------------------------------

class PythonVM(ViewModel):
    views = "main"

    def __init__(self):
        super().__init__()
        self.files = FileDialogRequest(self)
        self.heard = []


def requested(tmp_path):
    (tmp_path / "Views").mkdir(parents=True, exist_ok=True)
    (tmp_path / "Views" / "Main_View.yaml").write_text("""tesserae: 0.6
name: main
widget: Container
style: {flex_direction: vertical, width: 900, height: 800}
children:
  - {widget: Rect, name: elsewhere, style: {width: 80, height: 80, background: surface_variant}}
  - widget: FileDialog
    name: fd
    open: "{{ file_open }}"
    mode: "{{ file_mode }}"
    start: "{{ file_start }}"
    root: "{{ file_root }}"
    filters: "{{ file_filters }}"
    filter: "{{ file_filter }}"
    filename: "{{ file_filename }}"
    multiple: "{{ file_multiple }}"
    headline: "{{ file_headline }}"
    accept_label: "{{ file_accept_label }}"
    show_hidden: "{{ file_show_hidden }}"
    value: "{{ file_value }}"
    on_accept: file_accepted
    on_cancel: file_cancelled
""")
    app = App(root=tmp_path, width=900, height=800)
    app.bind(PythonVM)
    view = app.open_view("Main")
    app.show("main")
    settle(view)
    assert app.check() == []
    return view, app.bindings.viewmodel_for("main")


def test_a_viewmodel_opens_the_dialog_and_hears_the_paths(tmp_path):
    base = tree(tmp_path)
    view, vm = requested(tmp_path)
    vm.files.show(mode="open", start=str(base), filters=[{"label": "TDL", "patterns": ["*.tdl"]}], headline="Open a plan",
                  on_accept=lambda paths: vm.heard.append(("accept", paths)), on_cancel=lambda: vm.heard.append(("cancel",)))
    settle(view)
    assert vm.files.is_open and shown_names(view) == ["Alpha", "beta", "A.TDL", "c.tdl"] and view._built.nodes[PANEL].get("label") == "Open a plan"
    pick(view, "c.tdl")
    click(view, "actions.accept")
    assert vm.heard == [("accept", [str(base / "c.tdl")])] and not vm.files.is_open  # a list, though one path


def test_several_paths_and_a_cancel_come_back_through_the_callbacks(tmp_path):
    base = tree(tmp_path)
    view, vm = requested(tmp_path)
    vm.files.show(start=str(base), multiple=True, on_accept=lambda paths: vm.heard.append(("accept", paths)), on_cancel=lambda: vm.heard.append(("cancel",)))
    settle(view)
    pick(view, "b.txt")
    pick(view, "notes.md", ctrl=True)
    click(view, "actions.accept")
    assert vm.heard == [("accept", [str(base / "b.txt"), str(base / "notes.md")])]
    vm.files.show(mode="folder", start=str(base), on_accept=lambda paths: vm.heard.append(("accept", paths)), on_cancel=lambda: vm.heard.append(("cancel",)))
    settle(view)
    assert shown_names(view) == ["Alpha", "beta"]
    click(view, "actions.cancel")
    assert vm.heard[-1] == ("cancel",) and len(vm.heard) == 2 and not vm.files.is_open


def test_showing_again_while_open_replaces_the_request_and_close_calls_nothing(tmp_path):
    base = tree(tmp_path)
    view, vm = requested(tmp_path)
    vm.files.show(start=str(base), on_cancel=lambda: vm.heard.append("first cancelled"))
    settle(view)
    vm.files.show(mode="save", start=str(base / "Alpha"), filename="x.txt", on_accept=lambda paths: vm.heard.append(paths))
    settle(view)
    assert ctl(view).folder.get() == str(base / "Alpha") and node(view, "actions.accept.label").get("text") == "Save" and ctl(view).filename.get() == "x.txt"
    click(view, "actions.accept")
    assert vm.heard == [[str(base / "Alpha" / "x.txt")]]
    vm.files.show(start=str(base), on_cancel=lambda: vm.heard.append("never"))
    settle(view)
    vm.files.close()
    settle(view)
    assert not vm.files.is_open and vm.heard == [[str(base / "Alpha" / "x.txt")]]
    with pytest.raises(ValueError, match="mode is open, save or folder"):
        vm.files.show(mode="pick")


def test_opening_puts_the_focus_in_the_list_so_the_keys_work_at_once(tmp_path):
    base = tree(tmp_path)
    view, vm = opened(tmp_path, f'start: "{base}"')
    assert view._built.nodes[f"{PANEL}.list_group.list_box"].get("focused")
    view.window.simulate("key_down", key="arrow_down")
    settle(view)
    assert ctl(view).cursor.get() == 0
