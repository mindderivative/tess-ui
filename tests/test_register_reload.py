"""M48 Phase 2: `App.run(hot_reload=True)` watches every screen opened from a file -- `open_view()`ed, taking the file from the view itself (Q1);
a screen built from a spec and `register()`ed is named in the log instead (Q2).

As in `test_theme_reload.py`, a `FakeHandle` stands in for `tess_re`'s loop: the watcher queues each reload, and the test runs it on this thread.
"""

import queue
from pathlib import Path

import pytest

import tess_ui
from tess_ui import App, Signal, ViewModel
from tess_ui.spec.watch import ComposedWatcher

VIEW = """---
TDL: 0.2
Name: NAME
---
Container {
  Name: NAME
  Children {
    Text { Name: title, Text: <| title |>, Font_Family: Roboto, Font_Size: 14, Style { Foreground: "#000000", Width: WIDTH, Height: 20 } }
  }
}
"""


class FakeHandle:
    def __init__(self):
        self.queued: "queue.Queue" = queue.Queue()

    def call_soon(self, fn):
        self.queued.put(fn)


class Home(ViewModel):
    views = "home"

    def __init__(self):
        super().__init__()
        self.title = Signal("Home")


class Loaded(ViewModel):
    views = "loaded"

    def __init__(self):
        super().__init__()
        self.title = Signal("x")


def _write(path: Path, width: int = 100) -> Path:
    path.write_text(VIEW.replace("NAME", path.name.removesuffix("_View.tdl").lower()).replace("WIDTH", str(width)))
    return path


def _edit_until_queued(handle: FakeHandle, path: Path, width: int, attempts: int = 40):
    for _ in range(attempts):
        _write(path, width)
        try:
            return handle.queued.get(timeout=0.25)
        except queue.Empty:
            continue
    raise AssertionError(f"the watcher never queued a reload for {path}")


@pytest.fixture
def watching():
    started = []

    def start(app: App):
        handle = FakeHandle()
        started.extend(app._start_watchers(handle))
        return handle

    yield start
    for watcher in started:
        watcher.stop()


def _project(tmp_path, *names):
    (tmp_path / "Views").mkdir()
    return [_write(tmp_path / "Views" / f"{name}_View.tdl") for name in names]


def test_a_screen_reloads_in_place_keeping_its_viewmodel(tmp_path, watching):
    (path,) = _project(tmp_path, "Home")
    app = App(root=tmp_path)
    app.bind(Home)
    view = app.open_view("Home")
    vm = app.bindings.viewmodel_for("home")
    app.show("home")
    node = view.node("root.title")
    vm.title.set("Inbox")
    handle = watching(app)
    reload = _edit_until_queued(handle, path, width=240)
    assert node.get("width") == 100.0  # nothing applied until the loop runs it
    reload()
    assert view.node("root.title") == node and node.get("width") == 240.0
    assert node.get("text") == "Inbox"  # the binding kept its live value
    vm.title.set("Sent")
    assert node.get("text") == "Sent" and app.bindings.viewmodel_for("home") is vm  # still wired, same ViewModel


def test_an_opened_view_is_watched_by_the_file_it_keeps(tmp_path):
    (path,) = _project(tmp_path, "Home")
    app = App(root=tmp_path)
    app.bind(Home)
    app.open_view("Home")
    watchers = app._start_watchers(FakeHandle())
    try:
        assert [type(w) for w in watchers] == [ComposedWatcher] and path.resolve() in watchers[0].files
    finally:
        for w in watchers:
            w.stop()


def test_opened_screens_are_counted_and_a_spec_built_one_is_named(tmp_path, logs):
    _project(tmp_path, "Loaded", "Home")
    app = App(root=tmp_path)
    app.bind(Loaded)
    app.bind(Home)
    app.open_view("Loaded")
    app.open_view("Home")
    app.register("Scratch", tess_ui.View({"id": "root", "kind": "Container"}), None)
    watchers = app._start_watchers(FakeHandle())
    try:
        watched = sorted(f.name for w in watchers for f in w.files if f.name.endswith("_View.tdl"))
        assert watched == ["Home_View.tdl", "Loaded_View.tdl"]
        info = logs.messages("INFO")
        assert "hot reload: screen 'Scratch' isn't watched -- it was built from a spec, not a file" in info
        assert "hot reload on: watching 2 screen(s) and 0 theme/stylesheet file(s)" in info
    finally:
        for w in watchers:
            w.stop()
