"""`ComposedWatcher.start(handle)` (a `ViewWatcher`): event-driven hot reload on a background
thread (`watchfiles`), handing each reload to the event loop through
`tess_re`'s thread-safe `LoopHandle.call_soon` (tess_re M87).

`FakeHandle` stands in for the `LoopHandle`: it records what the watcher
queues, and the test runs each callable on its own (main) thread -- the
thread that owns the view, as `tess_re`'s loop would. The watcher thread
must never touch the view itself; if it did, `tess_re` would raise a
`PanicException` there.

A background watcher can miss an edit made before it has started
listening, so `_edit_until_queued` re-applies the same final edit until
the watcher reports it. Retrying is harmless since every attempt writes
the same content.
"""

import queue
import threading
import time
from pathlib import Path

import pytest

from tess_ui import App
from tess_ui.spec.watch import ComposedWatcher


class FakeHandle:
    def __init__(self):
        self.queued: "queue.Queue" = queue.Queue()
        self.threads: list[str] = []

    def call_soon(self, fn):
        self.threads.append(threading.current_thread().name)
        self.queued.put(fn)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _text_view(content: str, extra: str = "") -> str:
    """The view `Home_View.tdl`: a Container with the label, then `extra` (the TDL of more children, indented four spaces)."""
    return (
        "---\nTDL: 0.2\nName: Home\n---\nContainer {\n  Children {\n"
        f"    Text {{ Name: label, Text: {content}, Typography_Role: body_large, Style {{ Width: 100, Height: 20, Foreground: on_surface }} }}\n"
        + extra + "  }\n}\n"
    )


def _edit_until_queued(handle: FakeHandle, path: Path, text: str, attempts: int = 40):
    for _ in range(attempts):
        path.write_text(text)
        try:
            return handle.queued.get(timeout=0.25)
        except queue.Empty:
            continue
    raise AssertionError(f"the watcher never queued a reload for {path}")


@pytest.fixture
def started(tmp_path: Path):
    """An opened view with a started watcher; stopped afterwards."""
    watchers = []

    def start(text: str):
        view_path = _write(tmp_path / "Views" / "Home_View.tdl", text)
        app = App(root=tmp_path, search=[tmp_path / "more"])  # `more/` is a folder views are read from
        view = app.open_view("Home")
        watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
        handle = FakeHandle()
        watcher.start(handle)
        watchers.append(watcher)
        return view_path, view, watcher, handle

    yield start
    for watcher in watchers:
        watcher.stop()


def test_an_edit_is_queued_from_the_watcher_thread_and_applies_on_this_one(started):
    view_path, view, watcher, handle = started(_text_view("Hello"))
    assert watcher.running

    reload = _edit_until_queued(handle, view_path, _text_view("Goodbye"))
    assert view.node("root.label").get("text") == "Hello"  # nothing applied until the loop runs it
    reload()

    view.window.advance(16)
    assert view.node("root.label").get("text") == "Goodbye"
    assert handle.threads and all(name.startswith("tesserae-watch:") for name in handle.threads)


def test_an_edit_of_a_view_it_calls_is_picked_up(started, tmp_path: Path):
    part = _write(tmp_path / "Views" / "Footer_View.tdl", _text_view("v1").replace("Name: Home", "Name: Footer"))
    _, view, _, handle = started("---\nTDL: 0.2\nName: Home\n---\nContainer {\n  Children {\n    Footer { Name: foot }\n  }\n}\n")

    _edit_until_queued(handle, part, _text_view("v2").replace("Name: Home", "Name: Footer"))()
    view.window.advance(16)

    assert view.node("root.foot.label").get("text") == "v2"


def test_a_broken_edit_is_logged_and_the_watcher_carries_on(started, logs):
    view_path, view, watcher, handle = started(_text_view("Hello"))

    message = logs.edit_until(
        view_path,
        _text_view("Hello", "    NoSuchThing { Name: x }\n"),
        "ERROR",
        "NoSuchThing",
    )
    assert message.startswith(f"hot reload of {view_path} failed: ")
    logs.wait_for("DEBUG", "traceback")  # logged just after the ERROR, on the watcher thread
    assert handle.queued.empty()  # nothing for the loop to run
    assert watcher.running
    assert view.node("root.label").get("text") == "Hello"

    _edit_until_queued(handle, view_path, _text_view("Fixed"))()
    assert view.node("root.label").get("text") == "Fixed"
    assert f"reloaded {view_path}" in logs.messages("INFO")


def test_a_reload_tre_rejects_is_logged_on_the_loop(started, logs):
    view_path, view, _, handle = started(_text_view("Hello"))

    rejected = _edit_until_queued(handle, view_path, _text_view("Hello").replace("Typography_Role: body_large, ", ""))
    rejected()  # logs instead of raising, so tess_re's loop carries on

    message = logs.wait_for("ERROR", "typography_role")
    assert message.startswith(f"hot reload of {view_path} failed: ") and "typography_role" in message
    assert view.node("root.label").get("text") == "Hello"


def test_a_new_dependency_in_a_new_directory_is_watched_after_reload(started, tmp_path: Path):
    rect = "---\nTDL: 0.2\nName: Extra\n---\nRect {{ Style {{ Width: {n}, Height: {n}, Background: \"#112233\" }} }}\n"
    extra = _write(tmp_path / "more" / "Extra_View.tdl", rect.format(n=5))
    view_path, view, watcher, handle = started(_text_view("Hello"))

    _edit_until_queued(handle, view_path, _text_view("Hello", "    Extra { Name: extra }\n"))()
    assert extra.resolve() in watcher.files
    assert view.node("root.extra") is not None

    _edit_until_queued(handle, extra, rect.format(n=9))()


def test_unrelated_files_in_a_watched_directory_are_ignored(started, tmp_path: Path):
    _, _, _, handle = started(_text_view("Hello"))
    time.sleep(0.3)  # let the watcher start listening
    for i in range(3):
        (tmp_path / "notes.txt").write_text(f"not a dependency {i}")
    with pytest.raises(queue.Empty):
        handle.queued.get(timeout=0.5)


def test_stop_is_prompt_and_start_poll_are_guarded(started):
    _, _, watcher, handle = started(_text_view("Hello"))

    with pytest.raises(RuntimeError, match="called twice"):
        watcher.start(handle)
    with pytest.raises(RuntimeError, match="while start"):
        watcher.poll()

    began = time.monotonic()
    watcher.stop()
    assert time.monotonic() - began < 2.0
    assert not watcher.running
    assert watcher.poll() is False  # poll() is usable again once stopped
