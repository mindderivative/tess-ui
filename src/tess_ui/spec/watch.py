"""Tesserae-owned hot reload for the views, themes and stylesheets of a running app.

A view depends on more than its own file: every view it calls, every stylesheet of the views in use and every image it decodes. A change to any of
them re-reads the whole set and recomposes the view (`ComposedWatcher`), which keeps the nodes that keep their id, focus and in-flight animations. The set of
watched files is recomputed on every reload, so a view the file now calls is watched from then on.

Two ways to drive it:

- **`start(handle)`** -- a background thread watches for file-change events with `watchfiles`, reads the files there (all file I/O stays off the UI
  thread), and hands only the view's recompose to the event loop through `tess_re`'s thread-safe `LoopHandle.call_soon`.
  `App.run(hot_reload=True)` does this for every view.
- **`poll()`** -- no thread: checks each file's modification time and size. For a loop the app controls itself.

`tess_re`'s `View` is single-threaded: only the `LoopHandle` crosses threads, and the watcher thread never touches the view.

Reloads are logged with loguru (`tess_ui.log`): each applied reload at INFO. A reload that fails in the background (a syntax error, a bad view, a
spec `tess_re` rejects) is logged at ERROR, naming the file, with its traceback at DEBUG, and the view stays as it was. `poll()` raises instead,
since the app's own loop called it.

M31: `FileWatcher` is the same background-thread pattern for a fixed set of files with no dependencies of their own -- `App.run(hot_reload=True)`
uses it for theme and stylesheet files.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Tuple

import watchfiles
from loguru import logger

from tess_ui.spec.images import Frame

__all__ = ["ComposedWatcher", "FileWatcher"]

#: `(st_mtime_ns, st_size)`, or `None` for a file that doesn't exist.
_Stamp = Optional[Tuple[int, int]]


def _stamp(path: Path) -> _Stamp:
    try:
        stat = path.stat()
    except OSError:
        return None
    return (stat.st_mtime_ns, stat.st_size)


def _settled(paths: Iterable[Path], *, interval: float = 0.05, limit: float = 1.0) -> dict[Path, _Stamp]:
    """The files' stamps once a change has settled: an editor's save
    empties a file, then writes it, and macOS can report both as one
    event while the file is still empty (#39). So re-stat every `interval`
    until two readings agree and no watched file that exists is empty,
    giving up after `limit` (a file really left empty is then read as it
    is). A save that finished before the event costs one `interval`."""
    paths = list(paths)
    current = {p: _stamp(p) for p in paths}
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        time.sleep(interval)
        again = {p: _stamp(p) for p in paths}
        if again == current and not any(stamp is not None and stamp[1] == 0 for stamp in again.values()):
            return again
        current = again
    return current


#: How often a change is read again when a save lands while it's read.
_REREADS = 5


def _moved(stamps: dict[Path, _Stamp]) -> bool:
    """Whether any of these files changed since `stamps` were taken: a save
    that landed while they were read (#39)."""
    return any(_stamp(p) != stamp for p, stamp in stamps.items())


def _log_failure(what: str, exc: BaseException) -> None:
    """One ERROR line naming `what` and the error, with the traceback at
    DEBUG -- a typo shouldn't print a stack trace by default."""
    logger.error("hot reload of {} failed: {}", what, exc)
    logger.opt(exception=exc).debug("hot reload of {} failed, traceback:", what)


def _guarded(what: str, fn: Callable[[], None]) -> Callable[[], None]:
    """`fn`, for the event loop to run: a failure is logged, not raised,
    so the loop and the watcher carry on and the view stays as it was."""

    def run() -> None:
        try:
            fn()
        except Exception as exc:
            _log_failure(what, exc)

    return run


class _ViewWatcher:
    """Watches every file `view` was built from and reloads it on change. A subclass says how to read them (`_rebuild`) and how to apply the result (`_apply`).

    Inside `App.run()`, start it with the app's thread handle (or just use `App.run(hot_reload=True)`); in a loop the app controls itself, call `poll()`
    regularly.
    """

    def __init__(self, view: Any, path: str | Path) -> None:
        self._view = view
        self._path = Path(path)
        _, _, deps = self._rebuild()
        self._stamps: dict[Path, _Stamp] = {p: _stamp(p) for p in deps}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def files(self) -> frozenset[Path]:
        """Every file currently being watched, resolved."""
        return frozenset(self._stamps)

    @property
    def running(self) -> bool:
        """Whether `start()`'s background thread is watching."""
        return self._thread is not None and self._thread.is_alive()

    def _rebuild(self) -> tuple[Any, list[Frame], set[Path]]:
        """All the file work -- safe on any thread: `(what to apply, images, every file it was built from)`."""
        raise NotImplementedError

    def _apply(self, spec: Any, frames: list[Frame]) -> None:
        """The `tess_re` part -- only on the thread that owns the view."""
        raise NotImplementedError

    # -- no thread -------------------------------------------------

    def poll(self) -> bool:
        """Reloads the view if any watched file changed since the last
        poll. Returns `True` if it reloaded, `False` if nothing changed.

        A reload that fails (a syntax error, a bad view, a spec `tess_re`
        rejects) raises, naming the file, and leaves the view as it was.
        It raises once per change -- polling again without a further
        edit returns `False` rather than raising the same error again.
        """
        if self.running:
            raise RuntimeError("poll() while start()'s watcher thread is running")
        current = {p: _stamp(p) for p in self._stamps}
        if current == self._stamps:
            return False
        # Record what was seen *before* reading, so a write that lands
        # mid-reload is picked up by the next poll instead of lost.
        self._stamps = current
        spec, frames, deps = self._rebuild()
        self._stamps = {p: current[p] if p in current else _stamp(p) for p in deps}
        self._apply(spec, frames)
        return True

    # -- background thread (watchfiles) -----------------------------

    def start(self, handle: Any) -> None:
        """Starts watching on a background thread. `handle` is
        `tess_re.App.thread_handle()`'s `LoopHandle`; each reload is queued
        on it with `call_soon`, so it runs on the event-loop thread.

        A reload that fails is logged at ERROR, naming the file, and the
        view stays as it was; the loop and the watcher carry on.
        """
        if self._thread is not None:
            raise RuntimeError("start() called twice without stop()")
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._watch, args=(handle,), name=f"tesserae-watch:{self._path.name}", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stops the background thread and waits for it to finish."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def _reload(self, handle: Any) -> set[Path] | None:
        """One change: reads the files once they've settled and queues the
        new spec; returns what it was built from (`None` if nothing was
        queued). A save that lands while they're read is read again (#39)."""
        for _attempt in range(_REREADS):
            current = _settled(self._stamps)  # not mid-save (#39)
            if current == self._stamps:
                return None  # nothing changed: macOS reports writes from before the watch began (M76)
            self._stamps = current  # before reading, as `poll` does, so a write mid-reload isn't lost
            try:
                spec, frames, deps = self._rebuild()
            except Exception as exc:
                if _moved(current):
                    continue  # read mid-save: read it again
                _log_failure(str(self._path), exc)
                return None
            if _moved(current):
                continue
            self._stamps = {p: current[p] if p in current else _stamp(p) for p in deps}
            handle.call_soon(_guarded(str(self._path), lambda spec=spec, frames=frames: self._apply(spec, frames)))
            return deps
        return None

    def _watch(self, handle: Any) -> None:
        try:
            while not self._stop.is_set():
                dirs = sorted({p.parent for p in self._stamps if p.parent.is_dir()})
                if not dirs:
                    self._stop.wait(0.5)
                    continue
                for _changes in watchfiles.watch(
                    *dirs,
                    watch_filter=lambda _change, changed: Path(changed).resolve() in self._stamps,
                    stop_event=self._stop,
                    recursive=False,
                ):
                    deps = self._reload(handle)
                    if deps is not None and sorted({p.parent for p in deps if p.parent.is_dir()}) != dirs:
                        break  # a dependency moved to a new directory: re-watch
        except Exception as exc:  # the watcher itself failed; report it, don't die silently
            logger.opt(exception=exc).error("the hot-reload watcher for {} stopped", self._path)


class ComposedWatcher(_ViewWatcher):
    """Watches a view opened with `app.open_view` -- the file, every view it calls, and its pictures -- and recomposes it on change. The ViewModel,
    the nodes that keep their id and the `state:` of those nodes stay. `parse(path)` gives the parsed
    doc and the `ViewLibrary` that read the files, and `rules(library)` the rules to compose under (both from `App`).

    A change that fails to parse or compose is logged naming the file, and the view stays as it was. The files watched are re-read after each
    reload, so a view the file now calls is watched too."""

    def __init__(self, view: Any, path: str | Path, parse: Callable[[Path], tuple[Any, Any]], rules: Callable[[Any, Any], Any], *,
                 shipped: Optional[Path] = None, sheet_files: Optional[Callable[[Any, set[str]], list[Path]]] = None) -> None:
        self._parse, self._rules = parse, rules
        self._sheet_files = sheet_files or (lambda library, used: library.sheets_of(used)[1])
        if shipped is None:
            from tess_ui.shipped import SHIPPED as shipped  # Tesserae's own views are not the app's to edit
        self._shipped = shipped.resolve()
        super().__init__(view, path)

    def _rebuild(self) -> tuple[Any, list[Frame], set[Path]]:
        """All the file work, safe off the loop: parses the view and every view it calls (so a mistake in any of them is found here), and names the
        files."""
        doc, library = self._parse(self._path)
        used = library.used(doc)  # parses every view it calls, so a mistake in one is found here
        files = {p for p in library.read if self._shipped not in p.parents} | {self._path.resolve()}
        files |= set(self._view.image_files)
        files |= set(self._sheet_files(library, used))  # the project's stylesheets of the views in use: an edit to one reloads the view
        return (doc, library), [], files

    def _apply(self, spec: Any, frames: list[Frame]) -> None:
        if self._view.handle.closed:
            return
        doc, library = spec
        self._view.recompose(doc, library.doc, self._rules(library, doc))
        logger.info("reloaded {}", self._path)


class FileWatcher:
    """Watches a fixed set of files on a background thread, the way
    `ComposedWatcher.start` does. On a change, `rebuild()` runs on the
    watcher thread -- the file work -- and `apply(result)` is queued on
    `handle` with `call_soon`, so it runs on the event-loop thread. If
    either raises, the error is logged at ERROR, naming the file, and
    watching carries on.
    """

    def __init__(
        self,
        files: list[str | Path],
        rebuild: Callable[[], Any],
        apply: Callable[[Any], None],
        *,
        name: str = "files",
    ) -> None:
        self._files = frozenset(Path(f).resolve() for f in files)
        self._stamps: dict[Path, _Stamp] = {f: _stamp(f) for f in self._files}  # what was last read (M76)
        self._rebuild = rebuild
        self._apply = apply
        self._name = name
        #: How a log message names what's watched.
        self._what = ", ".join(sorted(str(f) for f in self._files))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def files(self) -> frozenset[Path]:
        """Every file being watched, resolved."""
        return self._files

    @property
    def running(self) -> bool:
        """Whether the background thread is watching."""
        return self._thread is not None and self._thread.is_alive()

    def start(self, handle: Any) -> None:
        """Starts watching. `handle` is `tess_re.App.thread_handle()`'s
        `LoopHandle`."""
        if self._thread is not None:
            raise RuntimeError("FileWatcher.start() called twice without stop()")
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._watch, args=(handle,), name=f"tesserae-watch:{self._name}", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stops the background thread and waits for it to finish."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
            self._thread = None

    def _watch(self, handle: Any) -> None:
        try:
            dirs = sorted({p.parent for p in self._files if p.parent.is_dir()})
            if not dirs:
                return
            for _changes in watchfiles.watch(
                *dirs,
                watch_filter=lambda _change, changed: Path(changed).resolve() in self._files,
                stop_event=self._stop,
                recursive=False,
            ):
                for _attempt in range(_REREADS):
                    current = _settled(self._files)  # not mid-save (#39)
                    if current == self._stamps:
                        break  # nothing changed: macOS reports writes from before the watch began (M76)
                    self._stamps = current
                    try:
                        result = self._rebuild()
                    except Exception as exc:
                        if _moved(current):
                            continue  # read mid-save: read it again (#39)
                        _log_failure(self._what, exc)
                        break
                    if _moved(current):
                        continue
                    handle.call_soon(_guarded(self._what, lambda result=result: self._apply(result)))
                    break
        except Exception as exc:  # the watcher itself failed; report it, don't die silently
            logger.opt(exception=exc).error("the hot-reload watcher for {} stopped", self._what)
