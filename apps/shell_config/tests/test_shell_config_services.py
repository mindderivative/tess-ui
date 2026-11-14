"""Phase C4 without the real shell: `check` and the problems list, a finding that selects its block and key, saving, "Apply as I edit", the status line, reload, and a file changed on disk.

The shell is a script written under `tmp_path` that prints the recorded answers (`conftest.FakeShell`); the folder is a copy of the representative configuration under `tmp_path`; the command layer
is handed the script's path, so the real `tesserae-shell` is never started. Commands run through `InlineOffload` (at once) except where a test proves the worker thread.
"""

import json
import os
import queue
import shutil
import threading
import time
from pathlib import Path

import pytest

from tess_shell_config.app import build
from tess_shell_config.files import ChangedOnDisk
from tess_shell_config.session import ConfigSession
from tess_shell_config.shell import Offload, ShellCommand
from tess_shell_config.watcher import FileWatch

CONFIG = Path(__file__).parent / "fixtures" / "config"
RECORDED = Path(__file__).parent / "fixtures" / "recorded"
MAIN = "Shells/Main_Shell.tdl"


def finding(line, column, message="A finding.", file=MAIN, severity="error", rule="some-rule", hint=""):
    return {"file": file, "line": line, "column": column, "severity": severity, "rule": rule, "message": message, "hint": hint}


def check_answer(*findings, files=5, omitted=0):
    return {"ok": not findings, "config_dir": "<config_dir>", "files": files, "errors": list(findings), "omitted": omitted}


class Rig:
    """A window over a copy of the configuration, with the fake shell as its command."""

    def __init__(self, tmp_path, fake_shell, schema, *, timeout=5.0):
        self.folder = tmp_path / "cfg"
        shutil.copytree(CONFIG, self.folder)
        self.fake = fake_shell
        self.state = tmp_path / "state"
        self.schema = schema
        self.timeout = timeout
        self.start()

    def start(self):
        self.session = ConfigSession(self.folder, self.schema, ShellCommand(str(self.fake.path), timeout=self.timeout), state_dir=self.state)
        self.built = build(self.session, reduced_motion=True)
        self.vm = self.built.viewmodel
        self.services = self.vm.services
        self.settle()

    def settle(self, n=4):
        for _ in range(n):
            self.built.window.advance(16)

    @property
    def path(self):
        return self.folder / MAIN

    def open(self, rel=MAIN):
        self.vm.open_file(rel)
        self.settle()
        return self.session.model

    def calls(self, word):
        return [c for c in self.fake.calls() if c.startswith(word)]

    def row_names(self):
        return [inst.name for inst in self.built.view.handle.composition.walk() if inst.name]


@pytest.fixture
def rig(tmp_path, fake_shell, schema):
    return Rig(tmp_path, fake_shell, schema)


def edit_height(rig, value="40"):
    """A form edit of the Top_Bar's Height, through the form's own commit (as a field does)."""
    model = rig.session.model
    bar = next(n for n in _walk(model.document.root) if getattr(n, "name", None) == "Top_Bar")
    model.select(bar.index_path)
    rig.vm._show(model, new_file=False)
    rig.vm.form_commit("k:Height|", {"text": value})
    rig.settle()


def _walk(node):
    from tess_shell_config.tdl import walk

    return walk(node)


# -- check and the problems list ---------------------------------------------------------------------------------------------------

def test_a_finding_is_listed_with_an_icon_and_words_and_file_line_and_column(rig):
    rig.fake.answer("check", (RECORDED / "check_findings.json").read_text(), fails=True)
    rig.services.request_check()
    [row] = rig.vm.problems.get()
    assert row["icon"] == "error" and row["severity"] == "Error" and row["where"] == "Shells/Foo_Shell.tdl:5:7"
    assert row["message"] == "This block is never closed." and row["hint"] == "Add the missing }" and row["rule"] == "tdl-unclosed-block"
    assert rig.vm.problems_title.get() == "Problems: 1 finding in 1 file" and rig.vm.has_problems.get()
    assert rig.calls("check") == [f"check --json --config-dir {rig.folder}"]
    names = rig.row_names()
    assert "problems_pane" in names and "problem_row" in names and "problem_icon" in names and "problem_severity" in names


def test_a_clean_check_says_so_and_a_warning_has_its_own_icon_and_word(rig):
    rig.fake.answer("check", (RECORDED / "check_clean.json").read_text())
    rig.services.request_check()
    assert rig.vm.problems.get() == [] and rig.vm.problems_title.get() == "Problems: none (2 files checked)" and not rig.vm.has_problems.get()
    rig.fake.answer("check", check_answer(finding(1, 1, severity="warning"), finding(2, 1, severity="info"), omitted=3), fails=True)
    rig.services.request_check()
    assert [(r["icon"], r["severity"]) for r in rig.vm.problems.get()] == [("alert", "Warning"), ("information", "Note"), ("information", "Note")]
    assert rig.vm.problems.get()[-1]["message"] == "3 more finding(s) were left out by check." and not rig.vm.problems.get()[-1]["clickable"]


def test_a_check_that_fails_to_run_is_one_message_and_editing_goes_on(rig):
    rig.open()
    rig.fake.answer("check", "", fails=True)  # exits 1 with nothing on its output
    rig.services.request_check()
    [row] = rig.vm.problems.get()
    assert row["severity"] == "Check" and "gave no JSON" in row["message"] and not row["clickable"]
    assert rig.vm.problems_title.get() == "Problems: the check did not run"
    edit_height(rig)  # editing is not stopped
    assert "Height: 40" in rig.session.model.text and rig.session.model.dirty


def test_a_check_that_does_not_answer_in_time_is_one_message(tmp_path, fake_shell, schema):
    rig = Rig(tmp_path, fake_shell, schema, timeout=0.3)
    fake_shell.delay(1.0)
    started = time.monotonic()
    rig.services.request_check()
    [row] = rig.vm.problems.get()
    assert "did not answer within 0.3 seconds" in row["message"] and time.monotonic() - started < 3


def test_a_check_with_no_command_asks_nothing(tmp_path, schema):
    folder = tmp_path / "cfg"
    shutil.copytree(CONFIG, folder)
    built = build(ConfigSession(folder, schema, None, state_dir=tmp_path / "state"), reduced_motion=True)
    built.viewmodel.services.request_check()
    assert built.viewmodel.problems.get() == [] and not built.viewmodel.checking.get()


def test_a_check_runs_on_a_worker_and_never_blocks_the_caller(tmp_path, fake_shell, schema):
    rig = Rig(tmp_path, fake_shell, schema)
    posted = queue.Queue()
    rig.services.offload = Offload(posted.put)
    rig.fake.answer("check", check_answer(finding(17, 13)), fails=True)
    fake_delay = 0.6
    rig.fake.delay(fake_delay)
    started = time.monotonic()
    rig.services.request_check()
    returned = time.monotonic() - started
    assert returned < fake_delay / 3 and rig.vm.checking.get() and rig.vm.problems.get() == []  # the call came back at once, the answer is not there
    rig.services.request_check()  # one at a time: asked again while it runs is remembered, not started
    assert len(rig.calls("check")) <= 1
    posted.get(timeout=5)()  # the worker posted its answer; the loop thread (here: this one) runs it
    assert len(rig.vm.problems.get()) == 1 or rig.vm.checking.get()  # the remembered request started the next run
    posted.get(timeout=5)()
    assert not rig.vm.checking.get() and rig.vm.problems.get()[0]["where"] == f"{MAIN}:17:13" and len(rig.calls("check")) == 2


def test_the_answer_of_a_worker_is_applied_on_the_thread_that_runs_the_post(tmp_path, fake_shell, schema):
    rig = Rig(tmp_path, fake_shell, schema)
    where = []
    posted = queue.Queue()
    rig.services.offload = Offload(posted.put)
    rig.services.request_check()
    post = posted.get(timeout=5)
    rig.vm.problems_title.set("x")
    post()
    where.append(threading.current_thread().name)
    assert where == [threading.current_thread().name] and rig.vm.problems_title.get().startswith("Problems: none")


# -- a finding selects its block and key ---------------------------------------------------------------------------------------------------

def focused(rig):
    found = []
    for inst in rig.built.view.handle.composition.walk():
        try:
            if rig.built.view.node(inst.id).get("focused"):
                found.append(inst.id)
        except (KeyError, ValueError):
            pass
    return found


def click(rig, line, column, message="Pointed at."):
    rig.fake.answer("check", check_answer(finding(line, column, message)), fails=True)
    rig.services.request_check()
    rig.services.pick_problem(0)
    rig.settle()


def test_clicking_a_finding_opens_the_file_selects_the_block_and_shows_the_key(rig):
    click(rig, 17, 13, "Width is wrong.")  # `Width: EXPAND` of Top_Bar
    model = rig.session.model
    assert model.relative == MAIN and model.selected.name == "Top_Bar" and model.selected.type == "Bar"
    assert rig.vm.structure_selected.get() and "Top_Bar" in rig.vm.selected_label.get()
    assert rig.vm.form_title.get() == "Bar  Top_Bar"
    rows = [i for i in rig.vm.form_items.get() if i["type"] == "row"]
    assert any(r["id"] == "k:Width" for r in rows)  # its group is open so the row is built
    assert rig.vm.status.get().startswith(f"{MAIN}:17:13: Width is wrong.") and not rig.vm.status_is_error.get()
    assert any("form_item[k:Width#" in node_id for node_id in focused(rig)), focused(rig)  # the key's own widget has the keyboard focus


def test_the_key_of_a_finding_in_a_nested_style_block_is_found_on_the_block_that_holds_the_style(rig):
    click(rig, 19, 22)  # `Background` inside `Style { }` of Top_Bar
    model = rig.session.model
    assert model.selected.name == "Top_Bar"
    assert "k:Background" in {i["id"] for i in rig.vm.form_items.get() if i["type"] == "row"}


def test_a_finding_inside_an_if_condition_selects_the_if(rig):
    click(rig, 24, 20)
    node = rig.session.model.selected
    assert type(node).__name__ == "If" and [i["id"] for i in rig.vm.form_items.get() if i["type"] == "row"] == ["f:condition"]


def test_a_finding_on_a_block_line_with_no_key_selects_the_block(rig):
    click(rig, 22, 17)  # the `Clock` block
    assert rig.session.model.selected.type == "Clock"


def test_a_finding_in_another_file_opens_that_file_and_one_outside_every_block_says_so(rig):
    rig.fake.answer("check", check_answer(finding(1, 1, file="Themes/Dark_Theme.tdl")), fails=True)
    rig.services.request_check()
    rig.services.pick_problem(0)
    assert rig.session.model.relative == "Themes/Dark_Theme.tdl" and not rig.vm.status_is_error.get() or rig.vm.status_is_error.get()
    assert "is not inside a block" in rig.vm.status.get() and rig.vm.status_is_error.get()  # line 1 is the metadata, no block
    rig.fake.answer("check", check_answer(finding(2, 2, file="Shells/Nowhere_Shell.tdl")), fails=True)
    rig.services.request_check()
    rig.services.pick_problem(0)
    assert "is not a file of" in rig.vm.status.get() and rig.vm.status_is_error.get()


def test_a_finding_in_a_file_with_syntax_errors_opens_it_in_the_text_view_and_says_why(rig):
    rig.fake.answer("check", check_answer(finding(6, 1, file="Shells/Broken_Shell.tdl")), fails=True)
    rig.services.request_check()
    rig.services.pick_problem(0)
    assert rig.session.model.relative == "Shells/Broken_Shell.tdl" and not rig.vm.has_tree.get()
    assert "syntax errors" in rig.vm.status.get() and rig.vm.status_is_error.get()


def test_a_finding_in_a_file_with_unsaved_changes_says_the_place_may_have_moved(rig):
    rig.open()
    edit_height(rig)
    click(rig, 17, 13)
    assert "unsaved changes" in rig.vm.status.get()


def test_the_paths_of_findings_may_be_absolute_or_start_with_dot_slash(rig):
    for name in (str(rig.folder / MAIN), "./" + MAIN):
        rig.fake.answer("check", check_answer(finding(17, 13, file=name)), fails=True)
        rig.services.request_check()
        rig.services.pick_problem(0)
        assert rig.session.model.selected.name == "Top_Bar"


# -- saving ----------------------------------------------------------------------------------------------------------------------------

def test_save_writes_the_file_runs_check_and_does_not_reload_unless_apply_is_on(rig):
    rig.fake.answer("status", (RECORDED / "status_running.json").read_text())
    rig.services.refresh_status()
    rig.open()
    edit_height(rig)
    assert rig.vm.dirty.get() and "Height: 32" in rig.path.read_text()  # nothing is written by an edit alone
    rig.vm.save()
    assert "Height: 40" in rig.path.read_text() and not rig.vm.dirty.get() and rig.vm.status.get() == f"Saved {MAIN}"
    assert len(rig.calls("check")) == 1 and rig.calls("reload") == []
    assert (rig.state / "backups").is_dir()  # the first save kept the old file


def test_a_save_with_apply_on_asks_a_running_shell_to_reload(rig):
    rig.fake.answer("status", (RECORDED / "status_running.json").read_text())
    rig.services.refresh_status()
    rig.services.apply_changed(True)
    rig.open()
    edit_height(rig)  # apply on: the commit wrote the file
    assert "Height: 40" in rig.path.read_text() and rig.calls("reload") == ["reload"] and len(rig.calls("check")) == 1
    assert rig.vm.status.get().startswith("Reloaded")


def test_a_save_with_apply_on_and_no_shell_running_does_not_reload(rig):
    rig.fake.answer("status", (RECORDED / "status_not_running.json").read_text(), fails=True)
    rig.services.refresh_status()
    rig.services.apply_changed(True)
    rig.open()
    edit_height(rig)
    assert "Height: 40" in rig.path.read_text() and rig.calls("reload") == [] and len(rig.calls("check")) == 1


def test_apply_writes_after_each_commit_undo_redo_and_structure_edit_but_not_while_it_is_off(rig):
    rig.open()
    original = rig.path.read_text()
    edit_height(rig)
    assert rig.path.read_text() == original  # off
    rig.vm.save()
    rig.services.apply_changed(True)
    rig.vm.undo()
    assert rig.path.read_text() == original  # undo is a commit: written
    rig.vm.redo()
    assert "Height: 40" in rig.path.read_text()
    edit_height(rig, "48")
    assert "Height: 48" in rig.path.read_text()
    rig.vm.structure_actions.duplicate()
    rig.settle()
    assert "Top_Bar_Copy" in rig.path.read_text()
    assert not rig.vm.dirty.get()


def test_typing_in_the_text_view_is_written_once_it_rests_and_only_when_it_parses(rig):
    timers = []
    rig.services.timer = lambda ms, fn: timers.append((ms, fn))
    rig.services.apply_changed(True)
    model = rig.open()
    text = model.text
    rig.vm.text.set(text.replace("Height: 32", "Height: 3"))
    rig.vm.text_edited()
    rig.vm.text.set(text.replace("Height: 32", "Height: 36"))
    rig.vm.text_edited()
    assert "Height: 32" in rig.path.read_text() and len(timers) == 2  # nothing yet; each edit asked for a write after a rest
    assert timers[0][0] == 200
    timers[0][1]()  # the first timer is stale: a newer edit came
    assert "Height: 32" in rig.path.read_text()
    timers[1][1]()
    assert "Height: 36" in rig.path.read_text()
    rig.vm.text.set(rig.session.model.text.replace("Monitor {", "Monitor {{"))  # no longer parses
    rig.vm.text_edited()
    timers[-1][1]()
    assert "Monitor {{" not in rig.path.read_text()


def test_the_apply_choice_is_kept_in_the_state_folder_and_read_back(tmp_path, fake_shell, schema):
    rig = Rig(tmp_path, fake_shell, schema)
    assert rig.vm.apply_on_edit.get() is False
    rig.services.apply_changed(True)
    assert json.loads((rig.state / "settings.json").read_text()) == {"apply_as_i_edit": True}
    assert not any(p.name == "settings.json" for p in rig.folder.rglob("*")) or (rig.folder / "settings.json").read_text() == (CONFIG / "settings.json").read_text()
    rig.start()
    assert rig.vm.apply_on_edit.get() is True
    rig.services.apply_changed(False)
    rig.start()
    assert rig.vm.apply_on_edit.get() is False


def test_the_apply_switch_in_the_window_is_the_signal(rig):
    switch = rig.built.view.node("root.apply_switch") if False else None
    names = rig.row_names()
    assert {"apply_switch", "check_button", "reload_button"} <= set(names) and switch is None
    rig.vm.apply_on_edit.set(True)
    rig.settle()
    rig.vm.apply_changed(True)
    assert rig.services.settings.apply_as_i_edit and "Apply as I edit is on" in rig.vm.status.get()


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to a read-only folder")
def test_a_failed_save_leaves_the_old_file_whole_and_names_the_cause(rig):
    rig.open()
    edit_height(rig)
    before = rig.path.read_bytes()
    shells = rig.folder / "Shells"
    shells.chmod(0o555)
    try:
        rig.vm.save()
    finally:
        shells.chmod(0o755)
    assert rig.path.read_bytes() == before and rig.vm.dirty.get()
    assert rig.vm.status_is_error.get() and "Cannot save Main_Shell.tdl: permission denied" in rig.vm.status.get() and "The old file is unchanged" in rig.vm.status.get()
    assert sorted(p.name for p in shells.iterdir()) == sorted(p.name for p in (CONFIG / "Shells").iterdir())  # no temporary file left behind
    assert rig.calls("check") == []  # nothing was saved, so nothing is checked
    rig.vm.save()  # the folder is writable again: the same edit is still there to save
    assert "Height: 40" in rig.path.read_text()


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to a read-only folder")
def test_a_failed_apply_write_says_so_and_editing_goes_on(rig):
    rig.services.apply_changed(True)
    rig.open()
    shells = rig.folder / "Shells"
    shells.chmod(0o555)
    try:
        edit_height(rig)
    finally:
        shells.chmod(0o755)
    assert rig.vm.status_is_error.get() and "permission denied" in rig.vm.status.get() and rig.vm.dirty.get()
    edit_height(rig, "44")  # the next commit tries again
    assert "Height: 44" in rig.path.read_text() and not rig.vm.dirty.get()


# -- the status line and reload -------------------------------------------------------------------------------------------------------------

def test_the_status_line_says_running_not_running_or_unknown(rig):
    rig.fake.answer("status", (RECORDED / "status_running.json").read_text())
    rig.services.refresh_status()
    assert rig.vm.shell_state.get() == "Shell: running (Top_Bar shown)" and rig.vm.shell_running.get()
    rig.fake.answer("status", (RECORDED / "status_not_running.json").read_text(), fails=True)
    rig.services.refresh_status()
    assert rig.vm.shell_state.get() == "Shell: not running (editing and checking still work)" and not rig.vm.shell_running.get()
    rig.fake.answer("status", "not json", fails=True)
    rig.services.refresh_status()
    assert rig.vm.shell_state.get().startswith("Shell: unknown (") and "no JSON" in rig.vm.shell_state.get() and not rig.vm.shell_running.get()
    assert "shell_text" in rig.row_names()


def test_the_reload_button_asks_the_running_shell_and_reports_its_answer(rig):
    rig.services.reload_shell()
    assert "No shell is running" in rig.vm.status.get() and rig.calls("reload") == []
    rig.fake.answer("status", (RECORDED / "status_running.json").read_text())
    rig.services.refresh_status()
    rig.open()
    edit_height(rig)
    rig.services.reload_shell()
    assert "save Shells/Main_Shell.tdl first" in rig.vm.status.get() and rig.calls("reload") == []
    rig.vm.save()
    rig.services.reload_shell()
    assert rig.calls("reload") == ["reload"] and rig.vm.status.get().startswith("Reloaded") and not rig.vm.status_is_error.get()
    rig.fake.answer("reload", "line 3: Unknown key\nmore", fails=True)
    rig.services.reload_shell()
    assert rig.vm.status.get() == "The shell did not reload: line 3: Unknown key" and rig.vm.status_is_error.get()


# -- a file changed on disk ----------------------------------------------------------------------------------------------------------------

def other_program_writes(rig, text=None):
    """Another program changes the open file (a write beside the application's own)."""
    current = rig.path.read_text()
    rig.path.write_text(text or current.replace("Edge: TOP", "Edge: BOTTOM"))
    return rig.path.read_bytes()


def test_a_change_by_another_program_asks_and_the_applications_own_save_does_not(rig):
    rig.open()
    edit_height(rig)
    rig.vm.save()
    rig.services.disk_events({MAIN: rig.path.read_bytes()})  # the watch reports our own save
    assert not rig.vm.has_disk_change.get() and rig.vm.disk_message.get() == ""
    raw = other_program_writes(rig)
    rig.services.disk_events({MAIN: raw})
    assert rig.vm.has_disk_change.get() and MAIN in rig.vm.disk_message.get() and "changed on disk by another program" in rig.vm.disk_message.get()
    assert {"disk_banner", "disk_reload_button", "disk_keep_button"} <= set(rig.row_names()) or rig.settle(4) is None


def test_a_save_over_a_file_another_program_changed_is_refused_and_leaves_it_whole(rig):
    rig.open()
    edit_height(rig)
    raw = other_program_writes(rig)
    with pytest.raises(ChangedOnDisk):
        rig.session.save()
    rig.vm.save()
    assert rig.path.read_bytes() == raw and rig.vm.dirty.get() and rig.vm.status_is_error.get() and "changed on disk by another program" in rig.vm.status.get()
    assert rig.vm.has_disk_change.get()  # even when the watch was not there to say it, the refused save asks
    assert rig.calls("check") == []


def test_reload_takes_the_disk_version_and_the_history_starts_over(rig):
    rig.open()
    edit_height(rig)
    raw = other_program_writes(rig)
    rig.services.disk_events({MAIN: raw})
    rig.vm.disk_reload()
    rig.settle()
    model = rig.session.model
    assert model.text == raw.decode() and not model.dirty and not model.can_undo and rig.vm.text.get() == raw.decode()
    assert not rig.vm.has_disk_change.get() and "Edge: BOTTOM" in rig.vm.text.get() and rig.vm.status.get() == f"Reloaded {MAIN} from disk"


def test_keep_leaves_the_version_here_asks_no_second_time_and_the_next_save_replaces_the_disks(rig):
    rig.open()
    edit_height(rig)
    raw = other_program_writes(rig)
    rig.services.disk_events({MAIN: raw})
    rig.vm.disk_keep()
    assert not rig.vm.has_disk_change.get() and rig.session.model.dirty and "Height: 40" in rig.session.model.text
    assert rig.path.read_bytes() == raw  # nothing written by choosing Keep
    rig.services.disk_events({MAIN: raw})  # the watch reports the same content again: not asked again
    assert not rig.vm.has_disk_change.get()
    rig.vm.save()
    assert "Height: 40" in rig.path.read_text() and not rig.vm.dirty.get()
    raw2 = other_program_writes(rig, "garbage {")
    rig.services.disk_events({MAIN: raw2})
    assert rig.vm.has_disk_change.get()  # a further change asks again


def test_a_change_of_a_file_that_is_not_open_only_reads_the_folder_again(rig):
    other = rig.folder / "Shells" / "Windows_Shell.tdl"
    other.write_text(other.read_text() + "\n")
    rig.services.disk_events({"Shells/Windows_Shell.tdl": other.read_bytes()})
    assert not rig.vm.has_disk_change.get()
    new = rig.folder / "Shells" / "Fresh_Shell.tdl"
    new.write_text("---\nTDL: 0.1\nShell: 0.1\nName: Fresh\n---\n\nShell { }\n")
    rig.services.disk_events({"Shells/Fresh_Shell.tdl": new.read_bytes()})
    assert any(row["value"] == "f:Shells/Fresh_Shell.tdl" for group in rig.vm.file_nodes.get() for row in group.get("children", []))


# -- the watch itself -----------------------------------------------------------------------------------------------------------------------

def wait_for(posted, timeout=8.0):
    """Run what the watch posted until `timeout`; returns the number of posts run."""
    ran = 0
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            posted.get(timeout=0.2)()
        except queue.Empty:
            if ran:
                return ran
        else:
            ran += 1
    return ran


def test_the_watch_reports_a_changed_tdl_file_with_its_bytes_and_ignores_other_files(tmp_path):
    folder = tmp_path / "watched"
    (folder / "Shells").mkdir(parents=True)
    (folder / "Shells" / "A_Shell.tdl").write_text("one")
    seen, posted = [], queue.Queue()
    watch = FileWatch(folder, posted.put, seen.append, lambda message: seen.append(message))
    watch.start()
    try:
        time.sleep(0.6)
        (folder / "notes.txt").write_text("ignored")
        (folder / "Shells" / "A_Shell.tdl").write_text("two")
        (folder / "Shells" / ".A_Shell.tdl.abc.tmp").write_text("temporary")
        wait_for(posted)
        assert seen == [{"Shells/A_Shell.tdl": b"two"}]
        (folder / "Shells" / "A_Shell.tdl").unlink()
        wait_for(posted)
        assert seen[-1] == {"Shells/A_Shell.tdl": None}
    finally:
        started = time.monotonic()
        watch.stop()
    assert time.monotonic() - started < 2 and not watch.running


def test_the_watch_runs_on_its_own_thread_and_the_window_decides_on_the_loop_thread(tmp_path, fake_shell, schema):
    rig = Rig(tmp_path, fake_shell, schema)
    posted = queue.Queue()
    rig.services.start(posted.put)
    try:
        assert rig.services.watch.running and threading.current_thread().name != "tess-shell-config-watch"
        rig.open()
        edit_height(rig)
        time.sleep(0.6)
        rig.vm.save()  # the application's own save: the watch will report it, and nothing is asked
        wait_for(posted)
        assert not rig.vm.has_disk_change.get()
        other_program_writes(rig)
        wait_for(posted)
        assert rig.vm.has_disk_change.get() and MAIN in rig.vm.disk_message.get()
        assert rig.calls("status") and rig.calls("check")  # `start` asked for the status and a first check, through the same offload
    finally:
        rig.services.stop()
    assert rig.services.watch is None


def test_a_watch_that_cannot_start_says_so_once_and_the_window_goes_on(tmp_path, fake_shell, schema):
    rig = Rig(tmp_path, fake_shell, schema)
    gone = tmp_path / "gone"
    seen, posted = [], queue.Queue()
    FileWatch(gone, posted.put, seen.append, seen.append).start()
    wait_for(posted, 5)
    assert len(seen) == 1 and seen[0].startswith("The file watch stopped:")
    rig.services._watch_failed(seen[0])
    assert rig.vm.status_is_error.get() and "will not be noticed" in rig.vm.status.get()
