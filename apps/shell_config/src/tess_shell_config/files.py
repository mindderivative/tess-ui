"""Reading and writing the user's `.tdl` files without changing a byte they did not change.

A file is read as bytes and decoded as UTF-8 with `surrogateescape`, so any byte string decodes and encodes back to itself: a byte order mark, CRLF or
a lone CR, and even bytes that are not UTF-8 survive. `write_atomic` writes a temporary file in the same folder and renames it over the old one, so a
full disk or a refused write leaves the old file whole. `Backups` copies a file's old content into the application's own state folder before the first
save of it in a session.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

__all__ = ["APP_DIR_NAME", "state_dir", "decode", "encode", "display_text", "is_utf8", "read_text", "write_atomic", "SaveError", "ChangedOnDisk", "Backups"]

APP_DIR_NAME = "tesserae-shell-config"


def state_dir(environ: dict[str, str] | None = None) -> Path:
    """The application's own state folder: `$XDG_STATE_HOME/tesserae-shell-config`, else `~/.local/state/tesserae-shell-config` (a relative `XDG_STATE_HOME` is invalid and ignored)."""
    env = os.environ if environ is None else environ
    base = env.get("XDG_STATE_HOME", "")
    if base and os.path.isabs(base):
        return Path(base) / APP_DIR_NAME
    home = env.get("HOME") or str(Path.home())
    return Path(home) / ".local" / "state" / APP_DIR_NAME


def decode(raw: bytes) -> str:
    """Bytes to text, keeping every byte: what is not UTF-8 becomes a lone surrogate that `encode` turns back into the same byte."""
    return raw.decode("utf-8", "surrogateescape")


def encode(text: str) -> bytes:
    return text.encode("utf-8", "surrogateescape")


def is_utf8(raw: bytes) -> bool:
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def display_text(text: str) -> str:
    """The text as a person's screen can show it: a byte that is not UTF-8 is drawn as the replacement character. Never saved."""
    return encode(text).decode("utf-8", "replace")


def read_text(path: str | Path) -> str:
    return decode(Path(path).read_bytes())


class SaveError(OSError):
    """A file could not be written. `str(error)` names the file and the cause; the old file is untouched."""


class ChangedOnDisk(SaveError):
    """The file on disk is not what this application last read or wrote: another program changed it. Nothing was written; the person is asked to reload or to keep their version."""

    def __init__(self, relative: str) -> None:
        self.relative = relative
        super().__init__(f"{relative} was changed on disk by another program since it was opened or saved here. Nothing was written: reload it, or keep your version.")


def write_atomic(path: str | Path, data: bytes) -> None:
    """Write `data` to `path` through a temporary file in the same folder, then rename it over the old file. The old file's permissions are kept."""
    path = Path(path)
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            shutil.copymode(path, temporary)
        os.replace(temporary, path)
        temporary = None
    except OSError as error:
        reason = error.strerror or str(error)
        raise SaveError(f"Cannot save {path.name}: {reason[:1].lower() + reason[1:]}. The old file is unchanged.") from error
    finally:
        if temporary is not None:
            with contextlib.suppress(OSError):
                os.unlink(temporary)


@dataclass
class Backups:
    """The first save of each file in a session copies the old content to `<state>/backups/<session>/<relative path>`; a file that is not there yet has nothing to copy."""

    root: Path
    session: str = ""

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.session = self.session or datetime.now().strftime("%Y%m%d-%H%M%S")
        self._done: set[Path] = set()

    @property
    def folder(self) -> Path:
        return self.root / "backups" / self.session

    def before_save(self, path: str | Path, relative: str | Path) -> Path | None:
        """Copy `path`'s content aside if this is its first save in the session. Returns where the copy is, or `None` (not the first save, or no old file)."""
        path = Path(path)
        if path in self._done:
            return None
        self._done.add(path)
        if not path.is_file():
            return None
        target = self.folder / Path(relative)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        except OSError as error:
            self._done.discard(path)  # nothing was kept: try again at the next save, and tell this one
            raise SaveError(f"Cannot keep a backup of {path.name} in {self.folder}: {error.strerror or error}. The file was not saved.") from error
        return target
