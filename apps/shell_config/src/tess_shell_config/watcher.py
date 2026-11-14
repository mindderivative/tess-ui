"""The file watch: the configuration folder is watched on a worker thread (`watchfiles`, the package the toolkit already depends on) and a change of a `.tdl` file is posted to the event loop.

The worker only reads: for each changed file it reads the bytes (or finds the file gone) and posts `on_change({relative path: bytes or None})` through `post`, a function that runs a callable on the
loop thread (`app.thread_handle().call_soon`). Whether a change is the application's own save is decided there, by comparing the bytes with what the model last read or wrote
(`ConfigSession.changed_on_disk`), so a save of this application never asks anything and no timing guess is involved. The temporary file a save writes ends in `.tmp` and is not a `.tdl` file.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import watchfiles

__all__ = ["FileWatch"]

#: Milliseconds the watcher collects changes for before it reports them: one save is one report.
DEBOUNCE_MS = 120


def _is_tdl(change: Any, path: str) -> bool:
    return path.endswith(".tdl")


class FileWatch:
    """Watches `folder` (recursively) from `start()` to `stop()`. `on_change` and `on_error` run on the loop thread, through `post`."""

    def __init__(self, folder: str | Path, post: Callable[[Callable[[], None]], Any], on_change: Callable[[Mapping[str, bytes | None]], None], on_error: Callable[[str], None]) -> None:
        self.folder = Path(folder)
        self._post = post
        self._on_change = on_change
        self._on_error = on_error
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._work, name="tess-shell-config-watch", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 3.0) -> None:
        """Ask the worker to end and wait for it (the watch checks every 50 ms, so this is quick)."""
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout)

    def _work(self) -> None:
        try:
            for changes in watchfiles.watch(self.folder, watch_filter=_is_tdl, debounce=DEBOUNCE_MS, step=50, stop_event=self._stop, rust_timeout=200, yield_on_timeout=False, raise_interrupt=False):
                found: dict[str, bytes | None] = {}
                for _, name in changes:
                    path = Path(name)
                    try:
                        rel = path.relative_to(self.folder).as_posix()
                    except ValueError:
                        try:
                            rel = path.resolve().relative_to(self.folder.resolve()).as_posix()
                        except (ValueError, OSError):
                            continue
                    try:
                        found[rel] = path.read_bytes()
                    except OSError:
                        found[rel] = None  # gone
                if found:
                    self._post(lambda found=found: self._on_change(found))  # type: ignore[misc]
        except Exception as error:  # the watch could not start or died (no inotify watches left, the folder is gone): the window is told once and goes on without it
            if not self._stop.is_set():
                message = f"The file watch stopped: {error}"
                self._post(lambda: self._on_error(message))
