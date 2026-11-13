"""Lossless open and save: the bytes of every file survive opening and saving unchanged (the tess_dl corpus, the shell's shipped files and representative files), a save is atomic,
the first save keeps a backup in the application's own state folder."""

import os
import shutil
import stat
from pathlib import Path

import pytest

from tess_shell_config.files import Backups, SaveError, decode, display_text, encode, state_dir, write_atomic
from tess_shell_config.model import DocumentModel
from tess_shell_config.session import ConfigSession

FIXTURES = Path(__file__).parent / "fixtures"
CORPUS = sorted((FIXTURES / "corpus").rglob("*.tdl"))
SHIPPED = sorted((FIXTURES / "shipped").rglob("*.tdl"))
CONFIG = sorted((FIXTURES / "config").rglob("*.tdl"))


def test_the_fixtures_are_there():
    assert len(CORPUS) >= 150 and len(SHIPPED) >= 30 and len(CONFIG) >= 8


@pytest.mark.parametrize("source", CORPUS + SHIPPED + CONFIG, ids=lambda p: p.relative_to(FIXTURES).as_posix())
def test_opening_and_saving_a_file_unchanged_leaves_it_byte_for_byte_the_same(source, tmp_path):
    """The acceptance criterion: open, save without a change, compare the bytes. Files with syntax errors (the corpus has many) open in the text view and save the same."""
    folder = tmp_path / "cfg"
    target = folder / "Shells" / "X_Shell.tdl"
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    before = target.read_bytes()
    session = ConfigSession(folder, state_dir=tmp_path / "state")
    model = session.open("Shells/X_Shell.tdl")
    assert model.data == before and not model.dirty
    session.save()
    assert target.read_bytes() == before
    assert sorted(p.name for p in target.parent.iterdir()) == ["X_Shell.tdl"], "no temporary file is left"


def test_every_byte_string_decodes_and_encodes_back():
    raw = bytes(range(256)) * 3 + "\ufeffé\r\n\r\x00".encode()
    assert encode(decode(raw)) == raw


def test_a_file_that_is_not_utf8_is_shown_with_replacement_characters_and_saves_its_bytes():
    raw = b"---\nTDL: 0.1\nName: X\n---\nShell { A: \xff\xfe }\n"
    model = DocumentModel.from_bytes(raw, "x_Shell.tdl")
    assert not model.utf8 and model.data == raw and "\ufffd" in model.display_text
    assert display_text(decode(raw)).count("\ufffd") == 2


def test_the_state_folder_follows_xdg_state_home(tmp_path):
    assert state_dir({"XDG_STATE_HOME": str(tmp_path), "HOME": "/h"}) == tmp_path / "tesserae-shell-config"
    assert state_dir({"XDG_STATE_HOME": "relative", "HOME": "/h"}) == Path("/h/.local/state/tesserae-shell-config")
    assert state_dir({"HOME": "/h"}) == Path("/h/.local/state/tesserae-shell-config")


def test_a_save_changes_only_that_file_through_a_rename_and_keeps_the_mode(tmp_path):
    target = tmp_path / "a.tdl"
    target.write_bytes(b"old")
    target.chmod(0o640)
    inode = target.stat().st_ino
    write_atomic(target, b"new")
    assert target.read_bytes() == b"new" and stat.S_IMODE(target.stat().st_mode) == 0o640
    assert target.stat().st_ino != inode, "written to a temporary file and renamed over the old one"
    assert [p.name for p in tmp_path.iterdir()] == ["a.tdl"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to a read-only folder")
def test_a_failed_save_leaves_the_old_file_intact_and_names_the_cause(tmp_path):
    folder = tmp_path / "cfg"
    (folder / "Shells").mkdir(parents=True)
    target = folder / "Shells" / "Main_Shell.tdl"
    target.write_bytes(b"---\nTDL: 0.1\nName: X\n---\nShell { }\n")
    session = ConfigSession(folder, state_dir=tmp_path / "state")
    model = session.open("Shells/Main_Shell.tdl")
    model.set_value((), "Anything", "1")
    old = target.read_bytes()
    folder.joinpath("Shells").chmod(0o555)  # the folder cannot take a new (temporary) file
    try:
        with pytest.raises(SaveError) as raised:
            session.save()
    finally:
        folder.joinpath("Shells").chmod(0o755)
    assert "Main_Shell.tdl" in str(raised.value) and "permission denied" in str(raised.value) and "unchanged" in str(raised.value)
    assert target.read_bytes() == old and model.dirty, "the file is as it was and the edit is still there to save again"
    assert [p.name for p in target.parent.iterdir()] == ["Main_Shell.tdl"]
    session.save()
    assert target.read_bytes() == model.data and not model.dirty


def test_the_first_save_keeps_the_old_content_in_the_state_folder_and_later_saves_do_not(tmp_path):
    folder = tmp_path / "cfg"
    (folder / "Shells").mkdir(parents=True)
    target = folder / "Shells" / "Main_Shell.tdl"
    original = b"---\nTDL: 0.1\nName: X\n---\nShell { }\n"
    target.write_bytes(original)
    state = tmp_path / "state"
    session = ConfigSession(folder, state_dir=state)
    model = session.open("Shells/Main_Shell.tdl")
    model.set_value((), "A", "1")
    first = model.data
    session.save()
    kept = list((state / "backups").rglob("Main_Shell.tdl"))
    assert len(kept) == 1 and kept[0].read_bytes() == original and kept[0].relative_to(state).parts[:1] == ("backups",)
    model.set_value((), "A", "2")
    session.save()
    assert kept[0].read_bytes() == original and len(list((state / "backups").rglob("*.tdl"))) == 1, "the backup is of the first save only"
    assert target.read_bytes() != first
    assert not any(p.is_relative_to(folder) for p in kept), "nothing is kept in the shell's own folder"


def test_a_backup_that_cannot_be_kept_stops_the_save_and_names_the_cause(tmp_path):
    state = tmp_path / "state"
    state.write_text("a file where the folder should be")
    target = tmp_path / "a.tdl"
    target.write_bytes(b"x")
    with pytest.raises(SaveError, match="backup"):
        Backups(state).before_save(target, "a.tdl")
    assert target.read_bytes() == b"x"


def test_saving_with_no_open_file_is_a_message(tmp_path):
    with pytest.raises(SaveError, match="no open file"):
        ConfigSession(tmp_path, state_dir=tmp_path / "s").save()
