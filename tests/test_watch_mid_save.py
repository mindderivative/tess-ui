"""#39: a watcher doesn't read a file in the middle of a save. A save
empties a file, then writes it, and macOS can report both as one event
while the file is still empty; the watchers read at once, so a reload
read an empty file ("'NoneType' object has no attribute 'get'") and
missed the edit (CI, macOS). Both watchers now let a change settle
(`_settled`) before reading. Here the one event is made on any platform:
`watchfiles` is faked to report the save while the file is empty, and the
content lands just after.
"""

import queue
import threading
import time
from pathlib import Path

from tess_ui import App
from tess_ui.spec import watch
from tess_ui.spec.watch import ComposedWatcher, FileWatcher, _settled, _stamp


class FakeHandle:
    def __init__(self):
        self.queued = queue.Queue()

    def call_soon(self, fn):
        self.queued.put(fn)


def _rect(width: int) -> str:
    return f"---\nTDL: 0.2\nName: Home\n---\nRect {{ Style {{ Width: {width}, Height: 10, Background: \"#000000\" }} }}\n"


def _opened(tmp_path: Path):
    """The app's own way to watch a view: `Home_View.tdl` opened with `open_view`, and the watcher the app makes for it."""
    (tmp_path / "Views").mkdir()
    view_file = tmp_path / "Views" / "Home_View.tdl"
    view_file.write_text(_rect(10), encoding="utf-8")
    app = App(root=tmp_path)
    view = app.open_view("Home")
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    return view_file, view, watcher


def _one_event_mid_save(monkeypatch, path: Path, content: str, delay: float = 0.12) -> None:
    """`watchfiles.watch`, faked: it empties `path`, reports that once,
    and the content lands `delay` later with no event of its own."""
    def fake_watch(*dirs, watch_filter, stop_event, recursive):
        path.write_text("", encoding="utf-8")
        threading.Timer(delay, lambda: path.write_text(content, encoding="utf-8")).start()
        yield {(watch.watchfiles.Change.modified, str(path))}
        stop_event.wait()

    monkeypatch.setattr(watch.watchfiles, "watch", fake_watch)


def test_a_view_reload_waits_for_the_save_to_finish(tmp_path, monkeypatch, logs):
    view_file, view, watcher = _opened(tmp_path)
    _one_event_mid_save(monkeypatch, view_file, _rect(42))
    handle = FakeHandle()
    watcher.start(handle)
    try:
        handle.queued.get(timeout=5)()
        view.window.advance(16)
        assert view.node("root").get("width") == 42.0
        assert logs.messages("ERROR") == []  # no reload of the empty file
    finally:
        watcher.stop()


def test_a_file_reload_waits_for_the_save_to_finish(tmp_path, monkeypatch, logs):
    theme = tmp_path / "Brand_Theme.tdl"
    theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: false }\n", encoding="utf-8")
    _one_event_mid_save(monkeypatch, theme, "---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: true }\n")
    read = []
    watcher = FileWatcher([theme], lambda: read.append(theme.read_text(encoding="utf-8")), lambda _: None)
    handle = FakeHandle()
    watcher.start(handle)
    try:
        handle.queued.get(timeout=5)
        assert read == ["---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: true }\n"]
    finally:
        watcher.stop()


def test_settling(tmp_path):
    steady = tmp_path / "steady.tdl"
    steady.write_text("a: 1\n", encoding="utf-8")
    started = time.monotonic()
    assert _settled([steady]) == {steady: _stamp(steady)}
    assert time.monotonic() - started < 0.5  # a finished save costs one check

    growing = tmp_path / "growing.tdl"
    growing.write_bytes(b"")
    threading.Timer(0.15, lambda: growing.write_bytes(b"b: 2\n")).start()  # bytes: Windows writes \r\n as text
    assert _settled([growing])[growing][1] == len(b"b: 2\n")  # waited out the empty file

    empty = tmp_path / "empty.tdl"
    empty.write_text("", encoding="utf-8")
    gone = tmp_path / "gone.tdl"
    started = time.monotonic()
    assert _settled([empty, gone], limit=0.2) == {empty: _stamp(empty), gone: None}
    assert 0.2 <= time.monotonic() - started < 1.0  # really empty: read as it is, after the limit


def test_a_save_that_lands_while_a_view_is_read_is_read_again(tmp_path, monkeypatch, logs):
    """CI, macOS: a save can land after the change settles but while the
    file is read (a test re-saving until a reload was queued did it). The
    read that failed isn't logged; the file is read again."""
    view_file, view, watcher = _opened(tmp_path)
    handle = FakeHandle()
    real_rebuild, reads = watcher._rebuild, []

    def rebuild_as_a_save_lands():
        reads.append(True)
        if len(reads) == 1:  # the save lands during the first read, which saw it half-written
            time.sleep(0.01)
            view_file.write_text(_rect(42), encoding="utf-8")
            raise ValueError("'NoneType' object has no attribute 'get'")
        return real_rebuild()

    monkeypatch.setattr(watcher, "_rebuild", rebuild_as_a_save_lands)

    def fake_watch(*dirs, watch_filter, stop_event, recursive):
        view_file.write_text(_rect(20), encoding="utf-8")
        yield {(watch.watchfiles.Change.modified, str(view_file))}
        stop_event.wait()

    monkeypatch.setattr(watch.watchfiles, "watch", fake_watch)
    watcher.start(handle)
    try:
        handle.queued.get(timeout=5)()
        view.window.advance(16)
        assert view.node("root").get("width") == 42.0 and len(reads) == 2
        assert logs.messages("ERROR") == []
    finally:
        watcher.stop()


def test_a_save_that_lands_while_a_file_is_read_is_read_again(tmp_path, monkeypatch, logs):
    theme = tmp_path / "Brand_Theme.tdl"
    theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: false }\n", encoding="utf-8")
    reads = []

    def rebuild():
        reads.append(theme.read_text(encoding="utf-8"))
        if len(reads) == 1:
            time.sleep(0.01)
            theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: true }\n", encoding="utf-8")
            raise ValueError("half a file")
        return reads[-1]

    def fake_watch(*dirs, watch_filter, stop_event, recursive):
        theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Seed: \"#112233\" }\n", encoding="utf-8")
        yield {(watch.watchfiles.Change.modified, str(theme))}
        stop_event.wait()

    monkeypatch.setattr(watch.watchfiles, "watch", fake_watch)
    applied = []
    watcher, handle = FileWatcher([theme], rebuild, applied.append), FakeHandle()
    watcher.start(handle)
    try:
        handle.queued.get(timeout=5)()
        assert applied == ["---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: true }\n"] and logs.messages("ERROR") == []
    finally:
        watcher.stop()


def test_a_read_that_finished_before_a_save_landed_is_not_queued(tmp_path, monkeypatch):
    """A read can succeed and still be stale: the save landed just after
    it. What's queued is the saved file, not what was read before it."""
    view_file, view, watcher = _opened(tmp_path)
    handle = FakeHandle()
    real_rebuild, reads = watcher._rebuild, []

    def rebuild_then_a_save_lands():
        result = real_rebuild()
        reads.append(True)
        if len(reads) == 1:
            time.sleep(0.01)
            view_file.write_text(_rect(42), encoding="utf-8")
        return result

    monkeypatch.setattr(watcher, "_rebuild", rebuild_then_a_save_lands)

    def fake_watch(*dirs, watch_filter, stop_event, recursive):
        view_file.write_text(_rect(20), encoding="utf-8")
        yield {(watch.watchfiles.Change.modified, str(view_file))}
        stop_event.wait()

    monkeypatch.setattr(watch.watchfiles, "watch", fake_watch)
    watcher.start(handle)
    try:
        handle.queued.get(timeout=5)()
        view.window.advance(16)
        assert view.node("root").get("width") == 42.0 and handle.queued.empty()
    finally:
        watcher.stop()


def test_a_file_read_that_finished_before_a_save_landed_is_not_queued(tmp_path, monkeypatch):
    theme = tmp_path / "Brand_Theme.tdl"
    theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: false }\n", encoding="utf-8")
    reads = []

    def rebuild():
        reads.append(theme.read_text(encoding="utf-8"))
        if len(reads) == 1:
            time.sleep(0.01)
            theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: true }\n", encoding="utf-8")
        return reads[-1]

    def fake_watch(*dirs, watch_filter, stop_event, recursive):
        theme.write_text("---\nTDL: 0.2\nName: Brand\n---\nTheme { Seed: \"#112233\" }\n", encoding="utf-8")
        yield {(watch.watchfiles.Change.modified, str(theme))}
        stop_event.wait()

    monkeypatch.setattr(watch.watchfiles, "watch", fake_watch)
    applied = []
    watcher, handle = FileWatcher([theme], rebuild, applied.append), FakeHandle()
    watcher.start(handle)
    try:
        handle.queued.get(timeout=5)()
        assert applied == ["---\nTDL: 0.2\nName: Brand\n---\nTheme { Dark: true }\n"] and handle.queued.empty()
    finally:
        watcher.stop()
