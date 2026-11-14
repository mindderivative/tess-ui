"""Fixtures of the Configuration Application's tests.

Every test works in its own `tmp_path`. The real-session guard of the repository's tests (`tests/real_session.py`) is applied first: no DISPLAY, no session bus, and the XDG folders
(the application's state folder among them) point at a private temporary folder. The shell is never run: the schema, `check` and `status` answers are recorded files in
`fixtures/`, and the `tesserae-shell` the application starts is a script written under `tmp_path`.

`tess_dl` needs Python 3.14; on an older Python these tests are not collected (the repository's own suite still runs there).
"""

import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests"))
import real_session  # noqa: E402

real_session.ensure()

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"

UNAVAILABLE = importlib.util.find_spec("tess_dl") is None or sys.platform == "win32"
if UNAVAILABLE:
    collect_ignore_glob = ["test_*.py"]  # a directory run; a file named on the command line (CI's partial run) is not ignored, so the hook below skips it


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    """A test module of the application that cannot be imported here (no `tess_dl`: it needs Python 3.14; Windows is not run) is skipped, not an error."""
    outcome = yield
    report = outcome.get_result()
    path = getattr(collector, "path", None)
    if UNAVAILABLE and report.failed and path is not None and HERE in Path(path).parents:
        report.outcome = "skipped"
        report.longrepr = (str(path), 0, "Skipped: the Configuration Application needs tess_dl (Python 3.14) and is not run on Windows")


@pytest.fixture(scope="session")
def schema_text():
    return (FIXTURES / "schema.json").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def schema_data(schema_text):
    return json.loads(schema_text)


@pytest.fixture(scope="session")
def schema(schema_text):
    from tess_shell_config.schema import Schema

    return Schema.from_json(schema_text)


FAKE_SHELL = """#!/bin/sh
# A stand-in for `tesserae-shell`: it prints the recorded answers that sit beside it and logs every call. It never reads or writes anything else.
here=$(dirname "$0")
echo "$@" >> "$here/calls.log"
[ -f "$here/delay" ] && sleep "$(cat "$here/delay")"
case "$1" in
  schema) cat "$here/schema.json" ;;
  check) cat "$here/check.json"; [ -f "$here/check.fails" ] && exit 1; exit 0 ;;
  status) cat "$here/status.json"; [ -f "$here/status.fails" ] && exit 3; exit 0 ;;
  reload) cat "$here/reload.json" 2>/dev/null; [ -f "$here/reload.fails" ] && exit 3; exit 0 ;;
  *) echo "unknown command $1" >&2; exit 2 ;;
esac
"""


class FakeShell:
    """A `tesserae-shell` script in `folder`, answering with the recorded files beside it. `calls()` is what the application asked, one line per call."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / "tesserae-shell"
        self.path.write_text(FAKE_SHELL)
        self.path.chmod(self.path.stat().st_mode | stat.S_IXUSR)
        (folder / "schema.json").write_text((FIXTURES / "schema.json").read_text(encoding="utf-8"))
        self.answer("check", {"ok": True, "config_dir": "<config_dir>", "files": 0, "errors": [], "omitted": 0})
        self.answer("status", {"config_dir": None})

    def answer(self, command: str, data, *, fails: bool = False) -> None:
        (self.folder / f"{command}.json").write_text(data if isinstance(data, str) else json.dumps(data))
        marker = self.folder / f"{command}.fails"
        if fails:
            marker.write_text("")
        elif marker.exists():
            marker.unlink()

    def delay(self, seconds: float) -> None:
        (self.folder / "delay").write_text(str(seconds))

    def calls(self) -> list[str]:
        log = self.folder / "calls.log"
        return log.read_text().splitlines() if log.exists() else []


@pytest.fixture
def fake_shell(tmp_path):
    return FakeShell(tmp_path / "bin")
