"""What the Files area does to the files of the configuration folder: a new file of a type, a duplicate, a rename and a delete that moves the file to the trash folder of the application's own state folder.

Nothing here removes a file: a deleted file is moved to `<state>/trash/<time>/<path in the folder>` and stays there. A new file is a minimal valid one: its metadata block and the root block of its type, empty.
A name is one word of letters, digits and `_` starting with a letter; the file is `Name_Type.tdl` (`settings.tdl` for the settings), a module in a folder of its own name. A file with a `Name` in its metadata
has that changed along with its file name by a duplicate and a rename, so two files never share a name. Each function says what it did in a returned path, and raises `FileOpError` with the message to show.
"""

from __future__ import annotations

import contextlib
import re
import shutil
from datetime import datetime
from pathlib import Path

import tess_dl

from tess_shell_config.files import SaveError, decode, encode, write_atomic
from tess_shell_config.folder import ConfigFile, FileType
from tess_shell_config.tdl import parse_text

__all__ = ["FileOpError", "TRASH", "SETTINGS_FILE", "valid_name", "name_of", "rel_for", "minimal_text", "unique_name", "create", "duplicate", "rename", "trash"]

#: The folder of the application's state folder that holds deleted files.
TRASH = "trash"
#: The one file of the settings type.
SETTINGS_FILE = "settings.tdl"
#: The folder of each type of file in the configuration folder.
_FOLDERS = {FileType.SHELL: "Shells", FileType.MODULE: "Modules", FileType.STYLE: "Styles", FileType.STYLESHEET: "Stylesheets", FileType.THEME: "Themes"}
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class FileOpError(Exception):
    """A file operation that cannot be done; `str(error)` says why. Nothing was changed."""


def valid_name(name: str) -> bool:
    return bool(_NAME.match(name))


def name_of(entry: ConfigFile) -> str:
    """The name a file is called: its stem without the `_Type` ending (`Main_Shell.tdl` -> `Main`)."""
    stem = entry.path.stem
    suffix = f"_{entry.type.root}"
    return stem[: -len(suffix)] if entry.type.root and stem.endswith(suffix) and len(stem) > len(suffix) else stem


def rel_for(file_type: FileType, name: str) -> str:
    """Where a new file of `file_type` called `name` goes, from the folder: `Themes/Mine_Theme.tdl`, `Modules/Mine/Mine_Module.tdl`, `settings.tdl`."""
    if file_type is FileType.SETTINGS:
        return SETTINGS_FILE
    folder = _FOLDERS.get(file_type)
    if folder is None:
        raise FileOpError("A file of no type cannot be made here: choose Shell, Module, Style, Stylesheet, Theme or Settings.")
    inner = f"{name}/" if file_type is FileType.MODULE else ""
    return f"{folder}/{inner}{name}_{file_type.root}.tdl"


def minimal_text(file_type: FileType, name: str, layout: str = "") -> str:
    """The text of a new file: the metadata block (`TDL` the language version `tess_dl` writes, and the `Name`) and the empty root block of its type. A module is not valid without its one layout block (the
    real checker: "a module has one layout root"), so a new module holds an empty `layout` block, the type the caller took from the schema (`blocks.module_layout`); `""` writes none."""
    body = f"{file_type.root} {{ }}" if not (layout and file_type is FileType.MODULE) else f"{file_type.root} {{\n    {layout} {{ }}\n}}"
    return f"---\nTDL: {tess_dl.LANGUAGE_VERSION}\nName: {name}\n---\n\n{body}\n"


def unique_name(files: list[ConfigFile], file_type: FileType, base: str) -> str:
    """`base`, or `base_2`, `base_3`... when a file of that type already has the name."""
    taken = {name_of(f).casefold() for f in files if f.type is file_type}
    candidate, number = base, 2
    while candidate.casefold() in taken:
        candidate, number = f"{base}_{number}", number + 1
    return candidate


def _check_new(folder: Path, files: list[ConfigFile], file_type: FileType, name: str, rel: str) -> None:
    if not valid_name(name):
        raise FileOpError(f"{name!r} is not a name: use letters, digits and _, starting with a letter.")
    if (folder / rel).exists() or any(f.rel.casefold() == rel.casefold() for f in files):
        raise FileOpError(f"{rel} already exists.")
    if file_type is not FileType.SETTINGS and any(f.type is file_type and name_of(f).casefold() == name.casefold() for f in files):
        raise FileOpError(f"A {file_type.root.lower()} called {name} already exists.")


def _write_new(folder: Path, rel: str, text: str) -> Path:
    target = folder / rel
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        write_atomic(target, encode(text))
    except (SaveError, OSError) as error:
        raise FileOpError(str(error)) from error
    return target


def create(folder: Path, files: list[ConfigFile], file_type: FileType, name: str, layout: str = "") -> str:
    """Write a new file of `file_type` called `name` (a module with an empty `layout` block, see `minimal_text`); returns its path from the folder."""
    rel = rel_for(file_type, name)
    _check_new(folder, files, file_type, name, rel)
    _write_new(folder, rel, minimal_text(file_type, name, layout))
    return rel


def _renamed_text(raw: bytes, new_name: str) -> str:
    """The file's text with its metadata `Name` changed (a file that does not parse is copied as it is)."""
    text = decode(raw)
    document = parse_text(text).document
    if document is None or document.metadata.get("Name") is None:
        return text
    return str(document.with_metadata("Name", new_name).text)


def _typed_target(entry: ConfigFile, new_name: str) -> str:
    """Where a file of the same type as `entry` and called `new_name` goes: beside the old one (a module in a folder of its own name, the new folder)."""
    if entry.type is FileType.OTHER:
        return (Path(entry.rel).parent / f"{new_name}.tdl").as_posix()
    if entry.type is FileType.MODULE and Path(entry.rel).parent.name == name_of(entry):
        return rel_for(FileType.MODULE, new_name)
    return (Path(entry.rel).parent / f"{new_name}_{entry.type.root}.tdl").as_posix()


def duplicate(folder: Path, files: list[ConfigFile], entry: ConfigFile, new_name: str) -> str:
    """Copy `entry` under `new_name` (its metadata `Name` follows); returns the new path from the folder. The settings file has no copy: there is one."""
    if entry.type is FileType.SETTINGS:
        raise FileOpError("settings.tdl is the one file of its kind: it cannot be copied.")
    rel = _typed_target(entry, new_name)
    _check_new(folder, files, entry.type, new_name, rel)
    _write_new(folder, rel, _renamed_text(entry.path.read_bytes(), new_name))
    return rel


def rename(folder: Path, files: list[ConfigFile], entry: ConfigFile, new_name: str, state_dir: Path) -> str:
    """Give `entry` another name: its file (a module's folder too) and its metadata `Name`; returns the new path from the folder. The old file is moved to the trash folder, not deleted."""
    if entry.type is FileType.SETTINGS:
        raise FileOpError("settings.tdl keeps its name: the shell looks for that file.")
    if new_name == name_of(entry):
        raise FileOpError(f"It is called {new_name} already.")
    rel = _typed_target(entry, new_name)
    _check_new(folder, [f for f in files if f.rel != entry.rel], entry.type, new_name, rel)
    _write_new(folder, rel, _renamed_text(entry.path.read_bytes(), new_name))
    old_module_folder = entry.path.parent if entry.type is FileType.MODULE and entry.path.parent.name == name_of(entry) else None
    trash(folder, entry, state_dir)
    if old_module_folder is not None:
        with contextlib.suppress(OSError):  # only when it is empty now: a module's other files stay where they are
            old_module_folder.rmdir()
    return rel


def trash(folder: Path, entry: ConfigFile, state_dir: Path, now: datetime | None = None) -> Path:
    """Move `entry` to `<state>/trash/<time>/<its path in the folder>` (never removed, never overwritten); returns where it is now."""
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    target = state_dir / TRASH / stamp / entry.rel
    number = 1
    while target.exists():
        number += 1
        target = state_dir / TRASH / f"{stamp}-{number}" / entry.rel
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(entry.path), str(target))
    except OSError as error:
        raise FileOpError(f"Cannot move {entry.rel} to the trash folder {target.parent}: {error.strerror or error}. The file is where it was.") from error
    return target
