"""The preview model of the configuration folder as the editor has it: `tess_shell.preview.preview(folder, overrides=...)`, with the text of every file that has unsaved changes standing in
for the file on disk, so the View follows what is being typed, not only what was saved. The shell's preview module is imported when it is first needed: an older `tesserae-shell` without
it says so (`PreviewMissing`) instead of stopping the window."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["OUTPUT", "PreviewMissing", "build_preview", "overrides_of"]

#: The screen the picture shows: a virtual output of the common size (the shell's own monitors are not asked, and nothing is drawn on a real one).
OUTPUT = ("Preview", 1920, 1080, 1.0)


class PreviewMissing(RuntimeError):
    """This `tesserae-shell` has no preview model."""


def overrides_of(folder: Path, models: dict[str, Any]) -> dict[Path, str]:
    """The text of each open file that has unsaved changes, by its path: what the shell is to read in place of the file on disk."""
    return {Path(folder) / rel: model.text for rel, model in models.items() if model.dirty}


def build_preview(folder: Path, overrides: dict[Path, str]) -> dict[str, Any]:
    """The preview model (`to_dict()` of the shell's, preview_version 1) for `folder` with `overrides`. Runs on a worker thread."""
    try:
        from tess_shell.preview import VirtualOutput, preview  # type: ignore[import-not-found]  # a tesserae-shell with the preview model (not every one has it)
    except ImportError as error:
        raise PreviewMissing("The View needs a newer tesserae-shell (one with the preview model).") from error
    name, width, height, scale = OUTPUT
    return preview(Path(folder), overrides=overrides, outputs=[VirtualOutput(name, width, height, scale)]).to_dict()  # type: ignore[no-any-return]
