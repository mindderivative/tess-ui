"""Shared fixtures."""

import os
import tempfile
import threading
import time

import pytest
from loguru import logger

# -- A bare run never reaches the person's own session ------------------------------------------------------------------------------
#
# Tests open windows (`App.run(max_frames=...)`, the example apps, the built executable) and write and read the OS clipboard through
# tess_re. With the person's DISPLAY, WAYLAND_DISPLAY and session bus in the environment they would do that on their desktop: a window
# on it, their clipboard overwritten. So a local run drops those variables (the tests that need a display skip, as on CI's Linux) and
# points the per-user config and cache at a private folder. `TESS_UI_ALLOW_REAL_SESSION=1` allows it, for a hand-run on purpose;
# CI (`CI` is set) is left alone, because its jobs run under their own `xvfb-run` display.
REAL_SESSION_VARIABLES = ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_ID", "XDG_SESSION_TYPE")


def keep_off_the_real_session(environ=os.environ):
    """Remove the real session from `environ` and return what was removed (empty when nothing was, or when it is allowed)."""
    if environ.get("TESS_UI_ALLOW_REAL_SESSION") == "1" or environ.get("CI"):
        return {}
    removed = {name: environ.pop(name) for name in REAL_SESSION_VARIABLES if name in environ}
    private = tempfile.mkdtemp(prefix="tess-ui-tests-")
    for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME", "XDG_RUNTIME_DIR"):
        environ[name] = os.path.join(private, name.lower())
        os.makedirs(environ[name], mode=0o700, exist_ok=True)
    environ.setdefault("TESS_UI_STATE_DIR", os.path.join(private, "state"))
    return removed


REMOVED_FROM_ENVIRONMENT = keep_off_the_real_session()


def pytest_report_header(config):
    if REMOVED_FROM_ENVIRONMENT:
        return "real session kept out of the tests (dropped " + ", ".join(sorted(REMOVED_FROM_ENVIRONMENT)) + "); TESS_UI_ALLOW_REAL_SESSION=1 allows it"


class LogRecords:
    """Every loguru record at DEBUG and above while a test runs, as
    `(level, message)` pairs. Watcher threads log too, so it's locked."""

    def __init__(self):
        self._lock = threading.Lock()
        self._records: list[tuple[str, str]] = []

    def sink(self, message):
        record = message.record
        with self._lock:
            self._records.append((record["level"].name, record["message"]))

    @property
    def records(self) -> list[tuple[str, str]]:
        with self._lock:
            return list(self._records)

    def messages(self, level: str) -> list[str]:
        return [m for lvl, m in self.records if lvl == level]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()

    def edit_until(self, path, text: str, level: str, contains: str, attempts: int = 40) -> str:
        """Writes `text` to `path` until a `level` record containing
        `contains` is logged -- a background watcher can miss an edit made
        before it started listening."""
        for _ in range(attempts):
            path.write_text(text)
            try:
                return self.wait_for(level, contains, timeout=0.25)
            except AssertionError:
                continue
        raise AssertionError(f"no {level} log containing {contains!r} after editing {path}; got {self.records}")

    def wait_for(self, level: str, contains: str, timeout: float = 5.0) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for message in self.messages(level):
                if contains in message:
                    return message
            time.sleep(0.02)
        raise AssertionError(f"no {level} log containing {contains!r}; got {self.records}")


@pytest.fixture
def logs():
    captured = LogRecords()
    handler_id = logger.add(captured.sink, level="DEBUG", format="{message}")
    yield captured
    logger.remove(handler_id)


# -- M43: tess_re's recorded answers (tests/reference.py) -----------------------

import reference  # noqa: E402


@pytest.fixture(autouse=True)
def _tre_reference(request):
    """Keys `reference.tess_re()` answers by the running test."""
    reference.begin(request.module.__name__, request.node.name)
    yield


def pytest_sessionfinish(session, exitstatus):
    """Recording: saved only if every test passed, so a mismatch is never
    written in as `tess_re`'s answer."""
    if reference.RECORDING and exitstatus == 0:
        reference.STORE.save()


@pytest.fixture(autouse=True)
def os_appearance(monkeypatch):
    """The OS's light/dark appearance, as `App(dark="system")` reads it
    (M53): unknown (`None`) by default, so an app starts dark whatever the
    desktop running the tests uses. A test sets `os_appearance.dark`."""
    import tess_ui.app

    class Appearance:
        dark = None

    appearance = Appearance()
    monkeypatch.setattr(tess_ui.app, "_os_dark", lambda window: appearance.dark)
    return appearance


@pytest.fixture(autouse=True)
def _the_os_does_not_ask_for_reduced_motion(monkeypatch):
    """An `App` that follows the OS (the default) would read reduced motion from the machine running the tests: GitHub's Windows and macOS
    runners ask for it, so every animation finished at once and the tests that watch one in progress failed. A test that cares passes
    `reduced_motion=True` or `False` itself; `test_os_preferences.py` drives the OS events directly."""
    from tess_ui.app import App

    wanted = App._wanted

    def not_reduced(self, name, mode):
        return False if (name == "reduced_motion" and mode == "system") else wanted(self, name, mode)

    monkeypatch.setattr(App, "_wanted", not_reduced)
