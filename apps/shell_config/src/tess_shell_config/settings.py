"""The application's own settings, in its own state folder (never in the shell's configuration folder): today only "Apply as I edit".

One small JSON file, written through the same temporary-file-and-rename the `.tdl` files use. A file that is missing or cannot be read gives the defaults; a failed write is reported to the caller,
and the setting stays as it was chosen for this session.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tess_shell_config.files import SaveError, write_atomic

__all__ = ["Settings"]

FILE_NAME = "settings.json"


class Settings:
    """`folder` is the application's state folder."""

    def __init__(self, folder: str | Path) -> None:
        self.path = Path(folder) / FILE_NAME
        self.values: dict[str, Any] = {"apply_as_i_edit": False}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if isinstance(data, dict) and isinstance(data.get("apply_as_i_edit"), bool):
            self.values["apply_as_i_edit"] = data["apply_as_i_edit"]

    @property
    def apply_as_i_edit(self) -> bool:
        return bool(self.values["apply_as_i_edit"])

    def set_apply_as_i_edit(self, on: bool) -> None:
        """Remember the choice. Raises `SaveError` when the state folder cannot be written."""
        self.values["apply_as_i_edit"] = bool(on)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise SaveError(f"Cannot keep the setting in {self.path.parent}: {error.strerror or error}.") from error
        write_atomic(self.path, (json.dumps(self.values, indent=2) + "\n").encode("utf-8"))
