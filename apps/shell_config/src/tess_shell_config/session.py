"""The session: the configuration folder, the schema, the shell command, and the files open in it. Everything but the window, so tests drive it directly.

Open files are kept by their path from the folder (`rel`); each is a `DocumentModel` that stays in memory, with its history, while the session lasts, so moving to
another file loses nothing. A save writes the file through a temporary file in its own folder and renames it; the first save of a file keeps its old content in the
application's own state folder.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

from tess_shell_config.files import Backups, ChangedOnDisk, SaveError, read_text, state_dir as default_state_dir, write_atomic
from tess_shell_config.folder import ConfigFile, FileType, scan
from tess_shell_config.model import DocumentModel
from tess_shell_config.schema import Schema
from tess_shell_config.shell import ShellCommand
from tess_shell_config.usermodules import MODULES_FOLDER, user_modules

__all__ = ["ConfigSession"]


class ConfigSession:
    """`folder` is the configuration folder, `schema` what the shell exported, `shell` the command layer (or `None` in a test that needs no command)."""

    def __init__(self, folder: str | Path, schema: Schema | None = None, shell: ShellCommand | None = None, state_dir: str | Path | None = None) -> None:
        self.folder = Path(folder)
        self.shipped_schema = schema  # what the shell exported
        self.schema = schema  # that, and the user's own modules
        self._modules_key: tuple[tuple[str, str, str], ...] = ()
        self.shell = shell
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
        self.backups = Backups(self.state_dir)
        self.files: list[ConfigFile] = []
        self.models: dict[str, DocumentModel] = {}
        self.current: str | None = None
        self.refresh()

    def refresh(self) -> list[ConfigFile]:
        """Read the folder again: the files by type, and the user's own modules."""
        self.files = scan(self.folder)
        self.update_modules()
        return self.files

    def update_modules(self) -> None:
        """Read the `Params` of the module files in the folder's `Modules/` folder (an open file's unsaved text, else the file on disk) and add those modules to the schema. Work is done only for a file whose text changed."""
        if self.shipped_schema is None:
            return
        seen: dict[str, tuple[str, str, str]] = {}
        for entry in self.files:
            if entry.type is not FileType.MODULE or not entry.rel.startswith(MODULES_FOLDER + "/"):
                continue
            model = self.models.get(entry.rel)
            try:
                text = model.text if model is not None else read_text(entry.path)
            except OSError:
                continue
            seen[entry.rel] = (entry.rel, text, entry.name)
        key = tuple(seen.values())
        if key == self._modules_key:
            return
        self._modules_key = key
        self.schema = self.shipped_schema.with_modules(user_modules(key, self.shipped_schema))

    def file(self, rel: str) -> ConfigFile:
        found = next((f for f in self.files if f.rel == rel), None)
        if found is None:
            raise KeyError(f"{rel} is not a file of {self.folder}")
        return found

    def open(self, rel: str) -> DocumentModel:
        """Open `rel` (read it from disk the first time) and make it the current file."""
        model = self.models.get(rel)
        if model is None:
            entry = self.file(rel)
            model = DocumentModel.from_bytes(entry.path.read_bytes(), entry.path, relative=rel)
            self.models[rel] = model
        self.current = rel
        return model

    def close(self, rel: str) -> None:
        self.models.pop(rel, None)
        if self.current == rel:
            self.current = None

    @property
    def model(self) -> DocumentModel | None:
        return self.models.get(self.current) if self.current else None

    def changed_on_disk(self, rel: str) -> bytes | None:
        """The bytes on disk when another program changed the open file `rel` (they are not what was last read or written here), else `None`. A file that is gone is not a change: a save writes it again."""
        model = self.models.get(rel)
        if model is None or model.path is None:
            return None
        try:
            raw = model.path.read_bytes()
        except OSError:
            return None
        return raw if raw != model.disk_bytes else None

    def reload(self, rel: str) -> DocumentModel:
        """Take the file's bytes from disk as the new state of its model (the person chose to reload). The history starts over."""
        model = self.models[rel]
        assert model.path is not None
        model.adopt_disk(model.path.read_bytes())
        return model

    def keep(self, rel: str) -> None:
        """The person chose to keep their version over what is on disk now: that content is the expected one, so it is not asked about again, and the next save replaces it."""
        model = self.models.get(rel)
        if model is not None and model.path is not None:
            with contextlib.suppress(OSError):
                model.keep_over(model.path.read_bytes())

    def save(self, rel: str | None = None) -> Path:
        """Write a file: the current one unless `rel` is given. The old content is kept aside the first time; the write is atomic. Raises `SaveError` (the old file is untouched), `ChangedOnDisk`
        (a `SaveError`) when another program changed the file since this one read or wrote it: that is never overwritten silently."""
        rel = rel or self.current
        model = self.models.get(rel) if rel else None
        if model is None or model.path is None:
            raise SaveError("There is no open file to save.")
        if self.changed_on_disk(rel) is not None:  # type: ignore[arg-type]
            raise ChangedOnDisk(rel)  # type: ignore[arg-type]
        self.backups.before_save(model.path, rel or model.path.name)
        write_atomic(model.path, model.data)
        model.mark_saved()
        return model.path

    def save_all(self) -> list[Path]:
        return [self.save(rel) for rel, model in self.models.items() if model.dirty]

    def dirty(self) -> list[str]:
        return [rel for rel, model in self.models.items() if model.dirty]

    def on_disk(self, rel: str) -> str:
        """The file's text as it is on disk now."""
        return read_text(self.file(rel).path)
