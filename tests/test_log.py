"""Tesserae's logging through loguru (`tess_ui.log`).

Tesserae logs with loguru's shared `logger` and adds no output of its
own; `configure_logging()` is an app's one-call console setup.
"""

import io
import os
import warnings
from pathlib import Path

import pytest
from loguru import logger

import tess_ui.fonts as fonts
from tess_ui import App, configure_logging
from tess_ui.fonts import FontFallbackWarning, check_font_families
from tess_ui.spec.watch import ComposedWatcher

RECT = '---\nTDL: 0.2\nName: Home\nTesserae: "0.6"\n---\nRect { Name: box, Style { Width: 10, Height: 10, Background: "#112233" } }\n'


@pytest.fixture
def configured(monkeypatch):
    """`configure_logging` into a buffer; undone afterwards."""
    monkeypatch.setattr(warnings, "showwarning", warnings.showwarning)
    ids = []

    def configure(**kwargs):
        buffer = io.StringIO()
        ids.append(configure_logging(sink=buffer, **kwargs))
        return buffer

    yield configure
    for handler_id in ids:
        logger.remove(handler_id)


def _reload_once(tmp_path: Path) -> Path:
    (tmp_path / "Views").mkdir()
    path = tmp_path / "Views" / "Home_View.tdl"
    path.write_text(RECT)
    app = App(root=tmp_path)
    view = app.open_view("Home")
    watcher = ComposedWatcher(view, view.source, app._composed_docs, lambda library, doc: app._composed_rules(library, doc=doc)[0])
    path.write_text(RECT.replace("Width: 10, Height: 10", "Width: 12, Height: 12"))
    stat = path.stat()
    os.utime(path, ns=(stat.st_mtime_ns + 10**9, stat.st_mtime_ns + 10**9))
    assert watcher.poll() is True
    return path


def test_configure_logging_writes_tesserae_messages_in_its_format(tmp_path: Path, configured):
    buffer = configured()
    path = _reload_once(tmp_path)
    line = next(l for l in buffer.getvalue().splitlines() if "reloaded" in l)
    assert f"| INFO     | tess_ui.spec.watch - reloaded {path}" in line


def test_the_level_filters(tmp_path: Path, configured):
    buffer = configured(level="WARNING")
    _reload_once(tmp_path)
    assert "reloaded" not in buffer.getvalue()


def test_an_app_can_silence_tesserae(tmp_path: Path, configured):
    buffer = configured()
    logger.disable("tess_ui")
    try:
        _reload_once(tmp_path)
    finally:
        logger.enable("tess_ui")
    assert "reloaded" not in buffer.getvalue()


def test_warnings_show_through_loguru_and_still_can_be_errors(configured, monkeypatch):
    monkeypatch.setattr(fonts, "_registered", set())
    buffer = configured()
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        check_font_families(["Inter"], "Brand_Theme.tdl")
    assert "WARNING  |" in buffer.getvalue()
    assert "FontFallbackWarning: Brand_Theme.tdl: font_family 'Inter'" in buffer.getvalue()

    with warnings.catch_warnings():
        warnings.simplefilter("error", FontFallbackWarning)
        with pytest.raises(FontFallbackWarning):
            check_font_families(["Inter"], "Brand_Theme.tdl")


def test_capture_warnings_can_be_turned_off(configured):
    before = warnings.showwarning
    configured(capture_warnings=False)
    assert warnings.showwarning is before


def test_run_with_hot_reload_says_what_it_watches(tmp_path: Path, logs):
    (tmp_path / "Views").mkdir()
    (tmp_path / "Views" / "Home_View.tdl").write_text(RECT)
    sheet = tmp_path / "default.tdl"
    sheet.write_text("---\nTDL: 0.2\nName: default\nTesserae: \"0.6\"\n---\nStyles { }\n")

    app = App(root=tmp_path, stylesheet=sheet)
    app.open_view("Home")

    class Handle:
        def call_soon(self, fn):
            pass

    watchers = app._start_watchers(Handle())
    try:
        assert "hot reload on: watching 1 screen(s) and 1 theme/stylesheet file(s)" in logs.messages("INFO")
    finally:
        for watcher in watchers:
            watcher.stop()
