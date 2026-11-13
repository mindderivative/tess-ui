"""The file system as the file dialog sees it: a handful of calls, so a test (or an app that browses something that is not the disk) can swap it.

`FileSystem` is the whole interface: `list_dir` (one folder, not its subfolders, each entry with the size and time it has), `is_dir`, `exists`, `make_dir`,
`real_path` (where a path really leads, symlinks followed, so a root can confine browsing) and the two places a dialog starts from, `home` and `cwd`. `LocalFileSystem`
is the disk. Every failure that a person can cause or meet (a folder that is not readable, has gone, or is a file; a name that is taken) is a `FileSystemError` whose text
is fit to show, and nothing else leaks out of a listing.

A folder is read once, when the dialog enters it, with one `scandir` and one `stat` per entry; nothing walks below it.
"""

from __future__ import annotations

import errno
import os
from dataclasses import dataclass
from typing import Protocol

__all__ = ["Entry", "FileSystem", "FileSystemError", "LocalFileSystem", "default", "use"]


class FileSystemError(Exception):
    """A file system call that failed in a way to tell the person: `str(error)` is the sentence, `path` the place it is about."""

    def __init__(self, message: str, path: str = "") -> None:
        super().__init__(message)
        self.path = path


@dataclass(frozen=True, slots=True)
class Entry:
    """One thing in a folder: its `name`, full `path`, whether it is a folder (a link to one is), its `size` in bytes and `modified` time (seconds since
    the epoch; `None` for a folder's size, and for either when the entry cannot be stat'ed, such as a broken link), and whether it is `hidden` (a name that starts with a dot)."""

    name: str
    path: str
    is_dir: bool
    size: int | None
    modified: float | None
    hidden: bool


class FileSystem(Protocol):
    """What the dialog needs of a file system."""

    def list_dir(self, path: str) -> list[Entry]:
        """The entries of the folder `path`, in no particular order. Raises `FileSystemError` when it cannot be read."""
        ...

    def is_dir(self, path: str) -> bool:
        """Whether `path` is a folder (a link to one is)."""
        ...

    def exists(self, path: str) -> bool:
        """Whether there is anything at `path`, a broken link included."""
        ...

    def make_dir(self, path: str) -> None:
        """Makes the folder `path` (its parent must be there). Raises `FileSystemError` when it cannot: the name is taken, or the place is not writable."""
        ...

    def real_path(self, path: str) -> str:
        """`path` with symlinks followed, as a root's check wants it."""
        ...

    def home(self) -> str:
        """The person's home folder."""
        ...

    def cwd(self) -> str:
        """The working folder."""
        ...


def _explain(error: OSError, path: str, what: str) -> FileSystemError:
    """A sentence for an `OSError`, with the place it is about."""
    code = error.errno
    if isinstance(error, PermissionError) or code in (errno.EACCES, errno.EPERM):
        reason = "permission denied"
    elif isinstance(error, FileNotFoundError) or code == errno.ENOENT:
        reason = "it is not there any more"
    elif isinstance(error, NotADirectoryError) or code == errno.ENOTDIR:
        reason = "it is not a folder"
    elif isinstance(error, FileExistsError) or code == errno.EEXIST:
        reason = "that name is taken"
    else:
        reason = error.strerror or type(error).__name__
    return FileSystemError(f"Cannot {what} {path}: {reason}", path)


class LocalFileSystem:
    """The disk."""

    def list_dir(self, path: str) -> list[Entry]:
        """The entries of the folder `path`: one `scandir` and one `stat` for each; a failure is a `FileSystemError` in words."""
        found: list[Entry] = []
        try:
            with os.scandir(path) as scan:
                for item in scan:
                    try:
                        is_dir = item.is_dir()  # a link to a folder is one
                    except OSError:
                        is_dir = False
                    size: int | None = None
                    modified: float | None = None
                    try:
                        info = item.stat()
                        modified = info.st_mtime
                        size = None if is_dir else info.st_size
                    except OSError:  # a broken link, or a file that went while we read
                        pass
                    found.append(Entry(item.name, item.path, is_dir, size, modified, item.name.startswith(".")))
        except OSError as error:
            raise _explain(error, path, "open") from None
        return found

    def is_dir(self, path: str) -> bool:
        """Whether `path` is a folder (a link to one is)."""
        return os.path.isdir(path)

    def exists(self, path: str) -> bool:
        """Whether there is anything at `path`, a broken link included."""
        return os.path.lexists(path)

    def make_dir(self, path: str) -> None:
        """Makes the folder `path`; a name that is taken, or a place that will not take it, is a `FileSystemError`."""
        try:
            os.mkdir(path)
        except OSError as error:
            raise _explain(error, path, "create") from None

    def real_path(self, path: str) -> str:
        """`path` with its symlinks followed."""
        return os.path.realpath(path)

    def home(self) -> str:
        """The person's home folder."""
        return os.path.expanduser("~")

    def cwd(self) -> str:
        """The working folder."""
        return os.getcwd()


_default: FileSystem = LocalFileSystem()


def default() -> FileSystem:
    """The file system a dialog uses when it is not given one: the disk, unless `use` put another in its place."""
    return _default


def use(filesystem: FileSystem | None) -> FileSystem:
    """Makes `filesystem` the default (`None` puts the disk back) and returns the one it replaced, so a test can put that back."""
    global _default
    previous = _default
    _default = filesystem if filesystem is not None else LocalFileSystem()
    return previous
