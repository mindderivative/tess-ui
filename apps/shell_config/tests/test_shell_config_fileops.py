"""The Files area's actions: a new file from a type, duplicate, rename, delete to the trash folder of the state folder (never removed)."""

import shutil
from datetime import datetime

import pytest
from test_shell_config_form_window import FormWindow
from test_shell_config_window import CONFIG

from tess_shell_config import fileops
from tess_shell_config.fileops import FileOpError
from tess_shell_config.folder import FileType, scan
from tess_shell_config.tdl import parse_text

TYPES = [FileType.SHELL, FileType.MODULE, FileType.STYLE, FileType.STYLESHEET, FileType.THEME, FileType.SETTINGS]


@pytest.fixture
def folder(tmp_path):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    return target


@pytest.fixture
def state(tmp_path):
    return tmp_path / "state"


def entry(folder, rel):
    return next(f for f in scan(folder) if f.rel == rel)


@pytest.mark.parametrize("file_type", TYPES)
def test_a_new_file_is_a_minimal_valid_one_with_its_metadata_block_and_its_types_empty_root(tmp_path, file_type):
    empty = tmp_path / "empty"
    empty.mkdir()
    rel = fileops.create(empty, [], file_type, "Mine")
    assert rel == {FileType.SHELL: "Shells/Mine_Shell.tdl", FileType.MODULE: "Modules/Mine/Mine_Module.tdl", FileType.STYLE: "Styles/Mine_Style.tdl",
                   FileType.STYLESHEET: "Stylesheets/Mine_Stylesheet.tdl", FileType.THEME: "Themes/Mine_Theme.tdl", FileType.SETTINGS: "settings.tdl"}[file_type]
    text = (empty / rel).read_text()
    parsed = parse_text(text)
    assert parsed.valid and parsed.document.root.type == file_type.root and not parsed.document.root.entries
    assert parsed.document.metadata.get("Name").text == "Mine" and text.startswith("---\nTDL: ")
    assert [(f.rel, f.type, f.errors) for f in scan(empty)] == [(rel, file_type, 0)]


def test_a_new_file_is_refused_for_a_bad_name_an_existing_file_or_an_existing_name(folder):
    files = scan(folder)
    for bad in ("", "1abc", "a b", "a/b", "../x", "x.y"):
        with pytest.raises(FileOpError, match="not a name"):
            fileops.create(folder, files, FileType.THEME, bad)
    with pytest.raises(FileOpError, match="already exists"):
        fileops.create(folder, files, FileType.THEME, "Dark")
    with pytest.raises(FileOpError, match="already exists"):
        fileops.create(folder, files, FileType.SETTINGS, "Settings")
    with pytest.raises(FileOpError, match="no type"):
        fileops.create(folder, files, FileType.OTHER, "X")
    assert sorted(p.name for p in (folder / "Themes").iterdir()) == ["Dark_Theme.tdl"]


def test_unique_name_counts_up(folder):
    files = scan(folder)
    assert fileops.unique_name(files, FileType.THEME, "Dark") == "Dark_2" and fileops.unique_name(files, FileType.THEME, "Fresh") == "Fresh"
    assert fileops.unique_name(files, FileType.SHELL, "Main") == "Main_2" and fileops.unique_name(files, FileType.STYLE, "Main") == "Main"


def test_a_duplicate_changes_the_name_in_the_metadata_and_nothing_else(folder):
    files = scan(folder)
    source = entry(folder, "Shells/Main_Shell.tdl")
    rel = fileops.duplicate(folder, files, source, "Main_Copy")
    assert rel == "Shells/Main_Copy_Shell.tdl"
    old, new = source.path.read_text(), (folder / rel).read_text()
    assert old.replace("Name: Main", "Name: Main_Copy", 1) == new
    with pytest.raises(FileOpError, match="already exists"):
        fileops.duplicate(folder, scan(folder), source, "Main_Copy")
    with pytest.raises(FileOpError, match="one file of its kind"):
        fileops.duplicate(folder, scan(folder), entry(folder, "settings.tdl"), "S2")


def test_a_file_with_syntax_errors_is_copied_byte_for_byte(folder):
    source = entry(folder, "Shells/Broken_Shell.tdl")
    rel = fileops.duplicate(folder, scan(folder), source, "Broken_Copy")
    assert (folder / rel).read_bytes() == source.path.read_bytes()


def test_a_module_copy_gets_a_folder_of_its_own_name(folder):
    rel = fileops.duplicate(folder, scan(folder), entry(folder, "Modules/Hello/Hello_Module.tdl"), "Hi")
    assert rel == "Modules/Hi/Hi_Module.tdl" and "Name: Hi" in (folder / rel).read_text()


def test_a_rename_moves_the_file_and_changes_the_name_and_the_old_file_is_in_the_trash(folder, state):
    source = entry(folder, "Themes/Dark_Theme.tdl")
    original = source.path.read_bytes()
    rel = fileops.rename(folder, scan(folder), source, "Night", state)
    assert rel == "Themes/Night_Theme.tdl" and not source.path.exists()
    assert (folder / rel).read_text() == original.decode().replace("Name: Dark", "Name: Night", 1)
    kept = list((state / "trash").rglob("Dark_Theme.tdl"))
    assert len(kept) == 1 and kept[0].read_bytes() == original


def test_a_module_rename_moves_its_folder_and_leaves_the_other_files_of_it(folder, state):
    (folder / "Modules" / "Hello" / "notes.txt").write_text("keep me")
    fileops.rename(folder, scan(folder), entry(folder, "Modules/Hello/Hello_Module.tdl"), "Hey", state)
    assert (folder / "Modules" / "Hey" / "Hey_Module.tdl").exists() and (folder / "Modules" / "Hello" / "notes.txt").read_text() == "keep me"
    assert not (folder / "Modules" / "Hello" / "Hello_Module.tdl").exists()


def test_a_rename_that_cannot_be_done_changes_nothing(folder, state):
    files = scan(folder)
    before = sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*"))
    for name, message in (("Dark", "already"), ("bad name", "not a name")):
        with pytest.raises(FileOpError, match=message):
            fileops.rename(folder, files, entry(folder, "Themes/Dark_Theme.tdl"), name, state)
    with pytest.raises(FileOpError, match="keeps its name"):
        fileops.rename(folder, files, entry(folder, "settings.tdl"), "Other", state)
    assert sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*")) == before and not state.exists()


def test_a_delete_moves_the_file_to_the_trash_folder_of_the_state_folder_and_never_removes_it(folder, state):
    source = entry(folder, "Styles/Hello_Style.tdl")
    original = source.path.read_bytes()
    now = datetime(2026, 11, 13, 12, 0, 0)
    first = fileops.trash(folder, source, state, now)
    assert first == state / "trash" / "20261113-120000" / "Styles" / "Hello_Style.tdl" and first.read_bytes() == original and not source.path.exists()
    source.path.write_bytes(b"second")  # the same name again at the same second: nothing is overwritten
    second = fileops.trash(folder, source, state, now)
    assert second != first and first.read_bytes() == original and second.read_bytes() == b"second"


def test_a_delete_that_fails_leaves_the_file_where_it_was(folder, tmp_path):
    source = entry(folder, "Styles/Hello_Style.tdl")
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where the trash folder should be")
    with pytest.raises(FileOpError, match="The file is where it was"):
        fileops.trash(folder, source, blocked)
    assert source.path.exists()


# -- in the window ---------------------------------------------------------------------------------------------------------------------

@pytest.fixture
def w(folder, tmp_path, schema):
    return FormWindow(folder, tmp_path, schema)


def files_of(w):
    return [r["value"] for g in w.vm.file_nodes.get() for r in g["children"]]


def test_the_buttons_are_enabled_for_a_chosen_file_and_new_is_always_there(w):
    assert not (w.vm.can_file_duplicate.get() or w.vm.can_file_rename.get() or w.vm.can_file_delete.get())
    w.vm.file_selected.set("g:Themes")
    w.settle()
    assert not w.vm.can_file_delete.get()
    w.open("Themes/Dark_Theme.tdl")
    assert w.vm.can_file_duplicate.get() and w.vm.can_file_rename.get() and w.vm.can_file_delete.get()
    w.open("settings.tdl")
    assert w.vm.can_file_delete.get() and not w.vm.can_file_duplicate.get() and not w.vm.can_file_rename.get()
    names = {inst.name for inst in w.built.view.handle.composition.walk() if inst.name}
    assert {"file_new_button", "file_duplicate_button", "file_rename_button", "file_delete_button"} <= names


def test_new_file_asks_for_the_type_then_the_name_and_opens_it(w, folder):
    w.vm.file_new()
    w.settle()
    assert w.vm.picker_title.get() == "New file of type" and [o["value"] for o in w.vm.picker_items.get()] == ["Shell", "Module", "Style", "Stylesheet", "Theme", "Settings"]
    w.vm.pick_option("Theme")
    w.settle()
    assert w.vm.prompt_open.get() and w.vm.prompt_text.get() == "New_Theme" and "theme" in w.vm.prompt_title.get()
    w.vm.prompt_accept("Dark")  # taken: the prompt stays open with the reason
    w.settle()
    assert w.vm.prompt_open.get() and "already exists" in w.vm.prompt_error.get()
    w.vm.prompt_accept("Fresh")
    w.settle()
    assert not w.vm.prompt_open.get() and (folder / "Themes" / "Fresh_Theme.tdl").exists()
    assert w.session.current == "Themes/Fresh_Theme.tdl" and "Themes/Fresh_Theme.tdl" in [r.rel for r in w.session.files] and w.vm.status.get() == "Made theme Fresh"
    assert "f:Themes/Fresh_Theme.tdl" in files_of(w) and w.vm.has_tree.get()


def test_new_settings_file_has_no_name_to_ask_and_the_one_there_is_refused(folder, tmp_path, schema):
    (folder / "settings.tdl").unlink()
    w = FormWindow(folder, tmp_path, schema)
    w.vm.file_new()
    w.vm.pick_option("Settings")
    w.settle()
    assert not w.vm.prompt_open.get() and (folder / "settings.tdl").exists() and w.session.current == "settings.tdl"
    w.vm.file_new()
    w.vm.pick_option("Settings")
    assert w.vm.status_is_error.get() and "exists already" in w.vm.status.get()


def test_duplicate_rename_and_delete_from_the_window(w, folder, tmp_path):
    w.open("Themes/Dark_Theme.tdl")
    w.vm.file_duplicate()
    w.settle()
    assert w.vm.prompt_text.get() == "Dark_Copy"
    w.vm.prompt_accept("Dusk")
    w.settle()
    assert (folder / "Themes" / "Dusk_Theme.tdl").exists() and w.session.current == "Themes/Dusk_Theme.tdl"
    w.vm.file_rename()
    w.settle()
    assert w.vm.prompt_text.get() == "Dusk"
    w.vm.prompt_accept("Dawn")
    w.settle()
    assert (folder / "Themes" / "Dawn_Theme.tdl").exists() and not (folder / "Themes" / "Dusk_Theme.tdl").exists() and w.session.current == "Themes/Dawn_Theme.tdl"
    w.vm.file_delete()
    w.settle()
    assert not (folder / "Themes" / "Dawn_Theme.tdl").exists() and w.session.current is None and not w.vm.has_file.get() and w.vm.text.get() == ""
    assert "f:Themes/Dawn_Theme.tdl" not in files_of(w) and "trash folder" in w.vm.status.get() and "not removed" in w.vm.status.get()
    assert [p.name for p in (tmp_path / "state" / "trash").rglob("*.tdl")].count("Dawn_Theme.tdl") == 1
    assert not w.vm.can_file_delete.get()


def test_a_file_with_unsaved_changes_is_not_renamed_or_deleted_and_a_copy_is_of_the_saved_file(w, folder):
    w.open("Themes/Dark_Theme.tdl")
    w.session.model.set_text(w.session.model.text + "\n# unsaved\n")
    w.vm.sync()
    w.settle()
    assert w.session.model.dirty
    for action in (w.vm.file_rename, w.vm.file_delete):
        action()
        assert w.vm.status_is_error.get() and "unsaved changes" in w.vm.status.get() and not w.vm.prompt_open.get()
    assert (folder / "Themes" / "Dark_Theme.tdl").exists()
    w.vm.file_duplicate()
    w.settle()
    assert w.vm.prompt_open.get()
    w.vm.prompt_accept("Dim")
    w.settle()
    assert "# unsaved" not in (folder / "Themes" / "Dim_Theme.tdl").read_text()


def test_cancel_closes_the_prompt_and_makes_nothing(w, folder):
    w.open("Themes/Dark_Theme.tdl")
    w.vm.file_rename()
    w.settle()
    w.vm.prompt_cancel()
    w.settle()
    assert not w.vm.prompt_open.get() and (folder / "Themes" / "Dark_Theme.tdl").exists()
    w.vm.prompt_accept("Whatever")  # nothing is waiting for it
    assert sorted(p.name for p in (folder / "Themes").iterdir()) == ["Dark_Theme.tdl"]


def test_the_file_actions_have_keys(w, folder):
    w.open("Themes/Dark_Theme.tdl")
    w.vm.shortcuts.move_focus(1)
    w.settle()
    w.key("f2")
    assert w.vm.prompt_open.get() and w.vm.prompt_text.get() == "Dark"
    w.vm.prompt_cancel()
    w.settle()
    w.key("d", ctrl=True, alt=True)
    assert w.vm.prompt_open.get() and w.vm.prompt_text.get() == "Dark_Copy"
    w.vm.prompt_cancel()
    w.settle()
    w.key("n", ctrl=True)
    assert w.vm.picker_title.get() == "New file of type"
