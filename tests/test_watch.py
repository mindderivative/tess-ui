"""M29 Phase 3: hot reload by polling file modification times -- a view opened with `app.open_view` is watched by a `ComposedWatcher` (a `ViewWatcher`),
which reloads it when a file it was read from changes.

Every edit here bumps the file's mtime explicitly (`_edit`), so the
tests don't depend on how finely the filesystem records timestamps.
"""

import os
from pathlib import Path

import pytest
from PIL import Image

from tess_ui import App, Signal, ViewModel
from tess_ui.spec.watch import ComposedWatcher


class VM(ViewModel):
    views = "home"

    def __init__(self):
        super().__init__()
        self.title = Signal("live")


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _bump_mtime(path: Path, before: int) -> None:
    os.utime(path, ns=(before + 1_000_000_000, before + 1_000_000_000))


def _edit(path: Path, text: str) -> None:
    before = path.stat().st_mtime_ns
    path.write_text(text)
    _bump_mtime(path, before)


def _view(name: str, body: str, header: str = "") -> str:
    """The TDL of `name`'s file: a Container that holds `body` (the TDL of its children, indented four spaces)."""
    return f"---\nTDL: 0.2\nName: {name}\n---\nContainer {{\n{header}  Children {{\n{body}  }}\n}}\n"


def _label(content: str, width: int = 100, text: str | None = None) -> str:
    text = content if text is None else text
    return f"    Text {{ Name: label, Text: {text}, Typography_Role: body_large, Style {{ Width: {width}, Height: 20, Foreground: on_surface }} }}\n"


def _text_view(content: str, extra_children: str = "") -> str:
    return _view("Home", _label(content) + extra_children)


def _png(path: Path, color=(255, 0, 0)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (2, 2), color).save(path)
    return path


def _watched(tmp_path: Path, text: str, *, viewmodel: bool = False):
    view_path = _write(tmp_path / "Views" / "Home_View.tdl", text)
    app = App(root=tmp_path)
    if viewmodel:
        app.bind(VM)
    view = app.open_view("Home")
    return view_path, view, ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])


def _text(view, name: str):
    view.window.advance(16)
    return view.node(f"root.{name}").get("text")


def test_poll_reports_no_change_until_a_file_changes(tmp_path: Path):
    _, _, watcher = _watched(tmp_path, _text_view("Hello"))
    assert watcher.poll() is False
    assert watcher.poll() is False


def test_editing_the_view_file_reconciles_the_live_view(tmp_path: Path):
    view_path, view, watcher = _watched(tmp_path, _text_view("Hello"))
    label = view.node("root.label")

    _edit(view_path, _text_view("Goodbye"))

    assert watcher.poll() is True
    assert _text(view, "label") == "Goodbye"
    assert view.node("root.label") is label  # same node, updated in place
    assert watcher.poll() is False


def test_editing_a_view_it_calls_reloads(tmp_path: Path):
    part = _write(tmp_path / "Views" / "Footer_View.tdl", _view("Footer", _label("v1")))
    _, view, watcher = _watched(tmp_path, _view("Home", "    Footer { Name: foot }\n"))
    assert part.resolve() in watcher.files

    _edit(part, _view("Footer", _label("v2")))

    assert watcher.poll() is True
    assert _text(view, "foot.label") == "v2"


def test_editing_a_view_with_params_that_is_called_with_a_value_reloads(tmp_path: Path):
    greeting = _write(tmp_path / "Views" / "Greeting_View.tdl", _view("Greeting", _label("Hi", width=0, text='"Hi"').replace("Width: 0", "Width: <| width |>"),
                                                                     header="  Params { Width { Type: int, Default: 10 } }\n"))
    _, view, watcher = _watched(tmp_path, _view("Home", "    Greeting { Name: greet, Width: 80 }\n"))
    assert greeting.resolve() in watcher.files

    _edit(greeting, greeting.read_text().replace('"Hi"', '"Hello there"'))

    assert watcher.poll() is True
    assert _text(view, "greet.label") == "Hello there"
    assert view.node("root.greet.label").get("width") == 80.0


def test_changing_an_image_file_reloads(tmp_path: Path):
    image = _png(tmp_path / "Views" / "logo.png")
    _, _, watcher = _watched(tmp_path, _view("Home", "    Image { Name: logo, Src: logo.png, Style { Width: 20, Height: 20 } }\n"))
    assert image.resolve() in watcher.files

    before = image.stat().st_mtime_ns
    _png(image, color=(0, 0, 255))
    _bump_mtime(image, before)

    assert watcher.poll() is True  # re-decoded and pushed without error


def test_a_newly_called_view_is_watched_after_reload(tmp_path: Path):
    view_path, view, watcher = _watched(tmp_path, _text_view("Hello"))
    rect = '---\nTDL: 0.2\nName: Extra\n---\nRect {{ Style {{ Width: {n}, Height: {n}, Background: "#112233" }} }}\n'
    part = _write(tmp_path / "Views" / "Extra_View.tdl", rect.format(n=5))
    assert part.resolve() not in watcher.files

    _edit(view_path, _text_view("Hello", "    Extra { Name: extra }\n"))
    assert watcher.poll() is True
    assert part.resolve() in watcher.files
    assert view.node("root.extra") is not None

    _edit(part, rect.format(n=9))
    assert watcher.poll() is True


def test_a_broken_edit_raises_once_then_recovers(tmp_path: Path):
    view_path, view, watcher = _watched(tmp_path, _text_view("Hello"))

    _edit(view_path, _text_view("Hello", "    NoSuchThing { Name: x }\n"))
    with pytest.raises(Exception, match="no widget named 'NoSuchThing'"):
        watcher.poll()
    assert watcher.poll() is False  # same broken state: no repeat error
    assert _text(view, "label") == "Hello"  # view left as it was

    _edit(view_path, _text_view("Fixed"))
    assert watcher.poll() is True
    assert _text(view, "label") == "Fixed"


def test_a_view_the_engine_rejects_is_reported_and_the_view_stays(tmp_path: Path):
    view_path, view, watcher = _watched(tmp_path, _text_view("Hello"))
    _edit(view_path, _text_view("Hello").replace("Typography_Role: body_large, ", ""))
    with pytest.raises(ValueError, match=r"Text requires text\.font_family \(or text\.typography_role\)"):
        watcher.poll()
    assert _text(view, "label") == "Hello"


def test_a_reload_that_edits_a_bound_node_keeps_its_live_value(tmp_path: Path):
    """M32: editing any property of a bound node used to make the node show its placeholder until its `Signal` next changed."""
    view_path, view, watcher = _watched(tmp_path, _view("Home", _label("placeholder", text="<| title |>"), header="  Name: home\n"), viewmodel=True)
    assert _text(view, "label") == "live"

    _edit(view_path, _view("Home", _label("placeholder", width=140, text="<| title |>"), header="  Name: home\n"))  # touches the bound node itself
    assert watcher.poll() is True
    assert _text(view, "label") == "live"  # not the placeholder
    assert view.node("root.label").get("width") == 140.0
