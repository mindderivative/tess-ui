"""The shell-command layer: `schema --json`, `check --json --config-dir` and `status --json` through a fake `tesserae-shell` script under tmp_path. The real shell is never run."""

import os
import json
import threading
import time
from pathlib import Path

import pytest

from tess_shell_config.schema import UnsupportedSchemaVersion
from tess_shell_config.shell import Offload, ShellCommand, ShellFailed, ShellNotFound, ShellTimeout

RECORDED = Path(__file__).parent / "fixtures" / "recorded"


def command(fake, **kwargs):
    return ShellCommand(str(fake.path), **kwargs)


def test_the_schema_is_read_through_the_command(fake_shell):
    schema = command(fake_shell).schema()
    assert schema.version_text == "1.1" and "Bar" in schema.roots
    assert fake_shell.calls() == ["schema --json"]


def test_check_passes_the_folder_and_reads_a_clean_answer(fake_shell, tmp_path):
    fake_shell.answer("check", (RECORDED / "check_clean.json").read_text())
    result = command(fake_shell).check(tmp_path / "cfg")
    assert result.ok and result.files == 2 and result.findings == () and result.omitted == 0
    assert fake_shell.calls() == [f"check --json --config-dir {tmp_path / 'cfg'}"]


def test_findings_come_back_with_file_line_column_rule_and_hint_even_when_the_command_exits_non_zero(fake_shell, tmp_path):
    fake_shell.answer("check", (RECORDED / "check_findings.json").read_text(), fails=True)
    result = command(fake_shell).check(tmp_path)
    assert not result.ok and len(result.findings) == 1
    finding = result.findings[0]
    assert (finding.file, finding.line, finding.column, finding.severity, finding.rule) == ("Shells/Foo_Shell.tdl", 5, 7, "error", "tdl-unclosed-block")
    assert finding.message == "This block is never closed." and finding.hint == "Add the missing }"
    assert str(finding) == "Shells/Foo_Shell.tdl:5:7: This block is never closed. (Add the missing })"


def test_status_keeps_what_the_shell_said_and_names_the_folder_when_it_does(fake_shell, tmp_path):
    fake_shell.answer("status", {"config_dir": str(tmp_path / "cfg"), "running": True, "pid": 7})
    status = command(fake_shell).status()
    assert status.config_dir == str(tmp_path / "cfg") and status.running is True and status.raw["pid"] == 7


def test_a_status_that_does_not_name_the_folder_yet_says_none(fake_shell):
    fake_shell.answer("status", {"shell": "x"})
    status = command(fake_shell).status()
    assert status.config_dir is None and status.running is None


def test_a_missing_command_is_a_message_naming_it(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(ShellNotFound) as raised:
        ShellCommand().schema()
    assert "tesserae-shell" in str(raised.value) and "PATH" in str(raised.value)
    with pytest.raises(ShellNotFound):
        ShellCommand(str(tmp_path / "nowhere")).check(tmp_path)


def test_a_command_found_by_name_on_the_path_runs(fake_shell, monkeypatch):
    monkeypatch.setenv("PATH", f"{fake_shell.folder}{os.pathsep}/usr/bin{os.pathsep}/bin")  # the script itself needs cat and sleep
    assert ShellCommand().schema().version_text == "1.1"


def test_a_command_that_does_not_answer_in_time_is_a_message(fake_shell, tmp_path):
    fake_shell.delay(5)
    started = time.monotonic()
    with pytest.raises(ShellTimeout) as raised:
        command(fake_shell, timeout=0.3).check(tmp_path)
    assert time.monotonic() - started < 4
    assert "check --json" in str(raised.value) and "0.3 seconds" in str(raised.value)


def test_an_answer_that_is_not_json_is_a_failure_with_the_reason(fake_shell, tmp_path):
    fake_shell.answer("check", "Traceback: boom", fails=True)
    with pytest.raises(ShellFailed) as raised:
        command(fake_shell).check(tmp_path)
    assert "exited with 1" in str(raised.value) and "boom" in str(raised.value)


def test_an_unknown_schema_major_version_is_refused_through_the_command(fake_shell):
    data = json.loads((fake_shell.folder / "schema.json").read_text())
    data["schema_version"] = "7.0"
    fake_shell.answer("schema", data)
    with pytest.raises(UnsupportedSchemaVersion):
        command(fake_shell).schema()


def test_the_command_runs_on_a_worker_thread_and_its_answer_is_posted_to_the_loop(fake_shell, tmp_path):
    posted: list = []
    done = threading.Event()
    ran_on = []

    def run():
        ran_on.append(threading.current_thread())
        return command(fake_shell).check(tmp_path)

    results, errors = [], []

    def post(fn):
        posted.append(fn)
        done.set()

    thread = Offload(post).submit(run, results.append, errors.append)
    assert done.wait(5)
    thread.join(5)
    assert ran_on[0] is not threading.main_thread() and results == [] and errors == []  # nothing ran on the loop until the loop runs it
    posted.pop()()
    assert len(results) == 1 and results[0].ok and errors == []


def test_a_failing_call_posts_its_error_to_the_loop(fake_shell, tmp_path):
    fake_shell.delay(5)
    posted: list = []
    done = threading.Event()
    errors = []
    Offload(lambda fn: (posted.append(fn), done.set())).submit(lambda: command(fake_shell, timeout=0.2).check(tmp_path), lambda value: None, errors.append)
    assert done.wait(5)
    posted.pop()()
    assert len(errors) == 1 and isinstance(errors[0], ShellTimeout)
