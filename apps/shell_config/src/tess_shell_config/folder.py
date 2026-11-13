"""The configuration folder: where it is, and its files by type.

A file's type is the word of its root block (`Shell`, `Module`, `Style`, `Stylesheet`, `Theme`, `Settings`), read with `tess_dl`. A file that does not parse far enough to
have a root block is typed by its name (`Name_Shell.tdl`, `settings.tdl`), and a file the application cannot place is listed under "Other". Nothing outside the folder is read,
and a `.tdl` file is never opened for writing here.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from tess_shell_config.files import decode
from tess_shell_config.tdl import parse_text

__all__ = ["FileType", "ConfigFile", "resolve_config_dir", "default_config_dir", "scan", "classify"]

#: Folders of the configuration directory that hold no configuration: generated schemas, logs, icons, the application's own trash.
SKIPPED_FOLDERS = frozenset({"schemas", "logs", "Icons", ".trash"})


class FileType(Enum):
    """The kinds of file, in the order the Files area lists them. `root` is the word of the root block that makes a file this type."""

    SHELL = ("Shell", "Shells")
    MODULE = ("Module", "Modules")
    STYLE = ("Style", "Styles")
    STYLESHEET = ("Stylesheet", "Stylesheets")
    THEME = ("Theme", "Themes")
    SETTINGS = ("Settings", "Settings")
    OTHER = ("", "Other files")

    def __init__(self, root: str, label: str) -> None:
        self.root = root
        self.label = label

    @classmethod
    def for_root(cls, root: str) -> FileType:
        return next((t for t in cls if t.root and t.root == root), cls.OTHER)

    @classmethod
    def for_name(cls, filename: str) -> FileType:
        """The type a file name says: `X_Shell.tdl` is a Shell, `settings.tdl` is the Settings. Used only when the root block cannot be read."""
        if filename == "settings.tdl":
            return cls.SETTINGS
        stem = filename.removesuffix(".tdl")
        return next((t for t in cls if t.root and t is not cls.SETTINGS and stem.endswith("_" + t.root)), cls.OTHER)


@dataclass(frozen=True)
class ConfigFile:
    """One file of the folder: where it is, its path from the folder (`rel`, with `/`), its type, its metadata `Name` and how many syntax errors it has."""

    path: Path
    rel: str
    type: FileType
    name: str
    errors: int

    @property
    def parses(self) -> bool:
        return self.errors == 0


def default_config_dir(environ: Mapping[str, str] | None = None) -> Path:
    """The shell's own discovery rule: `$XDG_CONFIG_HOME/tesserae-shell` when that is set and absolute, else `~/.config/tesserae-shell`."""
    env = os.environ if environ is None else environ
    base = env.get("XDG_CONFIG_HOME", "")
    if base and os.path.isabs(base):
        return Path(base) / "tesserae-shell"
    return Path(env.get("HOME") or str(Path.home())) / ".config" / "tesserae-shell"


def resolve_config_dir(argument: str | os.PathLike[str] | None, status_dir: str | None = None, environ: Mapping[str, str] | None = None) -> Path:
    """The folder to open: the one given with `--config-dir`, else the one the shell's `status --json` names, else the default place."""
    if argument:
        return Path(argument).expanduser()
    if status_dir:
        return Path(status_dir).expanduser()
    return default_config_dir(environ)


def classify(path: Path, raw: bytes, rel: str) -> ConfigFile:
    """Read one file's root block with `tess_dl` and say what it is."""
    parsed = parse_text(decode(raw), rel)
    if parsed.document is not None:
        document = parsed.document
        meta = document.metadata
        try:
            name = str(meta["Name"].text)  # type: ignore[attr-defined]
        except (KeyError, AttributeError, TypeError):
            name = path.stem
        return ConfigFile(path, rel, FileType.for_root(document.root.type), name, 0)
    return ConfigFile(path, rel, FileType.for_name(path.name), path.stem, max(1, len(parsed.errors)))


def scan(folder: str | os.PathLike[str]) -> list[ConfigFile]:
    """Every `.tdl` file under `folder`, typed, in the Files area's order (by type, then by path). A missing folder is an empty list."""
    base = Path(folder)
    files: list[ConfigFile] = []
    if not base.is_dir():
        return files
    for current, folders, names in os.walk(base):
        folders[:] = sorted(f for f in folders if f not in SKIPPED_FOLDERS and not f.startswith("."))
        for filename in names:
            if not filename.endswith(".tdl") or filename.startswith("."):
                continue
            path = Path(current) / filename
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            files.append(classify(path, raw, path.relative_to(base).as_posix()))
    order = {t: i for i, t in enumerate(FileType)}
    files.sort(key=lambda f: (order[f.type], f.rel.casefold()))
    return files
