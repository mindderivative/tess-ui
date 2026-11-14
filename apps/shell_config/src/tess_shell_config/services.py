"""What the window does with the shell command and the disk: `check` and the problems list, the status line, reload, "Apply as I edit", saving, and the file watch.

`Services(viewmodel)` puts its Signals and handlers on the ViewModel the way the form and the structure actions do (`problems`, `check_run`, `shell_state`, `apply_on_edit`, `disk_message`,
`disk_reload`, ...). Every command (`check`, `status`, `reload`) goes through an offload: on a worker thread, answered on the loop thread, so no command ever runs inside a frame. A window that
is not running (a test) is given an `InlineOffload` instead and everything happens at once.

The rules, from the specification:

- `check` runs after a save, never on the UI thread, with the command's 10 s timeout. A run that fails or times out is one message in the list; editing goes on. A run asked for while one is going
  is run once more when it ends.
- "Apply as I edit": after each commit (a form value, a structure edit, undo, redo, format) the file is written; typing in the text view is written once it stops (200 ms) and only when it parses.
  Every write is the same atomic save, the first of a file keeps the old content in the state folder. `reload` is asked of the shell after a save only when the last `status` said it is running and the
  setting is on; the Reload button asks it when it is running.
- A change of an open file on disk by another program is never overwritten: the watch posts it, a banner asks Reload or Keep, and a save of that file is refused until one is chosen.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from tess_ui import Signal, batch

from tess_shell_config.files import ChangedOnDisk, SaveError
from tess_shell_config.problems import failure_rows, locate, relative_to_folder, rows_for, title_for
from tess_shell_config.settings import Settings
from tess_shell_config.shell import CheckResult, InlineOffload, Offload, ShellCommandError, Status
from tess_shell_config.watcher import FileWatch

if TYPE_CHECKING:
    from tess_shell_config.viewmodel import ShellConfigViewModel

__all__ = ["Services", "TEXT_SAVE_DELAY_MS"]

#: How long typing in the text view rests before "Apply as I edit" writes it.
TEXT_SAVE_DELAY_MS = 200


class Services:
    """One per window. `viewmodel.session.shell` is the command layer (it may be `None`: then nothing here runs a command)."""

    def __init__(self, viewmodel: ShellConfigViewModel) -> None:
        self.vm = viewmodel
        self.session = viewmodel.session
        self.settings = Settings(self.session.state_dir)
        self.offload: Any = InlineOffload()
        self.timer: Callable[[int, Callable[[], None]], Any] | None = None  # `window.after(ms, fn)`, set when the window exists
        self.watch: FileWatch | None = None
        self.problems = Signal([])
        self.problems_title = Signal(title_for(None, False, False))
        self.has_problems = Signal(False)
        self.checking = Signal(False)
        self.shell_state = Signal("Shell: not asked yet")
        self.shell_running = Signal(False)
        self.apply_on_edit = Signal(self.settings.apply_as_i_edit)
        self.disk_message = Signal("")
        self.has_disk_change = Signal(False)
        self.last_check: CheckResult | None = None
        self.last_status: Status | None = None
        self._check_failed = False
        self._check_again = False
        self._text_generation = 0
        self._pending_disk: dict[str, bytes] = {}
        self._findings: list[Any] = []
        for name, signal in {"problems": self.problems, "problems_title": self.problems_title, "has_problems": self.has_problems, "checking": self.checking, "shell_state": self.shell_state,
                             "shell_running": self.shell_running, "apply_on_edit": self.apply_on_edit, "disk_message": self.disk_message, "has_disk_change": self.has_disk_change}.items():
            setattr(viewmodel, name, signal)
        for name, handler in {"check_run": self.request_check, "problem_pick": self.pick_problem, "shell_reload": self.reload_shell, "disk_reload": self.disk_reload, "disk_keep": self.disk_keep,
                              "apply_changed": self.apply_changed}.items():
            setattr(viewmodel, name, handler)

    # -- starting and stopping ---------------------------------------------------------------------------------------------------

    def start(self, post: Callable[[Callable[[], None]], Any], timer: Callable[[int, Callable[[], None]], Any] | None = None) -> None:
        """Go live: commands run on worker threads and are answered through `post` (a function that runs a callable on the loop thread), the folder is watched, and the first `status` and `check` are asked."""
        self.offload = Offload(post)
        self.timer = timer
        self.watch = FileWatch(self.session.folder, post, self.disk_events, self._watch_failed)
        self.watch.start()
        self.refresh_status()
        self.request_check()

    def stop(self) -> None:
        if self.watch is not None:
            self.watch.stop()
            self.watch = None

    # -- check and the problems list -----------------------------------------------------------------------------------------------

    def request_check(self) -> None:
        """Run `check` on the folder as it is on disk. One at a time: a request made while one runs is run again when it ends."""
        shell = self.session.shell
        if shell is None:
            return
        if self.checking.get():
            self._check_again = True
            return
        self.checking.set(True)
        self.problems_title.set(title_for(self.last_check, self._check_failed, True))
        folder = self.session.folder
        self.offload.submit(lambda: shell.check(folder), self._checked, self._check_not_run)

    def _checked(self, result: CheckResult) -> None:
        self.last_check, self._check_failed = result, False
        self._findings = list(result.findings)
        self._check_done(rows_for(result))

    def _check_not_run(self, error: BaseException) -> None:
        self._check_failed = True
        self._findings = []
        self._check_done(failure_rows(str(error) if isinstance(error, ShellCommandError) else f"The check failed: {error}"))

    def _check_done(self, rows: list[dict[str, Any]]) -> None:
        def apply() -> None:
            self.checking.set(False)
            self.problems.set(rows)
            self.has_problems.set(bool(rows))
            self.problems_title.set(title_for(self.last_check, self._check_failed, False))

        batch(apply)
        if self._check_again:
            self._check_again = False
            self.request_check()

    def pick_problem(self, index: Any) -> None:
        """A finding was clicked (or Enter on it): open its file, select the block it points at and show the key."""
        try:
            number = int(index)
            finding = self._findings[number] if number >= 0 else None
        except (ValueError, IndexError, TypeError):
            return
        if finding is None:  # the row of a message (the check did not run, findings left out) points at nothing
            return
        vm, session = self.vm, self.session
        rel = relative_to_folder(finding.file, session.folder)
        if not any(f.rel == rel for f in session.files):
            vm._say(f"{finding.file} is not a file of {session.folder}.", error=True)
            return
        if session.current != rel or rel not in session.models:
            vm.open_file(rel)
        model = session.model
        if model is None or model.relative != rel:
            return
        if not model.valid:
            vm._say(f"{rel} has syntax errors, so there is no structure to select in: line {finding.line}, column {finding.column}: {finding.message}", error=True)
            return
        document = model.document
        assert document is not None
        place = locate(document, finding.line, finding.column)
        if place is None:
            vm._say(f"{rel}:{finding.line}:{finding.column} is not inside a block: {finding.message}", error=True)
            return
        model.select(place.path)
        vm._show(model, new_file=False)
        shown = place.key is not None and vm.form.reveal(place.key)
        if shown:
            vm.shortcuts.focus_form_key(place.key)  # type: ignore[union-attr, arg-type]
        else:
            vm.shortcuts.focus_structure_selection()  # type: ignore[union-attr]
        note = " The file has unsaved changes, so the place may have moved." if model.dirty else ""
        vm._say(f"{rel}:{finding.line}:{finding.column}: {finding.message}" + (f" ({finding.hint})" if finding.hint else "") + note)

    # -- the shell: status, reload -------------------------------------------------------------------------------------------------

    def refresh_status(self) -> None:
        """Ask `status --json` and show the answer in the status line: running (with the surfaces it shows), not running, or unknown when the command could not say."""
        shell = self.session.shell
        if shell is None:
            self.shell_state.set("Shell: unknown (no command)")
            return
        self.offload.submit(shell.status, self._status_known, self._status_unknown)

    def _status_known(self, status: Status) -> None:
        self.last_status = status
        running = status.running
        if running:
            surfaces = status.surfaces
            text = "Shell: running" + (f" ({', '.join(surfaces)} shown)" if surfaces else "")
        elif running is False:
            text = "Shell: not running (editing and checking still work)"
        else:
            text = "Shell: unknown (status did not say)"
        self._shell_known(text, bool(running))

    def _shell_known(self, text: str, running: bool) -> None:
        def apply() -> None:
            self.shell_state.set(text)
            self.shell_running.set(running)

        batch(apply)

    def _status_unknown(self, error: BaseException) -> None:
        self.last_status = None
        self._shell_known(f"Shell: unknown ({error})", False)

    def reload_shell(self) -> None:
        """The Reload button: ask the running shell to apply the files now. Saved files only: with unsaved changes it says so."""
        shell = self.session.shell
        if shell is None:
            self.vm._say("There is no shell command to ask.", error=True)
            return
        if not self.shell_running.get():
            self.vm._say("No shell is running, so there is nothing to reload.", error=True)
            return
        dirty = self.session.dirty()
        if dirty:
            self.vm._say("Unsaved changes are not in the files the shell reads: save " + ", ".join(dirty) + " first.", error=True)
            return
        self.vm._say("Asking the shell to reload...")
        self.offload.submit(shell.reload, self._reloaded, lambda error: self.vm._say(str(error), error=True))

    def _reloaded(self, result: Any) -> None:
        self.vm._say(("Reloaded: " if result.ok else "The shell did not reload: ") + result.message, error=not result.ok)
        self.refresh_status()

    # -- saving ---------------------------------------------------------------------------------------------------------------------

    def save(self, *, quiet: bool = False) -> bool:
        """Write the open file. Returns whether it was written. On success: the check runs, and the shell is asked to reload when it runs and "Apply as I edit" is on."""
        vm = self.vm
        model = self.session.model
        if model is None:
            vm._say("There is no open file to save.", error=True)
            return False
        if not model.dirty:
            if not quiet:
                vm._say(f"{model.relative} has no unsaved changes")
            return False
        try:
            self.session.save()
        except ChangedOnDisk as error:
            self._pending_disk[error.relative] = self.session.changed_on_disk(error.relative) or b""
            self._show_disk_change()
            vm._say(str(error), error=True)
            return False
        except SaveError as error:
            vm._say(str(error), error=True)
            return False
        vm._say(f"Saved {model.relative}")
        vm._flags(model)
        vm._relabel_files()
        self.request_check()
        self.refresh_status()
        if self.apply_on_edit.get() and self.shell_running.get() and self.session.shell is not None:
            self.reload_shell()
        return True

    def edited(self, *, typing: bool = False) -> None:
        """A commit happened (or, with `typing`, a text edit): with "Apply as I edit" on the file is written now, or for typing once it rests."""
        if not self.apply_on_edit.get():
            return
        model = self.session.model
        if model is None or not model.dirty or not model.valid:
            return
        if not typing or self.timer is None:
            self._text_generation += 1
            self.save(quiet=True)
            return
        self._text_generation += 1
        generation = self._text_generation
        self.timer(TEXT_SAVE_DELAY_MS, lambda: self._typed_rest(generation))

    def _typed_rest(self, generation: int) -> None:
        if generation == self._text_generation and self.apply_on_edit.get():
            model = self.session.model
            if model is not None and model.dirty and model.valid:
                self.save(quiet=True)

    def apply_changed(self, on: Any) -> None:
        """The "Apply as I edit" switch: remembered in the state folder. Switching it on writes what is unsaved at once."""
        on = bool(on)
        if on == self.settings.apply_as_i_edit:
            return
        if on != self.apply_on_edit.get():
            self.apply_on_edit.set(on)
        try:
            self.settings.set_apply_as_i_edit(on)
        except SaveError as error:
            self.vm._say(f"{error} The choice holds for this session only.", error=True)
        if on:
            self.vm._say("Apply as I edit is on: each change is written to the file and the running shell is asked to reload.")
            self.edited()
        else:
            self.vm._say("Apply as I edit is off: nothing is written until you save.")

    # -- the file watch -------------------------------------------------------------------------------------------------------------

    def disk_events(self, changes: Mapping[str, bytes | None]) -> None:
        """The watch saw `.tdl` files change (their bytes, or `None` when one is gone). Runs on the loop thread. The Files list is read again; an open file whose content is not what this application last
        read or wrote is a change by another program, and the banner asks."""
        vm = self.vm
        asked = False
        for rel, raw in changes.items():
            model = self.session.models.get(rel)
            if model is None or raw is None:
                continue
            if raw != model.disk_bytes:
                self._pending_disk[rel] = raw
                asked = True
            else:
                self._pending_disk.pop(rel, None)  # back to what we have: nothing to ask
        vm.refresh_files()
        if asked or self._pending_disk:
            self._show_disk_change()

    def _watch_failed(self, message: str) -> None:
        self.vm._say(message + " Changes made by other programs will not be noticed; a save still checks the file before it writes.", error=True)

    def _banner(self, text: str, shown: bool) -> None:
        def apply() -> None:
            self.disk_message.set(text)
            self.has_disk_change.set(shown)

        batch(apply)

    def _show_disk_change(self) -> None:
        if not self._pending_disk:
            self._banner("", False)
            return
        rel = next(iter(self._pending_disk))
        more = len(self._pending_disk) - 1
        dirty = self.session.models[rel].dirty
        text = (f"{rel} was changed on disk by another program" + (f" (and {more} more)" if more else "") + ". "
                + ("Reload takes the disk's version and drops your unsaved changes; Keep leaves your version, and a save then replaces the disk's." if dirty
                   else "Reload takes the disk's version; Keep leaves what is shown here, and a save then replaces the disk's."))
        self._banner(text, True)

    def disk_reload(self) -> None:
        """Banner: take the file from disk (the model's history starts over)."""
        if not self._pending_disk:
            return
        rel = next(iter(self._pending_disk))
        self._pending_disk.pop(rel, None)
        vm = self.vm
        try:
            model = self.session.reload(rel)
        except OSError as error:
            vm._say(f"Cannot read {rel}: {error.strerror or error}", error=True)
            self._show_disk_change()
            return
        if self.session.current == rel:
            vm._show(model, new_file=True)
        else:
            vm._relabel_files()
        vm._say(f"Reloaded {rel} from disk")
        self._show_disk_change()
        if vm.shortcuts is not None:
            vm.shortcuts.keep_focus()

    def disk_keep(self) -> None:
        """Banner: keep what this window has. The disk's content is remembered, so the same change does not ask again; a save writes over it, because the person chose that."""
        if not self._pending_disk:
            return
        rel = next(iter(self._pending_disk))
        self._pending_disk.pop(rel, None)
        self.session.keep(rel)
        self.vm._say(f"Kept your version of {rel}; the next save replaces the file on disk.")
        self._show_disk_change()
        if self.vm.shortcuts is not None:
            self.vm.shortcuts.keep_focus()
