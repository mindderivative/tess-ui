"""Phase C4 in the window, driven with key events only: the check, the Problems area, a finding that selects its block and key, Apply as I edit, undo, save, reload and a file changed on disk."""

import shutil
import time

import pytest

from tess_shell_config.app import build
from tess_shell_config.session import ConfigSession
from tess_shell_config.shell import ShellCommand

from test_shell_config_services import MAIN, RECORDED, check_answer, finding
from test_shell_config_window import CONFIG, Window


class ShellWindow(Window):
    """The window of `Window`, over a session with the fake shell as its command and the recorded schema."""

    def __init__(self, folder, tmp_path, fake, schema):
        self.session = ConfigSession(folder, schema, ShellCommand(str(fake.path)), state_dir=tmp_path / "state")
        self.built = build(self.session, reduced_motion=True)
        self.vm = self.built.viewmodel
        self.window = self.built.window
        self.fake = fake
        self.settle(8)


@pytest.fixture
def folder(tmp_path):
    target = tmp_path / "cfg"
    shutil.copytree(CONFIG, target)
    return target


def test_check_the_problems_area_and_apply_work_from_the_keyboard_alone(folder, tmp_path, fake_shell, schema):
    w = ShellWindow(folder, tmp_path, fake_shell, schema)
    main = folder / MAIN
    original = main.read_bytes()
    fake_shell.answer("check", check_answer(finding(17, 13, "Width is wrong.", hint="Use a number."), finding(24, 20, "The condition is wrong.")), fails=True)
    # F5 runs the check; the list shows two findings, each with an icon and words
    w.key("F5")
    assert [r["where"] for r in w.vm.problems.get()] == [f"{MAIN}:17:13", f"{MAIN}:24:20"] and w.vm.has_problems.get()
    # F6 moves on through the areas; with findings listed the last of them is the Problems area
    for _ in range(8):
        if w.region() == 4:
            break
        w.key("F6")
    assert w.region() == 4 and w.focused()[0].endswith("problem_row[p:0]"), w.focused()
    # Enter on a finding opens its file, selects the block and puts the focus on the key's widget
    w.key("enter")
    assert w.session.current == MAIN and w.session.model.selected.name == "Top_Bar" and w.region() == 2
    assert any("form_item[k:Width#" in i for i in w.focused()), w.focused()
    # Ctrl+Shift+A switches Apply as I edit on: from now on every commit is written
    w.key("a", ctrl=True, shift=True)
    assert w.vm.apply_on_edit.get() is True and (tmp_path / "state" / "settings.json").exists()
    assert main.read_bytes() == original
    # Duplicate with the shortcut: written at once, and checked
    checks = len([c for c in fake_shell.calls() if c.startswith("check")])
    w.key("d", ctrl=True, shift=True)
    assert b"_Copy" in main.read_bytes() and not w.vm.dirty.get()
    assert len([c for c in fake_shell.calls() if c.startswith("check")]) == checks + 1
    # Ctrl+Z undoes it and the file is written again
    w.key("z", ctrl=True)
    assert main.read_bytes() == original
    # Ctrl+Shift+A off, Ctrl+Z / Ctrl+Y: nothing is written until Ctrl+S
    w.key("a", ctrl=True, shift=True)
    assert w.vm.apply_on_edit.get() is False
    w.key("y", ctrl=True)
    assert main.read_bytes() == original and w.vm.dirty.get()
    w.key("s", ctrl=True)
    assert b"_Copy" in main.read_bytes() and w.vm.status.get() == f"Saved {MAIN}"
    # Ctrl+Shift+R: no shell is running, it says so; then it is running and the answer is shown
    w.key("r", ctrl=True, shift=True)
    assert "No shell is running" in w.vm.status.get() and not [c for c in fake_shell.calls() if c.startswith("reload")]
    fake_shell.answer("status", (RECORDED / "status_running.json").read_text())
    w.vm.services.refresh_status()
    w.key("r", ctrl=True, shift=True)
    assert w.vm.status.get().startswith("Reloaded") and [c for c in fake_shell.calls() if c.startswith("reload")] == ["reload"]
    # another program changes the file: the banner asks, Ctrl+Shift+L takes the disk's version, Ctrl+Shift+U keeps ours
    external = main.read_text().replace("Edge: TOP", "Edge: BOTTOM")
    main.write_text(external)
    w.vm.services.disk_events({MAIN: main.read_bytes()})
    w.settle()
    assert w.vm.has_disk_change.get() and {"disk_banner", "disk_reload_button", "disk_keep_button"} <= {i.name for i in w.built.view.handle.composition.walk() if i.name}
    w.key("l", ctrl=True, shift=True)
    assert w.session.model.text == external and not w.vm.has_disk_change.get() and w.vm.text.get() == external
    w.vm.text.set(external + "# mine\n")
    w.vm.text_edited()
    main.write_text(external + "# theirs\n")
    w.vm.services.disk_events({MAIN: main.read_bytes()})
    w.key("u", ctrl=True, shift=True)
    assert not w.vm.has_disk_change.get() and w.session.model.dirty and main.read_text().endswith("# theirs\n")
    w.key("s", ctrl=True)
    assert main.read_text().endswith("# mine\n")


def test_a_live_window_starts_the_watch_and_close_stops_it(folder, tmp_path, fake_shell, schema):
    session = ConfigSession(folder, schema, ShellCommand(str(fake_shell.path)), state_dir=tmp_path / "state")
    built = build(session, reduced_motion=True, live=True)
    try:
        assert built.viewmodel.services.watch is not None and built.viewmodel.services.watch.running
    finally:
        started = time.monotonic()
        built.close()
    assert built.viewmodel.services.watch is None and time.monotonic() - started < 3
