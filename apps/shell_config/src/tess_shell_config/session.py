"""The session: the configuration folder, the schema, the shell command, and the files open in it. Everything but the window, so tests drive it directly.

Open files are kept by their path from the folder (`rel`); each is a `DocumentModel` that stays in memory, with its history, while the session lasts, so moving to
another file loses nothing. A save writes the file through a temporary file in its own folder and renames it; the first save of a file keeps its old content in the
application's own state folder.
"""

from __future__ import annotations

from pathlib import Path

from tess_shell_config.files import Backups, SaveError, read_text, state_dir as default_state_dir, write_atomic
from tess_shell_config.folder import ConfigFile, scan
from tess_shell_config.model import DocumentModel
from tess_shell_config.schema import Schema
from tess_shell_config.shell import ShellCommand

__all__ = ["ConfigSession"]


class ConfigSession:
    """`folder` is the configuration folder, `schema` what the shell exported, `shell` the command layer (or `None` in a test that needs no command)."""

    def __init__(self, folder: str | Path, schema: Schema | None = None, shell: ShellCommand | None = None, state_dir: str | Path | None = None) -> None:
        self.folder = Path(folder)
        self.schema = schema
        self.shell = shell
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
        self.backups = Backups(self.state_dir)
        self.files: list[ConfigFile] = []
        self.models: dict[str, DocumentModel] = {}
        self.current: str | None = None
        self.refresh()

    def refresh(self) -> list[ConfigFile]:
        """Read the folder again: the files by type."""
        self.files = scan(self.folder)
        return self.files

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

    def save(self, rel: str | None = None) -> Path:
        """Write a file: the current one unless `rel` is given. The old content is kept aside the first time; the write is atomic. Raises `SaveError` (the old file is untouched)."""
        rel = rel or self.current
        model = self.models.get(rel) if rel else None
        if model is None or model.path is None:
            raise SaveError("There is no open file to save.")
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
