"""M76: a watcher reloads only when a file really changed. On macOS,
FSEvents can report writes made just before a watch began, so a watcher
got an event for content it had already loaded and queued a needless
reload (three hot-reload tests failed there, on CI). Both watchers now
compare each file's stamp (mtime and size) with what they last read and
skip an event that changed nothing. Here the stale event is made on any
platform: the same content rewritten with its old mtime put back.
"""

import os
import queue
import time
from pathlib import Path

from tess_ui import App
from tess_ui.spec.watch import ComposedWatcher, FileWatcher


class FakeHandle:
    def __init__(self):
        self.queued = queue.Queue()

    def call_soon(self, fn):
        self.queued.put(fn)


def _rect(width: int) -> str:
    return f"---\nTDL: 0.2\nName: Home\n---\nRect {{ Style {{ Width: {width}, Height: 10, Background: \"#000000\" }} }}\n"


def _stale_event(path: Path) -> None:
    """An event for a file whose content and stamp didn't change."""
    stat = path.stat()
    path.write_bytes(path.read_bytes())
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))


def _settle(seconds=0.6):
    time.sleep(seconds)


def _real_edit_until_queued(handle, path, text, attempts=40):
    for _ in range(attempts):
        path.write_text(text, encoding="utf-8")
        try:
            return handle.queued.get(timeout=0.25)
        except queue.Empty:
            continue
    raise AssertionError(f"no reload queued for {path}")


def test_a_file_watcher_skips_an_event_that_changed_nothing(tmp_path):
    theme = tmp_path / "Brand_Theme.tdl"
    theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: false }\n", encoding="utf-8")
    rebuilt, handle = [], FakeHandle()
    watcher = FileWatcher([theme], lambda: rebuilt.append(theme.read_text(encoding="utf-8")), lambda _: None)
    watcher.start(handle)
    try:
        _settle()
        for _ in range(3):
            _stale_event(theme)
            _settle(0.3)
        assert rebuilt == [] and handle.queued.empty()
        _real_edit_until_queued(handle, theme, "---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: true }\n")
        assert rebuilt[-1].endswith("Theme { Dark: true }\n")
        _settle()
        while not handle.queued.empty():  # a real edit can make more than one event
            handle.queued.get()
        seen = len(rebuilt)
        for _ in range(3):  # and after it, what it read is the new baseline
            _stale_event(theme)
            _settle(0.3)
        assert len(rebuilt) == seen and handle.queued.empty()
    finally:
        watcher.stop()


def test_a_view_watcher_skips_an_event_that_changed_nothing(tmp_path):
    (tmp_path / "Views").mkdir()
    view_file = tmp_path / "Views" / "Home_View.tdl"
    view_file.write_text(_rect(10), encoding="utf-8")
    app = App(root=tmp_path)
    view = app.open_view("Home")
    watcher, handle = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0]), FakeHandle()
    watcher.start(handle)
    try:
        _settle()
        for _ in range(3):
            _stale_event(view_file)
            _settle(0.3)
        assert handle.queued.empty()
        apply = _real_edit_until_queued(handle, view_file, _rect(42))
        apply()
        view.window.advance(16)
        assert view.node("root").get("width") == 42.0
    finally:
        watcher.stop()
